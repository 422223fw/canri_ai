"""Run an isolated 400-request benchmark for code and science only.

The benchmark intentionally grades request relevance and answer usability,
not one exact wording. It keeps its files separate from the 1,000-task suite.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
SOURCE_ROOT = PROJECT_ROOT / "main_ai_canri"
OUTPUT_DIR = TEST_DIR / "Code_Science_Tests"
TASKS_FILE = OUTPUT_DIR / "code_science_400_tasks.json"
RESULTS_FILE = OUTPUT_DIR / "code_science_400_results.jsonl"
REPORT_FILE = OUTPUT_DIR / "code_science_400_report.json"
SUMMARY_FILE = OUTPUT_DIR / "code_science_400_summary.json"

INTERNAL_MARKERS = (
    "core idea:",
    "novel twist:",
    "direction: constraint_",
    "direction: risk_aware_",
    "here is the useful conclusion:",
    "the current draft did not pass canri's quality check",
    "reluctant hero concept lived",
)

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "clear",
    "code", "create", "does", "explain", "for", "from", "how", "i", "in",
    "include", "is", "it", "make", "must", "of", "only", "or", "output",
    "please", "program", "python", "show", "the", "this", "to", "use",
    "what", "with", "write", "you",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_task(task_id: int, category: str, prompt: str, group: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "category": category,
        "prompt": prompt,
        "session_group": group,
        "grading_policy": "Answer must be non-empty, relevant, and free of internal planning output.",
    }


def build_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    task_id = 1

    code_projects = [
        ("contact manager", "add, list, search by name, edit, delete, JSON save/load"),
        ("library manager", "add, list, search, borrow, return, delete, JSON save/load"),
        ("expense tracker", "add amount/category, list, search category, total, delete, JSON save/load"),
        ("note manager", "add, list, search, edit, delete, export TXT, JSON save/load"),
        ("to-do list", "add, list, mark done, delete, JSON save/load"),
        ("quiz game", "exactly 10 multiple-choice questions, four choices, score, play again"),
        ("temperature converter", "read Celsius or Fahrenheit, convert to the other unit, validate input, repeat until exit"),
        ("equation calculator", "solve linear and quadratic equations step by step and verify the solutions"),
        ("calculator", "addition, subtraction, multiplication, division, percentages, and JSON history"),
        ("text RPG", "player health, inventory, items, enemies, combat, JSON save/load, and a command loop"),
    ]
    for index in range(120):
        project, features = code_projects[index % len(code_projects)]
        variation = index // len(code_projects) + 1
        prompt = (
            f"Build a real runnable Python terminal {project}. Variation {variation}. "
            f"It must support {features}. Handle invalid input safely, use only the standard library, "
            "keep compatible with older JSON files when applicable, and keep running until the user types exit. "
            "Only output the final complete working Python code."
        )
        tasks.append(make_task(task_id, "code_generation", prompt, f"code_generation_{index + 1:03d}"))
        task_id += 1

    snippets = [
        "numbers = [3, 5, 7]\nprint(sum(numbers))",
        "def greet(name):\n    return f'Hello, {name}!'\nprint(greet('Maya'))",
        "items = {'a': 2, 'b': 4}\nprint(items['b'])",
        "for value in range(3):\n    print(value * 2)",
        "def is_even(number):\n    return number % 2 == 0\nprint(is_even(8))",
        "with open('data.txt', 'w', encoding='utf-8') as file:\n    file.write('hello')",
        "records = [{'name': 'Ari'}, {'name': 'Nora'}]\nprint([item['name'] for item in records])",
        "try:\n    value = int(input('Number: '))\nexcept ValueError:\n    print('Invalid number')",
        "class Counter:\n    def __init__(self):\n        self.value = 0\n    def increment(self):\n        self.value += 1",
        "import json\ndata = {'ready': True}\nprint(json.dumps(data))",
    ]
    for index in range(80):
        snippet = snippets[index % len(snippets)]
        prompt = (
            "Analyze this Python code. Explain what each important line does, identify the output "
            "or behavior, and mention one possible edge case. Do not invent code that is not shown.\n"
            f"```python\n{snippet}\n```"
        )
        tasks.append(make_task(task_id, "code_explanation", prompt, f"code_explanation_{index + 1:03d}"))
        task_id += 1

    science_topics = [
        "photosynthesis", "gravity", "DNA replication", "the water cycle", "electric current",
        "volcanoes", "the immune system", "atoms", "sound waves", "climate change",
        "cellular respiration", "plate tectonics", "natural selection", "the nervous system",
        "chemical bonds", "the carbon cycle", "vaccines", "the phases of the Moon",
        "renewable energy", "ocean currents",
    ]
    science_tasks = [
        "Explain {topic} accurately in four clear sentences for a student.",
        "What is {topic}? Give its main process and one everyday example.",
        "Explain why {topic} matters and name one common misconception about it.",
        "Compare {topic} with a closely related scientific idea in a short answer.",
        "Describe the cause and effect in {topic} without using advanced jargon.",
    ]
    for index in range(200):
        topic = science_topics[index % len(science_topics)]
        template = science_tasks[index % len(science_tasks)]
        prompt = template.format(topic=topic)
        tasks.append(make_task(task_id, "science", prompt, f"science_{index + 1:03d}"))
        task_id += 1

    if len(tasks) != 400 or sum(item["category"] == "code_generation" for item in tasks) != 120:
        raise RuntimeError("The code/science suite did not generate the expected task count.")
    if sum(item["category"] == "code_explanation" for item in tasks) != 80:
        raise RuntimeError("The code explanation count is incorrect.")
    if sum(item["category"] == "science" for item in tasks) != 200:
        raise RuntimeError("The science count is incorrect.")
    return tasks


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def relevance_tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9_]+", str(text).lower())
        if token not in STOP_WORDS and (token.isdigit() or len(token) >= 3)
    ]


def related(left: str, right: str) -> bool:
    return left == right or (
        not left.isdigit() and not right.isdigit()
        and len(left) >= 5 and len(right) >= 5 and left[:5] == right[:5]
    )


def evaluate(task_data: dict[str, Any], answer: str, error: str = "") -> dict[str, Any]:
    answer = str(answer or "")
    lowered = answer.lower()
    prompt_terms = list(dict.fromkeys(relevance_tokens(task_data["prompt"])))
    answer_terms = set(relevance_tokens(answer))
    matched = [
        term for term in prompt_terms
        if any(related(term, candidate) for candidate in answer_terms)
    ]
    lexical = min(1.0, len(matched) / max(1, min(8, len(prompt_terms))))
    category = task_data["category"]
    evidence = 0.0
    evidence_reason = ""
    if category == "code_generation":
        if "```" in answer or ("def " in answer and "import " in answer):
            evidence, evidence_reason = 0.55, "runnable code evidence"
    elif category == "code_explanation":
        if any(term in lowered for term in ["print", "output", "function", "line", "python"]):
            evidence, evidence_reason = 0.55, "code analysis evidence"
    elif category == "science":
        if any(term in lowered for term in ["because", "process", "energy", "cell", "matter", "system"]):
            evidence, evidence_reason = 0.35, "scientific explanation evidence"

    internal = any(marker in lowered for marker in INTERNAL_MARKERS)
    nonempty = bool(answer.strip()) and not error
    score = round(max(lexical, evidence), 3)
    passed = nonempty and score >= 0.15 and not internal
    return {
        "passed": passed,
        "checks": {
            "nonempty": nonempty,
            "related_to_request": score >= 0.15,
            "no_internal_report": not internal,
        },
        "relevance": {
            "score": score,
            "matched_prompt_terms": matched[:20],
            "evidence_reason": evidence_reason,
        },
        "error": error,
        "grading_policy": "Relevance and usable domain evidence only; no exact answer wording required.",
    }


def load_results(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    loaded: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
                loaded[int(item["id"])] = item
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return loaded


def rewrite_results(path: Path, records: dict[int, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for task_id in sorted(records):
            handle.write(json.dumps(records[task_id], ensure_ascii=False) + "\n")


def report_for(tasks: list[dict[str, Any]], records: dict[int, dict[str, Any]]) -> dict[str, Any]:
    ordered = [records[item["id"]] for item in tasks if item["id"] in records]
    categories: dict[str, dict[str, Any]] = {}
    for category in sorted({item["category"] for item in tasks}):
        group = [item for item in ordered if item["category"] == category]
        passed = sum(bool(item.get("evaluation", {}).get("passed")) for item in group)
        categories[category] = {
            "planned": sum(item["category"] == category for item in tasks),
            "completed": len(group),
            "passed": passed,
            "failed": len(group) - passed,
            "pass_rate_percent": round(passed / len(group) * 100, 2) if group else 0.0,
            "average_elapsed_seconds": round(
                sum(float(item.get("elapsed_seconds", 0)) for item in group) / len(group), 3
            ) if group else 0.0,
        }
    passed_total = sum(bool(item.get("evaluation", {}).get("passed")) for item in ordered)
    return {
        "title": "Canri AI Code and Science 400-Task Benchmark",
        "generated_utc": utc_now(),
        "total_planned": len(tasks),
        "total_completed": len(ordered),
        "total_passed": passed_total,
        "total_failed": len(ordered) - passed_total,
        "pass_rate_percent": round(passed_total / len(ordered) * 100, 2) if ordered else 0.0,
        "category_summary": categories,
        "primary_brains": dict(Counter(str(item.get("primary_brain") or "unknown") for item in ordered)),
        "tests": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--refresh-runtime", action="store_true")
    parser.add_argument("--limit", type=int, default=400,
                        help="Number of tasks to run from --start.")
    parser.add_argument("--start", type=int, default=0,
                        help="Zero-based task offset, useful for parallel shards.")
    parser.add_argument("--results-name", default=RESULTS_FILE.name,
                        help="JSONL filename inside the benchmark output directory.")
    args = parser.parse_args()

    tasks = build_tasks()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(TASKS_FILE, tasks)
    if args.start < 0:
        raise SystemExit("--start must be zero or greater")
    results_path = OUTPUT_DIR / Path(args.results_name).name
    if args.fresh and results_path.exists():
        results_path.unlink()
    records = load_results(results_path)
    limit = max(0, min(args.limit, len(tasks)))
    selected_tasks = tasks[args.start:args.start + limit]
    target_ids = {item["id"] for item in selected_tasks}
    records = {task_id: item for task_id, item in records.items() if task_id in target_ids}

    os.environ.setdefault("CANRI_KNOWLEDGE_BACKGROUND", "0")
    sys.path.insert(0, str(TEST_DIR))
    import run_canri_1000_tests as base

    runtime_root = base.prepare_isolated_runtime(refresh=args.refresh_runtime)
    sys.path.insert(0, str(runtime_root))
    import main as canri_main
    import Manager_brain as manager_module

    base.disable_test_persistence(canri_main)
    # Benchmark the first complete answer without retry loops. This does not
    # change the production setting, where targeted quality retries remain on.
    manager_module.MAX_QUALITY_RETRIES_PER_BRAIN = 0
    canri_main.register_all_brains()
    started_all = time.perf_counter()

    with results_path.open("a", encoding="utf-8", buffering=1) as output:
        for task_data in selected_tasks:
            task_id = task_data["id"]
            if task_id in records:
                continue
            started = time.perf_counter()
            response: dict[str, Any] = {}
            error = ""
            try:
                response = canri_main.process_user_message(
                    task_data["prompt"],
                    session_id=f"code_science_{task_data['session_group']}",
                )
                answer = str(response.get("display_text") or response.get("answer") or "")
            except Exception as exc:
                answer = ""
                error = f"{type(exc).__name__}: {exc}"
            record = {
                **task_data,
                "answer": answer,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "completed_utc": utc_now(),
                "primary_brain": response.get("primary_brain") if isinstance(response, dict) else None,
                "confidence": response.get("confidence") if isinstance(response, dict) else None,
                "evaluation": evaluate(task_data, answer, error),
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            records[task_id] = record
            completed = len(records)
            if completed % 10 == 0 or completed == len(selected_tasks):
                print(f"Completed {completed}/{len(selected_tasks)}", flush=True)

    report = report_for(selected_tasks, records)
    report["run_elapsed_seconds"] = round(time.perf_counter() - started_all, 3)
    write_json(REPORT_FILE, report)
    write_json(SUMMARY_FILE, {key: value for key, value in report.items() if key != "tests"})
    print(json.dumps({key: value for key, value in report.items() if key != "tests"}, ensure_ascii=False, indent=2))
    return 0 if report["total_completed"] == len(selected_tasks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
