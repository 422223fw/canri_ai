from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))
RUNTIME_ROOT = PROJECT_ROOT / "Canri_Tests" / "_runtime"
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)

from Brain_runtime import BrainRuntime
from Manager_brain import ManagerBrain
from brains.llm_bridge import LLMBridgeBrain


class _EchoBrain:
    def process(self, data):
        return {"answer": "echo", "source_size": len(str(data))}


class LLMBridgeAndMemoryTests(unittest.TestCase):
    def test_manager_runs_bridge_after_specialists_and_reviews_after_llm(self):
        manager = ManagerBrain()
        phases = manager.build_plan(
            {
                "intent": "question",
                "main_topic": "general",
                "routing_hints": [],
                "request_contract": {"requirements": [], "continuation": {}},
            },
            {},
        )
        names = [item["phase"] for item in phases]

        self.assertLess(names.index("domain_experts"), names.index("llm_context_bridge"))
        self.assertLess(names.index("llm_context_bridge"), names.index("local_model_assistance"))
        self.assertLess(names.index("local_model_assistance"), names.index("llm_candidate_review"))
        self.assertLess(names.index("llm_candidate_review"), names.index("verification"))

    def test_manager_sends_bounded_phase_specific_context_to_local_llm(self):
        source = {
            "_request_id": "request_compact",
            "original_text": "Explain the specialist result",
            "understanding": {"request_contract": {"requirements": []}},
            "memory": {"matches": ["memory " * 5000]},
            "knowledge": {"excerpt": "knowledge " * 5000},
        }
        results = {
            "Code_brain": {"generated_code": "x = 1\n" * 20000},
            "LLM_bridge_brain": {
                "context_packet": {
                    "native_prompt": "bounded prompt",
                    "specialist_count": 1,
                }
            },
            "Local_LLM_brain": {
                "status": "completed",
                "final_output": "candidate",
            },
        }

        local_context = ManagerBrain.build_llm_phase_context(
            source,
            results,
            "local_model_assistance",
        )
        review_context = ManagerBrain.build_llm_phase_context(
            source,
            results,
            "llm_candidate_review",
        )

        self.assertEqual(set(local_context["results"]), {"LLM_bridge_brain"})
        self.assertNotIn("memory", local_context)
        self.assertNotIn("knowledge", local_context)
        self.assertEqual(
            set(review_context["results"]),
            {"LLM_bridge_brain", "Local_LLM_brain"},
        )
        self.assertLess(len(json.dumps(local_context)), 30_000)

        manager = ManagerBrain()
        runtime_context = manager.build_context(
            local_context,
            {"request_contract": {"requirements": ["x" * 100_000]}},
            {"conversation": {"summary": "y" * 100_000}},
            "local_model_assistance",
            {},
            "Local_LLM_brain",
        )
        self.assertLess(len(json.dumps(runtime_context)), 35_000)
        self.assertEqual(
            runtime_context["manager_context"]["integration_mode"],
            "bounded_llm_bridge",
        )

    def test_bridge_keeps_prompt_inside_the_configured_budget(self):
        bridge = LLMBridgeBrain()
        result = bridge.process(
            {
                "original_text": "Explain gravity clearly and remember the current conversation.",
                "understanding": {
                    "request_contract": {
                        "requirements": [
                            {"text": "Use a simple example."},
                            {"text": "Do not expose internal reports."},
                        ]
                    }
                },
                "memory": {
                    "conversation": {
                        "turns": [
                            {"USER": "old context " * 500, "CANRI": "old answer " * 500}
                        ]
                    }
                },
                "results": {},
            }
        )
        packet = result["context_packet"]

        self.assertLessEqual(packet["prompt_tokens"], packet["prompt_budget_tokens"])
        self.assertIn("USER REQUEST", packet["selected_sections"])
        self.assertIn("REQUEST CONTRACT", packet["selected_sections"])
        self.assertFalse(packet["full_conversation_used"])

    def test_bridge_allows_llm_only_for_relevant_general_conversation(self):
        report_path = RUNTIME_ROOT / "ready_sealed_evaluation.json"
        settings_path = RUNTIME_ROOT / "ready_llm_settings.json"
        report_path.write_text(
            json.dumps(
                {
                    "status": "ready",
                    "automated_gate_passed": True,
                    "manual_review_approved": True,
                }
            ),
            encoding="utf-8",
        )
        settings_path.write_text(
            json.dumps({"native_sealed_evaluation_path": str(report_path)}),
            encoding="utf-8",
        )
        bridge = LLMBridgeBrain(settings_path=settings_path)
        result = bridge.process(
            {
                "original_text": "Tell me something useful about learning Python",
                "understanding": {"request_contract": {"requirements": []}},
                "results": {
                    "Local_LLM_brain": {
                        "status": "completed",
                        "final_output": "Learning Python is easier when you practice Python with small projects.",
                    }
                },
            }
        )

        self.assertTrue(result["candidate_accepted"])
        self.assertEqual(result["candidate_role"], "general_conversation")

    def test_experimental_model_remains_advisory_until_sealed_gate_passes(self):
        bridge = LLMBridgeBrain()
        result = bridge.process(
            {
                "original_text": "Tell me something useful about learning Python",
                "understanding": {"request_contract": {"requirements": []}},
                "results": {
                    "Local_LLM_brain": {
                        "status": "completed",
                        "final_output": "Learning Python is easier with small Python projects.",
                    }
                },
            }
        )

        self.assertFalse(result["candidate_accepted"])
        self.assertIn("sealed_quality_gate_not_passed", result["candidate_issues"])

    def test_specialist_output_cannot_be_replaced_by_llm(self):
        bridge = LLMBridgeBrain()
        result = bridge.process(
            {
                "original_text": "Write a Python program",
                "understanding": {"request_contract": {"requirements": []}},
                "results": {
                    "Code_brain": {"generated_code": "print('ok')"},
                    "Local_LLM_brain": {
                        "status": "completed",
                        "final_output": "Here is a Python program.",
                    },
                },
            }
        )

        self.assertFalse(result["candidate_accepted"])
        self.assertTrue(result["specialists_preserved"])

    def test_runtime_counts_reads_writes_and_lfm_llm_separately(self):
        statistics_path = RUNTIME_ROOT / "unit_runtime_statistics.json"
        memory_path = RUNTIME_ROOT / "unit_memory_statistics.json"
        runtime = BrainRuntime(
            statistics_path=statistics_path,
            memory_statistics_path=memory_path,
        )
        runtime.invoke(
            "Code_brain",
            _EchoBrain(),
            {"original_text": "build code"},
            request_id="request_test",
        )
        runtime.invoke(
            "Local_LLM_brain",
            _EchoBrain(),
            {"original_text": "help with the answer"},
            request_id="request_test",
        )
        runtime.record_information_exchange(
            "Memory_brain",
            {"answer": "stored response"},
            {"stored": True},
            request_id="request_test",
            caller_brain="Response_brain",
            phase="response_memory_write",
        )
        profile = runtime.finalize_request_memory(
            "request_test",
            session_id="chat_test",
            user_preview="test request",
        )

        self.assertGreater(profile["total_bytes"], 0)
        self.assertGreater(profile["lfm_bytes"], 0)
        self.assertGreater(profile["llm_bytes"], 0)
        self.assertEqual({item["family"] for item in profile["brains"]}, {"LFM", "LLM"})
        self.assertTrue(
            any(
                item["from"] == "Response_brain"
                and item["to"] == "Memory_brain"
                for item in profile["transfers"]
            )
        )
        self.assertTrue(memory_path.is_file())


if __name__ == "__main__":
    unittest.main()
