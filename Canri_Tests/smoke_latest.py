"""Focused end-to-end smoke tests for recent Canri routing fixes."""

from __future__ import annotations

import os
import sys
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = TEST_DIR / "_runtime" / "main_ai_canri"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ask(main_module, prompt: str, session: str) -> dict:
    result = main_module.process_user_message(prompt, session_id=session)
    require(isinstance(result, dict), f"No structured result for {session}")
    require(bool(result.get("display_text")), f"No display text for {session}")
    return result


def main() -> int:
    os.environ.setdefault("CANRI_KNOWLEDGE_BACKGROUND", "0")
    if not RUNTIME_ROOT.exists():
        raise RuntimeError("Run the 1,000-test runner once to prepare the isolated runtime.")

    sys.path.insert(0, str(RUNTIME_ROOT))
    import main as canri_main

    canri_main.memory_brain.save_memory = lambda: None
    canri_main.memory_brain.save_statistics = lambda: None
    canri_main.register_all_brains()

    science = ask(
        canri_main,
        "Explain photosynthesis accurately in 3 clear sentences for a student.",
        "smoke_science",
    )
    science_text = science["display_text"].lower()
    require("photosynthesis" in science_text, "Science answer is unrelated to photosynthesis")
    require("nuclear fusion" not in science_text, "Science answer selected an unrelated article")

    code_analysis = ask(
        canri_main,
        "Explain what this Python code does and state its output:\n```python\nvalues = [2, 4]\nprint(sum(values))\n```",
        "smoke_code_analysis",
    )
    analysis_text = code_analysis["display_text"].lower()
    require(
        any(term in analysis_text for term in ("print", "sum", "6", "output")),
        "Code explanation did not discuss the supplied snippet",
    )

    math = ask(
        canri_main,
        "Solve 3x + 9 = 18 step by step, then verify x.",
        "smoke_math",
    )
    require("3" in math["display_text"], "Math answer did not contain the verified solution")

    expense = ask(
        canri_main,
        "Build a real runnable Python terminal expense tracker with amount, category, description, total, delete, and expenses.json save/load. Only output the final full Python code.",
        "smoke_expense",
    )
    expense_text = expense["display_text"].lower()
    for required in ("amount", "category", "description", "expenses.json"):
        require(required in expense_text, f"Expense tracker is missing {required}")

    print("Focused end-to-end smoke tests passed: science, code analysis, math, code generation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
