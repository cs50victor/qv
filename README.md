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

`~/daily` is created by the agent only when work needs recording. Daily notes use
`~/daily/YYYY/MM/DD/main.html`. Each task has one canonical record at
`~/daily/YYYY/MM/DD/task/<task-id>.md` and artifacts under
`~/daily/YYYY/MM/DD/artifacts/<task-id>/`. Both stay under the task's local
start date; later daily notes link back.

Use [daily/main.template.html](daily/main.template.html) as a standalone starting
point. Replace `YYYY-MM-DD`, the four labeled example tasks and their self-contained
anchors with your date, tasks and record links. The colored legend filters by status;
All restores every row. Filtering needs JavaScript. It has examples of all four
agent-updated states: neutral
unchecked (not started), yellow indeterminate (in progress), green checked
(completed), and red unchecked with a blocked marker and visible reason (blocked).
Each row has a stable task ID and authoritative `data-status`; JavaScript derives
native checkbox properties and readable labels. The display is read-only, with no
browser storage or manual task mutation. Deferred work stays neutral with a note.
Keep useful notes, priorities, dependencies and history in expandable details or
linked canonical Markdown records, with the checklist visible first.

Both coordinator prompts require synchronization at lifecycle changes and before
status replies, backups and turn end, preserving routing and notice exceptions.
For an existing main.md, first save its exact bytes as a same-day history artifact,
link it from main.html, and verify task/history links before retiring the old main.
Re-read before replacement so concurrent edits survive. This repository supplies
instructions and a template, not a migration service or a persistence backend.

Open local HTML in a browser. GitHub repository blob pages display HTML source;
private repository authentication also prevents anonymous preview services from
being a suitable viewer. Do not deploy private daily pages to GitHub Pages or send
them to external renderers. Markdown task links remain ordinary file/repository
links, not an embedded Markdown viewer.

