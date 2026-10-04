# Queue Voice

One `uv` script and an editable `prompt.txt`: GPT Live (`gpt-live-1`, Marin) handles
voice; Astra (`gpt-6-astra`) coordinates through Codex and delegates research and
deliverable work to independent Codex CLI workers in detached tmux sessions.
No desktop app, Rust build, or custom MCP server.

Requires `uv`, `tmux`, Codex CLI 0.151+ with a signed-in account, an OpenAI API key with
GPT Live access, and a microphone. Use headphones.

```sh
export OPENAI_API_KEY="your-key"
uv run voice.py --cwd /path/to/project
```

Alternatively put `OPENAI_API_KEY=...` in `.env` beside the script. A missing/empty
key exits with status 1 before creating a client or opening audio. Codex uses its
existing authentication. The script retains Queue's full-access/no-approval mode.

The default coordinator prompt is `prompt.txt`; `--prompt /path/to/file` selects
another coordinator prompt. Edit the selected file and restart to apply changes.
GPT Live receives voice-interface instructions and forwards tool actions and
research to Astra. Ctrl+C closes voice and the SDK.
The Codex conversation ID is saved in ignored `.state/thread.json`; subsequent
runs resume it. `--new` starts a fresh conversation without deleting Codex history.
Do not run two copies against the same state file. The script does not manage
tmux worker lifetimes or promise work continues after exit.

`uv run voice.py --check` tests the Live connection without microphone/speaker
access; it opens a billable session. `--duration 30` limits a voice session to 30
seconds. API access and Codex authentication are separate requirements.

`~/.daily` is created by the agent only when work needs recording. Daily notes stay
at `~/.daily/YYYY/MM/DD.md`; completion notices use checkboxes in
`~/.daily/YYYY/MM/DD/notifications.md`, dated by local notification/completion time.
Workers may append assigned notices with completion/task IDs, timestamps, observed
outcomes, and result links; canonical records remain yours. On receipt/read, you
review notices, verify results, and record follow-up scope before proactively
assigning needed authorized investigation, validation, and reversible follow-through
to the responsible worker in its existing session. Continue authorized dependent
work once prerequisites are verified, without waiting for a status request.
Check off handled notices after recording outcomes and follow-through; checked
does not mean the goal or downstream actions are complete. Older unresolved notices
carry forward by link and are reviewed on resume/status.

When an action needs authorization, have workers finish authorized research and
prepare the reviewable draft/recipient/channel/supporting facts or payload/target
and evidence first. Only that action waits; valid existing authorization carries
forward. Sending a message requires explicit authorization. Keep verified findings,
prepared actions, completed steps, remaining decisions/authorization, blockers,
and next actions in records/artifacts; describe outstanding research honestly and
link details from brief status replies.

Notice production and wake-up delivery are separate. With the standalone watcher
active, workers append notices and do not also enqueue them. The watcher sends only
`Check notifications file: <absolute notice path under the resolved daily root>`;
details stay in the file. The watcher resolves the root, then constructs
`YYYY/MM/DD/notifications.md`; it does not resolve day/file symlinks. Journal sync
and automatic voice announcements are not implemented.

### Notification watcher

From your coordinator's own native shell tool, validate `CODEX_THREAD_ID` as a UUID
and compare verified current-thread metadata when available. Missing, malformed, or
conflicting identity blocks launch. Capture it before tmux; never substitute a worker
ID, recent rollout, or session-tree-root `CODEX_SESSION_ID`. Obtain any required
owning-server endpoint from the known connection and check `codex queue --help` in
the actual launch environment.

Record the watcher owner, resolved daily root/script, target, tmux target, and
writable log path before launch. Use at most one notification watcher total in
detached tmux, targeting your coordinator thread only. Workers append notices and
never start watchers. This watcher owns the shared daily root; unknown existing
ownership blocks another. After these checks, replace the checkout
and log paths below. The shell guard checks absence only; UUID and metadata
validation are preceding coordinator steps, not implemented by this snippet:

```sh
coordinator_thread_id="${CODEX_THREAD_ID:?current coordinator tool ID is required}"
tmux new-session -d -s qv-notifications -c /path/to/qv \
  sh -c 'exec uv run watch_notifications.py --thread "$1" >"$2" 2>&1' \
  sh "$coordinator_thread_id" /path/to/qv-notifications.log
```

