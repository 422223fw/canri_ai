from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Language_brain_1 import LanguageLoader
from Language_brain_7 import LanguageAnalysisEngine
from Understanding_brain import UnderstandingBrain


class LanguageDiscourseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.language_data = LanguageLoader().load_all()
        cls.engine = LanguageAnalysisEngine()

    def test_agent_continuation_uses_understanding_contract(self):
        understanding = {
            "main_topic": "code",
            "intent": "code_editing",
            "language": "en",
            "request_contract": {
                "action": "improve",
                "target": "the existing guessing game",
                "intent": "code_editing",
                "requirements": [{"id": "r1", "text": "Add music."}],
                "output_constraints": {"requested_format": "project_files"},
                "continuation": {
                    "requested": True,
                    "markers": ["continue the same"],
                    "preserve_previous_behavior": True,
                },
            },
        }
        result = self.engine.analyze(
            "Use Agent mode and continue the same project. Also add music.",
            {"understanding": understanding},
            self.language_data,
        )

        frame = result["semantic_frame"]
        self.assertTrue(frame["understanding_contract_used"])
        self.assertEqual(frame["actions"][0], "improve")
        self.assertEqual(frame["requested_output"], "project_files")
        self.assertTrue(frame["continuation"]["must_preserve_previous_result"])
        self.assertTrue(result["discourse"]["agent_mode_requested"])
        self.assertTrue(result["discourse"]["is_continuation"])

    def test_understanding_contract_owns_agent_continuation_semantics(self):
        understanding = UnderstandingBrain().process({
            "original_text": (
                "Use Agent mode with Restricted permissions. Continue the same "
                "project and also add music."
            ),
        })
        contract = understanding["request_contract"]

        self.assertTrue(contract["continuation"]["requested"])
        self.assertTrue(contract["continuation"]["agent_mode_requested"])
        self.assertTrue(contract["continuation"]["preserve_previous_behavior"])
        self.assertIn("agent_mode", contract["continuation"]["dialogue_acts"])
        self.assertIn("continuation", contract["continuation"]["dialogue_acts"])

    def test_topic_shift_does_not_reuse_previous_agent_project(self):
        understanding = UnderstandingBrain().process({
            "original_text": "Use Agent mode. New topic: explain gravity.",
        })
        continuation = understanding["request_contract"]["continuation"]

        self.assertTrue(continuation["agent_mode_requested"])
        self.assertTrue(continuation["topic_shift"])
        self.assertFalse(continuation["requested"])
        self.assertFalse(continuation["preserve_previous_behavior"])


if __name__ == "__main__":
    unittest.main()
