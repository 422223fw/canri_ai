from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from brains.agent import AgentBrain
from brains.project_context import ProjectContextBrain


@contextmanager
def test_workspace():
    root = PROJECT_ROOT / "Canri_Tests" / "agent_test_workspace" / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class ProjectContextBrainTests(unittest.TestCase):
    def test_reads_related_files_within_a_bounded_context(self):
        with test_workspace() as root:
            (root / "service.py").write_text(
                "from repository import ContactRepository\n\nclass ContactService:\n    pass\n",
                encoding="utf-8",
            )
            (root / "repository.py").write_text(
                "class ContactRepository:\n    pass\n",
                encoding="utf-8",
            )
            result = ProjectContextBrain().process({
                "original_text": "Update ContactService and its repository",
                "agent_settings": {
                    "mode": "restricted",
                    "workspace_path": str(root),
                },
            })
            self.assertEqual(result["workspace"], str(root.resolve()))
            self.assertIn("service.py", result["selected_files"])
            self.assertIn("repository.py", result["selected_files"])
            self.assertTrue(any(link["from"] == "service.py" for link in result["cross_file_links"]))


class AgentBrainTests(unittest.TestCase):
    def settings(self, root: Path, mode: str) -> dict:
        return {
            "mode": mode,
            "workspace_path": str(root),
            "allow_file_writes": True,
            "allow_terminal": True,
            "command_timeout_seconds": 30,
        }

    def test_autonomous_write_and_safe_command(self):
        with test_workspace() as root:
            pending = root / "pending.json"
            audit = root / "audit.jsonl"
            with patch("brains.agent.PENDING_FILE", pending), patch("brains.agent.AUDIT_FILE", audit):
                brain = AgentBrain()
                write_result = brain.process({
                    "session_id": "chat-a",
                    "agent_settings": self.settings(root, "autonomous"),
                    "agent_actions": [{"type": "write_file", "path": "app.py", "content": "print('ok')\n"}],
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(write_result["status"], "completed")
                self.assertEqual((root / "app.py").read_text(encoding="utf-8"), "print('ok')\n")

                command_result = brain.process({
                    "session_id": "chat-a",
                    "agent_settings": self.settings(root, "autonomous"),
                    "original_text": "/agent run python --version",
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(command_result["status"], "completed")
                self.assertEqual(command_result["action_results"][0]["returncode"], 0)

    def test_approval_mode_writes_only_after_matching_chat_approval(self):
        with test_workspace() as root:
            pending = root / "pending.json"
            audit = root / "audit.jsonl"
            with patch("brains.agent.PENDING_FILE", pending), patch("brains.agent.AUDIT_FILE", audit):
                brain = AgentBrain()
                first = brain.process({
                    "session_id": "chat-b",
                    "agent_settings": self.settings(root, "approval"),
                    "agent_actions": [{"type": "write_file", "path": "approved.py", "content": "VALUE = 7\n"}],
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(first["status"], "approval_required")
                self.assertFalse((root / "approved.py").exists())

                second = brain.process({
                    "session_id": "chat-b",
                    "agent_settings": self.settings(root, "approval"),
                    "original_text": f"/agent approve {first['approval_id']}",
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(second["status"], "completed")
                self.assertEqual((root / "approved.py").read_text(encoding="utf-8"), "VALUE = 7\n")
                stored = json.loads(pending.read_text(encoding="utf-8"))
                self.assertNotIn(first["approval_id"], stored["pending"])

    def test_rejects_path_escape_and_shell_operators(self):
        with test_workspace() as root:
            pending = root / "pending.json"
            audit = root / "audit.jsonl"
            with patch("brains.agent.PENDING_FILE", pending), patch("brains.agent.AUDIT_FILE", audit):
                brain = AgentBrain()
                escape = brain.process({
                    "agent_settings": self.settings(root, "autonomous"),
                    "agent_actions": [{"type": "write_file", "path": "../outside.py", "content": "bad = True\n"}],
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(escape["status"], "blocked")
                self.assertFalse((root.parent / "outside.py").exists())

                command = brain.process({
                    "agent_settings": self.settings(root, "autonomous"),
                    "original_text": "/agent run python --version && git status",
                    "results": {"Security_brain": {"safe": True}},
                })
                self.assertEqual(command["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
