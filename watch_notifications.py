# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check today's notifications immediately, then sleep five seconds after each check by default."""

import argparse
from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import notification_inbox


MARKER_NAME = ".notifications-enqueued-lines"


@dataclass(frozen=True)
class CheckResult:
    line_count: int | None
    queue_exit_code: int | None = None
    error: str | None = None


def check_notifications(
    daily_root: Path,
    thread: str,
    remote: str | None = None,
    *,
    today: date | None = None,
) -> CheckResult:
    """Enqueue on count changes; the marker records acceptance, not review."""
    if not thread.strip():
        raise ValueError("A coordinator thread ID or exact name is required")
    day = today if today is not None else date.today()
    directory = daily_root.expanduser().resolve() / day.strftime("%Y/%m/%d")
    notifications = directory / "notifications.md"
    try:
        with notifications.open("rb") as source:
            line_count = sum(1 for _ in source)
    except FileNotFoundError:
        return CheckResult(None)

    marker = directory / MARKER_NAME
    try:
        saved = marker.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        previous = None
    except UnicodeDecodeError as exc:
        raise ValueError(f"Invalid UTF-8 marker {marker}: restore its last successfully "
                         "enqueued count.") from exc
    else:
        if not saved.isascii() or not saved.isdecimal():
            raise ValueError(
                f"Invalid line-count marker {marker}: expected a nonnegative integer. "
                "Restore its last successfully enqueued count; do not reset it blindly."
            )
        previous = int(saved)
    if line_count == previous:
        return CheckResult(line_count)

    command = ["codex", "queue", "--thread", thread,
               "--message", f"Check notifications file: {notifications}"]
    if remote is not None:
        command.extend(["--remote", remote])
    context = f"{notifications} (thread {thread}, endpoint {remote or 'default'})"
    try:
        queued = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(line_count, error=(
            f"Could not enqueue {context}: {exc}. Check Codex installation and "
            "server reachability. Marker unchanged; next normal check will try again."
        ))
    if queued.returncode != 0:
        detail = queued.stderr.strip() or queued.stdout.strip() or "no CLI output"
        return CheckResult(line_count, queued.returncode, (
            f"codex queue exited {queued.returncode} for {context}: {detail}. "
            "Check the target thread and owning endpoint. Marker unchanged; "
            "next normal check will try again."
        ))

    try:
        temporary = marker.with_name(marker.name + ".tmp")
        temporary.write_text(f"{line_count}\n", encoding="utf-8")
        temporary.replace(marker)
    except OSError as exc:
        return CheckResult(line_count, queued.returncode, (
            f"Queue accepted {context}, but could not save marker {marker}: {exc}. "
            "Fix directory permissions/storage; the next check may enqueue a duplicate."
        ))
    return CheckResult(line_count, queued.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Before starting:
  Inspect existing watchers. Run at most one total, owned by the coordinator;
  never stop or retarget another thread's watcher. Verify the current thread
  from CODEX_THREAD_ID in its native shell (not a worker or CODEX_SESSION_ID)
  and its owning endpoint from connection metadata. Missing or conflicting
  identity blocks launch; review notices directly instead.
  Use codex queue --help for queue syntax. Workers must not start watchers.

Worker notice contract:
  Append to DAILY_ROOT/YYYY/MM/DD/notifications.md using the local completion
  date. Include a unique completion ID, task ID, timestamp with timezone offset,
  observed outcome and report links in one unchecked Markdown checklist entry.
  Return the actual notice path and timestamp to the coordinator.
  Producers and reviewers must open the sibling .notifications.lock in append
  mode and hold fcntl.flock(handle, fcntl.LOCK_EX) while rereading, deduplicating
  completion IDs and appending or checking a notice. Never replace or unlink
  the lock. Preserve other entries; check a notice only after evidence review.

Polling behavior:
  Queue a file pointer when today's notice line count changes. Same-count edits
  stay quiet. .notifications-enqueued-lines records queue acceptance, not review
  or delivery. Queue failures leave it unchanged; marker-save failures can cause
  duplicate wake-ups. Review errors before repairing a marker; do not reset it
  blindly. The foreground loop ends on interruption; it installs no service.

Optional captured-history wake-ups:
  Initialize state using notification_inbox.py --help. --thread must then be
  its owner UUID, --remote must match its saved server ('default' when omitted),
  and state must exclude verified own-app bundle IDs. Use this existing watcher
  or one owned heartbeat, never both. Accepted inbox pointers suppress repeated
  wake-ups; only notification_inbox.py ack records review. Neither path changes
  source messages. This script does not collect macOS notifications or prove
  capture works under DND; check the collector separately.
""")
    parser.add_argument("--thread", required=True, help="Coordinator thread ID or exact name")
    parser.add_argument("--remote", help="Owning Codex server endpoint, e.g. unix:///path/socket")
    parser.add_argument("--daily-root", type=Path, default=Path("~/daily"),
                        help="Daily records root (default: ~/daily)")
    parser.add_argument("--interval", type=float, default=5,
                        help="Seconds to sleep after each check (default: 5)")
    parser.add_argument("--notification-state", type=Path,
                        help="Opt-in private captured-history inbox, bound to this thread/server")
    args = parser.parse_args()
    if not args.thread.strip():
        parser.error("--thread must not be empty")
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a finite positive number")
    try:
        while True:
            try:
                result = check_notifications(args.daily_root, args.thread, args.remote)
            except (OSError, ValueError) as exc:
                print(f"Notification check failed: {exc}", file=sys.stderr, flush=True)
            else:
                if result.error:
                    print(result.error, file=sys.stderr, flush=True)
                elif result.queue_exit_code == 0:
                    print(f"Enqueued file notice: {result.line_count} lines; queue exit 0 "
                          "(acceptance only)", flush=True)
            if args.notification_state is not None:
                try:
                    message = notification_inbox.wake_inbox(
                        args.notification_state, args.thread, args.remote)
                except (OSError, ValueError, sqlite3.Error, KeyError, TypeError) as exc:
                    print(f"Notification inbox check failed: {exc}", file=sys.stderr, flush=True)
                else:
                    if message:
                        print(message, flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
