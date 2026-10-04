# Queue Voice

One `uv` script and an editable `prompt.txt`: GPT Live (`gpt-live-1`, Marin) handles
voice; Astra (`gpt-6-astra`) runs through Codex and delegates substantial work to
native Codex subagents. No desktop app, Rust build, or custom MCP server.

Requires `uv`, Codex CLI 0.151+ with a signed-in account, an OpenAI API key with
GPT Live access, and a microphone. Use headphones.

```sh
export OPENAI_API_KEY="your-key"
uv run voice.py --cwd /path/to/project
```

Alternatively put `OPENAI_API_KEY=...` in `.env` beside the script. A missing/empty
key exits with status 1 before creating a client or opening audio. Codex uses its
existing authentication. The script retains Queue's full-access/no-approval mode.

Edit `prompt.txt` and restart to apply changes. Ctrl+C closes voice and the SDK.
The Codex conversation ID is saved in ignored `.state/thread.json`; subsequent
runs resume it. `--new` starts a fresh conversation without deleting Codex history.
Do not run two copies against the same state file. Native agent lifetimes are owned
by Codex; the script does not promise work continues after exit.

`uv run voice.py --check` tests the Live connection without microphone/speaker
access; it opens a billable session. `--duration 30` limits a voice session to 30
seconds. API access and Codex authentication are separate requirements.

`~/.daily` is created by the agent only when work needs recording. Journal sync and
automatic idle task announcements are not implemented.

The user talks to one persistent coordinator throughout the day. Set daily goals,
change priorities, or ask "Where are we on today's goals?" The prompt tells Astra
to delegate execution, track dependencies and worker IDs in `~/.daily`, verify
results, and report status by goal without requiring worker-session switching.
This behavior is prompt-driven; the script does not implement a separate scheduler.

## Daily visual workspace

[`AGENTS.md`](AGENTS.md) is the complete, concise prompt for the daily coordinator,
combining visual explanations with evidence, tool, engineering, coordination,
and verification preferences; it does not require the dev-preferences skill.
Copy its contents into `~/.daily/AGENTS.md` and select `~/.daily` as the Codex app
project directory, or start the CLI there:

```sh
mkdir -p ~/.daily
cp AGENTS.md ~/.daily/AGENTS.md
codex --cd ~/.daily
```

Inspect any existing destination file before replacing it. Keep these instructions
in the daily workspace, not in your global `~/.codex/AGENTS.md`; sessions elsewhere
retain their existing guidance. Start a new conversation to load the new file.
Codex loads project guidance from the project root to the current directory;
without a detected project root it checks only the current directory, so start
from `~/.daily` rather than assuming a nested folder inherits this file.

Substantive explanations become diagrams, drawings, interactive HTML, or rendered
Manim videos when motion helps; simple answers and requested prose stay in chat.
Artifacts and sources live in `~/.daily/artifacts/<task-id>/`, linked from the task
record. Actual preview support, steering, and worker lifetimes depend on the
runtime; the prompt reports unverified behavior.

For the optional voice interface, explicitly supply the same daily prompt:

```sh
uv run voice.py --cwd ~/.daily --prompt ~/.daily/AGENTS.md
uv run voice.py --text --prompt ~/.daily/AGENTS.md
```

Use one interface at a time and the same prompt when switching. The default
`prompt.txt` retains qv's existing voice coordinator; it does not install these
visual preferences globally.

## Switch between voice and CLI

1. Stop voice with Ctrl+C. Copy the ID printed as `Codex: <thread-id>`, or read
   `.state/thread.json` beside `voice.py` after the first delegated request.
2. Run `uv run voice.py --text` to continue the same conversation in Codex CLI.
   This reads the saved thread ID and working directory and explicitly supplies
   the current `prompt.txt`, including `~/.daily` goals and task tracking. Text
   mode explicitly tells Astra there is no audio or GPT Live relay and to respond
   in written Markdown. It uses Codex authentication and does not require
   `OPENAI_API_KEY`.
3. Exit the CLI, then run `uv run voice.py --cwd /path/to/project` with the same
   working directory to resume voice from that conversation.

Do not use `--new` when switching. Use one interface at a time. Conversation
history resumes; the previous audio session does not.

Plain `codex resume <thread-id>` does not read this repository's `prompt.txt`.
Use `--text` so prompt edits and daily-record instructions are explicitly applied
at each switch. It refuses to create a different thread if no saved ID exists.
