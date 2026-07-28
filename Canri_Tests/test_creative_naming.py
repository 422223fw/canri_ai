from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from domain_packages.creativity.naming import ContextualNamingEngine


class CreativeNamingTests(unittest.TestCase):
    def setUp(self):
        self.engine = ContextualNamingEngine()
        self.report = {
            "advanced_word_tags": [
                {"word": "write", "semantic_tag": "action_command"},
                {"word": "constellation", "semantic_tag": "target_or_concept"},
                {"word": "luminous", "semantic_tag": "description"},
                {"word": "archive", "semantic_tag": "proper_or_technical_name"},
            ],
            "key_terms": ["constellation", "luminous", "archive"],
        }

    def test_project_names_come_from_concepts_not_command_verbs(self):
        names = self.engine.project_names("Write a luminous archive", self.report)
        self.assertNotIn("write", names["project_slug"])
        self.assertIn("constellation", names["source_concepts"])
        self.assertTrue(names["class_name"].isidentifier())

    def test_character_candidates_are_generated_and_unique(self):
        candidates = self.engine.character_candidates(
            "A luminous city under a constellation",
            self.report,
            count=8,
        )
        names = [item["name"] for item in candidates]
        self.assertGreaterEqual(len(names), 4)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(name.isalpha() for name in names))


if __name__ == "__main__":
    unittest.main()
