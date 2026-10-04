# Notification delivery

Read before starting, reusing or retargeting the completion watcher. Workers append
notices; only the owned watcher queues their file pointers. The coordinator can
always review notices directly when delivery is unavailable.

## Verify identity before launch

Before the first worker dispatch and on recovery:

1. Locate the qv checkout and inspect existing watchers. Reuse one only when its
   owner, resolved daily root, thread and server match the current coordinator.
   Unknown ownership blocks setup; do not stop or retarget someone else's watcher.
2. Read `CODEX_THREAD_ID` in the coordinator's native shell, validate UUID syntax
   and compare current-thread metadata when available. Capture it before tmux.
   Never substitute `CODEX_SESSION_ID`, a worker ID or a recent rollout.
3. Identify the owning server from verified connection metadata: a matching
   default connection or its known `--remote` endpoint. A thread UUID, saved SDK
   thread ID or successful enqueue does not establish server identity.
4. Check `codex queue --help` in the launch environment. Verify write access for
   logs and day markers. Record owner, script/checkout, daily root, thread, server,
   tmux target and log path in the task record.

Missing or conflicting identity, server or permissions blocks launch/reuse.
Report the specific gap, continue independent work and review notices directly.
At most one watcher may run in total. Someone else's existing watcher blocks
launching another; do not stop or retarget it. Retarget only an owned watcher after
the checks above; preserve the day marker and review unchecked notices independently.

## Launch from the verified checkout

The following is a template after those checks, not an identity-discovery command.
Replace the checkout and log paths. Pass the captured thread value explicitly:

```sh
coordinator_thread_id="${CODEX_THREAD_ID:?current coordinator tool ID is required}"
tmux new-session -d -s qv-notifications -c /path/to/qv \
  sh -c 'exec uv run watch_notifications.py --thread "$1" >"$2" 2>&1' \
  sh "$coordinator_thread_id" /private/path/qv-notifications.log
```

For a verified remote server, add `--remote <owning-server-endpoint>` to the script
invocation. Use an owned, nonconflicting tmux target. `--daily-root` defaults to
`~/daily`; `--interval` defaults to five seconds after each check. Archive wake-ups
are off by default; their [separate setup](actionable-notifications.md) uses the
same watcher, not another process.

## What delivery proves

The watcher checks completion notices first. It follows local dates and compares
line counts with `.notifications-enqueued-lines` in that day's directory. A missing
notice file is normal. The resolved root plus date/file path forms the pointer;
day/file symlinks are not resolved separately. A changed count, or an existing file
without a marker, queues a short file pointer. The marker advances only after
queue exit 0 and persists across restarts and target changes.

A failed queue call leaves the marker unchanged; the next regular check retries.
If saving the marker fails after acceptance, another pointer may be sent. Same-count
checkbox edits are silent. Queue calls can take up to 30 seconds and delay the next
check. Direct review must not depend on receiving another pointer.

Queue acceptance is not consumption, review, completion or speech. A stopped or
unloaded coordinator may not consume it. `voice.py` does not start the watcher,
back up records, or automatically speak notice results. Do not promise monitoring,
idle announcements, native steering or shutdown survival without live evidence.
