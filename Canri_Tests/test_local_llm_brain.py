from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
RUNTIME_ROOT = PROJECT_ROOT / "Canri_Tests" / "_runtime"
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from brains.local_llm import LocalLLMBrain, LocalModelError


class LocalLLMBrainTests(unittest.TestCase):
    def test_disabled_local_model_is_explicit_and_offline(self):
        path = RUNTIME_ROOT / "local_llm_disabled_settings.json"
        path.write_text(json.dumps({"enabled": False}), encoding="utf-8")
        result = LocalLLMBrain(path).process({"original_text": "Hello"})

        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["available"])
        self.assertFalse(result["external_api_used"])

    def test_native_shadow_is_disabled_and_never_used_for_the_answer(self):
        path = RUNTIME_ROOT / "local_llm_shadow_settings.json"
        path.write_text(
            json.dumps({"enabled": True, "native_shadow_enabled": False}),
            encoding="utf-8",
        )
        result = LocalLLMBrain(path).process_shadow({"original_text": "Hello"})

        self.assertEqual(result["status"], "shadow_disabled")
        self.assertFalse(result["available"])
        self.assertFalse(result["used_for_user_answer"])

    def test_extracts_fenced_json(self):
        loaded = LocalLLMBrain._extract_json(
            '```json\n{"final_output":"done","project_files":{}}\n```'
        )
        self.assertEqual(loaded["final_output"], "done")

    def test_project_paths_cannot_escape_workspace(self):
        brain = LocalLLMBrain()
        result = brain._normalize_output(
            {
                "final_output": "project",
                "project_files": {
                    "app/main.py": "print('ok')\n",
                    "../outside.py": "print('unsafe')\n",
                },
                "entrypoint": "app/main.py",
            },
            {},
        )
        self.assertEqual(result["project_files"], {"app/main.py": "print('ok')\n"})
        self.assertEqual(result["rejected_paths"], ["../outside.py"])

    def test_experimental_native_checkpoint_is_not_used_by_default(self):
        brain = LocalLLMBrain()
        with self.assertRaisesRegex(LocalModelError, "experimental"):
            brain._run_native(
                "Hello",
                {
                    "native_checkpoint_path": "domain_packages/local_llm/checkpoints/canri_native.pt",
                    "native_tokenizer_path": "domain_packages/local_llm/data/canri_tokenizer.json",
                    "native_training_status_path": "domain_packages/local_llm/training_status.json",
                    "native_allow_experimental": False,
                },
            )

    def test_native_prompt_prioritizes_request_requirements_and_failures(self):
        prompt = LocalLLMBrain().build_native_prompt(
            {
                "original_text": "Build the requested program.",
                "understanding": {
                    "request_contract": {"requirements": ["Keep running until exit."]}
                },
                "failed_requirements": ["The command loop is missing."],
            }
        )
        self.assertIn("Build the requested program", prompt)
        self.assertIn("Keep running until exit", prompt)
        self.assertIn("The command loop is missing", prompt)

    def test_native_prompt_uses_the_bridge_packet_when_available(self):
        prompt = LocalLLMBrain().build_native_prompt(
            {
                "original_text": "ignored fallback",
                "results": {
                    "LLM_bridge_brain": {
                        "context_packet": {"native_prompt": "bounded bridge prompt"}
                    }
                },
            }
        )

        self.assertEqual(prompt, "bounded bridge prompt")


if __name__ == "__main__":
    unittest.main()
