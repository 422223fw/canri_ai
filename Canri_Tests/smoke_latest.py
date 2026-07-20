"""Focused end-to-end smoke tests for recent Canri routing fixes."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
SOURCE_ROOT = PROJECT_ROOT / "main_ai_canri"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ask(main_module, prompt: str, session: str) -> dict:
    started = time.perf_counter()
    result = main_module.process_user_message(prompt, session_id=session)
    elapsed = time.perf_counter() - started
    require(isinstance(result, dict), f"No structured result for {session}")
    require(bool(result.get("display_text")), f"No display text for {session}")
    text = result["display_text"].lower()
    internal_markers = (
        "core idea:",
        "novel twist:",
        "here is the useful conclusion:",
        "'action': 'gather more information",
        "review relevant memory before executing",
    )
    require(
        not any(marker in text for marker in internal_markers),
        f"Internal planning leaked for {session}: {result['display_text'][:300]}",
    )
    require(elapsed < 30.0, f"Request exceeded release budget for {session}: {elapsed:.2f}s")
    result["_smoke_elapsed_seconds"] = round(elapsed, 3)
    print(f"PASS {session}: {elapsed:.2f}s")
    return result


def main() -> int:
    os.environ.setdefault("CANRI_KNOWLEDGE_BACKGROUND", "0")
    sys.path.insert(0, str(SOURCE_ROOT))
    import main as canri_main

    canri_main.memory_brain.save_memory = lambda: None
    canri_main.memory_brain.save_statistics = lambda: None
    canri_main.register_all_brains()

    greeting = ask(
        canri_main,
        "Hello Canri, can you help me today?",
        "smoke_conversation",
    )
    require("canri" in greeting["display_text"].lower() or "help" in greeting["display_text"].lower(), "Greeting was not conversational")

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

    emotion = ask(
        canri_main,
        "I had a difficult and tiring day. Give me one gentle, practical suggestion.",
        "smoke_emotion",
    )
    require(len(emotion["display_text"].split()) >= 5, "Emotional support answer was empty or too short")

    story_start = ask(
        canri_main,
        "Write a short story about Maya finding a glowing key in a quiet park. Only output the story.",
        "smoke_story_context",
    )
    require("maya" in story_start["display_text"].lower(), "Story omitted the requested character")
    story_continue = ask(
        canri_main,
        "Continue the same story: she opens the door that the key unlocks. Only output the continuation.",
        "smoke_story_context",
    )
    continuation_text = story_continue["display_text"].lower()
    require(
        any(term in continuation_text for term in ("maya", "key", "door")),
        f"Continuation did not preserve the previous story context: {story_continue['display_text'][:300]}",
    )

    expense = ask(
        canri_main,
        "Build a real runnable Python terminal expense tracker with amount, category, description, total, delete, and expenses.json save/load. Only output the final full Python code.",
        "smoke_expense",
    )
    expense_text = expense["display_text"].lower()
    for required in ("amount", "category", "description", "expenses.json"):
        require(required in expense_text, f"Expense tracker is missing {required}")

    library = ask(
        canri_main,
        "Build a real runnable Python library management program for the terminal. "
        "Add books with title, author, and year; list books; search by title or author; "
        "borrow, return, and delete a book by number; save and load library.json; keep "
        "older library.json files compatible. Use only the standard library. Only output code.",
        "smoke_library",
    )
    library_text = library["display_text"].lower()
    for required in (
        "library.json",
        "def add_book",
        "def search_books",
        "def borrow_book",
        "def return_book",
        "def delete_book",
        "def normalize_book",
    ):
        require(required in library_text, f"Library manager is missing {required}")

    print(
        "Focused end-to-end smoke tests passed: conversation, science, code analysis, "
        "math, emotion, story continuation, and code generation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
