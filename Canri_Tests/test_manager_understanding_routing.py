from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Manager_brain import ManagerBrain


class ManagerUnderstandingRoutingTests(unittest.TestCase):
    def setUp(self):
        self.manager = ManagerBrain()

    def test_unlisted_domain_comes_from_understanding_contract(self):
        report = {
            "main_topic": "astronomy",
            "intent": "research",
            "central_domains": [{"domain": "astronomy", "score": 92}],
            "request_contract": {
                "topic": "astronomy",
                "intent": "research",
                "requirements": [],
                "continuation": {"requested": False},
            },
        }

        self.assertEqual(self.manager.classify_request(report, {}), ["astronomy", "research"])
        self.assertEqual(self.manager.primary_domain(report, {}), "astronomy")

    def test_explicit_agent_follow_up_uses_active_chat_artifact(self):
        report = {
            "main_topic": "code",
            "intent": "code_editing",
            "requested_action": {"is_action_request": True, "action_word": "add"},
            "_agent_settings": {"mode": "restricted", "workspace_path": "C:/workspace"},
            "request_contract": {
                "topic": "code",
                "intent": "code_editing",
                "action": "add",
                "requirements": [{"id": "r1", "text": "Add music."}],
                "continuation": {
                    "requested": False,
                    "agent_mode_requested": True,
                },
            },
        }
        memory = {
            "conversation": {
                "continuation_request": False,
                "agent_continuation": {"type": "agent_project"},
            },
        }

        routing = self.manager.routing_decision(report, memory)
        phases = self.manager.build_plan(report, memory)
        by_name = {item["phase"]: item["brains"] for item in phases}

        self.assertTrue(routing["continuation"])
        self.assertIn("Creative_brain", by_name["agent_project_ideation"])
        self.assertIn("Agent_brain", by_name["agent_execution"])
        phase_order = [item["phase"] for item in phases]
        self.assertLess(phase_order.index("verification"), phase_order.index("agent_execution"))


if __name__ == "__main__":
    unittest.main()
