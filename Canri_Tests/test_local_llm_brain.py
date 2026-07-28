from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
if str(CANRI_ROOT) not in sys.path:
    sys.path.insert(0, str(CANRI_ROOT))

from brains.local_llm import LocalLLMBrain


class LocalLLMBrainTests(unittest.TestCase):
    def test_disabled_local_model_is_explicit_and_offline(self):
        path = CANRI_ROOT / "data" / "Local_model_settings.json"
        result = LocalLLMBrain(path).process({"original_text": "Hello"})

        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["available"])
        self.assertFalse(result["external_api_used"])

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


if __name__ == "__main__":
    unittest.main()
