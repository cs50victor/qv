# Workers and completion notices

Read before dispatching workers or editing notices. The coordinator owns task
records and review; workers implement, research and validate within assigned scope.

## Launch and follow up

1. Resolve a project or isolated worktree outside `~/daily`, including symlink
   aliases. Use `~/dev` for projects and `~/not-dev/<task-id>` for work without one.
   Set both tmux's working directory and Codex's `--cd` to that workspace.
2. Check CLI help. Launch a fresh independent Codex CLI session in detached tmux;
   prefer interactive mode for ongoing steering and `codex exec` for bounded work.
   Assign unique tmux targets and separate worktrees for concurrent editors.
3. Give the worker its task, evidence, owned files, constraints, completion criteria,
   output paths and notice contract below. It loads global/project instructions,
   not coordinator history or rules. No native subagents, coordinator forks/resumes
   or further worker delegation. Tell it to preserve others' changes.
4. Save output and the actual process exit status. Record observed identities in
   the task record. Reuse that worker's own session for follow-ups. Remain available
   for conversation and check progress with bounded waits, not busy-polling.

Stop only owned sessions. If launch fails, record the failure and continue other
work; doing the worker's job directly requires an explicit routing override.
Before the first dispatch and on recovery, check delivery using the
[watcher runbook](notification-delivery.md); unavailable delivery does not prevent
work with direct notice review.

## Give each worker a completion contract

Assign a task ID, a unique completion ID and the expected local-day notice path.
Verify permission for notice append, day-directory creation and the shared lock,
including at date rollover. Workers may write the daily area only for these
assigned operations. Intermediate results stay in their own workspace.

At completion, use the actual local date's `~/daily/YYYY/MM/DD/notifications.md`.
Append one `- [ ]` entry per completion ID with task/completion IDs, timestamp and
timezone offset, observed result and exact report/artifact links. Return the actual
path and timestamp. On access failure, retain results in the workspace and report
the notice blocker. A process start or queued message is not a completion result.

## Lock every notice write

All producers and reviewers use the same resolved, persistent `.notifications.lock`
beside the day's `notifications.md`. Open the lock with Python `open(..., "a")`
and acquire `fcntl.flock(handle, fcntl.LOCK_EX)`. Hold that handle while rereading,
checking the completion ID and appending or marking reviewed entries. Close it on
success or error; never replace or unlink the lock.

Create a missing day directory if needed. Append only assigned notices or change
only reviewed checkboxes; preserve concurrent entries and evidence. If locking or
writing fails, report it and leave unreviewed entries unchecked. This is a shared
file-writing contract, not a locking helper supplied by qv.

## Review before acknowledging

During ordinary work turns, promptly inspect unchecked notices when received or
read, including the indicated day, today and older days linked from active tasks.
Review artifacts, full diffs (including removals), logs and citations against the
requested outcome. Check who executes each changed instruction, where its inputs
come from, permissions and the failure path. Test real behavior proportionately;
do not treat a supplied-but-unavailable prerequisite as a successful workflow.

Record the outcome and follow-up scope before checking off a notice. Checked means
handled, including a reported failure, not that the goal is complete. Record handled
completion IDs to avoid replay. Continue authorized dependent work in the owning
worker's session after verifying prerequisites; carry unresolved work forward by
link. The main guide's standalone-answer and only-command exceptions still apply.
