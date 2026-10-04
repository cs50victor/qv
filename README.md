# Queue Voice

The voice script uses GPT Live (`gpt-live-1`, Marin) for audio and Astra
(`gpt-6-astra`) as the persistent Codex coordinator. Astra delegates research and
deliverable work to independent Codex CLI workers in detached tmux sessions.
A separate script watches completion notices.

Requires `uv`, `tmux`, a signed-in Codex CLI, an OpenAI API key with GPT Live access,
and a microphone. Use headphones. Watcher setup requires `CODEX_THREAD_ID` in the
coordinator's native shell and `codex queue` with `--thread`, `--message` and, when
needed, `--remote` in its launch environment.

```sh
export OPENAI_API_KEY="your-key"
uv run voice.py --cwd /path/to/project
```

Alternatively put `OPENAI_API_KEY=...` in `.env` beside the script. A missing/empty
key exits with status 1 before creating a client or opening audio. Codex uses its
existing authentication. Voice mode uses full filesystem access with no approval
prompts; CLI text mode uses its own configuration.

The default coordinator prompt is `prompt.txt`; `--prompt /path/to/file` selects
another coordinator prompt. Edit the selected file and restart to apply changes.
GPT Live receives separate voice-interface instructions and forwards explanation
requests, tool actions, research, deliverables and coordination to Astra. Ctrl+C
closes voice and the SDK.
The Codex conversation ID is saved in ignored `.state/thread.json`; subsequent
runs resume it. `--new` starts a fresh conversation without deleting Codex history.
Do not run two copies against the same state file. The script does not manage
tmux worker lifetimes or promise work continues after exit.

`uv run voice.py --check` tests the Live connection without microphone/speaker
access; it opens a billable session. `--duration 30` limits a voice session to 30
seconds. API access and Codex authentication are separate requirements.

## Coordinator guide

[Daily coordinator](daily/AGENTS.md) is the single guide for work: record the
outcome, assign an independent worker, review evidence, update the checklist and
back up. It includes direct/only-command exceptions and quiet notification
preparation. Technical procedures are in focused runbooks, loaded when needed:

- [Records, checklist and backups](daily/runbooks/daily-records.md)
- [Workers and completion notices](daily/runbooks/workers-and-notices.md)
- [Watcher identity and delivery](daily/runbooks/notification-delivery.md)
- [Captured message review](daily/runbooks/actionable-notifications.md)

The default `prompt.txt` is now a short entry point that tells the coordinator to
read the installed `~/daily/AGENTS.md`. `voice.py` reads only the selected prompt;
it does not expand links, copy instructions or launch services. Install the guide,
runbooks and template together before using the default prompt for work. Report
missing paths and use existing installation authorization to restore them from
the verified checkout; no repeated approval is needed.

Review destination files and preserve local edits before updating them. These
commands are for an intentional installation from this checkout; a symlinked
destination also changes its target. Global development preferences remain
separate from coordinator instructions:

```sh
mkdir -p ~/.codex ~/daily/runbooks
cp global/AGENTS.md ~/.codex/AGENTS.md
cp daily/AGENTS.md ~/daily/AGENTS.md
cp daily/runbooks/*.md ~/daily/runbooks/
cp daily/main.template.html ~/daily/main.template.html
```

Runbook links are relative to the guide's directory, so they resolve both in the
source tree and after installation. Scripts stay in the verified qv checkout;
installing documentation does not configure collectors or watchers. Sync reviewed
changes as a set, preserving local rules; do not update only the entry point.

Start the daily coordinator with `codex --cd ~/daily`, or select `~/daily` in the
Codex app and start a conversation there. Global preferences apply alongside the
local guide. Workers start in their own project/worktree outside `~/daily` and
load that project's instructions, not this coordinator's history. If a legacy
`~/.daily` alias exists, keep it pointing at `~/daily`, not a second writable copy.

For voice or text mode, the installed guide can also be selected explicitly:

```sh
uv run voice.py --cwd ~/daily --prompt ~/daily/AGENTS.md
uv run voice.py --text --prompt ~/daily/AGENTS.md
```

Use one interface at a time and the same prompt selection when switching. Daily
coordination prefers useful visual artifacts for explanations unless prose or
another format is requested. Worker/session and preview support must be verified
in the actual runtime.

## Daily checklist

Copy [main.template.html](daily/main.template.html) for a day page. Replace the
date placeholder, four labeled examples and self-contained anchors with real task
records. Its colored legend filters by status; All restores the list. Checkboxes
are read-only and derive from `data-status`; there is no browser storage.

Open local HTML in a browser. The Tailwind Play CDN is for development; inline CSS
preserves the page without it. Filtering and native indeterminate states need
JavaScript. [Browser evidence and preview](daily/main.template.validation.md)
describe the tested template. GitHub blob pages show source, not a live preview.
Do not publish private daily pages to Pages or external renderers.

## Notification delivery

By default, the standalone watcher queues completion-file pointers. The optional
`--notification-state` flag adds archive-inbox pointers to that same watcher.
Neither `voice.py` nor installing the guide starts it. Verify ownership and the
coordinator's thread/server using the delivery runbook before launch or reuse.

Captured messages support background research and response preparation; capture
needs a separate collector and sending requires explicit authorization. Queue
acceptance does not prove consumption, review or speech. Tests use synthetic
archives and fake queue calls, not live capture or DND/heartbeat evidence.

## Checks

```sh
uv run --no-project python -m unittest discover -s tests -v
```

## Switch between voice and CLI

1. Stop voice with Ctrl+C. Copy the ID printed as `Codex: <thread-id>`, or read
   `.state/thread.json` beside `voice.py` after the first delegated request.
2. Run `uv run voice.py --text --prompt /path/to/selected-prompt` to continue the
   same conversation, using the prompt selected for voice.
   This reads the saved thread ID and working directory and explicitly supplies
   the selected coordinator prompt (default `prompt.txt`), including daily task
   tracking. Text mode explicitly tells Astra there is no audio or GPT Live relay and to respond
   in written Markdown. It uses Codex authentication and does not require
   `OPENAI_API_KEY`.
3. Exit the CLI, then run
   `uv run voice.py --cwd /path/to/project --prompt /path/to/selected-prompt`
   with the same working directory and prompt to resume voice.

Do not use `--new` when switching. Use one interface at a time. Conversation
history resumes; the previous audio session does not.

Plain `codex resume <thread-id>` does not read this repository's `prompt.txt`.
Use `--text` so prompt edits and daily-record instructions are explicitly applied
at each switch. It refuses to create a different thread if no saved ID exists.
