"""
Small regression checks for the Canri routing and answer-quality path.

Run from the project root:
    python tools/check_canri_regression.py
"""

import struct
import sys
import wave
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "main_ai_canri"
sys.path.insert(0, str(PACKAGE_DIR))

from Code_brain import CodeBrain  # noqa: E402
from Collaboration_brain import CollaborationBrain  # noqa: E402
from Creative_brain import CreativeBrain  # noqa: E402
from Fact_Check_brain import FactCheckBrain  # noqa: E402
from Math_brain import MathBrain  # noqa: E402
from Manager_brain import ManagerBrain  # noqa: E402
from Memory_brain import MemoryBrain  # noqa: E402
from Quality_Control_brain import QualityControlBrain  # noqa: E402
from Response_brain import ResponseBrain  # noqa: E402
from Science_brain import ScienceBrain  # noqa: E402
from Spelling_brain import SpellingBrain  # noqa: E402
from Understanding_brain import UnderstandingBrain  # noqa: E402
from Data_context import context_view_for_brain  # noqa: E402
from Knowledge_collector import KnowledgeCollector  # noqa: E402
from Learning_brain import LearningBrain  # noqa: E402
from Planner_brain import PlannerBrain  # noqa: E402
from Geography_brain import GeographyBrain  # noqa: E402
from History_brain import HistoryBrain  # noqa: E402
from Emotion_brain import EmotionBrain  # noqa: E402
from Image_brain import ImageBrain  # noqa: E402
from Vision_brain import VisionBrain  # noqa: E402
from Voice_brain import VoiceBrain  # noqa: E402


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
    assert_true(result["verification"]["passed"], "Quadratic roots should be verified by substitution.")


def test_math_ignores_request_words_around_expression():
    math_brain = MathBrain()
    arithmetic = math_brain.process({
        "original_text": "Calculate 8 + 2. Show the steps and give the final answer."
    })
    linear = math_brain.process({
        "original_text": "Solve 3x + 9 = 18 step by step, then verify x."
    })

    assert_true(arithmetic.get("success") and str(arithmetic.get("answer")) in {"10", "10.0"}, "Embedded arithmetic failed.")
    assert_true(linear.get("success") and "3" in str(linear.get("answer")), "Embedded linear equation failed.")
    assert_true(linear.get("verification", {}).get("passed"), "Linear solution was not verified.")


def test_science_prefers_the_exact_user_topic():
    science = ScienceBrain()
    science.update_statistics = lambda *args, **kwargs: None
    result = science.process({
        "original_text": "Explain photosynthesis accurately in 3 clear sentences for a student.",
        "main_topic": "science",
        "topics": {},
        "words": [],
    })

    assert_true(result.get("top_article_ids", [None])[0] == "biology_photosynthesis", "Science selected an unrelated article.")
    answer = str(result.get("answer", "")).lower()
    assert_true("photosynthesis" in answer and "nuclear fusion" not in answer, "Science answer is unrelated to the request.")

    current = science.process({
        "original_text": "Explain electric current accurately in 3 clear sentences for a student.",
        "main_topic": "science",
        "topics": {},
        "words": [],
    })
    current_answer = str(current.get("answer", "")).lower()
    assert_true("electric" in current_answer and "current" in current_answer, "Science lost the requested multi-word topic.")


def test_quality_treats_code_analysis_as_explanation():
    prompt = "Explain what this Python code does: print(sum([2, 4]))"
    qc = QualityControlBrain()
    quality = qc.process({
        "original_text": prompt,
        "understanding": {
            "main_topic": "code",
            "intent": "code_analysis",
            "original_text": prompt,
        },
        "results": {
            "Code_brain": {
                "brain": "Code_brain",
                "mode": "code_analysis",
                "code_analyzed": "print(sum([2, 4]))",
                "answer": "The code adds 2 and 4, then prints 6.",
            }
        },
    })

    assert_true(quality.get("passed"), f"A valid code explanation failed quality control: {quality.get('issues')}")
    checks = {item.get("requirement"): item.get("passed") for item in quality.get("requirement_checks", [])}
    assert_true(checks.get("code_explained") is True, "Quality control did not record code-analysis coverage.")


def test_understanding_preserves_original_file_names():
    prompt = "Build an expense tracker and save it to expenses.json."
    report = UnderstandingBrain().process({
        "original_text": prompt,
        "corrected_text": "Build an expense tracker and save it to expense.json.",
    })
    files = report.get("request_contract", {}).get("detail_inventory", {}).get("file_names", [])
    assert_true("expenses.json" in files, "Understanding lost the exact filename from the original request.")
    assert_true("expense.json" not in files, "A spelling rewrite changed an exact filename requirement.")


