from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from Manager_brain import ManagerBrain
from Nervous_system_brain import NervousSystemBrain
from Quality_Control_brain import QualityControlBrain
from Research_brain import ResearchBrain
from Response_brain import ResponseBrain
from Emotion_brain import EmotionBrain
from Understanding_brain import UnderstandingBrain
from domain_packages.code.program_specs import (
    detect_existing_program_kind,
    detect_program_kind,
)


class SharedCodeSemanticsTests(unittest.TestCase):
    def test_generation_and_quality_share_program_kind_registry(self):
        prompts = {
            "contact_book": "Build a Python contact manager with search and edit.",
            "expense_tracker": "Build a terminal expense tracker with totals.",
            "equation_calculator": "Build a quadratic equation calculator.",
            "quiz_game": "Build a multiple choice quiz game.",
        }
        quality = QualityControlBrain()
        for expected, prompt in prompts.items():
            with self.subTest(expected=expected):
                self.assertEqual(detect_program_kind(prompt), expected)
                self.assertEqual(quality.detect_expected_program_kind(prompt.casefold()), expected)

    def test_existing_program_kind_uses_shared_signatures(self):
        code = "def add_contact(): pass\n\ndef list_contacts(): pass\n"
        self.assertEqual(detect_existing_program_kind(code), "contact_book")


class ScannerGroundingTests(unittest.TestCase):
    def test_every_brain_receives_bounded_scanner_evidence(self):
        manager = ManagerBrain()
        knowledge = {
            "matches": [{
                "article_id": "a1",
                "title": "Orbital mechanics",
                "summary": "Gravity changes satellite trajectories.",
                "trust_score": 90,
                "sources": [{"url": "https://example.test/orbit"}],
            }]
        }
        report = {
            "routing_hints": ["Science_brain", "Fact_Check_brain"],
        }
        creative_view = manager.build_scanner_view(knowledge, "Creative_brain", report)
        science_view = manager.build_scanner_view(knowledge, "Science_brain", report)
        self.assertTrue(creative_view["required_for_consideration"])
        self.assertEqual(len(creative_view["matches"]), 1)
        self.assertTrue(science_view["required_for_answer"])

    def test_nervous_system_uses_understanding_owners(self):
        brain = NervousSystemBrain()
        report = {"routing_hints": ["Astronomy_brain", "Fact_Check_brain"]}
        self.assertEqual(
            brain.owner_brains(report)[:2],
            ["Astronomy_brain", "Fact_Check_brain"],
        )

    def test_research_category_is_derived_from_source_profiles(self):
        brain = ResearchBrain()
        brain.sources = [{
            "name": "Orbital Spectroscopy Archive",
            "category": "orbital_dynamics",
            "source_type": "scientific_archive",
            "strengths": ["exoplanet spectroscopy", "orbital trajectory"],
            "domains": ["astronomy"],
        }]
        self.assertEqual(
            brain.detect_category("Compare an exoplanet orbital trajectory."),
            "orbital_dynamics",
        )


class ResponseRoutingTests(unittest.TestCase):
    def test_emotion_does_not_override_science_route(self):
        brain = ResponseBrain()
        report = {
            "main_topic": "science",
            "intent": "question",
            "routing_hints": ["Science_brain", "Emotion_brain"],
        }
        results = {
            "Emotion_brain": {
                "conversation_intent": "support",
                "support_response": "I hear you.",
            }
        }
        self.assertFalse(brain.is_pure_emotional_conversation(report, results, "Explain gravity"))

    def test_pure_support_request_can_use_emotion(self):
        brain = ResponseBrain()
        report = {
            "main_topic": "emotion",
            "intent": "question",
            "routing_hints": ["Emotion_brain", "Reasoning_brain"],
        }
        results = {
            "Emotion_brain": {
                "conversation_intent": "support",
                "support_response": "I hear you.",
            }
        }
        self.assertTrue(brain.is_pure_emotional_conversation(report, results, "I had a hard day"))


class EmotionGroundingTests(unittest.TestCase):
    def setUp(self):
        self.understanding = UnderstandingBrain()
        self.emotion = EmotionBrain()

    def analyze(self, text):
        report = self.understanding.process({"user_message": text})
        return self.emotion.process({
            "user_message": text,
            "understanding": report,
        })

    def test_difficult_exhausting_day_is_not_misclassified_as_joy(self):
        result = self.analyze(
            "I had a difficult and exhausting day. "
            "Can you give me practical emotional support?"
        )
        self.assertEqual(result["primary_emotion"], "sadness")
        self.assertEqual(result["conversation_intent"], "emotional_support")
        self.assertNotIn("good news", result["support_response"].lower())

    def test_direct_positive_message_remains_celebration(self):
        result = self.analyze("I succeeded today and I am very happy!")
        self.assertEqual(result["primary_emotion"], "joy")
        self.assertEqual(result["conversation_intent"], "celebration")


if __name__ == "__main__":
    unittest.main()
