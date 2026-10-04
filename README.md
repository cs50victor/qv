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

## Global preferences and daily coordinator

Two complete, copy-paste-ready instruction files are included; the templates are
kept below the repository root to avoid loading daily rules for qv workers:

| File | Install at | Applies to |
| --- | --- | --- |
| [global/AGENTS.md](global/AGENTS.md) | `~/.codex/AGENTS.md` | Development preferences in every project |
| [daily/AGENTS.md](daily/AGENTS.md) | `~/.daily/AGENTS.md` | Daily orchestration, visual artifacts, and brief chat |

Review existing destination files before replacing them, preserving any local
rules you need. If the global path is a symlink, writing through it also updates
its shared target. From this checkout:

```sh
mkdir -p ~/.codex ~/.daily
cp global/AGENTS.md ~/.codex/AGENTS.md
cp daily/AGENTS.md ~/.daily/AGENTS.md
codex --cd ~/.daily
```

In the Codex app, select `~/.daily` as the coordinator's project directory and
start a new conversation to load the files. Codex layers global and project
instructions; without a detected project root it checks only the current
directory, so start at `~/.daily` rather than assuming a nested folder inherits it.

The coordinator starts fresh Codex CLI processes in detached tmux sessions, with
both tmux and Codex working in the target project or its isolated workspace.
Workers never start in `~/.daily` or its descendants, including symlink aliases;
they load global development preferences and their target project's instructions.
They do not inherit the daily prompt or coordinator history through subagents,
forks, resumes, or forwarded developer instructions.

The coordinator maintains daily records and collects finished artifacts under
`~/.daily/artifacts/<task-id>/`. Substantive explanations become diagrams,
drawings, interactive HTML, or rendered Manim videos when motion helps; simple
answers and requested prose stay in chat. Preview support, steering, and worker
lifetimes depend on the runtime and are verified rather than promised.

For the optional voice interface, explicitly supply the daily coordinator prompt:

```sh
uv run voice.py --cwd ~/.daily --prompt ~/.daily/AGENTS.md
uv run voice.py --text --prompt ~/.daily/AGENTS.md
```

Use one interface at a time and the same prompt when switching. The default
`prompt.txt` retains the legacy native-subagent coordinator; use the daily file
for tmux workers and visual delivery.

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