def test_standard_library_does_not_mean_book_library():
    code = CodeBrain()
    quiz_prompt = "Build a Python terminal quiz game. Use only the standard library."
    inventory_prompt = "Build a Python terminal inventory tracker. Use only the standard library."
    assert_true(code.detect_direct_program_kind(quiz_prompt, "general") == "quiz_game", "Standard library hijacked quiz routing.")
    assert_true(code.detect_direct_program_kind(inventory_prompt, "general") == "shop_inventory", "Standard library hijacked inventory routing.")


def test_atoms_route_to_science():
    report = UnderstandingBrain().process("Explain atoms accurately in three sentences.")
    assert_true(report.get("main_topic") == "science", "The plural word atoms should route to science.")


def test_learning_does_not_use_creativity_for_missing_metadata():
    learning = LearningBrain()
    result = learning.request_creative_help(
        [{"brain": "Science_brain", "problem": "missing confidence", "result": {}}],
        {"main_topic": "science", "intent": "question"},
        {},
    )
    assert_true(result == [], "Missing confidence metadata should not start a creative simulation.")


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


def test_creative_uses_indexed_snippets_and_dictionary_entries():
    creative = CreativeBrain()
    report = {
        "words": [{
            "word": "butterfly",
            "exists": True,
            "type": "noun",
            "meanings": ["an insect with broad wings"],
            "forms": {},
            "connections": ["insect", "wing"]
        }]
    }
    context = creative.collect_indexed_project_context({
        "data_context": {
            "matches": [
                {
                    "file": "Company_products.json",
                    "score": 20,
                    "matched_terms": ["product"],
                    "sample": ["company"],
                    "value_matches": [{
                        "path": "products[0]",
                        "text": "Example product",
                        "matched_terms": ["product"]
                    }]
                },
                {
                    "file": "Security_rules.json",
                    "score": 30,
                    "matched_terms": ["security"],
                    "sample": [],
                    "value_matches": []
                }
            ]
        }
    }, report, ["butterfly", "product"])

    assert_true("Company_products.json" in context, "Creative brain should consume indexed project snippets.")
    assert_true("Security_rules.json" not in context, "Creative brain should exclude rule files from general retrieval.")
    assert_true("UnderstandingDk::butterfly" in context, "Creative brain should reuse exact dictionary results.")
    assert_true(
        not context["Company_products.json"].get("full_file_loaded"),
        "Creative context must not report whole-file loading."
    )


def test_understanding_builds_complete_request_contract():
    prompt = (
        "Build a real runnable Python expense tracker.\n"
        "1. Add expenses with amount, category, and description.\n"
        "2. Save and load expenses.json.\n"
        "Only output the final working Python code. Do not output a plan or placeholders."
    )
    understanding = UnderstandingBrain().process(prompt)
    contract = understanding.get("request_contract", {})

    assert_true(contract.get("action") == "build", "Understanding should detect the requested action.")
    assert_true(contract.get("topic") == "code", "Understanding should detect the code domain.")
    assert_true(len(contract.get("requirements", [])) >= 3, "Understanding should extract atomic requirements.")
    constraints = contract.get("output_constraints", {})
    assert_true(constraints.get("requested_format") == "code", "Understanding should detect code-only output.")
    assert_true("plan" in constraints.get("forbidden_sections", []), "Understanding should preserve forbidden output sections.")
    details = contract.get("detail_inventory", {})
    assert_true("expenses.json" in details.get("file_names", []), "Understanding should preserve exact file names.")
    detail_text = " ".join(
        item.get("text", "")
        for item in details.get("explicit_details", [])
    ).lower()
    for expected in ["amount", "category", "description", "save", "load"]:
        assert_true(expected in detail_text, f"Understanding should preserve the small detail: {expected}.")
    assert_true(bool(contract.get("global_picture", {}).get("goal")), "Understanding should preserve the global goal.")


def test_inline_code_punctuation_and_function_spelling():
    spelling = SpellingBrain()
    understanding = UnderstandingBrain()

    corrected = spelling.process("Use the prnit() function in Python.")
    assert_true("print()" in corrected["corrected_text"], "Spelling should correct a close known function name.")

    custom = spelling.process("Call calculate_total() after loading data.")
    assert_true("calculate_total()" in custom["corrected_text"], "Spelling must preserve a possible custom function.")

    report = understanding.process("Explain print(name) and then use input().")
    assert_true(report.get("main_topic") == "code", "Inline function calls should route as code context.")
    assert_true(report.get("code_context", {}).get("has_code"), "Understanding should mark inline code.")
    calls = [
        item.get("identifier")
        for item in report.get("code_context", {}).get("function_calls", [])
    ]
    assert_true("print" in calls and "input" in calls, "Understanding should preserve function-call identifiers.")
    punctuation = report.get("punctuation_analysis", {}).get("counts", {})
    assert_true(punctuation.get("(", 0) >= 2, "Understanding should interpret code punctuation.")


