from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Code_brain import CodeBrain


class CodeAgentContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = CodeBrain()

    def test_graphical_music_request_updates_existing_guessing_game(self):
        report = {
            "main_topic": "code",
            "intent": "code_editing",
            "request_contract": {
                "topic": "code",
                "intent": "code_editing",
                "requirements": [
                    {"text": "Use a graphical window instead of the terminal."},
                    {"text": "Add background music."},
                ],
                "continuation": {
                    "requested": True,
                    "preserve_previous_behavior": True,
                },
            },
        }
        result = self.brain.process({
            "original_text": (
                "Continue the same Python number-guessing game with a graphical "
                "window and music."
            ),
            "understanding": report,
            "existing_project_files": {
                "game.py": "import random\nsecret = random.randint(1, 100)\n",
                "main.py": "print('guess')\n",
            },
            "agent_creative_guidance": {
                "specialist_support": {"ideas": ["clear visual feedback"]},
            },
        })

        self.assertEqual(result["program_kind"], "graphical_guessing_game")
        self.assertEqual(sorted(result["project_files"]), ["game.py", "main.py"])
        self.assertTrue(result["project_review"]["ready"], result["project_review"])
        self.assertTrue(result["continuation"]["creative_guidance_used"])
        ast.parse(result["project_files"]["game.py"])
        ast.parse(result["project_files"]["main.py"])

    def test_explicit_agent_follow_up_uses_active_agent_project(self):
        report = {
            "main_topic": "code",
            "intent": "code_editing",
            "request_contract": {
                "topic": "code",
                "intent": "code_editing",
                "requirements": [
                    {"text": "Add a graphical window and background music."},
                ],
                "continuation": {
                    "requested": False,
                    "agent_mode_requested": True,
                    "preserve_previous_behavior": False,
                },
            },
        }
        result = self.brain.process({
            "original_text": (
                "Use Agent mode with Restricted permissions. Add a graphical "
                "window and music."
            ),
            "understanding": report,
            "memory": {
                "conversation": {
                    "agent_continuation": {
                        "type": "agent_project",
                        "workspace": "active-workspace",
                    },
                },
            },
            "existing_project_files": {
                "game.py": "import random\nsecret = random.randint(1, 100)\n",
                "main.py": "print('guess')\n",
            },
        })

        self.assertEqual(result["output_mode"], "project_update")
        self.assertEqual(result["changed_paths"], ["game.py", "main.py"])
        self.assertIn("tkinter", result["project_files"]["main.py"])
        self.assertIn("SoundController", result["project_files"]["main.py"])


if __name__ == "__main__":
    unittest.main()
