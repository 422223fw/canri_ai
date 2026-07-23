"""Focused smoke checks for the nervous, science, technology, code, and enrichment upgrade."""

from __future__ import annotations

import os
import sys
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
SOURCE_ROOT = PROJECT_ROOT / "main_ai_canri"
os.environ.setdefault("CANRI_KNOWLEDGE_BACKGROUND", "0")
sys.path.insert(0, str(TEST_DIR))

import run_canri_1000_tests as test_support


def run() -> None:
    # This focused smoke test avoids copying the large data directory. All
    # persistence hooks are disabled before requests are processed.
    sys.path.insert(0, str(SOURCE_ROOT))

    import main as canri_main
    import Manager_brain as manager_module

    test_support.disable_test_persistence(canri_main)
    manager_module.MAX_QUALITY_RETRIES_PER_BRAIN = 0
    canri_main.register_all_brains()

    science = canri_main.process_user_message(
        "Explain gravity accurately, including its main effect and one everyday example.",
        session_id="upgrade_science_smoke",
    )
    science_text = str(science.get("display_text") or "")
    assert science.get("primary_brain") in {"Science_brain", "Research_brain", "Fact_Check_brain"}
    assert "gravity" in science_text.lower()
    assert "serious and solemn" not in science_text.lower()

    technology = canri_main.process_user_message(
        "Explain what a CPU does and mention two important hardware considerations.",
        session_id="upgrade_technology_smoke",
    )
    technology_text = str(technology.get("display_text") or "")
    assert technology.get("primary_brain") in {"Technology_brain", "Research_brain", "Fact_Check_brain"}
    assert technology_text.strip()

    code = canri_main.process_user_message(
        "Build a runnable Python terminal program that asks for names until exit and greets each name.",
        session_id="upgrade_code_smoke",
    )
    code_text = str(code.get("display_text") or "")
    assert code.get("primary_brain") == "Code_brain"
    assert "def main" in code_text
    assert "Explanation" in code_text
    assert "Verification" in code_text

    print("brain upgrade smoke checks passed", flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback

        traceback.print_exc()
        os._exit(1)
    os._exit(0)