def test_company_and_product_context_is_expanded():
    manager = ManagerBrain()
    report = UnderstandingBrain().process("Which company makes PyCharm and what is it?")
    context = manager.build_dictionary_context(
        {"original_text": "Which company makes PyCharm and what is it?"},
        report,
        {}
    )
    matches = context.get("product_matches", [])
    assert_true(any(item.get("company") == "JetBrains" for item in matches), "Product lookup should connect PyCharm to JetBrains.")


def test_manager_routes_specialists_without_domain_leakage():
    understanding = UnderstandingBrain()
    manager = ManagerBrain()

    math_report = understanding.process("Solve step by step: x^2 - 5x + 6 = 0")
    math_plan = manager.flatten_plan(manager.build_plan(math_report, {}))
    assert_true("Math_brain" in math_plan, "Math request must route to Math_brain.")
    assert_true("Code_brain" not in math_plan, "Math request must not route to Code_brain.")

    code_report = understanding.process("Build a runnable Python todo program. Only output code.")
    decision = manager.routing_decision(code_report, {})
    assert_true(decision["primary_brain"] == "Code_brain", "Code request must choose Code_brain as primary.")
    assert_true("Story_brain" not in manager.flatten_plan(manager.build_plan(code_report, {})), "Code request must not route to Story_brain.")


def test_memory_keeps_continuation_inside_one_session():
    memory = MemoryBrain()
    memory.database = {
        "episodes": [],
        "conversations": {
            "chat_a": {
                "title": "Code chat",
                "turns": [{
                    "id": "a1",
                    "user": "Build a todo app",
                    "canri": "```python\ndef main():\n    print('todo')\n```",
                    "main_topic": "code",
                    "intent": "code_generation",
                    "keywords": ["todo", "code"],
                    "quality": {"passed": True}
                }]
            },
            "chat_b": {
                "title": "Story chat",
                "turns": [{
                    "id": "b1",
                    "user": "Write a story",
                    "canri": "A separate story.",
                    "main_topic": "story",
                    "intent": "story_creation",
                    "keywords": ["story"],
                    "quality": {"passed": True}
                }]
            }
        },
        "semantic_memory": {"topics": {}, "intents": {}, "keywords": {}, "tasks": {}},
        "metadata": {"version": "test"}
    }
    report = memory.build_conversation_report(
        "chat_a",
        {"main_topic": "code", "intent": "code_generation", "key_terms": ["todo", "edit"]},
        "Continue the same code and add edit."
    )

    assert_true(report["session_id"] == "chat_a", "Memory report should stay in the requested chat.")
    assert_true(report["continuation_source"]["turn_id"] == "a1", "Continuation should use the previous turn in the same chat.")
    assert_true(all(turn["id"] != "b1" for turn in report["relevant_turns"]), "Memory must not leak another chat.")
    assert_true(report["usable_previous_code"], "Continuation should expose previous code to Code_brain.")


def test_data_context_is_filtered_per_brain():
    context = {
        "domains": ["code", "science"],
        "query_terms": ["python", "physics"],
        "profiled_files": 2,
        "total_profiled_bytes": 200,
        "matches": [
            {"file": "Code_statistics.json", "score": 20, "matched_terms": ["python"], "value_matches": []},
            {"file": "Science_articles.json", "score": 18, "matched_terms": ["physics"], "value_matches": []}
        ]
    }
    view = context_view_for_brain(context, "Code_brain", max_sources=1)
    assert_true(view["brain"] == "Code_brain", "Context view should identify its target brain.")
    assert_true(len(view["matches"]) == 1, "Context view should enforce its source budget.")
    assert_true(view["selection_policy"] == "domain_filtered_lazy_context", "Context should report filtered lazy selection.")


def test_response_hides_quality_metadata_for_strict_output():
    response = ResponseBrain().process({
        "original_text": "Build a runnable Python program. Only output the final code.",
        "understanding": {
            "main_topic": "code",
            "intent": "code_generation",
            "request_contract": {
                "output_constraints": {"only_output": "final code", "requested_format": "code"}
            }
        },
        "results": {
            "Code_brain": {
                "brain": "Code_brain",
                "generated_code": "def main():\n    print('ok')\n\nif __name__ == \"__main__\":\n    main()\n",
                "language": "python",
                "confidence": 90
            },
            "Quality_Control_brain": {
                "passed": True,
                "quality_score": 100,
                "issues": []
            }
        }
    })
    text = response["display_text"].lower()
    assert_true("```python" in text, "Strict code output should contain the code block.")
    assert_true("quality note" not in text and "goal:" not in text, "Strict output must not leak internal metadata.")
    assert_true(response["strict_output"], "Response should mark strict output mode.")


