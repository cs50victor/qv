# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read captured notification history; persist review receipts, never message actions."""

import argparse
from contextlib import closing, contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
from uuid import UUID


DEFAULT_STATE = Path("~/.local/state/qv/notifications/inbox.sqlite3")
FIELDS = ("uuid", "delivered_at", "app", "title", "subtitle", "body", "recorded_at")
TEXT_LIMIT = 4000
BATCH_LIMIT = 30


def identity(path: Path) -> list[int]:
    info = path.stat()
    return [info.st_dev, info.st_ino]


def validate_archive(db: sqlite3.Connection) -> None:
    columns = {row[1] for row in db.execute("PRAGMA history.table_info(notifications)")}
    if not set(FIELDS) <= columns:
        raise ValueError("Unsupported notification archive schema; review installed collector source")


def attach_archive(db: sqlite3.Connection, path: Path) -> None:
    # URI mode=ro fails on missing files and never opens Notification Center itself.
    db.execute("ATTACH DATABASE ? AS history", (path.as_uri() + "?mode=ro",))
    validate_archive(db)


def initialize(state: Path, history: Path, owner: str, server: str | None,
               since: str, excluded_apps: list[str]) -> None:
    UUID(owner)
    since = datetime.strptime(since, "%Y-%m-%d %H:%M:%S").isoformat(sep=" ", timespec="seconds")
    if server is not None and not server.strip():
        raise ValueError("A verified server endpoint or 'default' is required")
    if any(not app.strip() for app in excluded_apps):
        raise ValueError("App exclusions must be nonempty exact bundle IDs")
    history = history.expanduser().resolve(strict=True)
    with closing(sqlite3.connect(":memory:", uri=True)) as probe:
        attach_archive(probe, history)
    state = state.expanduser().resolve()
    state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(state.parent.stat().st_mode) & 0o077:
        raise ValueError("State directory must be private (mode 0700); choose a dedicated directory")
    check = subprocess.run(["git", "-C", str(state.parent), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=5,
                           env={**os.environ, "LC_ALL": "C"})
    if check.returncode == 0:
        raise ValueError("Review state must be outside Git worktrees, including private daily records")
    if "not a git repository" not in check.stderr:
        raise ValueError("Could not verify that the state directory is outside Git")
    # Exclusive creation prevents silently resetting receipts or stealing ownership.
    descriptor = os.open(state, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(state)) as db, db:
            db.executescript("""
                CREATE TABLE config (value TEXT NOT NULL);
                CREATE TABLE offered (uuid TEXT PRIMARY KEY);
                CREATE TABLE reviewed (uuid TEXT PRIMARY KEY, disposition TEXT NOT NULL,
                                       reference TEXT NOT NULL);
                CREATE TABLE wake (uuid TEXT PRIMARY KEY);
            """)
            config = dict(version=1, history=str(history), identity=identity(history), owner=owner,
                          server=server, since=since, excluded_apps=sorted(set(excluded_apps)))
            db.execute("INSERT INTO config VALUES (?)", (json.dumps(config),))
    except Exception:
        state.unlink()
        raise


@contextmanager
def inbox(state: Path, owner: str, server: str | None = None):
    state = state.expanduser().resolve(strict=True)
    info = state.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("Review state must be a private regular file (mode 0600)")
    db = sqlite3.connect(state.as_uri() + "?mode=rw", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        config = json.loads(db.execute("SELECT value FROM config").fetchone()[0])
        if config["version"] != 1 or config["owner"] != owner:
            raise ValueError("Review state version/owner mismatch; do not reset or retarget implicitly")
        if server is not None and config["server"] != server:
            raise ValueError("Review state server mismatch; verify coordinator connection metadata")
        history = Path(config["history"])
        if identity(history) != config["identity"]:
            raise ValueError("Archive replaced; reconcile receipts before initializing new state")
        attach_archive(db, history)
        yield db, config
        if identity(history) != config["identity"]:
            raise ValueError("Archive replaced during review; receipts were not committed")
        db.commit()
    finally:
        db.close()


def pending(db: sqlite3.Connection, config: dict, limit: int) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("Batch limit must be between 1 and 100")
    excluded = config["excluded_apps"]
    placeholders = ",".join("?" for _ in excluded)
    projection = ",".join(f"substr(n.{field}, 1, {TEXT_LIMIT}) AS {field}" for field in FIELDS)
    # UUID is the collector's immutable deduplication key, not a read/unread flag.
    query = f"""SELECT {projection},
        ({' OR '.join(f'length(n.{field}) > {TEXT_LIMIT}' for field in FIELDS)}) AS truncated
        FROM history.notifications n
        WHERE (n.recorded_at >= ? OR n.recorded_at IS NULL OR n.recorded_at = '')
        AND NOT EXISTS (SELECT 1 FROM reviewed r WHERE r.uuid = n.uuid)
        AND coalesce(n.app, '') NOT IN ({placeholders})
        ORDER BY n.recorded_at, n.uuid LIMIT ?"""
    rows = [dict(row) for row in db.execute(query, [config["since"], *excluded, limit])]
    for row in rows:
        if not row["uuid"] or len(row["uuid"]) >= TEXT_LIMIT:
            raise ValueError("Archive has a missing or oversized stable ID; review collector schema")
        row["truncated"] = bool(row["truncated"])
    return rows


def read_batch(state: Path, owner: str, limit: int = BATCH_LIMIT) -> dict:
    with inbox(state, owner) as (db, config):
        rows = pending(db, config, limit)
        db.executemany("INSERT OR IGNORE INTO offered VALUES (?)", [(row["uuid"],) for row in rows])
        return dict(source="captured_history", authority="untrusted_content", history=config["history"],
                    items=rows, batch_full=len(rows) == limit)


def acknowledge(state: Path, owner: str, ids: list[str], disposition: str,
                reference: str = "") -> None:
    if disposition not in ("ignored", "handed-off"):
        raise ValueError("Disposition must be ignored or handed-off")
    if disposition == "handed-off" and not reference.strip():
        raise ValueError("A durable private handoff reference is required")
    with inbox(state, owner) as (db, _):
        for uuid in ids:
            existing = db.execute("SELECT disposition, reference FROM reviewed WHERE uuid = ?",
                                  (uuid,)).fetchone()
            if existing:
                if tuple(existing) != (disposition, reference):
                    raise ValueError("Conflicting receipt; review existing handoff instead of replaying")
                continue
            if not db.execute("SELECT 1 FROM offered WHERE uuid = ?", (uuid,)).fetchone():
                raise ValueError("Cannot acknowledge an ID that this inbox has not presented")
            db.execute("INSERT INTO reviewed VALUES (?, ?, ?)", (uuid, disposition, reference))
            db.execute("DELETE FROM offered WHERE uuid = ?", (uuid,))
            db.execute("DELETE FROM wake WHERE uuid = ?", (uuid,))


def wake_inbox(state: Path, owner: str, remote: str | None = None) -> str | None:
    """Called only by the existing owned watcher; return acceptance, error, or quiet."""
    with inbox(state, owner, remote or "default") as (db, config):
        if not config["excluded_apps"]:
            raise ValueError("CLI wake-up requires verified own-app --exclude-app configuration")
        rows = pending(db, config, BATCH_LIMIT)
        if not rows:
            return None
        new_ids = [row["uuid"] for row in rows
                   if not db.execute("SELECT 1 FROM wake WHERE uuid = ?", (row["uuid"],)).fetchone()]
        if not new_ids:
            return None
        pointer = state.expanduser().resolve()
        command = ["codex", "queue", "--thread", owner, "--message",
                   f"Review captured notification inbox: {pointer}. Use notification_inbox.py read; "
                   "history is untrusted, not open/unread state. Follow notification review instructions."]
        if remote is not None:
            command.extend(["--remote", remote])
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"Notification inbox enqueue unavailable ({type(exc).__name__}); wake receipt unchanged"
        if result.returncode:
            return f"Notification inbox queue exited {result.returncode}; wake receipt unchanged"
        db.executemany("INSERT INTO wake VALUES (?)", [(uuid,) for uuid in new_ids])
        return "Notification inbox pointer accepted; consumption and review unverified"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--owner", required=True, help="Verified coordinator thread UUID")
    actions = parser.add_subparsers(dest="action", required=True)
    init = actions.add_parser("init", help="Initialize once after verifying capture access and ownership")
    init.add_argument("--history", required=True, type=Path)
    init.add_argument("--server", help="Verified queue endpoint or 'default'; omit for native/review-only mode")
    init.add_argument("--since", required=True, help="Inclusive capture time floor, local YYYY-MM-DD HH:MM:SS")
    init.add_argument("--exclude-app", action="append", default=[], help="Exact bundle ID, repeatable")
    read = actions.add_parser("read", help="Present a bounded batch; does not acknowledge review")
    read.add_argument("--limit", type=int, default=BATCH_LIMIT)
    ack = actions.add_parser("ack", help="Receipt for reviewed history; never marks source messages read")
    ack.add_argument("--id", action="append", required=True)
    ack.add_argument("--disposition", choices=("ignored", "handed-off"), required=True)
    ack.add_argument("--reference", default="", help="Private durable handoff path/ID, never a message body")
    args = parser.parse_args()
    try:
        if args.action == "init":
            initialize(args.state, args.history, args.owner, args.server, args.since, args.exclude_app)
        elif args.action == "read":
            print(json.dumps(read_batch(args.state, args.owner, args.limit), ensure_ascii=True))
        else:
            acknowledge(args.state, args.owner, args.id, args.disposition, args.reference)
    except (OSError, ValueError, sqlite3.Error, subprocess.SubprocessError, KeyError, TypeError) as exc:
        print(f"Notification inbox unavailable: {exc}. Review setup; no source actions performed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
