# /// script
# requires-python = ">=3.11"
# dependencies = ["openai[realtime]==3.19.2", "openai-codex==0.157.1", "sounddevice>=0.5,<0.6", "python-dotenv>=1.1,<2"]
# ///
"""GPT Live voice with a persistent Astra Codex orchestrator. Run: uv run voice.py

Switch between voice and CLI using the same conversation:
1. Stop voice with Ctrl+C. Its ID is printed as Codex: <thread-id> and saved
   beside this script in .state/thread.json after the first delegated request.
2. Run uv run voice.py --text to resume that thread with the current prompt.txt.
3. Exit the CLI, then run this script with the same --cwd to resume voice.
Do not use --new when switching; it starts a different conversation.
Use one interface at a time. This resumes history, not the prior audio session.
"""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

RATE, FRAMES = 24000, 480
HERE = Path(__file__).resolve().parent


class Playback:
    def __init__(self):
        self.buffer = bytearray()
        self.lock = threading.Lock()
        self.last_packet = 0.0
        self.buffering = True

    def append(self, audio):
        with self.lock:
            if len(self.buffer) + len(audio) > RATE * 2 * 10:
                raise RuntimeError("Speaker playback fell more than 10 seconds behind")
            self.buffer.extend(audio)
            self.last_packet = time.monotonic()

    def callback(self, outdata, frames, timing, status):
        with self.lock:
            # Preserve Queue's 400 ms startup/recovery reserve and short-tail release.
            if self.buffering and self.buffer and (
                len(self.buffer) >= RATE * 2 * .4 or time.monotonic() - self.last_packet >= .4
            ):
                self.buffering = False
            count = 0 if self.buffering else min(len(outdata), len(self.buffer))
            outdata[:] = bytes(self.buffer[:count]) + bytes(len(outdata) - count)
            del self.buffer[:count]
            if count < len(outdata):
                self.buffering = True


class Inbox:
    def __init__(self):
        self.fragments = []
        self.seen = set()
        self.changed = asyncio.Event()
        self.requests = asyncio.Queue()

    def observe(self, event):
        if event.type == "session.input_transcript.delta":
            self.fragments.append((event.start_ms, event.delta))
            self.changed.set()
        elif event.type == "session.delegation.created" and event.delegation.target == "client":
            if event.delegation.id not in self.seen:
                self.seen.add(event.delegation.id)
                self.requests.put_nowait((event.delegation.id, event.offset_ms))

    async def take(self, offset):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), .35)
            except TimeoutError:
                if any(start <= offset for start, _ in self.fragments):
                    break
        text = "".join(text for start, text in self.fragments if start <= offset).strip()
        self.fragments = [(start, text) for start, text in self.fragments if start > offset]
        return text


def chunks(text, size=450):
    while text:
        chunk = text.encode()[:size].decode(errors="ignore")
        yield chunk
        text = text[len(chunk):]


