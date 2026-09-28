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

## Switch between voice and CLI

1. Stop voice with Ctrl+C. Copy the ID printed as `Codex: <thread-id>`, or read
   `.state/thread.json` beside `voice.py` after the first delegated request.
2. Run `codex resume <thread-id>` to continue the same conversation by typing.
3. Exit the CLI, then run `uv run voice.py --cwd /path/to/project` with the same
   working directory to resume voice from that conversation.

Do not use `--new` when switching. Use one interface at a time. Conversation
history resumes; the previous audio session does not.