def test_code_self_review_checks_request_alignment():
    reviewer = CodeBrain().self_reviewer
    review = reviewer.review_and_improve(
        "def main():\n    print('empty')\n\nif __name__ == \"__main__\":\n    main()\n",
        "python",
        "Build a runnable expense tracker that can add, list, search, delete, save and load JSON.",
        "expense_tracker"
    )
    assert_true(not review["ready"], "Code missing requested behavior must not pass self-review.")
    assert_true(review["request_alignment"]["failed"], "Self-review should list failed request checks.")


def test_planner_covers_every_request_requirement():
    prompt = (
        "Build a professional Python habit tracker. Add, list, search and delete habits. "
        "Save and load habits_custom.json. Only output runnable code."
    )
    contract = {
        "requirements": [
            {"id": "add", "text": "Add habits"},
            {"id": "search", "text": "Search habits"},
            {"id": "delete", "text": "Delete habits"},
            {"id": "file", "text": "Use habits_custom.json"},
        ],
        "output_constraints": {"requested_format": "code", "must_be_runnable": True},
        "global_picture": {"goal": prompt},
        "detail_inventory": {"file_names": ["habits_custom.json"]},
    }
    plan = PlannerBrain().process({
        "original_text": prompt,
        "main_topic": "code",
        "intent": "code_generation",
        "request_contract": contract,
    })["plan"]
    assert_true(plan["requirements_total"] == 4, "Planner lost an atomic requirement.")
    assert_true(plan["requirements_covered"] == 4, "Planner failed to cover every requirement.")
    assert_true(plan["all_requirements_planned"], "Planner must block incomplete requirement coverage.")
    assert_true(plan["graph_validation"]["valid"], "Planner produced an invalid dependency graph.")
    assert_true(plan["quality_pattern_id"], "Planner did not use professional quality knowledge.")


def test_code_recipe_builds_new_program_kind_and_exact_file():
    prompt = (
        "Build a runnable Python habit tracker for the terminal. Add, list, search and "
        "delete habits. Save and load habit_records.json. Only output final code."
    )
    result = CodeBrain().process({
        "original_text": prompt,
        "main_topic": "code",
        "intent": "code_generation",
    })
    code = result["generated_code"]
    assert_true(result["program_kind"] == "habit_tracker", "Code recipe routing chose the wrong project.")
    assert_true("habit_records.json" in code, "Code recipe lost the exact requested filename.")
    assert_true(result["project_recipe"]["id"], "Code generation did not use its project recipe database.")
    assert_true(result["self_review"]["ready"], "Complete recipe output failed self-review.")
    assert_true(result["code_metrics"]["syntax_valid"], "Generated recipe code has invalid Python syntax.")


def test_code_review_checks_edit_export_and_fields():
    review = CodeBrain().self_reviewer.review_and_improve(
        "def main():\n    print('incomplete')\n\nif __name__ == \"__main__\":\n    main()\n",
        "python",
        "Build a runnable notes app. Edit and export notes with title, body and tags.",
        "notes_app",
    )
    failed = {item["requirement"] for item in review["request_alignment"]["failed"]}
    assert_true("operation_edit" in failed, "Self-review did not check the edit operation.")
    assert_true("operation_export" in failed, "Self-review did not check the export operation.")
    assert_true("field_tags" in failed, "Self-review did not check a requested data field.")


def test_geography_uses_exact_index_and_structured_answer():
    result = GeographyBrain().process({
        "original_text": "What is the capital of Albania?",
        "main_topic": "geography",
        "intent": "question",
    })
    answer = result.get("structured_answer", {})
    assert_true(result.get("index_used"), "Geography did not use its fast index.")
    assert_true(result.get("candidate_records", 999) <= 5, "Exact geography lookup searched too many records.")
    assert_true(answer.get("capital") == "Tirana", "Capital lookup returned the wrong answer.")
    assert_true(result.get("place_detected") == "albania", "Geography selected the wrong place.")


def test_geography_distance_and_concept_definition():
    brain = GeographyBrain()
    distance = brain.process({
        "original_text": "What is the distance between Tokyo and Paris?",
        "main_topic": "geography",
        "intent": "question",
    }).get("structured_answer", {}).get("straight_line_distance", {})
    assert_true(9600 < distance.get("kilometers", 0) < 9900, "Great-circle distance is implausible.")
    concept = brain.process({
        "original_text": "Explain what a drainage basin is.",
        "main_topic": "geography",
        "intent": "question",
    })
    definition = concept.get("structured_answer", {}).get("definition", "").lower()
    assert_true("land area" in definition and "drain" in definition, "Geographic concept definition is too weak.")


