import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import voice


class ResumeTextTests(unittest.TestCase):
    def test_resume_preserves_saved_legacy_cwd_and_uses_visible_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            visible = root / "daily"
            visible.mkdir()
            legacy = root / ".daily"
            legacy.symlink_to(visible, target_is_directory=True)
            state = root / ".state"
            state.mkdir()
            (state / "thread.json").write_text(json.dumps({
                "cwd": str(legacy), "thread_id": "existing-thread",
            }))
            with patch.object(voice, "HERE", root), patch.object(voice.subprocess, "run") as run:
                run.return_value.returncode = 7
                self.assertEqual(voice.resume_text("Selected coordinator prompt."), 7)
            arguments = run.call_args.args[0]
            self.assertEqual(arguments[:5], ["codex", "resume", "existing-thread", "--cd", str(visible.resolve())])
            instructions = json.loads(arguments[-1].removeprefix("developer_instructions="))
            self.assertTrue(instructions.startswith("Selected coordinator prompt."))
            self.assertIn("~/daily records", instructions)
            self.assertNotIn("~/.daily", instructions)


if __name__ == "__main__":
    unittest.main()
