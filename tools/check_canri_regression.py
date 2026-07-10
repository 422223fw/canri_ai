"""
Small regression checks for the Canri routing and answer-quality path.

Run from the project root:
    python tools/check_canri_regression.py
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "main_ai_canri"
sys.path.insert(0, str(PACKAGE_DIR))

from Code_brain import CodeBrain  # noqa: E402
from Creative_brain import CreativeBrain  # noqa: E402
from Fact_Check_brain import FactCheckBrain  # noqa: E402
from Math_brain import MathBrain  # noqa: E402
from Quality_Control_brain import QualityControlBrain  # noqa: E402
from Response_brain import ResponseBrain  # noqa: E402


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_expense_tracker_code_and_quality():
    prompt = (
        "Build a real runnable Python expense tracker for the terminal. "
        "The program must let the user add expenses with amount, category, and description, "
        "list all expenses, search expenses by category, show the total amount spent, "
        "delete an expense, and save/load all data from expenses.json. "
        "Only output the final full working Python code."
    )

    code_brain = CodeBrain()
    result = code_brain.build_direct_python_program_result(
        prompt,
        ["expense", "tracker", "category", "total"],
        "file_io"
    )

    assert_true(result["program_kind"] == "expense_tracker", "Code_brain chose the wrong program kind.")
    code = result["generated_code"].lower()
    assert_true("expenses.json" in code, "Expense tracker must use expenses.json.")
    assert_true('"amount"' in code and '"category"' in code and '"description"' in code, "Expense fields are missing.")
    assert_true("def show_total" in code, "Total function is missing.")

    qc = QualityControlBrain()
    quality = qc.process({
        "original_text": prompt,
        "understanding": {
            "main_topic": "code",
            "intent": "code_generation",
            "original_text": prompt
        },
        "results": {
            "Code_brain": result
        }
    })

    assert_true(quality["passed"], f"Quality check failed: {quality.get('issues')}")
    assert_true(quality["quality_score"] == 100, "Expense tracker should score 100 in this regression.")


def test_quadratic_math():
    math_brain = MathBrain()
    result = math_brain.process({
        "original_text": "Solve this step by step: x^2 - 5x + 6 = 0"
    })

    assert_true(result["success"], "Math_brain failed to solve a simple quadratic equation.")
    assert_true(result["type"] == "quadratic_equation", "Math_brain used the wrong solver.")
    assert_true("2" in str(result["answer"]) and "3" in str(result["answer"]), "Quadratic solutions should include 2 and 3.")
    assert_true(result["steps"], "Quadratic solution should include steps.")


def test_response_blocks_bad_quality():
    response = ResponseBrain()
    display = response.process({
        "original_text": "Build a real runnable Python expense tracker.",
        "understanding": {
            "main_topic": "code",
            "intent": "code_generation",
            "original_text": "Build a real runnable Python expense tracker."
        },
        "results": {
            "Code_brain": {
                "brain": "Code_brain",
                "program_kind": "json_cli",
                "generated_code": "def main():\n    pass\n",
                "confidence": 70
            },
            "Quality_Control_brain": {
                "passed": False,
                "quality_score": 41,
                "needs_retry": True,
                "issues": [
                    {
                        "target_brain": "Code_brain",
                        "severity": "critical",
                        "problem": "Wrong program kind selected: expected expense_tracker, got json_cli.",
                        "instruction": "Select the dedicated complete program template."
                    }
                ]
            }
        }
    })

    text = display["display_text"]
    assert_true("did not pass Canri's quality check" in text, "Response should not present bad code as final.")


def test_quality_catches_wrong_program_kind():
    prompt = "Build a real runnable Python expense tracker for the terminal."
    qc = QualityControlBrain()
    quality = qc.process({
        "original_text": prompt,
        "understanding": {
            "main_topic": "code",
            "intent": "code_generation",
            "original_text": prompt
        },
        "results": {
            "Code_brain": {
                "brain": "Code_brain",
                "program_kind": "json_cli",
                "generated_code": "def main():\n    pass\n",
                "confidence": 70
            }
        }
    })

    issue_text = " ".join(issue["problem"] for issue in quality.get("issues", []))
    assert_true(not quality["passed"], "Quality should fail wrong program kind.")
    assert_true("Wrong program kind" in issue_text, "Quality should explain the wrong program kind.")


def test_fact_check_evidence_coverage():
    fact_check = FactCheckBrain()
    coverage = fact_check.evidence_coverage([
        {
            "source_brain": "Data_context",
            "source_type": "local_data_json",
            "trust_score": 80,
            "name": "Knowledge_sources.json"
        },
        {
            "source_brain": "Knowledge_database",
            "source_type": "local_knowledge_article",
            "trust_score": 82,
            "name": "Python"
        },
        {
            "source_brain": "UnderstandingDk",
            "source_type": "local_dictionary",
            "trust_score": 74,
            "name": "python"
        }
    ])

    assert_true(coverage["data_context"] == 1, "Fact check should count Data_context evidence.")
    assert_true(coverage["knowledge_database"] == 1, "Fact check should count Knowledge_database evidence.")
    assert_true(coverage["dictionary"] == 1, "Fact check should count dictionary evidence.")
    assert_true(coverage["strong_sources"] >= 2, "Fact check should count strong sources.")


def test_creative_story_returns_final_story():
    prompt = (
        "Write a short original story in 6 sentences about a quiet boy named Leo "
        "who finds a tiny door under his bed. Only output the final story."
    )

    creative = CreativeBrain()
    result = creative.solve_brain_task(
        "Story_brain",
        {
            "understanding": {
                "original_text": prompt,
                "main_topic": "story",
                "intent": "story_creation"
            }
        },
        "creative_story_support"
    )

    story = result.get("final_output", "")
    lowered = story.lower()
    assert_true("leo" in lowered, "Creative story output should use the requested character.")
    assert_true("door" in lowered, "Creative story output should keep the requested object.")
    assert_true("goal:" not in lowered and "core idea:" not in lowered, "Creative story output leaked an internal report.")
    assert_true(result.get("answer_for_source_brain", {}).get("story"), "Creative story payload should include a story field.")


def test_creative_code_returns_real_code():
    prompt = (
        "Build a real runnable Python expense tracker for the terminal with amount, "
        "category, description, search, total, delete, and expenses.json."
    )

    creative = CreativeBrain()
    result = creative.solve_brain_task(
        "Code_brain",
        {"original_text": prompt},
        "creative_code_assembly"
    )

    code = result.get("generated_code", "")
    lowered = code.lower()
    assert_true("def add_expense" in code, "Creative code fallback should generate an expense add function.")
    assert_true("def show_total" in code, "Creative code fallback should generate a total function.")
    assert_true("expenses.json" in lowered, "Creative code fallback should use expenses.json.")
    assert_true("production_draft" not in lowered, "Creative code fallback should not return placeholder variants.")


def main():
    tests = [
        test_expense_tracker_code_and_quality,
        test_quadratic_math,
        test_response_blocks_bad_quality,
        test_quality_catches_wrong_program_kind,
        test_fact_check_evidence_coverage,
        test_creative_story_returns_final_story,
        test_creative_code_returns_real_code,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All Canri regression checks passed.")


if __name__ == "__main__":
    main()