class Bridge:
    def __init__(self, thread, connection, save_state):
        self.thread, self.connection = thread, connection
        self.save_state = save_state
        self.inbox = Inbox()
        self.turn = None
        self.delegation = None

    async def say(self, text):
        await self.connection.session.commentary.append(
            delegation_id=self.delegation, content=next(chunks(text)))

    async def result(self, text):
        for chunk in list(chunks(text))[:20]:
            await self.connection.session.thinking.append(delegation_id=None, content=chunk)
        await self.say("Give a brief spoken summary of the verified result just supplied. "
                       "The full result remains in the Codex conversation.")

    async def consume(self):
        final, status = "", None
        try:
            async for event in self.turn.stream():
                if event.method == "item/completed":
                    item = event.payload.item.root
                    if item.type == "agentMessage":
                        print(f"\nCodex: {item.text}", flush=True)
                        phase = getattr(item.phase, "value", item.phase)
                        if phase == "commentary":
                            await self.say(item.text)
                        else:
                            final = item.text
                elif event.method == "turn/completed":
                    status = event.payload.turn.status.value
            if status == "completed":
                await self.result(final or "The coordinator turn ended without a text response. Do not infer task completion.")
            else:
                await self.say("The Codex turn stopped before completion. I need to inspect task status before claiming success.")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"\nCodex error: {exc}", file=sys.stderr)
            await self.say("Codex encountered an error. No actions were automatically replayed.")
        finally:
            self.turn = None

    async def run(self):
        incoming = asyncio.create_task(self.inbox.requests.get())
        consumer = None
        try:
            while True:
                done, _ = await asyncio.wait(
                    [incoming] + ([consumer] if consumer else []),
                    return_when=asyncio.FIRST_COMPLETED)
                if consumer and consumer in done:
                    consumer.result()
                    consumer = None
                if incoming in done:
                    self.delegation, offset = incoming.result()
                    incoming = asyncio.create_task(self.inbox.requests.get())
                    text = await self.inbox.take(offset)
                    if not text:
                        await self.say("I missed the words for that request. Please repeat it.")
                        continue
                    try:
                        if self.turn:
                            await self.turn.steer(text)
                        else:
                            if consumer:
                                await consumer
                            self.turn = await self.thread.turn(text)
                            self.save_state()
                            consumer = asyncio.create_task(self.consume())
                    except Exception as exc:
                        print(f"\nCodex request error: {exc}", file=sys.stderr)
                        await self.say("I couldn't deliver that request to Codex. I haven't retried it automatically.")
        finally:
            if self.turn:
                try:
                    await asyncio.wait_for(self.turn.interrupt(), 5)
                except Exception:
                    pass
            incoming.cancel()
            if consumer:
                consumer.cancel()
            await asyncio.gather(incoming, *([consumer] if consumer else []), return_exceptions=True)


async def voice(args, prompt):
    import sounddevice as sd
    from openai import AsyncOpenAI
    from openai_codex import AsyncCodex, ApprovalMode, CodexConfig, Sandbox

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    timer = loop.call_later(args.duration, stop.set) if args.duration else None
    state_path = HERE / ".state/thread.json"
    tasks = []
    try:
        async with AsyncCodex(config=CodexConfig(cwd=str(args.cwd))) as codex:
            options = dict(model="gpt-6-astra", cwd=str(args.cwd),
                           sandbox=Sandbox.full_access, approval_mode=ApprovalMode.deny_all,
                           config={"features.multi_agent": True},
                           developer_instructions=prompt + "\nYou are the Codex reasoning orchestrator. "
                           "GPT Live handles audio. You receive transcripts; do not claim to hear audio. "
                           "Use native Codex subagents for substantial work, not Queue desktop MCP tools. "
                           "Keep your own turns short so the user can keep talking. "
                           "All task status claims require verified evidence.")
            if state_path.exists():
                saved = json.loads(state_path.read_text())
                if saved["cwd"] != str(args.cwd):
                    raise RuntimeError("Saved conversation uses another directory. Use --new for a fresh conversation.")
                thread = await codex.thread_resume(saved["thread_id"], **options)
            else:
                thread = await codex.thread_start(ephemeral=False, **options)
            def save_state():
                state_path.parent.mkdir(mode=0o700, exist_ok=True)
                temporary = state_path.with_suffix(".tmp")
                temporary.write_text(json.dumps({"thread_id": thread.id, "cwd": str(args.cwd)}))
                temporary.chmod(0o600)
                temporary.replace(state_path)
            print(f"Codex: {thread.id} | {args.cwd}", flush=True)
            async with AsyncOpenAI() as client, client.live.connect() as connection:
                bridge = Bridge(thread, connection, save_state)
                playback = Playback()
                audio = asyncio.Queue(maxsize=100)
                fault = None
                closed = False

                def enqueue(data, status):
                    nonlocal fault
                    if stop.is_set():
                        return
                    if status or audio.full():
                        fault = RuntimeError(f"Microphone interrupted: {status or 'queue full'}")
                        stop.set()
                    else:
                        audio.put_nowait(data)

                def capture(data, frames, timing, status):
                    loop.call_soon_threadsafe(enqueue, bytes(data), status)

                async def send():
                    while True:
                        await connection.session.input_audio.append(
                            audio=base64.b64encode(await audio.get()).decode())

                async def receive():
                    nonlocal closed
                    async for event in connection:
                        bridge.inbox.observe(event)
                        if event.type == "session.output_audio.delta" and not args.check:
                            playback.append(base64.b64decode(event.delta))
                        elif event.type in {"session.input_transcript.delta", "session.output_transcript.delta"}:
                            print(event.delta, end="", flush=True)
                        elif event.type == "error":
                            raise RuntimeError(event.error.message)
                        elif event.type == "session.closed":
                            closed = True
                            print(f"\nVoice closed: {event.usage.seconds}s", flush=True)
                            return
                    raise RuntimeError("Voice connection ended without a session.closed event")

                await connection.session.start(session={
                    "model": "gpt-live-1",
                    "instructions": prompt + "\nYou are GPT Live, the voice interface. "
                    "Delegate actions, research, task coordination and missing context to Astra through client delegation. "
                    "Astra has a persistent Codex conversation and native subagents. "
                    "Keep listening while it works. Speak briefly, allow interruptions, and never invent task results. "
                    "Do not repeat completed actions on restart; ask the backend to recover context when necessary.",
                    "audio": {"format": {"type": "audio/pcm", "rate": RATE}, "output": {"voice": "marin"}},
                    "delegation": {"type": "client"},
                })
                event = await asyncio.wait_for(connection.recv(), 30)
                if event.type != "session.started":
                    raise RuntimeError(f"Voice did not start: {event.model_dump_json()}")
                print("Voice ready: GPT Live → Astra. Ctrl+C to quit.", flush=True)
                receiver = asyncio.create_task(receive())
                waiter = asyncio.create_task(stop.wait())
                tasks = [receiver, waiter]
                try:
                    if args.check:
                        stop.set()
                    else:
                        with sd.RawOutputStream(samplerate=RATE, channels=1, dtype="int16",
                                                blocksize=FRAMES, callback=playback.callback), \
                             sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16",
                                               blocksize=FRAMES, callback=capture):
                            tasks.extend([asyncio.create_task(send()), asyncio.create_task(bridge.run())])
                            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                            for task in done:
                                task.result()
                finally:
                    stop.set()
                    for task in tasks[1:]:
                        task.cancel()
                    await asyncio.gather(*tasks[1:], return_exceptions=True)
                    try:
                        if not closed:
                            await connection.session.close()
                            await asyncio.wait_for(asyncio.shield(receiver), 15)
                    finally:
                        receiver.cancel()
                        await asyncio.gather(receiver, return_exceptions=True)
                if fault:
                    raise fault
    finally:
        if timer:
            timer.cancel()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


