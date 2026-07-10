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


DATA_DIR = Path(__file__).parent / "data"
SEEDS_FILE = DATA_DIR / "Creative_seed_bank.json"
RULES_FILE = DATA_DIR / "Creative_scoring_rules.json"
GRAPHS_FILE = DATA_DIR / "Creative_evolution_graphs.json"
STATS_FILE = DATA_DIR / "Creative_statistics.json"
MEMORY_FILE = DATA_DIR / "Creative_memory.json"

ALWAYS_CANRI_DATA_FILES = [
    "Learning_history.json",
    "Learning_statistics.json",
    "Learning_rules.json",
    "Improvement_queue.json",
    "Brain_performance.json",
    "Memory_database.json",
    "Planner_task_templates.json",
    "Planner_dependency_graph.json",
    "Planner_risk_rules.json",
    "Reasoning_patterns.json",
    "Reasoning_rules.json",
    "Knowledge_index.json",
    "Knowledge_statistics.json",
]

DOMAIN_CANRI_DATA_FILES = {
    "code": [
        "code.json",
        "Code_dependency_graph.json",
        "Code_composition_tables.json",
        "Code_assembly_patterns.json",
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
        "Geography_statistics.json",
        "research_sources.json"
    ],
    "history": [
        "history_knowledge.json",
        "history_sources.json",
        "Articles.json",
        "research_sources.json"
    ],
    "security": [
        "research_sources.json",
        "Technical_terms.json",
        "Code_dependency_graph.json"
    ],
    "vision": [
        "Vision_file_profiles.json",
        "Vision_magic_signatures.json",
        "Vision_risk_rules.json"
    ],
    "voice": [
        "Voice_audio_profiles.json",
        "Voice_magic_signatures.json",
        "Voice_processing_tasks.json"
    ],
    "general": [
        "Translation_dictionary.json",
        "Synonyms.json",
        "Articles.json",
        "Technical_terms.json"
    ]
}

CANRI_DATA_FILES = [
    "Planner_task_templates.json",
    "Planner_dependency_graph.json",
    "Reasoning_patterns.json",
    "Code_dependency_graph.json",
    "Translation_dictionary.json",
    "Synonyms.json",
    "Articles.json",
    "Knowledge_index.json"
]

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


class CreativeBrain:

    def __init__(self):

        self.seeds = self.load_json(SEEDS_FILE, {})
        self.rules = self.load_json(RULES_FILE, {})
        self.graphs = self.load_json(GRAPHS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        self.creative_memory = self.load_json(MEMORY_FILE, {
            "ideas": [],
            "direction_profiles": {},
            "failed_directions": {},
            "successful_patterns": {}
        })
        self.graphs_by_seed = self.index_graphs_by_seed()
        self.canri_index = self.build_canri_index()
        self.code_assembler = CreativeCodeAssembler(self)

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

        for file_name in self.unique_files(ALWAYS_CANRI_DATA_FILES + CANRI_DATA_FILES):
            path = DATA_DIR / file_name

            if not path.exists():
                continue

            try:
                index[file_name] = self.summarize_canri_file(file_name)
            except Exception:
                index[file_name] = {
                    "count": 0,
                    "sample_terms": []
                }

        return index

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

        data = self.load_json(path, {})
        sample_terms = []
        matched_terms = []
        terms = [
            str(term).lower()
            for term in (terms or [])
            if term
        ]

        if isinstance(data, dict):
            count = len(data)
            iterable = list(data.items())[:400]

            for key, value in iterable:
                key_text = str(key)
                sample_terms.append(key_text)
                searchable = f"{key_text} {self.preview_json_value(value)}".lower()
                if terms and any(term in searchable for term in terms[:40]):
                    matched_terms.append(key_text)

        elif isinstance(data, list):
            count = len(data)
            iterable = data[:400]

            for item in iterable:
                term = self.item_name(item)
                if term:
                    sample_terms.append(term)

                searchable = self.preview_json_value(item).lower()
                if term and terms and any(key in searchable for key in terms[:40]):
                    matched_terms.append(term)
        else:
            count = 0

        return {
            "count": count,
            "sample_terms": [term for term in sample_terms if term][:sample_limit],
            "matched_terms": [term for term in matched_terms if term][:sample_limit],
            "used": True
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

        return self.unique_files(file_names)

    def collect_canri_context(self, domain, terms, data=None):

        context = {}

        for file_name in self.relevant_canri_files(domain, data):
            context[file_name] = self.summarize_canri_file(
                file_name,
                terms,
                sample_limit=60
            )

        return context

    def terms_from_canri_context(self, canri_context):

        terms = []

        for file_info in canri_context.values():
            terms.extend(file_info.get("matched_terms", [])[:20])
            terms.extend(file_info.get("sample_terms", [])[:6])

        clean = []
        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip()
            if term and term not in clean and term not in GENERIC_TERMS:
                clean.append(term)

        return clean[:80]

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "creative",
                "intent": "creative_generation",
                "words": []
            }

        understanding = data.get("understanding")

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
            f"{name} stepped into {elements['setting']} and noticed {elements['discovery']}.",
            "At first the discovery seemed small, but it changed the whole shape of the day.",
            f"The real problem was {elements['conflict']}.",
            f"{name} felt afraid, but curiosity made the next step feel possible.",
            "Instead of rushing, the character listened for the quiet rule hidden inside the moment.",
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

        generation_size = 100
        max_rounds = 5

        scored, history, stop_reason, final_direction = self.evolve(
            domain,
            terms,
            direction,
            generation_size,
            max_rounds
        )

        best = scored[0] if scored else {}
        best_score = best.get("scores", {}).get("total", 0)
        final_output = self.build_creative_final_output(
            text,
            domain,
            best,
            "Creative_brain",
            "creative_generation"
        )

        if isinstance(best, dict):
            best = dict(best)
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
                "returned_final_output": bool(final_output)
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
                "mode": "domain_retrieval",
                "loaded_learning_files": all(
                    file_name in canri_context
                    for file_name in [
                        "Learning_history.json",
                        "Learning_statistics.json",
                        "Learning_rules.json",
                        "Improvement_queue.json",
                        "Brain_performance.json"
                    ]
                ),
                "files_considered": len(canri_context),
                "domain": domain,
                "reason": "load learning and memory always, then load domain files only when relevant"
            },
            "creative_memory": {
                "ideas_stored": len(self.creative_memory.get("ideas", [])),
                "domain_profile": self.creative_memory.get("direction_profiles", {}).get(domain, {})
            },
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
