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
        test_manager_builds_targeted_retry_context,
        test_manager_shares_results_inside_same_phase,
        test_collaboration_brain_runs_bounded_peer_dialogue,
        test_scanner_context_reaches_every_brain,
        test_reliable_source_parsers,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All Canri regression checks passed.")


if __name__ == "__main__":
    main()