def resume_text(prompt):
    state_path = HERE / ".state/thread.json"
    if not state_path.exists():
        raise RuntimeError("No saved voice conversation yet. Send a request in voice mode first.")
    saved = json.loads(state_path.read_text())
    cwd = Path(saved["cwd"]).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("Saved working directory is not a directory")
    return subprocess.run([
        "codex", "resume", saved["thread_id"], "--cd", str(cwd),
        "--model", "gpt-6-astra", "--enable", "multi_agent",
        "--config", "developer_instructions=" + json.dumps(prompt, ensure_ascii=False),
    ], check=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Codex working directory for voice; text uses the saved directory")
    parser.add_argument("--prompt", type=Path, default=HERE / "prompt.txt")
    parser.add_argument("--text", action="store_true", help="Resume the saved thread in Codex CLI with the current prompt")
    parser.add_argument("--new", action="store_true", help="Start a fresh Codex conversation")
    parser.add_argument("--check", action="store_true", help="Billable connection check, without microphone or speaker")
    parser.add_argument("--duration", type=float, help="Stop voice after this many seconds")
    args = parser.parse_args()
    if args.text and (args.new or args.check or args.duration is not None):
        parser.error("--text cannot be combined with --new, --check, or --duration")
    if not args.text:
        from dotenv import load_dotenv
        load_dotenv(HERE / ".env")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            print("Missing OPENAI_API_KEY. Set it in your environment or .env next to voice.py.", file=sys.stderr)
            return 1
    try:
        prompt = args.prompt.read_text().strip()
        if not prompt:
            raise ValueError("Prompt file is empty")
        if args.text:
            return resume_text(prompt)
        args.cwd = args.cwd.resolve(strict=True)
        if not args.cwd.is_dir():
            raise ValueError("--cwd must be a directory")
        if args.duration is not None and args.duration <= 0:
            raise ValueError("--duration must be positive")
        if args.new:
            (HERE / ".state/thread.json").unlink(missing_ok=True)
        asyncio.run(voice(args, prompt))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
