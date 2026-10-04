import contextlib
from datetime import date
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import watch_notifications as watcher


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.daily = self.root / "daily records"
        self.day = date(2026, 10, 3)
        self.directory = self.daily / "2026/10/03"
        self.directory.mkdir(parents=True)
        self.notifications = self.directory / "notifications.md"
        self.marker = self.directory / watcher.MARKER_NAME
        self.calls = self.root / "calls.jsonl"
        self.exit_file = self.root / "queue-exit"
        executable = self.root / "codex"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys\n"
            "with open(os.environ['WATCH_TEST_CALLS'], 'a') as log:\n"
            "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "status = pathlib.Path(os.environ['WATCH_TEST_EXIT'])\n"
            "code = int(status.read_text()) if status.exists() else 0\n"
            "if code: print('test owning server unavailable', file=sys.stderr)\n"
            "sys.exit(code)\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        environment = patch.dict(os.environ, {
            "PATH": f"{self.root}{os.pathsep}{os.environ['PATH']}",
            "WATCH_TEST_CALLS": str(self.calls),
            "WATCH_TEST_EXIT": str(self.exit_file),
        })
        environment.start()
        self.addCleanup(environment.stop)

    def check(self, **kwargs):
        return watcher.check_notifications(self.daily, "disposable-thread", today=self.day,
                                           **kwargs)

    def argv(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_append_enqueues_once_and_checkbox_edit_is_quiet(self):
        self.notifications.write_text("- [ ] first\n", encoding="utf-8")
        self.assertEqual(self.check().queue_exit_code, 0)
        self.assertEqual(self.marker.read_text(), "1\n")
        self.assertIsNone(self.check().queue_exit_code)
        self.notifications.write_text("- [x] first\n- [ ] second\n", encoding="utf-8")
        self.assertEqual(self.check().queue_exit_code, 0)
        self.notifications.write_text("- [x] first\n- [x] second\n", encoding="utf-8")
        self.assertIsNone(self.check().queue_exit_code)
        self.assertEqual(self.marker.read_text(), "2\n")
        self.assertEqual(len(self.argv()), 2)

    def test_queue_message_only_contains_absolute_path_and_remote(self):
        self.notifications.write_text("- [ ] PRIVATE DETAIL\n", encoding="utf-8")
        result = self.check(remote="unix:///test-owning-server.sock")
        self.assertEqual(result.line_count, 1)
        self.assertEqual(result.queue_exit_code, 0)
        self.assertEqual(self.argv(), [[
            "queue", "--thread", "disposable-thread", "--message",
            f"Check notifications file: {self.notifications.resolve()}",
            "--remote", "unix:///test-owning-server.sock",
        ]])

    def test_failed_queue_preserves_marker_then_next_check_succeeds(self):
        self.notifications.write_text("- [ ] one\n- [ ] two\n", encoding="utf-8")
        self.marker.write_text("1\n")
        self.exit_file.write_text("7")
        result = self.check()
        self.assertEqual((result.line_count, result.queue_exit_code), (2, 7))
        self.assertIn("test owning server unavailable", result.error)
        self.assertIn(str(self.notifications), result.error)
        self.assertEqual(self.marker.read_text(), "1\n")
        self.exit_file.write_text("0")
        self.assertEqual(self.check().queue_exit_code, 0)
        self.assertEqual(self.marker.read_text(), "2\n")
        self.assertIsNone(self.check().queue_exit_code)
        self.assertEqual(len(self.argv()), 2)

    def test_failed_first_queue_does_not_create_marker(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        self.exit_file.write_text("1")
        self.assertEqual(self.check().queue_exit_code, 1)
        self.assertFalse(self.marker.exists())

    def test_restart_uses_persisted_marker(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        self.check()
        script = Path(watcher.__file__).resolve()
        process = subprocess.run([
            sys.executable, "-c",
            "from pathlib import Path; from datetime import date; "
            "from watch_notifications import check_notifications; "
            f"result = check_notifications(Path({str(self.daily)!r}), "
            "'disposable-thread', today=date(2026, 10, 3)); "
            "assert result.line_count == 1 and result.queue_exit_code is None",
        ], cwd=script.parent, capture_output=True, text=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(self.argv()), 1)

    def test_legacy_root_alias_shares_marker_and_resolves_visible_pointer(self):
        legacy = self.root / ".daily"
        legacy.symlink_to(self.daily, target_is_directory=True)
        self.notifications.write_text("- [ ] first\n", encoding="utf-8")
        self.assertEqual(self.check().queue_exit_code, 0)
        result = watcher.check_notifications(legacy, "disposable-thread", today=self.day)
        self.assertIsNone(result.queue_exit_code)
        with (legacy / "2026/10/03/notifications.md").open("a") as notices:
            notices.write("- [ ] second\n")
        result = watcher.check_notifications(legacy, "disposable-thread", today=self.day)
        self.assertEqual(result.queue_exit_code, 0)
        self.assertEqual(self.marker.read_text(), "2\n")
        self.assertEqual(self.argv()[-1][4], f"Check notifications file: {self.notifications.resolve()}")
        self.assertIsNone(self.check().queue_exit_code)
        self.assertEqual(len(self.argv()), 2)

    def test_cli_default_uses_visible_daily_under_home(self):
        visible = self.root / "daily"
        directory = visible / self.day.strftime("%Y/%m/%d")
        directory.mkdir(parents=True)
        notifications = directory / "notifications.md"
        notifications.write_text("- [ ] visible notice\n")
        with patch.dict(os.environ, {"HOME": str(self.root)}), \
                patch.object(sys, "argv", ["watch_notifications.py", "--thread", "disposable-thread"]), \
                patch.object(watcher, "date") as local_date, \
                patch.object(watcher.time, "sleep", side_effect=KeyboardInterrupt), \
                contextlib.redirect_stdout(io.StringIO()):
            local_date.today.return_value = self.day
            self.assertEqual(watcher.main(), 0)
        self.assertEqual(self.argv()[0][4], f"Check notifications file: {notifications.resolve()}")
        self.assertEqual((directory / watcher.MARKER_NAME).read_text(), "1\n")
        self.assertFalse((self.root / ".daily").exists())

    def test_local_day_rollover_uses_independent_file_and_marker(self):
        self.notifications.write_text("- [ ] old day\n", encoding="utf-8")
        next_directory = self.daily / "2026/10/04"
        next_directory.mkdir(parents=True)
        next_file = next_directory / "notifications.md"
        next_file.write_text("- [ ] new day\n", encoding="utf-8")
        with patch.object(watcher, "date") as local_date:
            local_date.today.side_effect = [self.day, date(2026, 10, 4)]
            watcher.check_notifications(self.daily, "disposable-thread")
            watcher.check_notifications(self.daily, "disposable-thread")
        self.assertEqual(self.marker.read_text(), "1\n")
        self.assertEqual((next_directory / watcher.MARKER_NAME).read_text(), "1\n")
        self.assertIn(str(next_file), self.argv()[1][4])
        self.assertEqual(len(self.argv()), 2)

    def test_absent_file_is_quiet_and_creates_nothing(self):
        absent_root = self.root / "absent daily"
        result = watcher.check_notifications(absent_root, "disposable-thread", today=self.day)
        self.assertIsNone(result.line_count)
        self.assertIsNone(result.queue_exit_code)
        self.assertFalse(absent_root.exists())
        self.marker.write_text("2\n")
        self.assertIsNone(self.check().line_count)
        self.assertEqual(self.marker.read_text(), "2\n")
        self.assertEqual(self.argv(), [])

    def test_corrupt_marker_is_reported_and_preserved(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        for value in ["garbage\n", "-1\n", "", "1.5\n", "١\n"]:
            with self.subTest(value=value):
                self.marker.write_text(value)
                with self.assertRaisesRegex(ValueError, "Restore its last successfully"):
                    self.check()
                self.assertEqual(self.marker.read_text(), value)
        self.assertEqual(self.argv(), [])

    def test_count_decrease_and_last_line_without_newline(self):
        self.notifications.write_text("- [ ] one\n- [ ] two", encoding="utf-8")
        self.assertEqual(self.check().line_count, 2)
        self.notifications.write_text("- [ ] replacement", encoding="utf-8")
        self.assertEqual(self.check().line_count, 1)
        self.assertEqual(self.marker.read_text(), "1\n")
        self.assertEqual(len(self.argv()), 2)

    def test_launch_failure_preserves_marker(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        with patch.dict(os.environ, {"PATH": str(self.root / "no-executable")}):
            result = self.check()
        self.assertEqual(result.line_count, 1)
        self.assertIsNone(result.queue_exit_code)
        self.assertIn("Check Codex installation", result.error)
        self.assertFalse(self.marker.exists())

    def test_accepted_queue_and_marker_failure_are_distinct(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        self.marker.with_name(self.marker.name + ".tmp").mkdir()
        result = self.check()
        self.assertEqual((result.line_count, result.queue_exit_code), (1, 0))
        self.assertIn("Queue accepted", result.error)
        self.assertIn("may enqueue a duplicate", result.error)
        self.assertFalse(self.marker.exists())
        self.assertEqual(len(self.argv()), 1)

    def test_queue_timeout_preserves_marker(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        self.marker.write_text("0\n")
        with patch.object(watcher.subprocess, "run", side_effect=
                          subprocess.TimeoutExpired("codex queue", 30)):
            result = self.check()
        self.assertEqual(result.line_count, 1)
        self.assertIsNone(result.queue_exit_code)
        self.assertIn("next normal check", result.error)
        self.assertEqual(self.marker.read_text(), "0\n")

    def test_invalid_utf8_marker_is_reported_and_preserved(self):
        self.notifications.write_text("- [ ] notice\n", encoding="utf-8")
        self.marker.write_bytes(b"\xff")
        with self.assertRaisesRegex(ValueError, str(self.marker)):
            self.check()
        self.assertEqual(self.marker.read_bytes(), b"\xff")
        self.assertEqual(self.argv(), [])

    def test_loop_rechecks_failed_queue_at_default_interval(self):
        self.notifications.write_text("- [ ] one\n- [ ] two\n", encoding="utf-8")
        self.marker.write_text("1\n")
        self.exit_file.write_text("7")
        intervals = []

        def next_interval(seconds):
            intervals.append(seconds)
            if len(intervals) == 1:
                self.assertEqual(self.marker.read_text(), "1\n")
                self.exit_file.write_text("0")
            else:
                raise KeyboardInterrupt

        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["watch_notifications.py", "--thread",
                                       "disposable-thread", "--daily-root", str(self.daily)]), \
                patch.object(watcher, "date") as local_date, \
                patch.object(watcher.time, "sleep", side_effect=next_interval), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            local_date.today.return_value = self.day
            self.assertEqual(watcher.main(), 0)
        self.assertEqual(intervals, [5, 5])
        self.assertEqual(self.marker.read_text(), "2\n")
        self.assertEqual(len(self.argv()), 2)
        self.assertIn("codex queue exited 7", errors.getvalue())
        self.assertIn("acceptance only", output.getvalue())

    def test_cli_rejects_invalid_launch_inputs_before_queueing(self):
        """Missing target and invalid interval fail at the launch boundary."""
        script = Path(watcher.__file__).resolve()
        invalid = [
            ([], "--thread"),
            (["--thread", " "], "--thread must not be empty"),
        ]
        for value in ["0", "-1", "nan", "inf"]:
            invalid.append((["--thread", "disposable-thread", f"--interval={value}"],
                            "--interval must be a finite positive number"))
        for arguments, diagnostic in invalid:
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, str(script), *arguments,
                                         "--daily-root", str(self.daily)],
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(diagnostic, result.stderr)
        self.assertEqual(self.argv(), [])


if __name__ == "__main__":
    unittest.main()
