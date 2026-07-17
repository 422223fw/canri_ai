"""
Creative_brain.py
Canri AI

Creative_brain is Canri's backup and invention engine.
It uses combinational creativity + evolutionary creativity:
- generate many candidate ideas
- score relevance, novelty, coherence, usefulness, and safety
- keep the best ideas
- mutate/merge them
- stop when improvement is small or quality is high enough
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from Data_context import build_shared_data_context, context_view_for_brain
except (ImportError, ModuleNotFoundError):
    build_shared_data_context = None
    context_view_for_brain = None


DATA_DIR = Path(__file__).parent / "data"
SEEDS_FILE = DATA_DIR / "Creative_seed_bank.json"
RULES_FILE = DATA_DIR / "Creative_scoring_rules.json"
GRAPHS_FILE = DATA_DIR / "Creative_evolution_graphs.json"
STATS_FILE = DATA_DIR / "Creative_statistics.json"
MEMORY_FILE = DATA_DIR / "Creative_memory.json"
WRITING_RULES_FILE = DATA_DIR / "Creative_writing_rules.json"

ALWAYS_CANRI_DATA_FILES = [
    "Learning_history.json",
    "Learning_statistics.json",
    "Improvement_queue.json",
    "Brain_performance.json",
    "Memory_database.json",
    "Planner_task_templates.json",
    "Planner_dependency_graph.json",
    "Planner_quality_patterns.json",
    "Reasoning_patterns.json",
    "Knowledge_index.json",
    "Knowledge_statistics.json",
]

DOMAIN_CANRI_DATA_FILES = {
    "code": [
        "code.json",
        "Code_terms_dictionary.json",
        "Punctuation_dictionary.json",
        "Code_dependency_graph.json",
        "Code_composition_tables.json",
        "Code_assembly_patterns.json",
        "Code_project_recipes.json",
        "Code_statistics.json",
        "Technology_terms.json",
        "Technical_terms.json"
    ],
    "game": [
        "Game_types.json",
        "Game_mechanics.json",
        "Game_systems.json",
        "Game_balance_rules.json",
        "Game_design_graph.json",
        "Game_statistics.json",
        "Story_templates.json",
        "Character_templates.json",
        "World_templates.json"
    ],
    "story": [
        "Story_templates.json",
        "Story_structures.json",
        "Story_genres.json",
        "Character_templates.json",
        "Character_traits.json",
        "World_templates.json",
        "World_rules.json",
        "Emotion_patterns.json"
    ],
    "science": [
        "Articles.json",
        "Articles_statistics.json",
        "Technical_terms.json",
        "Units_dictionary.json",
        "research_sources.json"
    ],
    "technology": [
        "Technology_terms.json",
        "Hardware_dictionary.json",
        "Tech_stack_templates.json",
        "Technical_terms.json",
        "Abbreviations.json"
    ],
    "language": [
        "Punctuation_dictionary.json",
        "Translation_dictionary.json",
        "Synonyms.json",
        "Antonyms.json",
        "Idioms.json",
        "Slang_dictionary.json",
        "Language_examples.json",
        "Language_models.json",
        "Language_rules.json"
    ],
    "geography": [
        "Geography_places.json",
        "Geography_concepts.json",
        "Geography_regions.json",
        "Geography_index.json",
        "Geography_relations.json",
        "Geography_query_patterns.json",
        "Geography_creative_profiles.json",
        "Geography_statistics.json",
        "research_sources.json"
    ],
    "history": [
        "history_knowledge.json",
        "history_sources.json",
        "History_events.json",
        "History_figures.json",
        "History_timelines.json",
        "History_index.json",
        "Articles.json",
        "research_sources.json"
    ],
    "math": [
        "Math_formulas.json",
        "Math_problem_patterns.json",
        "Math_examples.json",
        "Math_index.json",
        "Units_dictionary.json",
        "Math_statistics.json"
    ],
    "security": [
        "research_sources.json",
        "Technical_terms.json",
        "Code_dependency_graph.json"
    ],
    "emotion": [
        "Emotion_patterns.json",
        "Emotion_response_styles.json",
        "Conversation_patterns.json",
        "Emotional_support_strategies.json"
    ],
    "image_generation": [
        "Image_styles.json",
        "Image_subject_templates.json",
        "Image_prompt_templates.json",
        "Image_composition_rules.json",
        "Image_generation_profiles.json",
        "Image_history.json"
    ],
    "vision": [
        "Vision_file_profiles.json",
        "Vision_magic_signatures.json",
        "Media_analysis_profiles.json"
    ],
    "voice": [
        "Voice_audio_profiles.json",
        "Voice_magic_signatures.json",
        "Voice_processing_tasks.json",
        "Audio_analysis_profiles.json"
    ],
    "general": [
        "Company_products.json",
        "Punctuation_dictionary.json",
        "Translation_dictionary.json",
        "Synonyms.json",
        "Articles.json",
        "Technical_terms.json"
    ]
}

CANRI_DATA_FILES = [
    "Planner_task_templates.json",
    "Planner_dependency_graph.json",
    "Planner_quality_patterns.json",
    "Reasoning_patterns.json",
    "Code_dependency_graph.json",
    "Code_project_recipes.json",
    "Translation_dictionary.json",
    "Synonyms.json",
    "Articles.json",
    "Knowledge_index.json"
]

# Rules control behavior and must not be treated as creative source material.
# Quality patterns are evidence/checklists, not executable policy, so they stay available.
CREATIVE_DATA_EXCLUDED_SUFFIXES = ("_rules.json", "_risk_rules.json")
CREATIVE_DATA_EXCLUDED_FILES = {
    "Creative_scoring_rules.json",
    "Learning_rules.json",
    "Reasoning_rules.json",
}

GENERIC_TERMS = {
    "the", "and", "for", "with", "that", "this", "what", "how",
    "why", "create", "make", "build", "thing", "idea",
    "תעשה", "תכין", "לי", "של", "את", "מה", "איך", "זה"
}

UNSAFE_TERMS = {
    "bomb", "weapon", "suicide", "malware", "phishing", "ransomware",
    "פצצה", "נשק", "להתאבד", "פישינג"
}


class CreativeCodeAssembler:

    def __init__(self, creative_brain):

        self.creative_brain = creative_brain

    def assemble(self, request, rescue_result=None):

        request = request if isinstance(request, dict) else {
            "original_text": str(request)
        }
        rescue_result = rescue_result or {}

        report = self.creative_brain.get_understanding_report(request)
        memory_report = self.creative_brain.get_memory_report(request)
        text = self.creative_brain.extract_text(request, report)
        terms = self.creative_brain.collect_terms(report, memory_report, text)
        language = self.detect_language(text, terms)
        canri_context = self.creative_brain.collect_canri_context(
            "code",
            terms,
            request
        )
        graph_plan = self.build_code_graph(terms, canri_context)
        code = self.generate_code(language, terms, graph_plan)

        return {
            "brain": "Creative_brain",
            "purpose": "creative_code_assembly",
            "language": language,
            "terms_used": terms[:80],
            "code_graph": graph_plan,
            "canri_code_context": {
                file_name: {
                    "count": data.get("count", 0),
                    "matched_terms": data.get("matched_terms", [])[:20],
                    "sample_terms": data.get("sample_terms", [])[:10]
                }
                for file_name, data in canri_context.items()
                if file_name.startswith("Code_") or file_name == "code.json"
            },
            "generated_code": code,
            "assembly_notes": [
                "CreativeCodeAssembler used code snippets, dependency graph, composition tables, and creative evolution context.",
                "The generated code is a safe draft for Code_brain to refine, not executed code.",
                "Security_brain should review before running generated code."
            ],
            "confidence": self.estimate_confidence(terms, graph_plan, canri_context)
        }

    def detect_language(self, text, terms):

        lowered = f"{text.lower()} {' '.join(terms)}"

        language_rules = [
            ("python", ["python", "py", "tkinter", "pygame", "fastapi", "django"]),
            ("javascript", ["javascript", "js", "node", "react", "express"]),
            ("java", ["java", "spring", "minecraft"]),
            ("html", ["html", "css", "website", "page"]),
            ("csharp", ["c#", "csharp", "unity"]),
            ("cpp", ["c++", "cpp", "unreal"])
        ]

        for language, keywords in language_rules:
            if any(keyword in lowered for keyword in keywords):
                return language

        return "python"

    def build_code_graph(self, terms, canri_context):

        matched = []

        for file_name, data in canri_context.items():
            if file_name in [
                "code.json",
                "Code_dependency_graph.json",
                "Code_composition_tables.json",
                "Code_assembly_patterns.json"
            ]:
                matched.extend(data.get("matched_terms", [])[:30])

        if not matched:
            matched = terms[:12]

        nodes = list(dict.fromkeys(
            self.normalize_code_node(term)
            for term in matched[:18]
            if term
        ))

        if not nodes:
            nodes = [
                "input_parser",
                "core_logic",
                "validator",
                "result_builder"
            ]

        edges = []
        for index in range(len(nodes) - 1):
            edges.append({
                "from": nodes[index],
                "to": nodes[index + 1],
                "reason": "assembly_order"
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "order": nodes,
            "strategy": "evolutionary_code_composition",
            "missing_parts": [
                node
                for node in nodes
                if node in {"core_logic", "validator", "result_builder"}
            ][:6]
        }

    def normalize_code_node(self, term):

        term = re.sub(r"[^a-zA-Z0-9_]+", "_", str(term).lower()).strip("_")

        if not term:
            return ""

        replacements = {
            "inventory": "inventory_system",
            "save": "save_system",
            "load": "load_system",
            "player": "player_model",
            "enemy": "enemy_model",
            "api": "api_handler",
            "json": "json_serializer",
            "security": "security_validator",
            "file": "file_handler"
        }

        return replacements.get(term, term[:48])

    def generate_code(self, language, terms, graph_plan):

        if language == "javascript":
            return self.generate_javascript(graph_plan)

        if language == "java":
            return self.generate_java(terms)

        if language == "html":
            return self.generate_html(terms)

        return self.generate_python(terms, graph_plan)

    def generate_python(self, terms, graph_plan):

        term_text = " ".join(str(term).lower() for term in terms)

        if any(term in term_text for term in ["expense", "spending", "category"]):
            return self.generate_expense_tracker_python()

        if any(term in term_text for term in ["todo", "to do", "task"]):
            return self.generate_todo_python()

        if any(term in term_text for term in ["note", "notes"]):
            return self.generate_notes_python()

        if any(term in term_text for term in ["calculator", "calculate", "math"]):
            return self.generate_calculator_python()

        return self.generate_generic_cli_python(terms, graph_plan)

    def generate_expense_tracker_python(self):

        return "\n".join([
            "import json",
            "from pathlib import Path",
            "",
            "EXPENSES_FILE = Path(\"expenses.json\")",
            "",
            "",
            "def load_expenses():",
            "    if not EXPENSES_FILE.exists():",
            "        return []",
            "    try:",
            "        data = json.loads(EXPENSES_FILE.read_text(encoding=\"utf-8\"))",
            "    except json.JSONDecodeError:",
            "        print(\"Could not read expenses.json. Starting empty.\")",
            "        return []",
            "    return data if isinstance(data, list) else []",
            "",
            "",
            "def save_expenses(expenses):",
            "    EXPENSES_FILE.write_text(json.dumps(expenses, indent=2, ensure_ascii=False), encoding=\"utf-8\")",
            "",
            "",
            "def add_expense(expenses):",
            "    try:",
            "        amount = float(input(\"Amount: \").strip())",
            "    except ValueError:",
            "        print(\"Amount must be a number.\")",
            "        return",
            "    category = input(\"Category: \").strip()",
            "    description = input(\"Description: \").strip()",
            "    if not category or not description:",
            "        print(\"Category and description are required.\")",
            "        return",
            "    expenses.append({\"amount\": amount, \"category\": category, \"description\": description})",
            "    save_expenses(expenses)",
            "    print(\"Expense saved.\")",
            "",
            "",
            "def list_expenses(expenses):",
            "    if not expenses:",
            "        print(\"No expenses yet.\")",
            "        return",
            "    for index, expense in enumerate(expenses, start=1):",
            "        print(f\"{index}. ${expense.get('amount', 0):.2f} | {expense.get('category', '')} | {expense.get('description', '')}\")",
            "",
            "",
            "def search_by_category(expenses, category):",
            "    category = category.strip().lower()",
            "    matches = [expense for expense in expenses if expense.get(\"category\", \"\").lower() == category]",
            "    if not matches:",
            "        print(\"No matching expenses found.\")",
            "        return",
            "    list_expenses(matches)",
            "",
            "",
            "def show_total(expenses):",
            "    total = sum(float(expense.get(\"amount\", 0)) for expense in expenses)",
            "    print(f\"Total spent: ${total:.2f}\")",
            "",
            "",
            "def delete_expense(expenses, raw_number):",
            "    try:",
            "        index = int(raw_number) - 1",
            "    except ValueError:",
            "        print(\"Please enter a valid expense number.\")",
            "        return",
            "    if index < 0 or index >= len(expenses):",
            "        print(\"Expense number is out of range.\")",
            "        return",
            "    removed = expenses.pop(index)",
            "    save_expenses(expenses)",
            "    print(f\"Deleted: {removed.get('description', '')}\")",
            "",
            "",
            "def print_help():",
            "    print(\"Commands: add, list, search <category>, total, delete <number>, help, quit\")",
            "",
            "",
            "def main():",
            "    expenses = load_expenses()",
            "    print(\"Expense Tracker\")",
            "    print_help()",
            "    while True:",
            "        command = input(\"> \").strip()",
            "        lowered = command.lower()",
            "        if lowered == \"add\":",
            "            add_expense(expenses)",
            "        elif lowered == \"list\":",
            "            list_expenses(expenses)",
            "        elif lowered.startswith(\"search \"):",
            "            search_by_category(expenses, command[7:])",
            "        elif lowered == \"total\":",
            "            show_total(expenses)",
            "        elif lowered.startswith(\"delete \"):",
            "            delete_expense(expenses, command[7:].strip())",
            "        elif lowered == \"help\":",
            "            print_help()",
            "        elif lowered == \"quit\":",
            "            save_expenses(expenses)",
            "            break",
            "        else:",
            "            print(\"Unknown command. Type help for commands.\")",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    main()",
            ""
        ])

    def generate_todo_python(self):

        return self.generate_generic_json_cli_python(
            "tasks.json",
            "Task Manager",
            "task"
        )

    def generate_notes_python(self):

        return self.generate_generic_json_cli_python(
            "notes.json",
            "Notes App",
            "note"
        )

    def generate_calculator_python(self):

        return "\n".join([
            "def calculate(left, operator, right):",
            "    if operator == \"+\":",
            "        return left + right",
            "    if operator == \"-\":",
            "        return left - right",
            "    if operator == \"*\":",
            "        return left * right",
            "    if operator == \"/\":",
            "        if right == 0:",
            "            raise ZeroDivisionError(\"Cannot divide by zero.\")",
            "        return left / right",
            "    if operator == \"%\":",
            "        return left * right / 100",
            "    raise ValueError(\"Unknown operator.\")",
            "",
            "",
            "def main():",
            "    print(\"Calculator\")",
            "    print(\"Use: number operator number. Example: 10 % 25\")",
            "    print(\"Type quit to exit.\")",
            "    while True:",
            "        raw = input(\"> \").strip()",
            "        if raw.lower() == \"quit\":",
            "            break",
            "        parts = raw.split()",
            "        if len(parts) != 3:",
            "            print(\"Use format: number operator number\")",
            "            continue",
            "        try:",
            "            left = float(parts[0])",
            "            operator = parts[1]",
            "            right = float(parts[2])",
            "            print(calculate(left, operator, right))",
            "        except (ValueError, ZeroDivisionError) as error:",
            "            print(error)",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    main()",
            ""
        ])

    def generate_generic_json_cli_python(self, file_name, title, item_name):

        return "\n".join([
            "import json",
            "from pathlib import Path",
            "",
            f"DATA_FILE = Path(\"{file_name}\")",
            "",
            "",
            "def load_items():",
            "    if not DATA_FILE.exists():",
            "        return []",
            "    try:",
            "        data = json.loads(DATA_FILE.read_text(encoding=\"utf-8\"))",
            "    except json.JSONDecodeError:",
            "        return []",
            "    return data if isinstance(data, list) else []",
            "",
            "",
            "def save_items(items):",
            "    DATA_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding=\"utf-8\")",
            "",
            "",
            "def add_item(items):",
            "    title = input(\"Title: \").strip()",
            "    details = input(\"Details: \").strip()",
            "    if not title:",
            "        print(\"Title is required.\")",
            "        return",
            "    items.append({\"title\": title, \"details\": details, \"done\": False})",
            "    save_items(items)",
            f"    print(\"{item_name.title()} saved.\")",
            "",
            "",
            "def list_items(items):",
            "    if not items:",
            "        print(\"No items yet.\")",
            "        return",
            "    for index, item in enumerate(items, start=1):",
            "        mark = \"x\" if item.get(\"done\") else \" \"",
            "        print(f\"{index}. [{mark}] {item.get('title', '')} - {item.get('details', '')}\")",
            "",
            "",
            "def search_items(items, word):",
            "    word = word.strip().lower()",
            "    matches = [item for item in items if word in item.get(\"title\", \"\").lower() or word in item.get(\"details\", \"\").lower()]",
            "    list_items(matches)",
            "",
            "",
            "def delete_item(items, raw_number):",
            "    try:",
            "        index = int(raw_number) - 1",
            "    except ValueError:",
            "        print(\"Enter a valid number.\")",
            "        return",
            "    if index < 0 or index >= len(items):",
            "        print(\"Number is out of range.\")",
            "        return",
            "    removed = items.pop(index)",
            "    save_items(items)",
            "    print(f\"Deleted: {removed.get('title', '')}\")",
            "",
            "",
            "def main():",
            "    items = load_items()",
            f"    print(\"{title}\")",
            "    print(\"Commands: add, list, search <word>, delete <number>, quit\")",
            "    while True:",
            "        command = input(\"> \").strip()",
            "        lowered = command.lower()",
            "        if lowered == \"add\":",
            "            add_item(items)",
            "        elif lowered == \"list\":",
            "            list_items(items)",
            "        elif lowered.startswith(\"search \"):",
            "            search_items(items, command[7:])",
            "        elif lowered.startswith(\"delete \"):",
            "            delete_item(items, command[7:].strip())",
            "        elif lowered == \"quit\":",
            "            save_items(items)",
            "            break",
            "        else:",
            "            print(\"Unknown command.\")",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    main()",
            ""
        ])

    def generate_generic_cli_python(self, terms, graph_plan):

        class_name = self.class_name_from_terms(terms)
        nodes = graph_plan.get("order", [])
        lines = [
            "# Generated by Creative_brain CreativeCodeAssembler",
            "# Runnable generic fallback. Code_brain should still refine it for the exact request.",
            "",
            f"class {class_name}:",
            "",
            "    def __init__(self):",
            "        self.items = []",
            ""
        ]

        for node in nodes[:10]:
            method = self.safe_identifier(node)
            lines.extend([
                f"    def {method}(self, data=None):",
                f"        \"\"\"Apply the {node.replace('_', ' ')} step.\"\"\"",
                "        data = data or {}",
                f"        data['{method}'] = data.get('{method}', True)",
                "        return data",
                ""
            ])

        lines.extend([
            "    def run(self, data=None):",
            "        data = data or {}"
        ])

        for node in nodes[:10]:
            lines.append(f"        data = self.{self.safe_identifier(node)}(data)")

        lines.extend([
            "        return data",
            "",
            "",
            "def build_solution(data=None):",
            f"    return {class_name}().run(data)",
            "",
            "",
            "def main():",
            "    print('Creative Python fallback')",
            "    result = build_solution({})",
            "    print(result)",
            "",
            "",
            "if __name__ == '__main__':",
            "    main()",
            ""
        ])

        return "\n".join(lines)

    def generate_javascript(self, graph_plan):

        nodes = graph_plan.get("order", [])
        lines = [
            "// Generated by Creative_brain CreativeCodeAssembler",
            "// Draft only: review before execution.",
            "",
            "function buildSolution(input = {}) {",
            "  let data = { ...input };"
        ]

        for node in nodes[:10]:
            key = self.safe_identifier(node)
            lines.append(f"  data.{key} = data.{key} || true;")

        lines.extend([
            "  return data;",
            "}",
            "",
            "module.exports = { buildSolution };"
        ])

        return "\n".join(lines)

    def generate_java(self, terms):

        class_name = self.class_name_from_terms(terms)

        return "\n".join([
            "// Generated by Creative_brain CreativeCodeAssembler",
            "// Draft only: review before execution.",
            f"public class {class_name} {{",
            "    public String run(String input) {",
            "        if (input == null) {",
            "            input = \"\";",
            "        }",
            "        return input;",
            "    }",
            "}"
        ])

    def generate_html(self, terms):

        title = " ".join(terms[:4]).title() or "Canri Draft"

        return "\n".join([
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            f"  <title>{title}</title>",
            "</head>",
            "<body>",
            f"  <main>{title}</main>",
            "</body>",
            "</html>"
        ])

    def class_name_from_terms(self, terms):

        words = [
            re.sub(r"[^a-zA-Z0-9]", "", term).title()
            for term in terms[:4]
            if re.sub(r"[^a-zA-Z0-9]", "", term)
        ]

        return "".join(words)[:40] or "CreativeSolution"

    def safe_identifier(self, value):

        value = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value).lower()).strip("_")

        if not value:
            value = "step"

        if value[0].isdigit():
            value = f"step_{value}"

        return value[:48]

    def estimate_confidence(self, terms, graph_plan, canri_context):

        score = 45
        score += min(len(terms), 20)
        score += min(len(graph_plan.get("nodes", [])) * 3, 25)

        code_files_used = sum(
            1
            for file_name in canri_context
            if file_name.startswith("Code_") or file_name == "code.json"
        )
        score += min(code_files_used * 4, 20)

        return min(round(score, 2), 100)


class DictionaryGuidedComposer:
    """Build small, grammatical lexical alternatives from UnderstandingDk tags.

    This is deliberately bounded.  It creates candidate phrasing plans rather
    than blindly combining every dictionary word, which would make output slow
    and incoherent.
    """

    STORY_OPENERS = ["walked", "stepped", "moved", "wandered"]
    STORY_NOTICING_VERBS = ["noticed", "found", "spotted", "discovered"]
    STORY_REACTIONS = ["strange", "important", "unsettling", "impossible"]
    STORY_RESPONSES = ["carefully", "bravely", "quietly", "patiently"]

    def __init__(self, writing_rules=None):
        self.writing_rules = writing_rules if isinstance(writing_rules, dict) else {}

    def lexical_evidence(self, report, terms):
        report = report if isinstance(report, dict) else {}
        tags = report.get("advanced_word_tags", [])
        evidence = {
            "nouns": [],
            "verbs": [],
            "adjectives": [],
            "related": [],
            "definitions": []
        }

        for tag in tags[:120] if isinstance(tags, list) else []:
            if not isinstance(tag, dict):
                continue
            word = str(tag.get("word", "")).strip().lower()
            if not re.fullmatch(r"[a-z][a-z-]{1,40}", word):
                continue
            word_type = str(tag.get("normalized_type", "")).lower()
            if word_type == "noun":
                evidence["nouns"].append(word)
            elif word_type == "verb":
                evidence["verbs"].append(word)
            elif word_type == "adjective":
                evidence["adjectives"].append(word)
            evidence["related"].extend(
                str(item).lower()
                for item in tag.get("connection_hints", [])[:4]
                if isinstance(item, str)
            )
            definition = tag.get("definition_hint")
            if definition:
                evidence["definitions"].append(str(definition)[:160])

        for term in terms[:80]:
            term = str(term).strip().lower()
            if re.fullmatch(r"[a-z][a-z-]{1,40}", term):
                evidence["nouns"].append(term)

        return {
            key: list(dict.fromkeys(values))[:60]
            for key, values in evidence.items()
        }

    def score_plan(self, plan, text, evidence):
        lowered = str(text or "").lower()
        score = 50
        anchors = set(evidence.get("nouns", []) + evidence.get("verbs", []))
        request_words = set(re.findall(r"[a-z][a-z-]+", lowered))
        score += min(len(anchors.intersection(request_words)) * 5, 25)
        score += min(
            len(set(evidence.get("related", [])).intersection(request_words)) * 2,
            8
        )
        if evidence.get("definitions"):
            score += 3
        score += {
            "walked": 10,
            "stepped": 9,
            "wandered": 7,
            "moved": 4
        }.get(plan["opening_verb"], 0)
        if plan["noticing_verb"] in {"noticed", "found", "spotted", "discovered"}:
            score += 8
        score += {
            "strange": 10,
            "impossible": 8,
            "unsettling": 6,
            "important": 4
        }.get(plan["reaction_adjective"], 0)
        if plan["response_adverb"] in {"carefully", "bravely", "quietly", "patiently"}:
            score += 6
        if plan.get("character_descriptor"):
            score += 7
        if len({
            plan["opening_verb"], plan["noticing_verb"],
            plan["reaction_adjective"], plan["response_adverb"]
        }) == 4:
            score += 5
        return min(score, 140)

    def character_descriptors(self, evidence):
        allowed = set(self.writing_rules.get("safe_character_descriptors", [
            "curious", "quiet", "brave", "careful", "kind", "thoughtful"
        ]))
        requested = [
            word for word in evidence.get("adjectives", [])
            if word in allowed
        ]
        return requested or [""]

    def build_plan(self, report, text, terms, domain, candidate_limit=96):
        evidence = self.lexical_evidence(report, terms)
        candidates = []

        if domain != "story":
            return {
                "enabled": False,
                "reason": "Lexical composition is reserved for user-facing creative language.",
                "evidence": evidence,
                "candidate_count": 0
            }

        descriptors = self.character_descriptors(evidence)
        for index in range(candidate_limit):
            plan = {
                "opening_verb": self.STORY_OPENERS[index % len(self.STORY_OPENERS)],
                "noticing_verb": self.STORY_NOTICING_VERBS[(index // 2) % len(self.STORY_NOTICING_VERBS)],
                "reaction_adjective": self.STORY_REACTIONS[(index // 5) % len(self.STORY_REACTIONS)],
                "response_adverb": self.STORY_RESPONSES[(index // 11) % len(self.STORY_RESPONSES)],
                "character_descriptor": descriptors[index % len(descriptors)]
            }
            plan["score"] = self.score_plan(plan, text, evidence)
            candidates.append(plan)

        candidates.sort(
            key=lambda item: (
                item["score"],
                item["noticing_verb"] == "discovered",
                item["response_adverb"] == "carefully"
            ),
            reverse=True
        )
        selected = candidates[0] if candidates else {}
        return {
            "enabled": True,
            "strategy": "dictionary_tags_plus_grammar_safe_sentence_frames",
            "candidate_count": len(candidates),
            "selected": selected,
            "evidence": evidence,
            "rules_applied": self.writing_rules.get("writing_rules", []),
            "diversity": {
                "unique_opening_verbs": len({item["opening_verb"] for item in candidates}),
                "unique_noticing_verbs": len({item["noticing_verb"] for item in candidates}),
                "unique_reaction_adjectives": len({item["reaction_adjective"] for item in candidates}),
                "unique_response_adverbs": len({item["response_adverb"] for item in candidates})
            },
            "alternatives": candidates[:12]
        }


class EvolutionaryTextComposer:
    """Evolve paragraph-level answers while preserving source claims."""

    DEFAULT_MODES = [
        "direct",
        "deductive",
        "inductive",
        "causal",
        "comparative",
        "critical",
        "systems"
    ]
    INTERNAL_BRAINS = {
        "Manager_brain", "Planner_brain", "Quality_Control_brain",
        "Memory_brain", "Learning_brain", "Collaboration_brain",
        "Reasoning_brain", "Fact_Check_brain"
    }
    INTERNAL_MARKERS = {
        "goal:", "core idea:", "novel twist:", "constraint:",
        "validation:", "direction:", "review relevant memory",
        "extract the complete request contract"
    }

    def split_sentences(self, text):
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if not clean:
            return []
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", clean)
        return [part.strip() for part in parts if len(part.strip()) >= 20][:36]

    def looks_internal(self, text):
        lowered = str(text or "").lower()
        return sum(marker in lowered for marker in self.INTERNAL_MARKERS) >= 2

    def extract_result_text(self, brain_name, result):
        if brain_name in self.INTERNAL_BRAINS or not isinstance(result, dict):
            return ""
        for key in ["final_output", "answer", "explanation", "summary", "story"]:
            value = result.get(key)
            if isinstance(value, str) and value.strip() and not self.looks_internal(value):
                return value.strip()
        return ""

    def collect_source_material(self, data, canri_context, base_output):
        sources = []
        data = data if isinstance(data, dict) else {}
        results = data.get("results", {})
        if isinstance(results, dict):
            for brain_name, result in results.items():
                text = self.extract_result_text(brain_name, result)
                if text:
                    sources.append({
                        "source": brain_name,
                        "text": text,
                        "trust": float(result.get("confidence", 70) or 70)
                    })

        source_result = data.get("source_result")
        if isinstance(source_result, dict):
            text = self.extract_result_text(
                str(data.get("source_brain", "specialist_brain")),
                source_result
            )
            if text:
                sources.append({
                    "source": str(data.get("source_brain", "specialist_brain")),
                    "text": text,
                    "trust": float(source_result.get("confidence", 70) or 70)
                })

        for file_name, file_info in (canri_context or {}).items():
            if not isinstance(file_info, dict):
                continue
            for snippet in file_info.get("snippets", [])[:3]:
                if not isinstance(snippet, dict):
                    continue
                text = str(snippet.get("text", "")).strip()
                if len(text) >= 60:
                    sources.append({
                        "source": file_name,
                        "text": text,
                        "trust": float(file_info.get("trust_score", 68) or 68)
                    })

        lowered_base = str(base_output or "").lower()
        if (
            base_output
            and not self.looks_internal(base_output)
            and "the final response should be the finished result" not in lowered_base
        ):
            sources.insert(0, {
                "source": "Creative_brain_base_output",
                "text": str(base_output),
                "trust": 72.0
            })

        unique = []
        seen = set()
        for source in sources:
            key = re.sub(r"\W+", " ", source["text"].lower())[:240]
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(source)
        return unique[:16]

    def sentence_role(self, sentence, index, total):
        lowered = sentence.lower()
        if index == 0:
            return "definition_or_overview"
        if any(word in lowered for word in ["because", "causes", "results in", "therefore", "mechanism"]):
            return "cause_or_mechanism"
        if any(word in lowered for word in ["evidence", "study", "source", "measured", "observed"]):
            return "evidence"
        if any(word in lowered for word in ["example", "for instance", "such as", "application"]):
            return "example_or_application"
        if any(word in lowered for word in ["however", "but", "limit", "uncertain", "although"]):
            return "limit_or_qualification"
        if index == total - 1:
            return "conclusion"
        return "supporting_explanation"

    def order_for_mode(self, records, mode):
        priority = {
            "direct": ["definition_or_overview", "supporting_explanation", "cause_or_mechanism", "evidence", "example_or_application", "limit_or_qualification", "conclusion"],
            "deductive": ["definition_or_overview", "cause_or_mechanism", "supporting_explanation", "evidence", "conclusion", "limit_or_qualification"],
            "inductive": ["evidence", "example_or_application", "supporting_explanation", "cause_or_mechanism", "definition_or_overview", "conclusion"],
            "causal": ["cause_or_mechanism", "definition_or_overview", "supporting_explanation", "example_or_application", "evidence", "conclusion"],
            "comparative": ["definition_or_overview", "example_or_application", "supporting_explanation", "limit_or_qualification", "conclusion"],
            "critical": ["definition_or_overview", "limit_or_qualification", "evidence", "cause_or_mechanism", "supporting_explanation", "conclusion"],
            "systems": ["definition_or_overview", "cause_or_mechanism", "supporting_explanation", "example_or_application", "evidence", "limit_or_qualification", "conclusion"]
        }.get(mode, [])
        rank = {role: index for index, role in enumerate(priority)}
        return sorted(records, key=lambda item: (rank.get(item["role"], 99), item["index"]))

    def build_article(self, ordered, paragraph_size):
        paragraphs = []
        for start in range(0, len(ordered), paragraph_size):
            paragraph = " ".join(item["text"] for item in ordered[start:start + paragraph_size])
            if paragraph:
                paragraphs.append(paragraph)
        return "\n\n".join(paragraphs)

    def refine_order(self, ordered):
        """Keep a readable article arc without changing any source sentence."""
        overview = [item for item in ordered if item["role"] == "definition_or_overview"]
        conclusion = [item for item in ordered if item["role"] == "conclusion"]
        middle = [
            item for item in ordered
            if item["role"] not in {"definition_or_overview", "conclusion"}
        ]
        return overview[:1] + middle + overview[1:] + conclusion

    def fact_profile(self, data):
        results = data.get("results", {}) if isinstance(data, dict) else {}
        fact = results.get("Fact_Check_brain", {}) if isinstance(results, dict) else {}
        if not isinstance(fact, dict):
            fact = {}
        return {
            "verdict": fact.get("verdict", "not_checked"),
            "confidence": float(fact.get("confidence", 0) or 0),
            "verified": bool(fact.get("verified")),
            "evidence_count": int(fact.get("evidence_count", 0) or 0),
            "needs_research": bool(fact.get("needs_research"))
        }

    def reasoning_modes(self, data):
        results = data.get("results", {}) if isinstance(data, dict) else {}
        reasoning = results.get("Reasoning_brain", {}) if isinstance(results, dict) else {}
        directions = reasoning.get("reasoning_directions", {}) if isinstance(reasoning, dict) else {}
        modes = []
        selected = directions.get("selected", {}) if isinstance(directions, dict) else {}
        if isinstance(selected, dict) and selected.get("mode"):
            modes.append(selected["mode"])
        for item in directions.get("alternatives", []) if isinstance(directions, dict) else []:
            if isinstance(item, dict) and item.get("mode"):
                modes.append(item["mode"])
        modes.extend(self.DEFAULT_MODES)
        return list(dict.fromkeys(modes))[:9]

    def score_variant(self, variant, request_text, source_count, fact_profile):
        request_terms = {
            term for term in re.findall(r"[a-z][a-z-]{2,}", request_text.lower())
            if term not in GENERIC_TERMS
        }
        output_terms = set(re.findall(r"[a-z][a-z-]{2,}", variant["text"].lower()))
        coverage = len(request_terms.intersection(output_terms)) / max(len(request_terms), 1)
        role_count = len(set(variant["roles"]))
        score = 42 + coverage * 28 + min(role_count * 4, 20) + min(source_count * 2, 10)
        if fact_profile["verified"]:
            score += 8
        elif fact_profile["needs_research"]:
            score -= 10
        if self.looks_internal(variant["text"]):
            score -= 35
        if len(variant["text"]) < 120:
            score -= 12
        variant["scores"] = {
            "request_coverage": round(coverage * 100, 2),
            "structural_roles": role_count,
            "source_preservation": 100,
            "fact_confidence": fact_profile["confidence"],
            "total": round(max(0, min(score, 100)), 2)
        }
        return variant

    def evolve(self, data, report, text, domain, base_output, canri_context):
        sources = self.collect_source_material(data, canri_context, base_output)
        sentences = []
        for source in sources:
            for sentence in self.split_sentences(source["text"]):
                sentences.append({
                    "text": sentence,
                    "source": source["source"],
                    "trust": source["trust"]
                })

        unique_sentences = []
        seen = set()
        for item in sentences:
            signature = re.sub(r"\W+", " ", item["text"].lower()).strip()
            if signature in seen:
                continue
            seen.add(signature)
            item["index"] = len(unique_sentences)
            item["role"] = self.sentence_role(item["text"], item["index"], len(sentences))
            unique_sentences.append(item)
        unique_sentences = unique_sentences[:24]

        if not unique_sentences:
            return {
                "enabled": False,
                "reason": "No source-backed sentences were available.",
                "selected_output": base_output,
                "candidate_count": 0
            }

        fact_profile = self.fact_profile(data)
        modes = self.reasoning_modes(data)
        candidates = []
        for mode in modes:
            ordered = self.order_for_mode(unique_sentences, mode)
            for paragraph_size in [2, 3, 4]:
                article = self.build_article(ordered, paragraph_size)
                candidate = {
                    "id": f"response_{mode}_{paragraph_size}",
                    "mode": mode,
                    "paragraph_size": paragraph_size,
                    "text": article,
                    "roles": [item["role"] for item in ordered],
                    "sources": list(dict.fromkeys(item["source"] for item in ordered))
                }
                candidates.append(
                    self.score_variant(candidate, text, len(sources), fact_profile)
                )

        candidates.sort(key=lambda item: item["scores"]["total"], reverse=True)
        evolution_history = [{
            "round": 1,
            "population": len(candidates),
            "best_id": candidates[0]["id"],
            "best_score": candidates[0]["scores"]["total"]
        }]

        population = list(candidates)
        for round_number in [2, 3]:
            elites = sorted(
                population,
                key=lambda item: item["scores"]["total"],
                reverse=True
            )[:6]
            children = []
            for index, elite in enumerate(elites):
                base_mode = elite["mode"].replace("_refined", "")
                ordered = self.refine_order(
                    self.order_for_mode(unique_sentences, base_mode)
                )
                paragraph_size = 2 + ((elite["paragraph_size"] + index + round_number) % 3)
                child = {
                    "id": f"response_{base_mode}_refined_r{round_number}_{index}",
                    "mode": f"{base_mode}_refined",
                    "paragraph_size": paragraph_size,
                    "text": self.build_article(ordered, paragraph_size),
                    "roles": [item["role"] for item in ordered],
                    "sources": list(dict.fromkeys(item["source"] for item in ordered)),
                    "parent_id": elite["id"],
                    "evolution_stage": round_number
                }
                child = self.score_variant(child, text, len(sources), fact_profile)
                if child["roles"] and child["roles"][0] == "definition_or_overview":
                    child["scores"]["total"] = min(100, child["scores"]["total"] + 3)
                children.append(child)
            population.extend(children)
            population.sort(key=lambda item: item["scores"]["total"], reverse=True)
            evolution_history.append({
                "round": round_number,
                "population": len(population),
                "children": len(children),
                "best_id": population[0]["id"],
                "best_score": population[0]["scores"]["total"]
            })

        candidates = population
        selected = candidates[0]
        # Narrative and code ordering must remain owned by their specialist builders.
        selected_output = base_output if domain in {"story", "code", "emotion"} else selected["text"]
        return {
            "enabled": True,
            "algorithm": "source_preserving_multi_direction_response_evolution",
            "candidate_count": len(candidates),
            "rounds_completed": len(evolution_history),
            "evolution_history": evolution_history,
            "selected_mode": selected["mode"],
            "selected_score": selected["scores"]["total"],
            "selected_output": selected_output,
            "paragraph_plan": [
                {"sentence": item["text"], "role": item["role"], "source": item["source"]}
                for item in self.order_for_mode(unique_sentences, selected["mode"])
            ],
            "fact_profile": fact_profile,
            "source_count": len(sources),
            "sources": [source["source"] for source in sources],
            "alternatives": [
                {
                    "id": item["id"],
                    "mode": item["mode"],
                    "scores": item["scores"]
                }
                for item in candidates[:10]
            ],
            "claims_rewritten": False,
            "safety_rule": "Factual source sentences are preserved instead of invented from word combinations."
        }


class CreativeBrain:

    def __init__(self):

        self.seeds = self.load_json(SEEDS_FILE, {})
        self.rules = self.load_json(RULES_FILE, {})
        self.graphs = self.load_json(GRAPHS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        self.writing_rules = self.load_json(WRITING_RULES_FILE, {})
        self.creative_memory = self.load_json(MEMORY_FILE, {
            "ideas": [],
            "direction_profiles": {},
            "failed_directions": {},
            "successful_patterns": {}
        })
        self.geography_index = self.load_json(
            DATA_DIR / "Geography_index.json",
            {}
        )
        self.geography_creative_profiles = self.load_json(
            DATA_DIR / "Geography_creative_profiles.json",
            {}
        )
        self.graphs_by_seed = self.index_graphs_by_seed()
        self.canri_index = self.build_canri_index()
        self.code_assembler = CreativeCodeAssembler(self)
        self.dictionary_composer = DictionaryGuidedComposer(self.writing_rules)
        self.text_composer = EvolutionaryTextComposer()

        print("Creative Brain Loaded")

    # ---------- loading ----------

    def load_json(self, path, default):

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def save_creative_memory(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with MEMORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.creative_memory, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def index_graphs_by_seed(self):

        index = {}

        for graph in self.graphs.values():
            seed_id = graph.get("seed_id")
            if seed_id:
                index[seed_id] = graph

        return index

    def build_canri_index(self):

        index = {}

        for file_name in self.all_creative_data_files():
            path = DATA_DIR / file_name

            if not path.exists():
                continue

            try:
                stat = path.stat()
                index[file_name] = {
                    "bytes": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                    "sample_terms": [
                        term
                        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", path.stem.lower())
                        if term not in GENERIC_TERMS
                    ],
                    "indexed": True,
                    "loaded": False
                }
            except OSError:
                index[file_name] = {
                    "bytes": 0,
                    "sample_terms": [],
                    "indexed": False,
                    "loaded": False
                }

        return index

    def is_creative_data_file(self, file_name):

        name = str(file_name or "").strip()
        lowered = name.lower()
        if not name or name in CREATIVE_DATA_EXCLUDED_FILES:
            return False
        return not lowered.endswith(CREATIVE_DATA_EXCLUDED_SUFFIXES)

    def all_creative_data_files(self):

        file_names = list(ALWAYS_CANRI_DATA_FILES) + list(CANRI_DATA_FILES)
        for domain_files in DOMAIN_CANRI_DATA_FILES.values():
            file_names.extend(domain_files)
        return [
            file_name
            for file_name in self.unique_files(file_names)
            if self.is_creative_data_file(file_name)
        ]

    def unique_files(self, file_names):

        clean = []

        for file_name in file_names:
            if file_name and file_name not in clean:
                clean.append(file_name)

        return clean

    def summarize_canri_file(self, file_name, terms=None, sample_limit=80):

        path = DATA_DIR / file_name

        if not path.exists():
            return {
                "count": 0,
                "sample_terms": [],
                "matched_terms": [],
                "used": False
            }

        sample_terms = []
        matched_terms = []
        terms = [
            str(term).lower()
            for term in (terms or [])
            if term
        ]

        try:
            with path.open("r", encoding="utf-8", errors="replace") as file:
                sample = file.read(160_000)
        except OSError:
            sample = ""

        searchable = sample.lower()
        sample_terms = list(dict.fromkeys(
            re.findall(r'"(?:word|name|title|term|type|category)"\s*:\s*"([^"\n]{1,80})"', sample)
        ))[:sample_limit]
        for term in terms[:40]:
            if term in searchable:
                matched_terms.append(term)

        return {
            "count": None,
            "sample_terms": [term for term in sample_terms if term][:sample_limit],
            "matched_terms": [term for term in matched_terms if term][:sample_limit],
            "used": bool(sample),
            "bytes_read": len(sample.encode("utf-8", errors="ignore")),
            "full_file_loaded": False,
            "retrieval_mode": "bounded_sample_fallback"
        }

    def preview_json_value(self, value):

        if isinstance(value, dict):
            parts = []
            for key, item in list(value.items())[:8]:
                parts.append(str(key))
                if isinstance(item, (str, int, float)):
                    parts.append(str(item))
                elif isinstance(item, list):
                    parts.extend(str(entry) for entry in item[:6])
            return " ".join(parts)

        if isinstance(value, list):
            return " ".join(str(item) for item in value[:12])

        return str(value)

    def item_name(self, item):

        if isinstance(item, dict):
            for key in ["word", "id", "name", "title", "term", "type", "pattern"]:
                if item.get(key):
                    return str(item[key])

        return str(item)[:80] if item else ""

    def relevant_canri_files(self, domain, data=None):

        data = data or {}
        file_names = list(ALWAYS_CANRI_DATA_FILES)
        file_names.extend(DOMAIN_CANRI_DATA_FILES.get(domain, []))
        file_names.extend(DOMAIN_CANRI_DATA_FILES.get("general", []))

        source_brain = ""
        if isinstance(data, dict):
            source_brain = str(data.get("source_brain", "")).lower()

        for known_domain, known_files in DOMAIN_CANRI_DATA_FILES.items():
            if known_domain in source_brain:
                file_names.extend(known_files)

        return [
            file_name
            for file_name in self.unique_files(file_names)
            if self.is_creative_data_file(file_name)
        ]

    def collect_canri_context(self, domain, terms, data=None):

        context = {}

        for file_name in self.relevant_canri_files(domain, data):
            context[file_name] = self.summarize_canri_file(
                file_name,
                terms,
                sample_limit=60
            )

        return context

    def collect_indexed_project_context(self, data, report, terms):

        data = data if isinstance(data, dict) else {}
        indexed = data.get("data_context")

        if not isinstance(indexed, dict) or not indexed.get("matches"):
            full_context = data.get("full_data_context")
            if isinstance(full_context, dict) and full_context.get("matches"):
                indexed = full_context

        if (
            (not isinstance(indexed, dict) or not indexed.get("matches"))
            and build_shared_data_context is not None
        ):
            query = " ".join(str(term) for term in terms[:60])
            indexed = build_shared_data_context(query, limit=16)

        if isinstance(indexed, dict) and context_view_for_brain is not None:
            indexed = context_view_for_brain(
                indexed,
                "Creative_brain",
                max_sources=12
            )

        context = {}
        for match in (indexed or {}).get("matches", [])[:12]:
            if not isinstance(match, dict):
                continue
            file_name = str(match.get("file", "")).strip()
            if not self.is_creative_data_file(file_name):
                continue

            snippets = []
            for item in match.get("value_matches", [])[:5]:
                if isinstance(item, dict) and item.get("text"):
                    snippets.append({
                        "path": item.get("path"),
                        "text": str(item.get("text", ""))[:360],
                        "matched_terms": item.get("matched_terms", [])[:8]
                    })

            context[file_name] = {
                "count": match.get("items"),
                "sample_terms": match.get("sample", [])[:20],
                "matched_terms": match.get("matched_terms", [])[:20],
                "snippets": snippets,
                "score": match.get("score", 0),
                "source_group": match.get("source_group", "canri_data"),
                "used": True,
                "full_file_loaded": False,
                "retrieval_mode": "indexed_relevant_snippets"
            }

        knowledge = data.get("knowledge", {})
        if isinstance(knowledge, dict):
            for match in knowledge.get("matches", [])[:6]:
                if not isinstance(match, dict):
                    continue
                title = str(match.get("title", "knowledge article")).strip()
                context[f"Knowledge_database::{title}"] = {
                    "count": 1,
                    "sample_terms": [title],
                    "matched_terms": [
                        term for term in terms[:40]
                        if term in f"{title} {match.get('summary', '')}".lower()
                    ],
                    "snippets": [{
                        "title": title,
                        "summary": str(match.get("summary", ""))[:900],
                        "content_excerpt": str(match.get("content_excerpt", ""))[:1400],
                        "trust_score": match.get("trust_score", 0),
                        "sources": match.get("sources", [])[:4]
                    }],
                    "source_group": "knowledge_index",
                    "used": True,
                    "full_file_loaded": False,
                    "retrieval_mode": "knowledge_index_lookup"
                }

        dictionary_context = data.get("dictionary", {})
        if isinstance(dictionary_context, dict):
            selected_items = []
            selected_items.extend(dictionary_context.get("entries", [])[:20])
            selected_items.extend(dictionary_context.get("company_matches", [])[:8])
            selected_items.extend(dictionary_context.get("product_matches", [])[:8])
            for item in selected_items:
                if not isinstance(item, dict):
                    continue
                name = str(
                    item.get("word")
                    or item.get("name")
                    or item.get("product")
                    or item.get("company")
                    or "dictionary item"
                ).strip()
                context[f"Dictionary_context::{name}"] = {
                    "count": 1,
                    "sample_terms": [name, str(item.get("type", ""))],
                    "matched_terms": [name.lower()],
                    "snippets": [item],
                    "source_group": "dictionary_and_products",
                    "used": True,
                    "full_file_loaded": False,
                    "retrieval_mode": "manager_selected_lookup"
                }

        # Understanding_brain already performed exact indexed dictionary,
        # grammar, and connection lookups. Reuse only those selected entries.
        for word_info in report.get("words", [])[:60]:
            if not isinstance(word_info, dict) or not word_info.get("exists"):
                continue
            word = str(word_info.get("word", "")).strip().lower()
            if not word:
                continue
            context[f"UnderstandingDk::{word}"] = {
                "count": 1,
                "sample_terms": [word, str(word_info.get("type", ""))],
                "matched_terms": [word],
                "snippets": [{
                    "source": "main_dictionary + Grammar_dictionary + Connections_Dictionary",
                    "word": word,
                    "type": word_info.get("type"),
                    "meanings": word_info.get("meanings", [])[:3],
                    "forms": word_info.get("forms", {}),
                    "connections": word_info.get("connections", [])[:10]
                }],
                "source_group": "understanding_dictionaries",
                "used": True,
                "full_file_loaded": False,
                "retrieval_mode": "exact_dictionary_lookup"
            }

        return context

    def collect_indexed_geography_context(self, terms, text="", limit=10):

        if not isinstance(self.geography_index, dict):
            return {}
        term_index = self.geography_index.get("terms", {})
        exact_index = self.geography_index.get("exact", {})
        records = self.geography_index.get("records", {})
        lowered_text = str(text).lower()
        references = []

        for phrase, refs in sorted(exact_index.items(), key=lambda item: len(item[0]), reverse=True):
            if len(phrase) > 2 and re.search(
                rf"(?<![\w]){re.escape(str(phrase).lower())}(?![\w])",
                lowered_text
            ):
                references.extend(refs)
        for term in terms[:60]:
            normalized = re.sub(r"\s+", " ", str(term).lower()).strip()
            references.extend(term_index.get(normalized, []))
            for token in re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9'\-\u0590-\u05FF]{1,}", normalized):
                references.extend(term_index.get(token, []))

        selected = []
        for reference in dict.fromkeys(references):
            record = records.get(reference)
            if not isinstance(record, dict):
                continue
            score = sum(
                1
                for term in terms[:40]
                if str(term).lower() in self.preview_json_value(record).lower()
            )
            if reference.split(":", 1)[-1] in lowered_text:
                score += 10
            selected.append((score, reference, record))
        selected.sort(key=lambda item: item[0], reverse=True)

        context = {}
        for score, reference, record in selected[:limit]:
            profile = self.geography_creative_profiles.get(reference.split(":", 1)[-1], {})
            context[f"Geography_index::{reference}"] = {
                "count": 1,
                "sample_terms": [record.get("name", reference), record.get("type", "")],
                "matched_terms": [
                    term for term in terms[:40]
                    if str(term).lower() in self.preview_json_value(record).lower()
                ],
                "snippets": [{"geography": record, "creative_profile": profile}],
                "score": score,
                "source_group": "geography_fast_index",
                "used": True,
                "full_file_loaded": False,
                "retrieval_mode": "geography_inverted_index"
            }
        return context

    def terms_from_canri_context(self, canri_context):

        terms = []

        for file_info in canri_context.values():
            terms.extend(file_info.get("matched_terms", [])[:20])
            terms.extend(file_info.get("sample_terms", [])[:6])
            for snippet in file_info.get("snippets", [])[:4]:
                snippet_text = self.preview_json_value(snippet)
                terms.extend(
                    re.findall(
                        r"[a-zA-Z][a-zA-Z0-9_-]{2,}",
                        snippet_text.lower()
                    )[:14]
                )

        clean = []
        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip()
            if term and term not in clean and term not in GENERIC_TERMS:
                clean.append(term)

        return clean[:120]

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "creative",
                "intent": "creative_generation",
                "words": []
            }

        for key in ["understanding", "understanding_report"]:
            understanding = data.get(key)
            if isinstance(understanding, dict):
                return understanding

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_memory_report(self, data):

        if not isinstance(data, dict):
            return {}

        memory = data.get("memory")

        if isinstance(memory, dict):
            return memory

        return {}

    def extract_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in [
                "original_text", "corrected_text", "user_message", "question",
                "query", "text", "goal", "task", "missing", "problem"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_terms(self, report, memory_report, text):

        terms = []

        for key in ["main_topic", "intent", "language", "target_language"]:
            value = report.get(key)
            if value and value != "unknown":
                terms.append(str(value))

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            terms.extend(str(topic) for topic in topics)

        for task in report.get("possible_tasks", []):
            terms.append(str(task).replace("_", " "))

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            if word_data.get("word"):
                terms.append(str(word_data["word"]))

            for connection in word_data.get("connections", [])[:10]:
                terms.append(str(connection))

        for keyword in memory_report.get("current_keywords", [])[:30]:
            terms.append(str(keyword))

        for match in memory_report.get("ranked_matches", [])[:8]:
            if isinstance(match, dict):
                terms.extend(str(keyword) for keyword in match.get("keywords", [])[:8])
                if match.get("summary"):
                    terms.append(str(match["summary"]))

        terms.extend(
            re.findall(
                r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
                text
            )
        )

        clean = []
        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip()
            term = term.replace("_", " ")
            if term and len(term) > 1 and term not in GENERIC_TERMS and term not in clean:
                clean.append(term)

        return clean[:120]

    # ---------- generation ----------

    def detect_domain(self, report, terms, text):

        topic = str(report.get("main_topic", "")).lower()
        lowered = f"{text.lower()} {' '.join(terms)}"

        for domain in ["story", "code", "game", "science", "technology", "language", "geography", "history", "math", "security"]:
            if topic == domain or domain in lowered:
                return domain

        if "character" in lowered:
            return "story"
        if "function" in lowered or "python" in lowered:
            return "code"

        return "story" if "creative" in lowered else "general"

    def analyze_direction(self, report, memory_report, terms, text, domain):

        lowered = f"{text.lower()} {' '.join(terms)}"
        intent = str(report.get("intent", "creative_generation")).lower()

        direction = {
            "domain": domain,
            "intent": intent,
            "primary_goal": self.extract_primary_goal(report, text, domain),
            "good_direction": [],
            "bad_direction": [],
            "constraints": [],
            "preferred_strategy": "balanced_evolution",
            "change_direction_when": [],
            "continue_direction_when": [],
            "memory_bias": self.memory_bias_for_domain(domain),
            "confidence": 65
        }

        if domain == "code":
            direction["good_direction"].extend([
                "solves the missing function",
                "can be routed back to Code_brain",
                "keeps security and integration visible"
            ])
            direction["bad_direction"].extend([
                "placeholder without implementation path",
                "unsafe shell or file behavior",
                "language mismatch"
            ])
            direction["preferred_strategy"] = "practical_invention"

        elif domain == "story":
            direction["good_direction"].extend([
                "clear character goal",
                "strong conflict",
                "world detail affects plot",
                "emotion and ending are connected"
            ])
            direction["bad_direction"].extend([
                "random weirdness without purpose",
                "flat conflict",
                "setting that does not affect the story"
            ])
            direction["preferred_strategy"] = "narrative_evolution"

        elif domain == "security":
            direction["good_direction"].extend([
                "safe alternative",
                "harm-reducing answer",
                "no operational harmful details"
            ])
            direction["bad_direction"].extend([
                "creative harmful instructions",
                "evasion",
                "dangerous procedural detail"
            ])
            direction["preferred_strategy"] = "safe_redirection"

        else:
            direction["good_direction"].extend([
                "relevant to the request",
                "novel but understandable",
                "usable by another Canri brain"
            ])
            direction["bad_direction"].extend([
                "irrelevant novelty",
                "contradiction",
                "too vague to act on"
            ])

        if any(term in lowered for term in ["professional", "production", "real", "serious"]):
            direction["constraints"].append("professional_quality")
            direction["confidence"] += 8

        if any(term in lowered for term in ["safe", "security", "danger", "private"]):
            direction["constraints"].append("safety_first")
            direction["preferred_strategy"] = "risk_aware_evolution"

        if memory_report.get("memory_found", 0):
            direction["constraints"].append("reuse_relevant_memory")
            direction["continue_direction_when"].append("idea improves on previous memory instead of repeating it")
            direction["confidence"] += 7

        direction["change_direction_when"].extend([
            "top ideas repeat the same concept",
            "novelty rises but coherence drops",
            "relevance stays low for two generations",
            "safety score drops below acceptable level"
        ])

        direction["continue_direction_when"].extend([
            "best score improves meaningfully",
            "relevance and novelty both improve",
            "the idea becomes easier for specialist brains to use"
        ])

        direction["confidence"] = min(direction["confidence"], 100)

        return direction

    def extract_primary_goal(self, report, text, domain):

        for key in ["goal", "task", "original_text", "corrected_text"]:
            value = report.get(key)
            if value:
                return str(value)[:180]

        if text:
            return text[:180]

        return f"create useful {domain} idea"

    def memory_bias_for_domain(self, domain):

        successful = self.creative_memory.get("successful_patterns", {})
        failed = self.creative_memory.get("failed_directions", {})

        return {
            "successful_terms": successful.get(domain, [])[:20],
            "failed_terms": failed.get(domain, [])[:20],
            "previous_ideas": [
                idea
                for idea in self.creative_memory.get("ideas", [])[-30:]
                if idea.get("domain") == domain
            ][-8:]
        }

    def candidate_seed_pool(self, domain, terms, limit=140):

        scored = []
        term_text = " ".join(terms)

        for seed in self.seeds.values():
            score = 0
            if seed.get("domain") == domain:
                score += 25

            searchable = " ".join([
                seed.get("domain", ""),
                seed.get("genre", ""),
                seed.get("tone", ""),
                seed.get("archetype", ""),
                " ".join(seed.get("ingredients", []))
            ]).lower()

            score += sum(2 for term in terms[:30] if term in searchable)

            if seed.get("genre", "") in term_text:
                score += 8

            scored.append((score, seed))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            seed
            for score, seed in scored[:limit]
            if score > 0
        ] or list(self.seeds.values())[:limit]

    def graph_for_seed(self, seed):

        return self.graphs_by_seed.get(
            seed.get("id", ""),
            {}
        )

    def build_idea_model(self, seed, terms, direction, index):

        user_terms = terms[:10] or ["unknown goal"]
        ingredients = seed.get("ingredients", [])
        domain = seed.get("domain", direction.get("domain", "general"))

        mechanisms = [
            "feedback loop",
            "constraint-based design",
            "layered system",
            "adaptive workflow",
            "memory-guided selection",
            "risk-aware routing",
            "prototype-test-improve loop"
        ]

        constraints = [
            "must stay useful",
            "must be explainable",
            "must avoid unsafe output",
            "must connect to existing Canri brains",
            "must be simple enough to implement"
        ]

        audiences = [
            "the user",
            "a specialist brain",
            "Code_brain",
            "Planner_brain",
            "Response_brain"
        ]

        validation = [
            "score against goal fit",
            "check novelty against memory",
            "verify safety before output",
            "test whether another brain can use it",
            "compare against simpler alternatives"
        ]

        return {
            "goal": direction.get("primary_goal", f"solve {domain} task"),
            "domain": domain,
            "core_subject": user_terms[index % len(user_terms)],
            "mechanism": mechanisms[index % len(mechanisms)],
            "constraint": constraints[index % len(constraints)],
            "audience": audiences[index % len(audiences)],
            "risk": "too vague or disconnected from the request",
            "validation": validation[index % len(validation)],
            "novel_twist": seed.get("archetype") or seed.get("tone") or "unusual useful combination",
            "components": list(dict.fromkeys(ingredients + user_terms[:6]))[:14],
            "tradeoff": "balance novelty with coherence",
            "implementation_hint": "route the strongest version back to the specialist brain"
        }

    def concept_from_model(self, model, direction):

        return (
            f"Goal: {model.get('goal')}. "
            f"Core idea: use {model.get('mechanism')} around {model.get('core_subject')} "
            f"for {model.get('audience')}. "
            f"Novel twist: {model.get('novel_twist')}. "
            f"Constraint: {model.get('constraint')}. "
            f"Validation: {model.get('validation')}. "
            f"Tradeoff: {model.get('tradeoff')}. "
            f"Implementation: {model.get('implementation_hint')}. "
            f"Direction: {direction.get('preferred_strategy', 'balanced_evolution')}."
        )

    def mutation_operator(self, index, generation, graph_paths):

        operators = [
            "change_mechanism",
            "add_constraint",
            "change_audience",
            "invert_tradeoff",
            "add_validation",
            "reduce_risk",
            "graph_guided_jump",
            "memory_distinction"
        ]

        if graph_paths:
            operators.append("graph_guided_jump")

        return operators[(index + generation) % len(operators)]

    def apply_semantic_mutation(self, model, operator, terms, direction, graph_paths, index):

        mutated = dict(model)
        terms = terms or ["idea"]
        graph_hint = graph_paths[index % len(graph_paths)] if graph_paths else "new structural path"

        if operator == "change_mechanism":
            mechanisms = [
                "multi-step planner",
                "evidence-first filter",
                "dependency graph",
                "evolutionary search",
                "local memory retrieval",
                "specialist-brain handoff"
            ]
            mutated["mechanism"] = mechanisms[index % len(mechanisms)]

        elif operator == "add_constraint":
            constraints = direction.get("constraints", []) or [
                "must produce a concrete output",
                "must be testable",
                "must be safe by default",
                "must use project data"
            ]
            mutated["constraint"] = constraints[index % len(constraints)]

        elif operator == "change_audience":
            audiences = [
                "a beginner user",
                "an advanced builder",
                "Code_brain",
                "Research_brain",
                "Response_brain",
                "Manager_brain"
            ]
            mutated["audience"] = audiences[index % len(audiences)]

        elif operator == "invert_tradeoff":
            mutated["tradeoff"] = "prefer a surprising approach only if it remains easy to verify"
            mutated["novel_twist"] = f"invert the normal approach to {terms[index % len(terms)]}"

        elif operator == "add_validation":
            mutated["validation"] = "run score checks for relevance, novelty, coherence, safety, and handoff usefulness"

        elif operator == "reduce_risk":
            mutated["risk"] = "unsafe, vague, or impossible direction"
            mutated["constraint"] = "must include a safe fallback and a clear stop condition"

        elif operator == "graph_guided_jump":
            mutated["mechanism"] = f"graph-guided transition: {graph_hint}"
            mutated["implementation_hint"] = "follow the graph path, then let the specialist brain refine the final structure"

        elif operator == "memory_distinction":
            mutated["novel_twist"] = "explicitly avoid repeating previous creative memory"
            mutated["validation"] = "compare components against creative memory and keep a distinct structure"

        mutated["components"] = list(dict.fromkeys(
            mutated.get("components", []) + [terms[index % len(terms)]]
        ))[:16]

        return mutated

    def crossover_idea_models(self, left_model, right_model, direction, index):

        return {
            "goal": left_model.get("goal") or right_model.get("goal"),
            "domain": left_model.get("domain") or right_model.get("domain"),
            "core_subject": left_model.get("core_subject") or right_model.get("core_subject"),
            "mechanism": right_model.get("mechanism") or left_model.get("mechanism"),
            "constraint": left_model.get("constraint") or right_model.get("constraint"),
            "audience": right_model.get("audience") or left_model.get("audience"),
            "risk": left_model.get("risk") or right_model.get("risk"),
            "validation": right_model.get("validation") or left_model.get("validation"),
            "novel_twist": f"{left_model.get('novel_twist', 'idea')} + {right_model.get('novel_twist', 'idea')}",
            "components": list(dict.fromkeys(
                left_model.get("components", []) + right_model.get("components", [])
            ))[:18],
            "tradeoff": "combine the strongest practical part with the most novel part",
            "implementation_hint": direction.get("primary_goal", "return a usable combined idea")
        }

    def make_candidate(self, seed, terms, generation, index, parent_ids=None, direction=None):

        parent_ids = parent_ids or []
        direction = direction or {}
        user_terms = terms[:8] or ["unknown goal"]
        ingredients = seed.get("ingredients", [])
        graph = self.graph_for_seed(seed)
        graph_paths = graph.get("mutation_paths", [])
        merge_strategy = graph.get("merge_strategy", "combine strongest useful parts")

        title_parts = [
            seed.get("tone", "focused"),
            seed.get("genre", seed.get("domain", "creative")),
            user_terms[index % len(user_terms)]
        ]

        idea_model = self.build_idea_model(
            seed,
            terms,
            direction,
            index
        )
        idea_model["implementation_hint"] = f"Graph strategy: {merge_strategy}"
        concept = self.concept_from_model(idea_model, direction)

        return {
            "id": f"idea_g{generation}_{index}_{seed.get('id', 'seed')}",
            "title": " ".join(str(part).replace("_", " ") for part in title_parts).title(),
            "domain": seed.get("domain", "general"),
            "genre": seed.get("genre"),
            "tone": seed.get("tone"),
            "archetype": seed.get("archetype"),
            "concept": concept,
            "idea_model": idea_model,
            "ingredients": list(dict.fromkeys(ingredients + user_terms[:6])),
            "graph_used": {
                "id": graph.get("id"),
                "mutation_paths": graph_paths[:6],
                "merge_strategy": merge_strategy,
                "selection_rule": graph.get("selection_rule")
            },
            "direction_strategy": direction.get("preferred_strategy", "balanced_evolution"),
            "parent_ids": parent_ids,
            "generation": generation,
            "scores": {}
        }

    def initial_generation(self, domain, terms, direction, size=100):

        seeds = self.candidate_seed_pool(domain, terms, limit=max(size, 120))
        candidates = []

        for index in range(size):
            seed = seeds[index % len(seeds)]
            candidates.append(
                self.make_candidate(seed, terms, 1, index, direction=direction)
            )

        return candidates

    def mutate_candidate(self, candidate, terms, generation, index, direction):

        ingredients = list(candidate.get("ingredients", []))
        if terms:
            ingredients.append(terms[(generation + index) % len(terms)])

        graph_paths = candidate.get("graph_used", {}).get("mutation_paths", [])
        mutation_type = self.mutation_operator(
            index,
            generation,
            graph_paths
        )
        model = self.apply_semantic_mutation(
            candidate.get("idea_model", {}),
            mutation_type,
            terms,
            direction,
            graph_paths,
            index
        )
        concept = self.concept_from_model(model, direction)

        mutated = dict(candidate)
        mutated["id"] = f"idea_g{generation}_{index}_{candidate['id']}"
        mutated["concept"] = concept
        mutated["idea_model"] = model
        mutated["mutation_operator"] = mutation_type
        mutated["ingredients"] = list(dict.fromkeys(ingredients))[:16]
        mutated["parent_ids"] = [candidate["id"]]
        mutated["generation"] = generation
        mutated["scores"] = {}

        return mutated

    def merge_candidates(self, left, right, generation, index, direction):

        ingredients = list(dict.fromkeys(left.get("ingredients", []) + right.get("ingredients", [])))[:18]
        model = self.crossover_idea_models(
            left.get("idea_model", {}),
            right.get("idea_model", {}),
            direction,
            index
        )

        return {
            "id": f"idea_g{generation}_merge_{index}_{left['id']}",
            "title": f"{left.get('title', 'Idea')} / {right.get('title', 'Idea')}",
            "domain": left.get("domain") or right.get("domain"),
            "genre": left.get("genre") or right.get("genre"),
            "tone": right.get("tone") or left.get("tone"),
            "archetype": left.get("archetype") or right.get("archetype"),
            "concept": self.concept_from_model(model, direction),
            "idea_model": model,
            "mutation_operator": "crossover",
            "ingredients": ingredients,
            "graph_used": left.get("graph_used") or right.get("graph_used", {}),
            "direction_strategy": direction.get("preferred_strategy", "balanced_evolution"),
            "parent_ids": [left["id"], right["id"]],
            "generation": generation,
            "scores": {}
        }

    # ---------- scoring ----------

    def idea_signature(self, candidate):

        model = candidate.get("idea_model", {})
        fields = [
            model.get("goal", ""),
            model.get("core_subject", ""),
            model.get("mechanism", ""),
            model.get("constraint", ""),
            model.get("audience", ""),
            model.get("validation", ""),
            model.get("novel_twist", ""),
            model.get("tradeoff", "")
        ]
        fields.extend(model.get("components", [])[:8])

        return {
            re.sub(r"\s+", " ", str(field).lower()).strip()
            for field in fields
            if field
        }

    def novelty_search_score(self, candidate, domain, scored_archive=None):

        signature = self.idea_signature(candidate)
        if not signature:
            return {
                "score": 35,
                "nearest_similarity": 1,
                "archive_size": 0
            }

        archive = scored_archive
        if archive is None:
            archive = [
                idea
                for idea in self.creative_memory.get("ideas", [])[-120:]
                if idea.get("domain") == domain
            ]

        if not archive:
            return {
                "score": 85,
                "nearest_similarity": 0,
                "archive_size": 0
            }

        nearest = 0
        for idea in archive:
            old_signature = set(
                re.sub(r"\s+", " ", str(field).lower()).strip()
                for field in (
                    idea.get("idea_signature", [])
                    or idea.get("ingredients", [])
                    or []
                )
                if field
            )

            if not old_signature:
                continue

            overlap = len(signature & old_signature)
            union = max(len(signature | old_signature), 1)
            nearest = max(nearest, overlap / union)

        return {
            "score": round(max(0, min((1 - nearest) * 100, 100)), 2),
            "nearest_similarity": round(nearest, 3),
            "archive_size": len(archive)
        }

    def structural_depth_score(self, candidate):

        model = candidate.get("idea_model", {})
        required = [
            "goal", "mechanism", "constraint", "audience",
            "risk", "validation", "novel_twist", "tradeoff",
            "implementation_hint"
        ]

        filled = sum(1 for key in required if model.get(key))
        components = len(set(model.get("components", [])))
        has_graph = bool(candidate.get("graph_used", {}).get("id"))
        has_operator = bool(candidate.get("mutation_operator"))

        return min(
            100,
            filled * 8 + min(components * 3, 24) + (12 if has_graph else 0) + (8 if has_operator else 0)
        )

    def score_candidate(self, candidate, terms, domain, direction):

        text = " ".join([
            candidate.get("title", ""),
            candidate.get("concept", ""),
            " ".join(candidate.get("ingredients", []))
        ]).lower()

        term_hits = len(set(term for term in terms if term in text))
        relevance = min(100, 35 + term_hits * 8)

        good_direction_hits = sum(
            1
            for phrase in direction.get("good_direction", [])
            if any(part in text for part in phrase.split()[:3])
        )

        bad_direction_hits = sum(
            1
            for phrase in direction.get("bad_direction", [])
            if any(part in text for part in phrase.split()[:3])
        )

        relevance = min(100, relevance + good_direction_hits * 4)

        structural_depth = self.structural_depth_score(candidate)
        novelty_search = self.novelty_search_score(candidate, domain)

        novelty = min(
            100,
            40
            + len(set(candidate.get("ingredients", []))) * 3
            + (12 if candidate.get("parent_ids") else 0)
            + (8 if candidate.get("graph_used", {}).get("id") else 0)
            + novelty_search.get("score", 0) * 0.25
        )

        coherence = 68 + structural_depth * 0.18
        if len(candidate.get("concept", "")) > 500:
            coherence -= 12
        if candidate.get("domain") != domain and domain != "general":
            coherence -= 10
        if bad_direction_hits:
            coherence -= bad_direction_hits * 6

        usefulness = 55 + min(term_hits * 5, 25) + structural_depth * 0.18

        if candidate.get("graph_used", {}).get("merge_strategy"):
            usefulness += 5

        memory_score = self.score_against_creative_memory(candidate, domain)
        usefulness += memory_score.get("boost", 0)
        novelty -= memory_score.get("repeat_penalty", 0)
        novelty = max(0, min(novelty, 100))
        usefulness = max(0, min(usefulness, 100))

        safety = 100
        if any(term in text for term in UNSAFE_TERMS):
            safety = 35

        total = (
            relevance * 0.26
            + novelty * 0.24
            + coherence * 0.18
            + usefulness * 0.16
            + structural_depth * 0.08
            + novelty_search.get("score", 0) * 0.08
            + safety * 0.10
        )

        candidate["scores"] = {
            "relevance": round(relevance, 2),
            "novelty": round(novelty, 2),
            "coherence": round(coherence, 2),
            "usefulness": round(usefulness, 2),
            "safety": round(safety, 2),
            "structural_depth": round(structural_depth, 2),
            "novelty_search": novelty_search,
            "direction_fit": round(max(0, 70 + good_direction_hits * 8 - bad_direction_hits * 12), 2),
            "memory_fit": memory_score,
            "graph_fit": 85 if candidate.get("graph_used", {}).get("id") else 45,
            "total": round(total, 2)
        }

        return candidate

    def score_against_creative_memory(self, candidate, domain):

        text = " ".join([
            candidate.get("title", ""),
            candidate.get("concept", ""),
            " ".join(candidate.get("ingredients", []))
        ]).lower()

        previous = [
            idea
            for idea in self.creative_memory.get("ideas", [])[-80:]
            if idea.get("domain") == domain
        ]

        repeat_penalty = 0
        boost = 0

        for idea in previous:
            old_terms = set(idea.get("ingredients", []))
            new_terms = set(candidate.get("ingredients", []))
            overlap = len(old_terms & new_terms)

            if overlap >= 8:
                repeat_penalty += 5
            elif overlap >= 3:
                boost += 2

            if idea.get("title", "").lower() in text:
                repeat_penalty += 8

        return {
            "boost": min(boost, 12),
            "repeat_penalty": min(repeat_penalty, 25),
            "previous_domain_ideas": len(previous)
        }

    def score_generation(self, candidates, terms, domain, direction):

        scored = [
            self.score_candidate(candidate, terms, domain, direction)
            for candidate in candidates
        ]

        scored.sort(
            key=lambda item: item["scores"]["total"],
            reverse=True
        )

        return scored

    def evaluate_strategic_stop(
        self,
        scored,
        history,
        direction,
        generation,
        improvement
    ):

        top = scored[0]
        scores = top.get("scores", {})

        idea_depth = self.estimate_idea_depth(top)
        goal_fit = scores.get("relevance", 0)
        novelty = scores.get("novelty", 0)
        coherence = scores.get("coherence", 0)
        safety = scores.get("safety", 0)
        direction_fit = scores.get("direction_fit", 0)

        repeated = self.detect_generation_repetition(scored[:12])

        decision = {
            "should_stop": False,
            "reason": "continue_evolving",
            "idea_depth": idea_depth,
            "goal_fit": goal_fit,
            "direction_fit": direction_fit,
            "repeated_direction": repeated,
            "next_action": "continue_same_direction"
        }

        if safety < 70:
            decision.update({
                "should_stop": False,
                "reason": "unsafe_direction_change_required",
                "next_action": "change_to_safe_direction"
            })
            return decision

        if repeated and generation >= 2:
            decision.update({
                "should_stop": False,
                "reason": "direction_repeating",
                "next_action": "change_direction"
            })
            return decision

        if (
            goal_fit >= 82
            and novelty >= 72
            and coherence >= 66
            and direction_fit >= 70
            and idea_depth >= 70
            and generation >= 2
        ):
            decision.update({
                "should_stop": True,
                "reason": "strategic_quality_good_enough",
                "next_action": "stop_and_merge_best"
            })
            return decision

        if generation >= 3 and improvement < 2 and idea_depth >= 62 and goal_fit >= 74:
            decision.update({
                "should_stop": True,
                "reason": "diminishing_returns_with_usable_idea",
                "next_action": "stop_before_overfitting"
            })
            return decision

        if generation >= 3 and improvement < 2:
            decision.update({
                "should_stop": False,
                "reason": "low_improvement_change_direction",
                "next_action": "change_direction"
            })
            return decision

        return decision

    def estimate_idea_depth(self, candidate):

        ingredients = candidate.get("ingredients", [])
        concept = candidate.get("concept", "")
        graph_used = candidate.get("graph_used", {})
        parents = candidate.get("parent_ids", [])

        depth = 25
        depth += min(len(set(ingredients)) * 4, 35)
        depth += 15 if graph_used.get("id") else 0
        depth += 10 if parents else 0
        depth += 10 if len(concept) > 180 else 0
        depth += 5 if "Merge target:" in concept else 0

        return min(depth, 100)

    def detect_generation_repetition(self, candidates):

        titles = [
            candidate.get("title", "").lower()
            for candidate in candidates
        ]

        if len(set(titles)) <= max(3, len(titles) // 3):
            return True

        core_ingredients = [
            tuple(candidate.get("ingredients", [])[:4])
            for candidate in candidates
        ]

        return len(set(core_ingredients)) <= max(3, len(core_ingredients) // 3)

    def select_elites(self, scored, count=8):

        return scored[:count]

    def select_novelty_elites(self, scored, count=6):

        novelty_sorted = sorted(
            scored,
            key=lambda item: (
                item.get("scores", {}).get("novelty_search", {}).get("score", 0),
                item.get("scores", {}).get("structural_depth", 0)
            ),
            reverse=True
        )

        selected = []
        seen = set()

        for candidate in novelty_sorted:
            candidate_id = candidate.get("id")
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            selected.append(candidate)
            if len(selected) >= count:
                break

        return selected

    def tournament_select(self, pool, index, tournament_size=5):

        if not pool:
            return None

        contenders = [
            pool[(index + offset * 7) % len(pool)]
            for offset in range(tournament_size)
        ]

        contenders.sort(
            key=lambda item: (
                item.get("scores", {}).get("total", 0) * 0.75
                + item.get("scores", {}).get("novelty_search", {}).get("score", 0) * 0.25
            ),
            reverse=True
        )

        return contenders[0]

    def unique_candidates(self, candidates):

        unique = []
        seen = set()

        for candidate in candidates:
            candidate_id = candidate.get("id")
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            unique.append(candidate)

        return unique

    def build_next_generation(self, scored, terms, direction, generation, generation_size):

        elites = self.select_elites(scored, count=max(6, generation_size // 14))
        novelty_elites = self.select_novelty_elites(scored, count=max(4, generation_size // 18))
        parent_pool = self.unique_candidates(
            elites + novelty_elites + scored[:max(18, generation_size // 4)]
        )
        next_generation = self.unique_candidates(
            elites + novelty_elites
        )

        index = 0
        while len(next_generation) < generation_size:
            left = self.tournament_select(parent_pool, index)
            right = self.tournament_select(parent_pool, index + 3)

            if not left:
                break

            if index % 5 in [0, 3] and right:
                child = self.merge_candidates(
                    left,
                    right,
                    generation + 1,
                    index,
                    direction
                )
                child["evolution_operator"] = "crossover"
            else:
                child = self.mutate_candidate(
                    left,
                    terms,
                    generation + 1,
                    index,
                    direction
                )
                child["evolution_operator"] = "semantic_mutation"

            next_generation.append(child)
            index += 1

        return next_generation[:generation_size]

    def change_direction(
        self,
        direction,
        reason
    ):

        changed = dict(direction)
        previous = changed.get("preferred_strategy", "balanced_evolution")

        if reason in ["direction_repeating", "low_improvement_change_direction"]:
            changed["preferred_strategy"] = "constraint_shift"
            changed["constraints"] = list(dict.fromkeys(changed.get("constraints", []) + ["force_new_angle"]))
        elif reason == "unsafe_direction_change_required":
            changed["preferred_strategy"] = "safe_redirection"
            changed["constraints"] = list(dict.fromkeys(changed.get("constraints", []) + ["safety_first"]))
        else:
            changed["preferred_strategy"] = "balanced_evolution"

        changed["previous_strategy"] = previous
        changed["changed_because"] = reason

        return changed

    def evolve(self, domain, terms, direction, generation_size=100, max_rounds=5):

        candidates = self.initial_generation(domain, terms, direction, generation_size)
        history = []
        previous_best = 0
        stop_reason = "max_rounds"

        for generation in range(1, max_rounds + 1):
            scored = self.score_generation(candidates, terms, domain, direction)
            top = scored[0]
            best_score = top["scores"]["total"]
            improvement = best_score - previous_best
            strategic_stop = self.evaluate_strategic_stop(
                scored,
                history,
                direction,
                generation,
                improvement
            )

            history.append({
                "generation": generation,
                "candidate_count": len(scored),
                "best_score": best_score,
                "improvement": round(improvement, 2),
                "best_id": top["id"],
                "best_title": top["title"],
                "strategic_stop": strategic_stop
            })

            if strategic_stop["should_stop"]:
                stop_reason = strategic_stop["reason"]
                return scored, history, stop_reason, direction

            if strategic_stop["next_action"] in [
                "change_direction",
                "change_to_safe_direction"
            ]:
                direction = self.change_direction(
                    direction,
                    strategic_stop["reason"]
                )

            previous_best = best_score
            candidates = self.build_next_generation(
                scored,
                terms,
                direction,
                generation,
                generation_size
            )

        return self.score_generation(candidates, terms, domain, direction), history, stop_reason, direction

    # ---------- public helpers ----------

    def rescue_brain(
        self,
        brain_name,
        failure_reason,
        context=None,
        needed_output="idea"
    ):

        context = context or {}

        rescue_request = {
            "understanding": context.get("understanding", context),
            "memory": context.get("memory", {}),
            "problem": failure_reason,
            "goal": f"rescue {brain_name} and produce {needed_output}",
            "rescue": {
                "brain_name": brain_name,
                "failure_reason": failure_reason,
                "needed_output": needed_output
            }
        }

        result = self.process(rescue_request)

        best = result.get("best_idea", {})

        return {
            "brain": "Creative_brain",
            "purpose": "brain_rescue",
            "rescued_brain": brain_name,
            "failure_reason": failure_reason,
            "needed_output": needed_output,
            "direction_analysis": result.get("direction_analysis", {}),
            "best_idea": best,
            "quality": result.get("quality", {}),
            "rescue_plan": self.build_rescue_plan(brain_name, failure_reason, best, needed_output),
            "confidence": result.get("confidence", 0)
        }

    def looks_like_internal_report(self, text):

        lowered = str(text or "").lower()
        markers = [
            "goal:",
            "core idea:",
            "novel twist:",
            "constraint:",
            "validation:",
            "tradeoff:",
            "implementation:",
            "direction:"
        ]

        return sum(1 for marker in markers if marker in lowered) >= 3

    def requested_sentence_count(self, text, default=6):

        lowered = str(text or "").lower()
        range_match = re.search(
            r"(\d+)\s*(?:-|to)\s*(\d+)\s+sentences?",
            lowered
        )
        if range_match:
            return max(1, min(int(range_match.group(2)), 10))

        exact_match = re.search(r"(\d+)\s+sentences?", lowered)
        if exact_match:
            return max(1, min(int(exact_match.group(1)), 10))

        return default

    def task_text(self, task_report):

        report = self.get_understanding_report(task_report)
        text = self.extract_text(task_report, report)

        if text:
            return text

        if isinstance(task_report, dict):
            source_result = task_report.get("source_result", {})
            if isinstance(source_result, dict):
                for key in [
                    "original_text",
                    "final_output",
                    "answer",
                    "summary",
                    "draft",
                    "story",
                    "generated_code"
                ]:
                    value = source_result.get(key)
                    if value:
                        return str(value)

        return str(task_report or "")

    def is_story_request(self, text, task_type="", source_brain=""):

        lowered = str(text or "").lower()
        task_type = str(task_type or "").lower()

        if source_brain in {"Story_brain", "Character_brain", "World_brain"}:
            return True

        markers = [
            "story",
            "chapter",
            "character",
            "plot",
            "narrative",
            "sentences",
            "continue the same story",
            "make me up a story",
            "write a short original story"
        ]

        return "story" in task_type or any(marker in lowered for marker in markers)

    def is_code_request(self, text, task_type="", source_brain=""):

        lowered = str(text or "").lower()
        task_type = str(task_type or "").lower()

        if source_brain == "Code_brain":
            return True

        markers = [
            "code",
            "program",
            "python",
            "javascript",
            "function",
            "class",
            "terminal",
            "json file",
            "runnable"
        ]

        return "code" in task_type or any(marker in lowered for marker in markers)

    def extract_story_name(self, text):

        text = str(text or "")
        named = re.search(r"\bnamed\s+([A-Z][a-zA-Z]{1,30})\b", text)
        if named:
            return named.group(1)

        about_name = re.search(
            r"\babout\s+(?:a|an|the)?\s*([A-Z][a-zA-Z]{1,30})\b",
            text
        )
        if about_name:
            return about_name.group(1)

        if re.search(r"\bpatient\b", text, re.IGNORECASE):
            return "Elias"
        if re.search(r"\bboy\b", text, re.IGNORECASE):
            return "Leo"
        if re.search(r"\bgirl\b", text, re.IGNORECASE):
            return "Maya"

        return "Ari"

    def story_elements_from_text(self, text):

        lowered = str(text or "").lower()
        elements = {
            "setting": "a quiet place",
            "discovery": "a strange clue",
            "conflict": "a choice that could not be ignored",
            "ending": "a small brave step forward"
        }

        if "park" in lowered:
            elements["setting"] = "the quiet park"
        elif "bed" in lowered or "tiny door" in lowered:
            elements["setting"] = "the room above a tiny hidden door"
        elif "meeting" in lowered:
            elements["setting"] = "the final meeting room"

        if "glowing key" in lowered or "key" in lowered:
            elements["discovery"] = "a glowing key that pulsed like it was alive"
        elif "tiny door" in lowered or "door" in lowered:
            elements["discovery"] = "a tiny door glowing under the bed"
        elif "patient" in lowered and "six months" in lowered:
            elements["discovery"] = "the missing patient returning after six months"

        if "everyone is asleep" in lowered:
            elements["conflict"] = "whether to wake the sleeping city or protect its silence"
        elif "injured" in lowered:
            elements["conflict"] = "how to keep going after being hurt"
        elif "patient" in lowered:
            elements["conflict"] = "whether the truth should be spoken before the final decision"

        if "wake" in lowered:
            elements["ending"] = "a careful decision to wake only one lantern first"
        elif "meeting" in lowered:
            elements["ending"] = "the meeting changing because someone finally told the truth"

        return elements

    def build_story_output(self, text, best=None):

        sentence_count = self.requested_sentence_count(text, default=6)
        name = self.extract_story_name(text)
        elements = self.story_elements_from_text(text)
        lowered = str(text or "").lower()
        lexical_plan = (
            best.get("lexical_plan", {}).get("selected", {})
            if isinstance(best, dict)
            else {}
        )
        opening_verb = lexical_plan.get("opening_verb", "stepped")
        noticing_verb = lexical_plan.get("noticing_verb", "noticed")
        reaction_adjective = lexical_plan.get("reaction_adjective", "strange")
        response_adverb = lexical_plan.get("response_adverb", "carefully")
        character_descriptor = lexical_plan.get("character_descriptor", "")
        character_intro = (
            f"{name}, a {character_descriptor} character,"
            if character_descriptor
            else name
        )

        if lexical_plan:
            generated_sentences = [
                f"{character_intro} {opening_verb} into {elements['setting']} and {noticing_verb} {elements['discovery']}.",
                f"The discovery seemed {reaction_adjective} because it changed what {name} believed about the place.",
                f"The situation forced {name} to confront {elements['conflict']}.",
                f"Instead of reacting immediately, {name} examined the available clues {response_adverb}.",
                f"That pause revealed a choice connected to {elements['ending']}.",
                f"By acting on the choice, {name} changed both the problem and the way it was understood.",
                f"The experience ended with {name} carrying a clearer sense of what to do next."
            ]
            return " ".join(generated_sentences[:sentence_count])

        if "patient" in lowered and "six months" in lowered:
            sentences = [
                f"For six months, nobody at the clinic knew where {name} had gone.",
                "His empty chair stayed in the corner of the waiting room, marked only by a folder no one wanted to close.",
                "On the morning of the final meeting, he walked in wearing the same gray coat but carrying a sealed envelope.",
                "The doctors were shocked, but he asked them to listen before they wrote the last report.",
                "Inside the envelope were notes from every day he had been missing, showing that he had been searching for the person who caused the accident that changed his life.",
                "When the meeting ended, the final decision was no longer about where he had been, but about what everyone owed to the truth.",
                f"{name} left quietly, no longer a vanished patient but the one person brave enough to return.",
            ]
            return " ".join(sentences[:sentence_count])

        if "tiny door" in lowered and "asleep" in lowered:
            sentences = [
                f"{name} found the tiny door under his bed after hearing a soft bell ring beneath the floorboards.",
                "When he opened it, a glowing city no larger than a toy box shimmered in the dark.",
                "Every window was lit, but every person in the city slept with their hands folded over their hearts.",
                "At the center of the city, a silver clock showed his own heartbeat instead of the time.",
                f"{name} understood that waking the city too quickly might break the spell that kept it safe.",
                "He chose to light one small tower first and wait until the sleepers opened their eyes on their own.",
                "By morning, the door was still there, and Leo knew the city trusted him to return.",
            ]
            return " ".join(sentences[:sentence_count])

        sentences = [
            f"{character_intro} {opening_verb} into {elements['setting']} and {noticing_verb} {elements['discovery']}.",
            f"At first the discovery seemed {reaction_adjective}, but it changed the whole shape of the day.",
            f"The real problem was {elements['conflict']}.",
            f"{name} felt afraid, but curiosity made the next step feel possible.",
            f"Instead of rushing, {name} moved {response_adverb} and listened for the quiet rule hidden inside the moment.",
            f"In the end, the choice became {elements['ending']}.",
            "Nothing became simple, but the world felt wider than it had before.",
        ]

        return " ".join(sentences[:sentence_count])

    def build_general_creative_output(self, text, best=None, source_brain=""):

        best = best or {}
        model = best.get("idea_model", {}) if isinstance(best, dict) else {}

        goal = model.get("goal") or str(text or "the task").strip()
        mechanism = model.get("mechanism") or "a focused step-by-step approach"
        constraint = model.get("constraint") or "keep the output concrete and useful"
        validation = model.get("validation") or "compare the result against the user's request"

        if self.looks_like_internal_report(goal):
            goal = "the user's request"

        return (
            f"Use {mechanism} to solve {goal}. "
            f"Keep one clear constraint: {constraint}. "
            f"Before returning the answer, validate it by: {validation}. "
            "The final response should be the finished result, not the internal simulation."
        )

    def build_conversation_output(self, text, emotion_result=None):

        emotion_result = emotion_result if isinstance(emotion_result, dict) else {}
        support_response = str(
            emotion_result.get("support_response")
            or emotion_result.get("final_output")
            or ""
        ).strip()
        if support_response and not self.looks_like_internal_report(support_response):
            return support_response

        hebrew = bool(re.search(r"[\u0590-\u05ff]", str(text or "")))
        if hebrew:
            return (
                "\u05d0\u05e0\u05d9 \u05db\u05d0\u05df \u05d0\u05d9\u05ea\u05da. \u05d0\u05e4\u05e9\u05e8 \u05dc\u05e1\u05e4\u05e8 \u05dc\u05d9 \u05de\u05d4 \u05e7\u05d5\u05e8\u05d4, "
                "\u05d5\u05e0\u05e1\u05d3\u05e8 \u05d0\u05ea \u05d6\u05d4 \u05d9\u05d7\u05d3 \u05e6\u05e2\u05d3 \u05d0\u05d7\u05e8 \u05e6\u05e2\u05d3."
            )
        return (
            "I am here with you. Tell me what is happening, and we can work "
            "through it one step at a time."
        )

    def build_creative_final_output(
        self,
        text,
        domain,
        best=None,
        source_brain="Creative_brain",
        task_type="creative_generation"
    ):

        best = best or {}

        for key in ["final_output", "story", "answer"]:
            value = best.get(key) if isinstance(best, dict) else None
            if isinstance(value, str) and value.strip():
                if not self.looks_like_internal_report(value):
                    return value.strip()

        if self.is_story_request(text, task_type, source_brain) or domain == "story":
            return self.build_story_output(text, best)

        if self.is_code_request(text, task_type, source_brain) or domain == "code":
            code_result = self.code_assembler.assemble({
                "original_text": text,
                "main_topic": "code",
                "intent": "code_generation"
            })
            return code_result.get("generated_code", "").strip()

        return self.build_general_creative_output(
            text,
            best,
            source_brain
        )

    def creative_execution_policy(self, report, text, detected_domain):

        report = report if isinstance(report, dict) else {}
        intent = str(report.get("intent", "")).lower()
        topic = str(report.get("main_topic", "")).lower()
        lowered = str(text or "").lower()
        explicit_story = intent == "story_creation" or topic == "story" or any(
            marker in lowered
            for marker in ["write a story", "create a story", "continue the story", "chapter", "narrative"]
        )
        explicit_code = intent in {"code_generation", "code_analysis"} or topic == "code"
        emotional_conversation = topic == "emotion" or any(
            marker in lowered
            for marker in [
                "i feel", "can we talk", "listen to me", "need someone",
                "having a hard time", "\u05e7\u05e9\u05d4 \u05dc\u05d9", "\u05d0\u05e4\u05e9\u05e8 \u05dc\u05d3\u05d1\u05e8",
                "\u05d0\u05e0\u05d9 \u05de\u05e8\u05d2\u05d9\u05e9", "\u05d0\u05e0\u05d9 \u05de\u05e8\u05d2\u05d9\u05e9\u05d4"
            ]
        )
        factual = intent in {"question", "research"} and not any(
            marker in lowered
            for marker in ["brainstorm", "invent", "creative idea", "imagine"]
        )

        if explicit_code:
            return {
                "mode": "code_assembly",
                "domain": "code",
                "generation_size": 60,
                "max_rounds": 3,
                "allow_story": False,
                "reason": "Code request requires code assembly, never narrative output."
            }
        if explicit_story:
            return {
                "mode": "story_generation",
                "domain": "story",
                "generation_size": 80,
                "max_rounds": 4,
                "allow_story": True,
                "reason": "User explicitly requested narrative content."
            }
        if emotional_conversation:
            return {
                "mode": "conversation_support",
                "domain": "emotion",
                "generation_size": 24,
                "max_rounds": 2,
                "allow_story": False,
                "reason": "Emotion_brain leads; creativity only improves supportive phrasing."
            }
        if factual:
            return {
                "mode": "support_only",
                "domain": "general",
                "generation_size": 24,
                "max_rounds": 2,
                "allow_story": False,
                "reason": "Factual requests may use creative problem solving but must not become fiction."
            }
        return {
            "mode": "creative_generation",
            "domain": detected_domain,
            "generation_size": 60,
            "max_rounds": 4,
            "allow_story": detected_domain == "story",
            "reason": "Creative generation requested or useful for the selected domain."
        }

    def answer_payload(
        self,
        final_output,
        domain,
        source_brain,
        task_type,
        confidence,
        best=None
    ):

        payload = {
            "final_output": final_output,
            "answer": final_output,
            "source_brain": source_brain,
            "task_type": task_type,
            "domain": domain,
            "confidence": confidence,
            "simulation_summary": {
                "selected_idea": (best or {}).get("title"),
                "score": (best or {}).get("scores", {}).get("total", confidence),
                "kept_internal": True
            }
        }

        if domain == "story" or self.is_story_request(final_output, task_type, source_brain):
            payload["story"] = final_output

        if domain == "code" or self.is_code_request(final_output, task_type, source_brain):
            payload["generated_code"] = final_output

        return payload

    def solve_brain_task(
        self,
        source_brain,
        task_report,
        task_type="solve_problem"
    ):

        task_report = task_report or {}

        if task_type == "creative_code_assembly" or source_brain == "Code_brain":
            code_result = self.create_code(task_report)
            generated_code = code_result.get("generated_code", "")
            answer_for_source = {
                "final_output": generated_code,
                "answer": generated_code,
                "generated_code": generated_code,
                "language": code_result.get("language", "python"),
                "code_assembly": code_result.get("code_assembly", {}),
                "code_graph": code_result.get("code_graph", {}),
                "confidence": code_result.get("confidence", 0)
            }
            return {
                "brain": "Creative_brain",
                "source_brain": source_brain,
                "task_type": task_type,
                "answer_for_source_brain": answer_for_source,
                "final_output": generated_code,
                "answer": generated_code,
                "suggested_actions": [
                    {
                        "step": 1,
                        "action": "send generated draft back to Code_brain",
                        "detail": "Code_brain should refine names, imports, and exact integration."
                    },
                    {
                        "step": 2,
                        "action": "review with Security_brain",
                        "detail": "Generated code is not executed by Creative_brain."
                    }
                ],
                "generated_code": generated_code,
                "code_graph": code_result.get("code_graph", {}),
                "simulation_summary": {
                    "mode": "creative_code_assembly",
                    "internal_idea_kept": True,
                    "returned_user_facing_code": bool(generated_code)
                },
                "quality": {
                    "code_assembled": bool(generated_code),
                    "graph_used": bool(code_result.get("code_graph", {}).get("nodes"))
                },
                "confidence": code_result.get("confidence", 0)
            }

        context = {
            "understanding": task_report.get(
                "understanding",
                task_report
            ),
            "memory": task_report.get(
                "memory",
                {}
            ),
            "goal": task_report.get(
                "goal",
                f"solve task from {source_brain}"
            ),
            "problem": task_report.get(
                "problem",
                task_report.get("failure_reason", "")
            ),
            "task_type": task_type,
            "source_brain": source_brain
        }

        rescue = self.rescue_brain(
            source_brain,
            context.get(
                "problem",
                "brain requested creative help"
            ),
            context,
            task_type
        )

        text = self.task_text(task_report)
        report = self.get_understanding_report(task_report)
        terms = self.collect_terms(
            report,
            self.get_memory_report(task_report),
            text
        )
        domain = self.detect_domain(report, terms, text)
        execution_policy = self.creative_execution_policy(
            report,
            text,
            domain
        )
        domain = execution_policy["domain"]
        best = rescue.get("best_idea", {})
        final_output = self.build_creative_final_output(
            text,
            domain,
            best,
            source_brain,
            task_type
        )
        confidence = rescue.get("confidence", 0)
        answer_for_source = self.answer_payload(
            final_output,
            domain,
            source_brain,
            task_type,
            confidence,
            best
        )

        return {
            "brain": "Creative_brain",
            "source_brain": source_brain,
            "task_type": task_type,
            "answer_for_source_brain": answer_for_source,
            "final_output": final_output,
            "answer": final_output,
            "story": answer_for_source.get("story"),
            "generated_code": answer_for_source.get("generated_code"),
            "suggested_actions": rescue.get("rescue_plan", []),
            "simulation_summary": {
                "mode": "brain_rescue",
                "selected_idea": best.get("title") if isinstance(best, dict) else None,
                "internal_idea_kept": True,
                "returned_final_output": bool(final_output)
            },
            "quality": rescue.get("quality", {}),
            "confidence": confidence
        }

    def build_rescue_plan(
        self,
        brain_name,
        failure_reason,
        best_idea,
        needed_output
    ):

        return [
            {
                "step": 1,
                "action": "identify failure",
                "detail": failure_reason
            },
            {
                "step": 2,
                "action": "use creative direction",
                "detail": best_idea.get("title", "creative fallback idea")
            },
            {
                "step": 3,
                "action": "return to specialist brain",
                "detail": f"Route {needed_output} back to {brain_name} for domain-specific execution."
            }
        ]

    def create_code(self, request):

        result = self.rescue_brain(
            "Code_brain",
            "missing function or weak local code match",
            {
                "understanding": request if isinstance(request, dict) else {
                    "original_text": str(request),
                    "main_topic": "code"
                }
            },
            "code direction"
        )

        best = result.get("best_idea", {})
        assembled = self.code_assembler.assemble(
            request,
            result
        )

        return {
            "brain": "Creative_brain",
            "purpose": "code_fallback",
            "idea": best,
            "code_assembly": assembled,
            "code_graph": assembled.get("code_graph", {}),
            "canri_code_context": assembled.get("canri_code_context", {}),
            "generated_code": assembled.get("generated_code", ""),
            "assembly_notes": assembled.get("assembly_notes", []),
            "confidence": max(
                result.get("confidence", 0),
                assembled.get("confidence", 0)
            )
        }

    def remember_creative_result(
        self,
        domain,
        direction,
        best,
        stop_reason
    ):

        if not best:
            return

        memory_item = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "title": best.get("title"),
            "concept": best.get("concept"),
            "idea_model": best.get("idea_model", {}),
            "idea_signature": list(self.idea_signature(best)),
            "mutation_operator": best.get("mutation_operator"),
            "evolution_operator": best.get("evolution_operator"),
            "ingredients": best.get("ingredients", []),
            "scores": best.get("scores", {}),
            "direction_strategy": direction.get("preferred_strategy"),
            "stop_reason": stop_reason
        }

        self.creative_memory.setdefault("ideas", []).append(memory_item)
        self.creative_memory["ideas"] = self.creative_memory["ideas"][-500:]

        if best.get("scores", {}).get("total", 0) >= 78:
            successful = self.creative_memory.setdefault("successful_patterns", {})
            domain_terms = successful.setdefault(domain, [])
            domain_terms.extend(best.get("ingredients", [])[:8])
            successful[domain] = list(dict.fromkeys(domain_terms))[-80:]

            operators = self.creative_memory.setdefault("successful_operators", {})
            domain_operators = operators.setdefault(domain, {})
            operator = best.get("mutation_operator") or best.get("evolution_operator") or "initial"
            domain_operators[operator] = domain_operators.get(operator, 0) + 1

        if stop_reason in [
            "direction_repeating",
            "unsafe_direction_change_required",
            "low_improvement_change_direction"
        ]:
            failed = self.creative_memory.setdefault("failed_directions", {})
            failed_terms = failed.setdefault(domain, [])
            failed_terms.append(direction.get("preferred_strategy", "unknown"))
            failed[domain] = list(dict.fromkeys(failed_terms))[-40:]

        profiles = self.creative_memory.setdefault("direction_profiles", {})
        profile = profiles.get(domain, {
            "uses": 0,
            "average_score": 0
        })
        old_uses = profile.get("uses", 0)
        old_average = profile.get("average_score", 0)
        new_score = best.get("scores", {}).get("total", 0)
        profile["uses"] = old_uses + 1
        profile["average_score"] = round(
            ((old_average * old_uses) + new_score) / max(profile["uses"], 1),
            2
        )
        profile["last_strategy"] = direction.get("preferred_strategy")
        profiles[domain] = profile

        self.save_creative_memory()

    # ---------- statistics/process ----------

    def update_statistics(self, domain, best_score, stop_reason):

        stats = self.statistics.get("Creative_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_domain"] = domain
        stats["last_best_score"] = best_score
        stats["last_stop_reason"] = stop_reason
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("seeds", len(self.seeds))
        stats.setdefault("rules", len(self.rules))
        stats.setdefault("graphs", len(self.graphs))

        self.statistics["Creative_brain"] = stats
        self.save_statistics()

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        terms = self.collect_terms(report, memory_report, text)
        domain = self.detect_domain(report, terms, text)
        execution_policy = self.creative_execution_policy(
            report,
            text,
            domain
        )
        domain = execution_policy["domain"]
        canri_context = self.collect_indexed_project_context(
            data,
            report,
            terms
        )
        if domain in {"geography", "story", "general"}:
            canri_context.update(
                self.collect_indexed_geography_context(terms, text, limit=10)
            )
        if not canri_context:
            canri_context = self.collect_canri_context(
                domain,
                terms,
                data if isinstance(data, dict) else {}
            )
        canri_terms = self.terms_from_canri_context(canri_context)
        terms = list(dict.fromkeys(terms + canri_terms))[:160]
        direction = self.analyze_direction(
            report,
            memory_report,
            terms,
            text,
            domain
        )
        lexical_plan = self.dictionary_composer.build_plan(
            report,
            text,
            terms,
            domain
        )

        generation_size = execution_policy["generation_size"]
        max_rounds = execution_policy["max_rounds"]

        scored, history, stop_reason, final_direction = self.evolve(
            domain,
            terms,
            direction,
            generation_size,
            max_rounds
        )

        best = scored[0] if scored else {}
        if isinstance(best, dict):
            best = dict(best)
            best["lexical_plan"] = lexical_plan
        best_score = best.get("scores", {}).get("total", 0)
        final_output = self.build_creative_final_output(
            text,
            domain,
            best,
            "Creative_brain",
            "creative_generation"
        )
        if execution_policy.get("mode") == "conversation_support":
            results = data.get("results", {}) if isinstance(data, dict) else {}
            emotion_result = results.get("Emotion_brain", {}) if isinstance(results, dict) else {}
            final_output = self.build_conversation_output(text, emotion_result)

        response_evolution = self.text_composer.evolve(
            data if isinstance(data, dict) else {},
            report,
            text,
            domain,
            final_output,
            canri_context
        )
        evolved_output = str(response_evolution.get("selected_output", "")).strip()
        if (
            response_evolution.get("enabled")
            and evolved_output
            and domain not in {"story", "code", "emotion"}
            and not self.looks_like_internal_report(evolved_output)
        ):
            final_output = evolved_output

        if isinstance(best, dict):
            best["final_output"] = final_output
            if domain == "story":
                best["story"] = final_output
            if domain == "code":
                best["generated_code"] = final_output

        self.remember_creative_result(
            domain,
            final_direction,
            best,
            stop_reason
        )

        self.update_statistics(domain, best_score, stop_reason)

        return {
            "brain": "Creative_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "domain": domain,
            "execution_policy": execution_policy,
            "terms_used": terms,
            "direction_analysis": final_direction,
            "final_output": final_output,
            "answer": final_output,
            "story": final_output if domain == "story" else None,
            "generated_code": final_output if domain == "code" else None,
            "best_idea": best,
            "top_ideas": scored[:10],
            "simulation_summary": {
                "selected_idea": best.get("title") if isinstance(best, dict) else None,
                "internal_evolution_kept": True,
                "returned_final_output": bool(final_output),
                "report_separated_from_output": True,
                "story_output_allowed": execution_policy.get("allow_story", False)
            },
            "evolution": {
                "generation_size": generation_size,
                "rounds_completed": len(history),
                "history": history,
                "stop_reason": stop_reason,
                "algorithm": {
                    "candidate_model": "structured_idea_model",
                    "mutation": "semantic_field_mutation",
                    "selection": "elitism + novelty_elites + tournament_selection",
                    "crossover": "idea_model_crossover",
                    "novelty_search": True,
                    "reinforcement_memory": "successful operators and patterns are stored in Creative_memory.json"
                }
            },
            "strategic_stop": history[-1].get("strategic_stop", {}) if history else {},
            "quality": {
                "best_score": best_score,
                "good_enough": best_score >= 78,
                "creative_enough": best.get("scores", {}).get("novelty", 0) >= 70,
                "coherent_enough": best.get("scores", {}).get("coherence", 0) >= 65,
                "safe_enough": best.get("scores", {}).get("safety", 0) >= 70,
                "direction_good_enough": best.get("scores", {}).get("direction_fit", 0) >= 70,
                "graph_used": bool(best.get("graph_used", {}).get("id")),
                "remembered": True
            },
            "canri_data_used": canri_context,
            "canri_data_strategy": {
                "mode": "project_wide_indexed_retrieval",
                "full_files_loaded": any(
                    bool(file_info.get("full_file_loaded"))
                    for file_info in canri_context.values()
                    if isinstance(file_info, dict)
                ),
                "rules_files_excluded": True,
                "understanding_dictionaries_available": any(
                    str(file_name).startswith("UnderstandingDk::")
                    or file_info.get("source_group") == "understanding_dictionaries"
                    for file_name, file_info in canri_context.items()
                    if isinstance(file_info, dict)
                ),
                "files_considered": len(canri_context),
                "domain": domain,
                "reason": (
                    "search all project data sources, exclude rule files, and return only "
                    "the highest-scoring snippets plus exact dictionary lookups"
                )
            },
            "creative_memory": {
                "ideas_stored": len(self.creative_memory.get("ideas", [])),
                "domain_profile": self.creative_memory.get("direction_profiles", {}).get(domain, {})
            },
            "dictionary_guided_composition": lexical_plan,
            "response_evolution": response_evolution,
            "confidence": min(100, round(best_score, 2)),
            "suggested_next_brains": [
                brain_name
                for brain_name in [
                    "Story_brain" if domain == "story" else None,
                    "Code_brain" if domain == "code" else None,
                    "Planner_brain",
                    "Security_brain" if best.get("scores", {}).get("safety", 100) < 80 else None,
                    "Response_brain"
                ]
                if brain_name
            ],
            "raw_suggested_next_brains": [
                "Story_brain" if domain == "story" else None,
                "Code_brain" if domain == "code" else None,
                "Planner_brain",
                "Security_brain" if best.get("scores", {}).get("safety", 100) < 80 else None,
                "Response_brain"
            ],
            "rules": [
                "Generate many candidates before choosing.",
                "Keep novelty, relevance, coherence, usefulness, and safety visible.",
                "Stop when quality is high enough or improvement becomes small.",
                "Use Creative_brain as fallback when specialist brains are stuck."
            ]
        }


brain = CreativeBrain()