The detached shell receives the captured ID as an argument. For a remote owning
server, add `--remote <owning-server-endpoint>` to the watcher command. qv prints SDK
`thread.id` at startup and saves it in `.state/thread.json` after the first request;
saved state must belong to the active invocation. CLI `/statusline` exposes
`thread-id` (legacy alias `session-id`); remote CLI `/status` can display its
connected address. These UI commands are separate from the model's shell-tool
identity lookup. The watcher supports `--daily-root` (default `~/.daily`) and
`--interval` (default 5 seconds).

The watcher checks immediately, then waits five seconds after each check by
default. Slow queue calls delay the next check. Each check follows the local date
and reads that day's `notifications.md` line count. A missing file is normal. A
changed count, or an existing file without a marker, causes
`codex queue --thread ID --message <short-file-pointer>`, with
`--remote` when supplied. The same day's `.notifications-enqueued-lines` persists
the last successfully enqueued count, shared across targets, and advances only
after queue exit 0. On retargeting, stop only your owned watcher and preserve the
marker; review unchecked notices independently of count. Failed enqueue leaves the
marker unchanged for the next ordinary check; failure to save
the marker after acceptance can cause a duplicate pointer. Same-count checkbox
edits do not ping. Resume/status review still handles unchecked or linked older
notices even when their count has not changed.

Queue exit 0 means acceptance, not consumption, evidence review, or task success.
Use an eligible loaded coordinator on its owning server; a stopped/unloaded parent
may not consume a pointer. Consumption does not establish a spoken announcement
through the qv voice relay. `voice.py` does not install or start the watcher, and no
Stop hook, hidden queue option, or API bridge is needed for it.

The user talks to one persistent coordinator throughout the day. Set daily goals,
change priorities, or ask "Where are we on today's goals?" The prompt tells Astra
to handle clock/date/timezone calls, available-evidence answers, and coordination
directly; delegate acquiring new facts and creating or changing deliverables/code,
including a one-source lookup. Explicit direction to act directly or run only a
specified command overrides routing defaults. Astra records goals and planned
launch metadata in `~/.daily` before dispatch, then observed IDs and actual results,
reviews evidence, and reports status by goal without worker-session switching.
This behavior is prompt-driven; the script does not implement a separate scheduler.
Work requests are recorded before switching scope; work-status replies and work-turn
reconciliation include earlier and deferred outcomes, including mixed answer/work
turns. Standalone clocks and available-evidence answers need no new task or worker;
only-command requests exclude unrelated record and worker actions.

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
drawings, interactive HTML, or rendered Manim videos when motion helps; answers
from available evidence and requested prose stay in chat. Preview support,
steering, and worker lifetimes depend on the runtime and are verified rather than promised.

Both `prompt.txt` and the daily template use the same delegation routing. Select
the daily coordinator prompt for its visual-delivery preferences:

```sh
uv run voice.py --cwd ~/.daily --prompt ~/.daily/AGENTS.md
uv run voice.py --text --prompt ~/.daily/AGENTS.md
```

Use one interface at a time and the same `--prompt` selection when switching;
omitting it selects `prompt.txt` in either interface. Both prompts keep daily
records under your ownership; workers keep intermediate workspace outputs, with
assigned notification appends and their directory and lock operations as the only
exception. All producers and acknowledgers use the same persistent
`.notifications.lock` beside that day's `notifications.md`,
opened in append mode and locked with Python standard-library
`fcntl.flock(handle, fcntl.LOCK_EX)`. Hold the handle while rereading/editing notices
and close it on completion or error; never unlink or replace the lock file. Worker
permissions must cover assigned notice-directory/lock operations on the first day
and at rollover. This is a prompt contract, with no installed locking helper.

## Switch between voice and CLI

1. Stop voice with Ctrl+C. Copy the ID printed as `Codex: <thread-id>`, or read
   `.state/thread.json` beside `voice.py` after the first delegated request.
2. Run `uv run voice.py --text` to continue the same conversation in Codex CLI.
   This reads the saved thread ID and working directory and explicitly supplies
   the selected coordinator prompt (default `prompt.txt`), including daily task
   tracking. Text mode explicitly tells Astra there is no audio or GPT Live relay and to respond
   in written Markdown. It uses Codex authentication and does not require
   `OPENAI_API_KEY`.
3. Exit the CLI, then run `uv run voice.py --cwd /path/to/project` with the same
   working directory to resume voice from that conversation.

Do not use `--new` when switching. Use one interface at a time. Conversation
history resumes; the previous audio session does not.

Plain `codex resume <thread-id>` does not read this repository's `prompt.txt`.
Use `--text` so prompt edits and daily-record instructions are explicitly applied
at each switch. It refuses to create a different thread if no saved ID exists.