def test_creative_uses_geography_inverted_index():
    brain = CreativeBrain()
    context = brain.collect_indexed_geography_context(
        ["sahara", "desert", "journey"],
        "Create a story set in the Sahara Desert",
        limit=4,
    )
    assert_true(context, "Creative brain found no indexed geography context.")
    assert_true(
        any("place:sahara desert" in key for key in context),
        "Creative brain did not retrieve the exact requested place."
    )
    assert_true(
        all(item.get("retrieval_mode") == "geography_inverted_index" for item in context.values()),
        "Creative geography retrieval did not use the fast index."
    )


def test_manager_builds_targeted_retry_context():
    manager = ManagerBrain()
    quality = {
        "retry_requests": [{
            "target_brain": "Code_brain",
            "problem": "Missing delete operation",
            "instruction": "Add delete by number."
        }]
    }
    context = manager.build_retry_context(
        {"original_text": "Build an app"},
        {"Code_brain": {"generated_code": "def main(): pass"}},
        {},
        {},
        {},
        quality,
        "Code_brain",
        quality["retry_requests"][0]
    )
    assert_true(context["retry_target"] == "Code_brain", "Retry should target one specialist.")
    assert_true(context["retry_instructions"] == ["Add delete by number."], "Retry should contain exact correction instructions.")
    assert_true(context["previous_attempt"], "Retry should preserve the previous attempt.")


def test_manager_shares_results_inside_same_phase():
    class FirstBrain:
        def process(self, data):
            return {"brain": "First_brain", "answer": "first result"}

    class SecondBrain:
        def process(self, data):
            seen = data.get("results", {}).get("First_brain", {}).get("answer")
            return {"brain": "Second_brain", "saw_first": seen}

    manager = ManagerBrain()
    manager.register_brain("First_brain", FirstBrain())
    manager.register_brain("Second_brain", SecondBrain())
    results = manager.execute(
        ["First_brain", "Second_brain"],
        {"original_text": "test", "results": {}},
        {"main_topic": "general", "intent": "request"},
        {},
        "test_phase"
    )
    assert_true(results["Second_brain"]["saw_first"] == "first result", "Brains in one phase must see earlier results.")


def test_collaboration_brain_runs_bounded_peer_dialogue():
    class ConsultingBrain:
        def __init__(self, name):
            self.name = name

        def process(self, data):
            dialogue = data.get("brain_dialogue", {})
            return {
                "brain": self.name,
                "answer": f"{self.name} improved its result",
                "saw_peer_messages": len(dialogue.get("peer_messages", [])),
                "answered_question": bool(dialogue.get("question")),
            }

    manager = ManagerBrain()
    coordinator = CollaborationBrain()
    manager.register_brain("Collaboration_brain", coordinator)
    manager.register_brain("Code_brain", ConsultingBrain("Code_brain"))
    manager.register_brain("Planner_brain", ConsultingBrain("Planner_brain"))
    manager.register_brain("Reasoning_brain", ConsultingBrain("Reasoning_brain"))
    report = {"main_topic": "code", "intent": "code_generation"}
    initial_results = {
        "Code_brain": {"brain": "Code_brain", "code": "print('hello')"},
        "Planner_brain": {"brain": "Planner_brain", "plan": ["write", "check"]},
        "Reasoning_brain": {"brain": "Reasoning_brain", "analysis": "Check requirements"},
    }
    planning = coordinator.process({
        "understanding": report,
        "routing_decision": manager.routing_decision(report, {}),
        "results": initial_results,
    })
    replies, consensus = manager.execute_collaboration_round(
        {"original_text": "Write Python code", "results": initial_results},
        report,
        {},
        initial_results,
        planning,
    )
    assert_true(len(planning["consultation_requests"]) == 3, "Consultation should include the relevant team.")
    assert_true(all(item.get("saw_peer_messages") for item in replies.values()), "Every participant must see peer messages.")
    assert_true(all(item.get("answered_question") for item in replies.values()), "Every participant must receive a question.")
    assert_true(consensus and consensus["round"] == "consensus", "Coordinator must consolidate the replies.")
    assert_true(consensus["bounded"], "Internal dialogue must be bounded.")