The template loads the [Tailwind v4 Play CDN](https://tailwindcss.com/docs/installation/play-cdn),
which Tailwind documents for development, not production hosting. Inline CSS keeps
the list, colors, notes and links usable if the CDN fails; the small local script
sets indeterminate properties and labels independently of the CDN. Without
JavaScript, CSS still shows status text and markers, and task links remain usable.

The [captured notification review](docs/actionable-notifications.md)
flow reads an existing archive and prepares actionable response drafts for review.
Capture requires a separate collector; sending requires explicit authorization.

Completion notices use checkboxes in
`~/daily/YYYY/MM/DD/notifications.md`, dated by local notification/completion time.
Workers append assigned notices with task and completion IDs, timestamps,
observed outcomes and result links, and return the actual completion-date notice
path in workspace results or captured output. The coordinator owns canonical
records and updates their links to that path during reconciliation. Subject to
the standalone-answer and only-command exceptions below, it reviews notices on
receipt or read in the indicated file, the current day's file and linked older
files. It verifies results and records follow-up scope before assigning necessary
authorized investigation, validation and reversible follow-through to the
responsible worker's existing session. Dependent work proceeds after prerequisite
verification, without waiting for a status request. Notices are checked off after
outcomes and follow-through are recorded; checked means handled, including failure
or blockage, not goal completion. Unresolved older notices stay linked for recovery.

Before asking for authorization, the coordinator has workers finish authorized
research and prepare the exact message draft, recipient, channel and supporting
facts, or the external action payload, target and evidence. Sending messages
requires explicit authorization. Existing authorization carries forward; only
the action awaiting approval pauses. The coordinator keeps findings, prepared
actions, remaining decisions, blockers and next actions in linked records and
reports status by goal.

Notice production and wake-up delivery are separate. With the standalone watcher
active, workers append notices and do not also enqueue them. By default, the watcher
sends only completion-file pointers:
`Check notifications file: <absolute notice path under the resolved daily root>`;
details stay in the file. The watcher resolves the root, then constructs
`YYYY/MM/DD/notifications.md`; it does not resolve day or file symlinks in the
pointer. The scripts do not implement journal sync or automatic voice
announcements; the daily prompt directs the coordinator to back up records.
With the opt-in `--notification-state` option, that same watcher also queues private
archive-inbox pointers after checking completion notices. See the
[capture setup and ownership requirements](docs/actionable-notifications.md).

### Notification watcher

Before its first worker dispatch and on work recovery, the coordinator inspects
all notification watchers. It reuses an owned watcher only if its daily root,
thread and server match the current configuration verified below. An owned
mismatch follows the retargeting rules below; unknown ownership blocks setup.
It launches only if none exists and prerequisites pass. Greetings, standalone
answers and only-command requests do not trigger setup. Blockers leave direct
notice review in place while other authorized work continues.

From the coordinator's own native shell tool, validate `CODEX_THREAD_ID` as a
UUID and compare verified current-thread metadata when available. Missing,
malformed, or conflicting identity blocks launch or reuse. Capture it before
tmux; never substitute a worker ID, recent rollout, or session-tree-root
`CODEX_SESSION_ID`. Obtain any required owning-server endpoint from known
connection metadata, or verify a matching default connection; record the source.
If neither can be established, block launch or reuse and review notices
directly. A thread ID or accepted queue message is not server evidence. Check
`codex queue --help` in the actual launch environment.

Before launch, verify write access for logs and day markers; record the watcher
owner, resolved daily root and script, thread and server target, tmux target,
and log path. Use at most one notification watcher total in detached tmux,
targeting only the coordinator thread. Workers append notices and never start
watchers. After these checks, replace the checkout and log paths below. The
shell guard checks absence only; UUID and metadata validation are preceding
coordinator steps, not implemented by this snippet:

```sh
coordinator_thread_id="${CODEX_THREAD_ID:?current coordinator tool ID is required}"
tmux new-session -d -s qv-notifications -c /path/to/qv \
  sh -c 'exec uv run watch_notifications.py --thread "$1" >"$2" 2>&1' \
  sh "$coordinator_thread_id" /path/to/qv-notifications.log
```

The detached shell receives the captured ID as an argument. For a remote owning
server, add `--remote <owning-server-endpoint>` to the watcher command. qv prints SDK
`thread.id` at startup and saves it in `.state/thread.json` after the first request;
saved state must belong to the active invocation. Printed or saved SDK thread IDs
do not identify the owning server: qv saves only the thread ID and working
directory and supplies no SDK endpoint-discovery recipe. If verified connection
metadata is unavailable, watcher setup remains blocked and the coordinator reviews
notices directly. The watcher supports `--daily-root` (default `~/daily`) and
`--interval` (default 5 seconds).

The watcher checks immediately, then waits five seconds after each check by
default. Slow queue calls delay the next check; each queue call has a 30-second
timeout. Each check follows the local date and reads that day's `notifications.md`
line count. A missing file is normal. A changed count, or an existing file without
a marker, causes
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
Use an eligible loaded coordinator on its owning server; a stopped or unloaded
coordinator may not consume a pointer. Consumption does not establish a spoken
announcement through the qv voice relay. `voice.py` does not install or start
the watcher.

The user talks to one persistent coordinator: set goals, change priorities or ask
for status without switching worker sessions. Both prompts have Astra handle
clock, date and timezone questions, available-evidence answers, setup and evidence
review directly. Acquiring new facts, validation and creating or changing code or
deliverables go to workers, including one-source lookups. Daily visual-artifact
requirements also apply to explanations based on available facts.

Explicit direct-execution or no-delegation requests override routing defaults.
Only-command requests exclude unrelated record, worker, watcher and notice
actions even when a pointer arrives; pending notices stay unchecked for the next
ordinary work turn. Standalone answers needing no artifact require no new task or
worker. Mixed answer and work turns require intake and reconciliation.

Astra records work on receipt before switching scope, records planned launch
metadata before dispatch and adds observed IDs and results afterward. Status and
end-of-work reconciliation cover earlier and deferred outcomes. This behavior is
prompt-driven; the script does not implement a scheduler.

## Global preferences and daily coordinator

Two complete, copy-paste-ready instruction files are included; the templates are
kept below the repository root to avoid loading daily rules for qv workers:

| File | Install at | Applies to |
| --- | --- | --- |
| [global/AGENTS.md](global/AGENTS.md) | `~/.codex/AGENTS.md` | Development preferences in every project |
| [daily/AGENTS.md](daily/AGENTS.md) | `~/daily/AGENTS.md` | Daily orchestration, visual artifacts, and brief chat |

qv's `daily/AGENTS.md` is the authoritative daily prompt source; sync reviewed
changes to the installed copy. It directs the coordinator to keep a native goal
active against evolving canonical records, coordinate through responsive bounded
waits, and verify private GitHub backups at meaningful checkpoints and before
ending work turns. Standalone-answer and only-command exceptions still apply.

To recover daily records, clone the authenticated user's private `daily`
repository into a separate directory, verify the recorded backup commit, then
restore needed files without overwriting newer local work. Only pushed contents
are recoverable this way; consult the recorded exclusions for ignored files and
external artifacts. Reconcile the recovered prompt with qv before installing it.

Review existing destination files before replacing them, preserving any local
rules you need. If the global path is a symlink, writing through it also updates
its shared target. From this checkout:

```sh
mkdir -p ~/.codex ~/daily
cp global/AGENTS.md ~/.codex/AGENTS.md
cp daily/AGENTS.md ~/daily/AGENTS.md
codex --cd ~/daily
```

In the Codex app, select `~/daily` as the coordinator's project directory and
start a new conversation to load the files. Codex layers global and project
instructions; without a detected project root it checks only the current
directory, so start at `~/daily` rather than assuming a nested folder inherits it.

The coordinator starts fresh Codex CLI processes in detached tmux sessions, with
both tmux and Codex working in the target project or its isolated workspace.
Workers never start in `~/daily` or its descendants, including symlink aliases;
they load global development preferences and their target project's instructions.
On installations migrated from the former `~/.daily` location, keep that path as
a compatibility symlink to `~/daily`, never a second writable copy. Existing links
and workers then reach the same records and persistent notification locks; the
worker-directory exclusion applies through that alias too.
They do not inherit the daily prompt or coordinator history through subagents,
forks, resumes, or forwarded developer instructions.

The daily coordinator collects verified finished artifacts under
`~/daily/YYYY/MM/DD/artifacts/<task-id>/` under the task's start date.
Substantive explanations use useful visual artifacts
unless the user requests prose or another format, even when the facts are already
available. Standalone answers needing no artifact stay in chat. The default prompt
does not require visuals. Preview support, steering and worker lifetimes depend on
the runtime and must be verified.

Both `prompt.txt` and the daily template use independent CLI workers. Select
the daily coordinator prompt for its visual-delivery preferences:

```sh
uv run voice.py --cwd ~/daily --prompt ~/daily/AGENTS.md
uv run voice.py --text --prompt ~/daily/AGENTS.md
```

Use one interface at a time and the same `--prompt` selection when switching;
omitting it selects `prompt.txt` in either interface. The coordinator maintains
daily records. Workers keep intermediate outputs in their workspace and may write
to the daily area only for assigned notices and required directory and lock
operations. All producers and acknowledgers use the same persistent
`.notifications.lock` beside that day's `notifications.md`,
opened in append mode and locked with Python standard-library
`fcntl.flock(handle, fcntl.LOCK_EX)`. Hold the handle while rereading/editing notices
and close it on completion or error; never unlink or replace the lock file. Verify
workers' authorized permissions cover notice appends and day-directory and lock
creation on the first day and at rollover. If access fails, workers preserve
workspace evidence and report the notice-write blocker. This is a prompt contract,
with no installed locking helper.

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
