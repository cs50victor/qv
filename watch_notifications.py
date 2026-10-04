# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check today's notifications every five seconds and enqueue a file pointer."""

import argparse
from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path
import subprocess
import sys
import time


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread", required=True, help="Coordinator thread ID or exact name")
    parser.add_argument("--remote", help="Owning Codex server endpoint, e.g. unix:///path/socket")
    parser.add_argument("--daily-root", type=Path, default=Path("~/.daily"),
                        help="Daily records root (default: ~/.daily)")
    parser.add_argument("--interval", type=float, default=5,
                        help="Seconds between checks (default: 5)")
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
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