def test_scanner_context_reaches_every_brain():
    class EvidenceAwareBrain:
        def process(self, data):
            scanner = data.get("scanner_knowledge", {})
            return {
                "brain": "EvidenceAwareBrain",
                "saw_scanner": scanner.get("available"),
                "saw_excerpt": bool(scanner.get("matches", [{}])[0].get("content_excerpt")),
            }

    manager = ManagerBrain()
    manager.register_brain("Science_brain", EvidenceAwareBrain())
    knowledge = {
        "available": True,
        "matches": [{
            "article_id": "knowledge_test",
            "title": "Test evidence",
            "summary": "A concise evidence summary.",
            "content_excerpt": "A longer scanner article excerpt used by specialist brains.",
            "trust_score": 94,
            "source_count": 2,
            "sources": [{"source_id": "pubmed"}, {"source_id": "crossref"}],
        }]
    }
    results = manager.execute(
        ["Science_brain"],
        {
            "original_text": "Explain the evidence",
            "knowledge": knowledge,
            "dictionary": {},
            "data_context": {},
            "full_data_context": {},
            "shared_context": {},
        },
        {"main_topic": "science", "intent": "question"},
        {},
        "scanner_test",
    )
    result = results["Science_brain"]
    assert_true(result["saw_scanner"] and result["saw_excerpt"], "A specialist did not receive scanner evidence.")
    assert_true(result["scanner_context"]["received"], "Manager did not record scanner delivery.")
    assert_true(result["scanner_context"]["required"], "Factual brains must be grounded when evidence exists.")
    assert_true(set(result["scanner_context"]["sources"]) == {"pubmed", "crossref"}, "Source IDs were lost.")


def test_reliable_source_parsers():
    collector = KnowledgeCollector()
    pubmed_xml = """
    <PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
    <Journal><Title>Reliable Journal</Title><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
    <ArticleTitle>Evidence-based test article</ArticleTitle><Abstract><AbstractText Label="BACKGROUND">
    This is a sufficiently detailed publisher abstract describing methods, observations, evidence,
    limitations, and conclusions for a parser regression test in the local Canri knowledge collector.
    </AbstractText></Abstract></Article></MedlineCitation><PubmedData><ArticleIdList>
    <ArticleId IdType="doi">10.1000/test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>
    """
    collector.request_text = lambda *args, **kwargs: pubmed_xml
    pubmed = collector.fetch_pubmed_articles(["123"])
    assert_true(len(pubmed) == 1 and pubmed[0]["source_id"] == "pubmed", "PubMed XML was not parsed.")
    assert_true("BACKGROUND" in pubmed[0]["text"], "Structured PubMed abstract labels were lost.")

    collector.request_json = lambda *args, **kwargs: {
        "message": {"items": [{
            "DOI": "10.1000/crossref-test",
            "title": ["Crossref evidence record"],
            "abstract": "<jats:p>This publication abstract contains enough meaningful evidence, methodology, context, limitations, and conclusions to pass the collector content threshold safely.</jats:p>",
            "publisher": "Test Publisher",
            "container-title": ["Test Journal"],
            "published": {"date-parts": [[2025]]},
        }]}
    }
    crossref = collector.search_crossref_articles("evidence", 1)
    assert_true(len(crossref) == 1 and crossref[0]["source_id"] == "crossref", "Crossref JSON was not parsed.")
    assert_true("<jats" not in crossref[0]["text"], "Crossref JATS markup was not cleaned.")


def test_history_uses_indexed_events_and_timelines():
    history = HistoryBrain()
    causal = history.process("Why did World War 1 begin, and what followed it?")
    timeline = history.process("Give a timeline of the French and Haitian revolutions.")
    figure = history.process("Who was Alan Turing?")

    assert_true(causal.get("verified"), "History should find a curated local event.")
    assert_true("alliance" in causal.get("final_output", "").lower(), "History lost the indexed causes.")
    titles = [item.get("title") for item in timeline.get("timeline", [])]
    assert_true("French Revolution" in titles and "Haitian Revolution" in titles, "History timeline is incomplete.")
    assert_true("Alan Turing" in figure.get("final_output", ""), "History figure lookup failed.")


def test_historical_importance_routes_to_history_not_language():
    prompt = "Explain why the printing press was historically important in three sentences."
    report = UnderstandingBrain().process(prompt)
    manager = ManagerBrain()
    decision = manager.routing_decision(report, {})

    assert_true(report.get("main_topic") == "history", "Understanding misclassified a history request.")
    assert_true(decision.get("primary_brain") == "History_brain", "History request leaked to Language_brain.")


def test_math_extended_solvers_and_verification():
    math_brain = MathBrain()
    linear = math_brain.process("Solve 2x + 3 = 5x - 9 step by step")
    system = math_brain.process("Solve 2x + y = 5; x - y = 1")
    fraction = math_brain.process("Calculate 1/2 + 3/4")
    probability = math_brain.process("Probability with 3 favorable outcomes out of 10 total outcomes")

    assert_true(linear.get("answer") == 4 and linear["verification"]["passed"], "Two-sided linear solving failed.")
    assert_true(system.get("answer") == {"x": 2.0, "y": 1.0}, "Linear-system answer is wrong.")
    assert_true(system["verification"]["passed"], "Linear-system substitution failed.")
    assert_true(fraction.get("answer") == "5/4", "Exact fraction arithmetic failed.")
    assert_true(abs(probability.get("answer", 0) - 0.3) < 1e-12, "Probability solver was not selected.")
    assert_true(bool(linear.get("formula_context")), "Math did not retrieve indexed formula context.")


