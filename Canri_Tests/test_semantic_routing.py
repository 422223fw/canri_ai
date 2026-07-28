from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Understanding_brain import UnderstandingBrain
from domain_packages.registry import build_domain_package_context


class SemanticRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = UnderstandingBrain()

    def assert_route(self, text, domain, brain_name):
        report = self.brain.process({"original_text": text})
        self.assertEqual(report["main_topic"], domain)
        self.assertIn(domain, report["central_domains"])
        self.assertIn(brain_name, report["routing_hints"])
        return report

    def test_routes_requests_from_whole_request_analysis(self):
        cases = (
            ("Explain how gravity bends a satellite path.", "science", "Science_brain"),
            ("Build a Python contact manager with JSON storage.", "code", "Code_brain"),
            ("Write a story about a child in a hidden city.", "story", "Story_brain"),
            ("I had a difficult day and need emotional support.", "emotion", "Emotion_brain"),
            ("What is the capital of France?", "geography", "Geography_brain"),
            ("Solve x^2 - 5x + 6 = 0 step by step.", "math", "Math_brain"),
        )
        for text, domain, brain_name in cases:
            with self.subTest(domain=domain):
                self.assert_route(text, domain, brain_name)

    def test_domain_packages_follow_understanding_report(self):
        for text, expected in (
            ("Build a Python contact manager.", "code"),
            ("Write an original story.", "creativity"),
            ("Solve 14 * 8 step by step.", "math"),
        ):
            report = self.brain.process({"original_text": text})
            context = build_domain_package_context(
                report.get("central_domains", []),
                report,
            )
            self.assertIn(expected, context["selected_package_ids"])

    def test_specialists_do_not_reintroduce_static_domain_tables(self):
        forbidden = (
            "DOMAIN_HINTS",
            "DOMAIN_RULES",
            "domain_owner = {",
            "domain_actions = {",
            "intent_keywords = {",
            "domain_keywords = {",
        )
        files = (
            "Manager_brain.py",
            "Planner_brain.py",
            "Reasoning_brain.py",
            "Technology_brain.py",
            "Creative_brain.py",
        )
        source = "\n".join(
            (CANRI_ROOT / name).read_text(encoding="utf-8")
            for name in files
        )
        for marker in forbidden:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