def test_creative_registers_non_rule_project_data():
    creative = CreativeBrain()
    required = {
        "Code_project_recipes.json",
        "Planner_quality_patterns.json",
        "History_events.json",
        "History_index.json",
        "Math_formulas.json",
        "Math_problem_patterns.json",
    }
    assert_true(required.issubset(creative.canri_index), "Creative data index is missing new non-rule files.")
    assert_true("Learning_rules.json" not in creative.canri_index, "Creative must not use behavior rules as idea data.")
    assert_true("Planner_risk_rules.json" not in creative.canri_index, "Creative must not ingest risk rules as idea data.")


def test_emotional_conversation_routes_to_support():
    prompt = "I feel lonely and I need someone to talk to."
    understanding = UnderstandingBrain().process(prompt)
    assert_true(understanding.get("main_topic") == "emotion", "Understanding missed an emotional conversation.")

    manager = ManagerBrain()
    decision = manager.routing_decision(understanding, {})
    assert_true(decision.get("primary_brain") == "Emotion_brain", "Manager did not route emotional support correctly.")

    emotion = EmotionBrain()
    emotion.update_statistics = lambda *args, **kwargs: None
    emotion_result = emotion.process({"original_text": prompt, "understanding": understanding})
    assert_true(emotion_result.get("conversation_intent") == "emotional_support", "Emotion intent is wrong.")
    assert_true(bool(emotion_result.get("support_response")), "Emotion did not produce support text.")
    assert_true(bool(emotion_result.get("support_strategy")), "Emotion did not retrieve a support strategy.")

    response = ResponseBrain()
    response.update_statistics = lambda *args, **kwargs: None
    final = response.process({
        "original_text": prompt,
        "understanding": understanding,
        "results": {"Emotion_brain": emotion_result}
    })
    assert_true(final.get("primary_brain") == "Emotion_brain", "Response did not select emotional support.")
    assert_true("Goal:" not in final.get("display_text", ""), "Response leaked an internal creative report.")


def test_emotion_does_not_override_code():
    prompt = "I am frustrated, but write a runnable Python calculator."
    report = {"main_topic": "code", "intent": "code_generation", "original_text": prompt}
    response = ResponseBrain()
    response.update_statistics = lambda *args, **kwargs: None
    result = response.process({
        "original_text": prompt,
        "understanding": report,
        "results": {
            "Emotion_brain": {
                "conversation_intent": "venting",
                "support_response": "That sounds frustrating.",
                "primary_emotion": "anger"
            },
            "Code_brain": {
                "generated_code": "def main():\n    print(2 + 2)\n\nif __name__ == '__main__':\n    main()",
                "confidence": 90
            }
        }
    })
    assert_true(result.get("primary_brain") == "Code_brain", "Emotion incorrectly replaced a code result.")
    assert_true("def main" in result.get("display_text", ""), "Code output disappeared from the response.")


def test_creative_uses_emotion_output_without_story():
    creative = CreativeBrain()
    creative.update_statistics = lambda *args, **kwargs: None
    creative.remember_creative_result = lambda *args, **kwargs: None
    result = creative.process({
        "original_text": "Can we talk? I feel worried.",
        "understanding": {
            "original_text": "Can we talk? I feel worried.",
            "main_topic": "emotion",
            "intent": "conversation"
        },
        "results": {
            "Emotion_brain": {
                "support_response": "The worry sounds real. What is the most immediate concern?"
            }
        }
    })
    assert_true(result["execution_policy"]["mode"] == "conversation_support", "Creative used the wrong emotional mode.")
    assert_true(result.get("domain") == "emotion", "Creative changed emotional support into another domain.")
    assert_true("Use mechanism" not in result.get("final_output", ""), "Creative returned instructions instead of support.")


def test_image_request_spec_and_clean_svg():
    image = ImageBrain()
    image.save_history = lambda: None
    image.update_statistics = lambda *args, **kwargs: None
    result = image.process("Create a friendly robot poster, 16:9, neon, wide shot, blue and gold.")
    spec = result.get("request_spec", {})
    assert_true(spec.get("aspect_ratio") == "16:9", "Image aspect ratio was not understood.")
    assert_true(spec.get("width") == 1280 and spec.get("height") == 720, "Image dimensions are wrong.")
    assert_true("neon" in spec.get("lighting", []), "Image lighting detail was lost.")
    svg = Path(result["image_file"]).read_text(encoding="utf-8")
    assert_true("display: none" in svg, "SVG preview still shows the oversized generated title.")
    assert_true(result["engine_status"]["external_raster_model"] == "not_configured", "Image engine status is misleading.")


def test_vision_ast_and_safe_archive_inspection():
    directory = PROJECT_ROOT / "Canri_Tests" / "runtime_fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    code_path = directory / "vision_sample.py"
    code_path.write_text("import json\n\ndef hello(name):\n    return f'Hello {name}'\n", encoding="utf-8")
    archive_path = directory / "vision_sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("docs/readme.txt", "safe preview")

    vision = VisionBrain()
    vision.update_statistics = lambda *args, **kwargs: None
    result = vision.process({"files": [str(code_path), str(archive_path)]})
    files = {Path(item["path"]).suffix: item for item in result["files"]}
    assert_true(files[".py"]["content_analysis"]["python_ast"]["syntax_valid"], "Python AST validation failed.")
    assert_true("hello" in files[".py"]["content_analysis"]["python_ast"]["functions"], "Vision missed a Python function.")
    assert_true(files[".zip"]["archive_analysis"]["entry_count"] == 1, "Archive structure was not inspected.")
    assert_true(files[".zip"]["archive_analysis"]["extracted"] is False, "Vision must not extract archives.")


def test_voice_real_wav_signal_analysis():
    directory = PROJECT_ROOT / "Canri_Tests" / "runtime_fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    wav_path = directory / "voice_tone.wav"
    samples = [int(12000 * ((index % 20) / 10 - 1)) for index in range(8000)]
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(b"".join(struct.pack("<h", value) for value in samples))

    voice = VoiceBrain()
    voice.update_statistics = lambda *args, **kwargs: None
    result = voice.process({"files": [str(wav_path)]})
    signal = result["media"][0]["signal_analysis"]
    assert_true(signal.get("available"), "Voice did not analyze real WAV samples.")
    assert_true(signal.get("rms_level", 0) > 0, "Voice RMS should be greater than zero.")
    assert_true(result["media"][0]["transcript"] is None, "Voice invented a transcript.")


def test_creative_registers_emotion_and_media_data():
    creative = CreativeBrain()
    required = {
        "Conversation_patterns.json",
        "Emotional_support_strategies.json",
        "Image_generation_profiles.json",
        "Media_analysis_profiles.json",
        "Audio_analysis_profiles.json",
    }
    assert_true(required.issubset(creative.canri_index), "Creative index is missing emotional or media data.")


def main():
    tests = [
        test_expense_tracker_code_and_quality,
        test_quadratic_math,
        test_math_ignores_request_words_around_expression,
        test_science_prefers_the_exact_user_topic,
        test_quality_treats_code_analysis_as_explanation,
        test_understanding_preserves_original_file_names,
        test_standard_library_does_not_mean_book_library,
        test_atoms_route_to_science,
        test_learning_does_not_use_creativity_for_missing_metadata,
        test_response_blocks_bad_quality,
        test_quality_catches_wrong_program_kind,
        test_fact_check_evidence_coverage,
        test_creative_story_returns_final_story,
        test_creative_code_returns_real_code,
        test_creative_uses_indexed_snippets_and_dictionary_entries,
        test_understanding_builds_complete_request_contract,
        test_inline_code_punctuation_and_function_spelling,
        test_company_and_product_context_is_expanded,
        test_manager_routes_specialists_without_domain_leakage,
        test_memory_keeps_continuation_inside_one_session,
        test_data_context_is_filtered_per_brain,
        test_response_hides_quality_metadata_for_strict_output,
        test_code_self_review_checks_request_alignment,
        test_planner_covers_every_request_requirement,
        test_code_recipe_builds_new_program_kind_and_exact_file,
        test_code_review_checks_edit_export_and_fields,
        test_geography_uses_exact_index_and_structured_answer,
        test_geography_distance_and_concept_definition,
        test_creative_uses_geography_inverted_index,
        test_manager_builds_targeted_retry_context,
        test_manager_shares_results_inside_same_phase,
        test_collaboration_brain_runs_bounded_peer_dialogue,
        test_scanner_context_reaches_every_brain,
        test_reliable_source_parsers,
        test_history_uses_indexed_events_and_timelines,
        test_historical_importance_routes_to_history_not_language,
        test_math_extended_solvers_and_verification,
        test_creative_registers_non_rule_project_data,
        test_emotional_conversation_routes_to_support,
        test_emotion_does_not_override_code,
        test_creative_uses_emotion_output_without_story,
        test_image_request_spec_and_clean_svg,
        test_vision_ast_and_safe_archive_inspection,
        test_voice_real_wav_signal_analysis,
        test_creative_registers_emotion_and_media_data,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All Canri regression checks passed.")


if __name__ == "__main__":
    main()
