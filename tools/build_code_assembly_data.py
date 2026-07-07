import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

CODE_FILE = DATA_DIR / "code.json"
GRAPH_FILE = DATA_DIR / "Code_dependency_graph.json"
COMPOSITION_FILE = DATA_DIR / "Code_composition_tables.json"
PATTERNS_FILE = DATA_DIR / "Code_assembly_patterns.json"


ORDER_GROUPS = {
    "hello": 10,
    "variable": 15,
    "function": 20,
    "class": 25,
    "list": 30,
    "dict": 30,
    "file_read": 35,
    "file_write": 40,
    "json_load": 35,
    "json_save": 40,
    "csv_read": 35,
    "csv_write": 40,
    "api": 55,
    "server": 50,
    "route": 60,
    "database": 45,
    "sql": 45,
    "login": 65,
    "token": 70,
    "password": 50,
    "validation": 32,
    "game": 50,
    "player": 45,
    "enemy": 48,
    "inventory": 52,
    "score": 70,
    "test": 90,
}


DEPENDENCY_HINTS = {
    "json_save": ["json_load", "file_read"],
    "file_write": ["file_read"],
    "csv_write": ["csv_read"],
    "route": ["server"],
    "api": ["server"],
    "login": ["password", "validation"],
    "token": ["login"],
    "database": ["validation"],
    "sql": ["database"],
    "enemy": ["player"],
    "inventory": ["player"],
    "score": ["player"],
    "test": ["function"],
}


COMPATIBLE_CATEGORIES = {
    "file_read": ["json_load", "csv_read", "file_write", "validation"],
    "json_load": ["json_save", "validation", "api"],
    "json_save": ["file_write", "api"],
    "csv_read": ["csv_write", "validation"],
    "database": ["sql", "api", "validation", "login"],
    "sql": ["database", "api"],
    "server": ["route", "api", "login"],
    "route": ["api", "validation"],
    "api": ["json_load", "json_save", "database", "route"],
    "login": ["password", "token", "database", "validation"],
    "password": ["login", "validation"],
    "game": ["player", "enemy", "inventory", "score"],
    "player": ["enemy", "inventory", "score", "game"],
    "enemy": ["player", "score", "game"],
    "inventory": ["player", "game", "json_save"],
    "function": ["test", "validation"],
    "class": ["function", "test"],
    "validation": ["function", "api", "database", "login"],
}


def load_code_items():
    with CODE_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return list(data.values())
    return data


def norm(value):
    return str(value or "").strip().lower()


def item_terms(item):
    terms = set()
    for key in ["id", "name", "language", "category", "description"]:
        value = item.get(key)
        if value:
            terms.update(norm(value).replace("-", "_").split("_"))
            terms.add(norm(value))
    for tag in item.get("tags", []):
        terms.add(norm(tag))
        terms.update(norm(tag).replace("-", "_").split("_"))
    return {term for term in terms if term}


def category_of(item):
    category = norm(item.get("category"))
    tags = [norm(tag) for tag in item.get("tags", [])]
    name = norm(item.get("name"))
    text = " ".join([category, name, " ".join(tags)])

    for known in ORDER_GROUPS:
        if known in text:
            return known

    if "json" in text and ("load" in text or "read" in text):
        return "json_load"
    if "json" in text and ("save" in text or "write" in text):
        return "json_save"
    if "file" in text and ("load" in text or "read" in text):
        return "file_read"
    if "file" in text and ("save" in text or "write" in text):
        return "file_write"
    if "http" in text or "endpoint" in text:
        return "api"

    return category or "general"


def build_indexes(items):
    by_category = defaultdict(list)
    by_language = defaultdict(list)

    for item in items:
        category = category_of(item)
        language = norm(item.get("language")) or "unknown"
        by_category[category].append(item)
        by_language[language].append(item)

    return by_category, by_language


def find_first_id(by_category, language, category, current_id):
    for item in by_category.get(category, []):
        if item.get("id") == current_id:
            continue
        if norm(item.get("language")) == language:
            return item.get("id")
    return None


def build_graph(items, by_category):
    graph = {}

    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue

        language = norm(item.get("language")) or "unknown"
        category = category_of(item)
        requires = []

        for needed_category in DEPENDENCY_HINTS.get(category, []):
            needed_id = find_first_id(
                by_category,
                language,
                needed_category,
                item_id
            )
            if needed_id:
                requires.append(needed_id)

        compatible_categories = COMPATIBLE_CATEGORIES.get(
            category,
            ["function", "validation", "test"]
        )

        compatible_with = []
        for compatible_category in compatible_categories:
            compatible_id = find_first_id(
                by_category,
                language,
                compatible_category,
                item_id
            )
            if compatible_id and compatible_id not in compatible_with:
                compatible_with.append(compatible_id)

        graph[item_id] = {
            "id": item_id,
            "language": language,
            "category": category,
            "order_group": ORDER_GROUPS.get(category, 50),
            "provides": sorted(item_terms(item))[:20],
            "requires": requires,
            "compatible_with": compatible_with[:8],
            "glue_strategy": choose_glue_strategy(category),
            "risk_level": choose_risk_level(category),
            "confidence": 82 if category != "general" else 68
        }

    return graph


def choose_glue_strategy(category):
    if category in {"json_load", "json_save", "file_read", "file_write", "csv_read", "csv_write"}:
        return "connect_by_shared_file_path_and_data_object"
    if category in {"database", "sql"}:
        return "connect_by_shared_database_connection"
    if category in {"server", "route", "api"}:
        return "connect_by_request_response_flow"
    if category in {"login", "password", "token"}:
        return "connect_by_authentication_flow"
    if category in {"game", "player", "enemy", "inventory", "score"}:
        return "connect_by_game_state_object"
    return "connect_by_function_call_or_return_value"


def choose_risk_level(category):
    if category in {"login", "password", "token", "database", "sql"}:
        return "medium"
    if category in {"file_write", "json_save", "csv_write"}:
        return "low_medium"
    return "low"


def connection_type(first_category, second_category):
    combined = {first_category, second_category}
    if combined & {"json_load", "json_save", "file_read", "file_write", "csv_read", "csv_write"}:
        return "file_data_flow"
    if combined & {"database", "sql"}:
        return "database_flow"
    if combined & {"server", "route", "api"}:
        return "web_request_flow"
    if combined & {"login", "password", "token"}:
        return "security_flow"
    if combined & {"game", "player", "enemy", "inventory", "score"}:
        return "game_state_flow"
    return "function_flow"


def build_composition_tables(items, graph, by_language, limit=1200):
    tables = {}
    count = 0

    for language, language_items in sorted(by_language.items()):
        for first, second in combinations(language_items, 2):
            first_id = first.get("id")
            second_id = second.get("id")
            if not first_id or not second_id:
                continue

            first_node = graph[first_id]
            second_node = graph[second_id]

            related = (
                second_id in first_node.get("compatible_with", [])
                or first_id in second_node.get("compatible_with", [])
                or bool(set(first_node["provides"]) & set(second_node["provides"]))
                or first_node["category"] == second_node["category"]
            )

            if not related:
                continue

            ordered = sorted(
                [first_id, second_id],
                key=lambda item_id: (
                    graph[item_id]["order_group"],
                    item_id
                )
            )

            rule_id = f"compose_{ordered[0]}__{ordered[1]}"
            tables[rule_id] = {
                "id": rule_id,
                "language": language,
                "primary": ordered[0],
                "secondary": ordered[1],
                "order": ordered,
                "connection_type": connection_type(
                    first_node["category"],
                    second_node["category"]
                ),
                "adapter_notes": [
                    "Keep imports and setup code before callable logic.",
                    "Pass returned data into the next function instead of using hidden globals.",
                    "Rename duplicate helper functions before merging into an existing file."
                ],
                "score": min(
                    95,
                    70 + len(set(first_node["provides"]) & set(second_node["provides"])) * 3
                )
            }

            count += 1
            if count >= limit:
                return tables

    return tables


def build_patterns(graph, composition_tables):
    patterns = {}
    grouped = defaultdict(list)

    for node in graph.values():
        grouped[(node["language"], node["category"])].append(node["id"])

    base_patterns = [
        ("safe_file_pipeline", ["file_read", "json_load", "validation", "json_save"]),
        ("database_crud_pipeline", ["validation", "database", "sql", "api"]),
        ("web_api_pipeline", ["server", "route", "api", "json_load"]),
        ("auth_pipeline", ["password", "login", "token", "database"]),
        ("game_system_pipeline", ["player", "enemy", "inventory", "score"]),
        ("tested_function_pipeline", ["function", "validation", "test"]),
    ]

    for language in sorted({node["language"] for node in graph.values()}):
        for pattern_name, categories in base_patterns:
            steps = []
            for category in categories:
                candidates = grouped.get((language, category), [])
                if candidates:
                    steps.append(candidates[0])

            if len(steps) < 2:
                continue

            pattern_id = f"{language}_{pattern_name}"
            patterns[pattern_id] = {
                "id": pattern_id,
                "language": language,
                "name": pattern_name,
                "steps": steps,
                "preferred_order_groups": [
                    graph[step]["order_group"]
                    for step in steps
                ],
                "composition_rules": [
                    rule_id
                    for rule_id, rule in composition_tables.items()
                    if rule["language"] == language
                    and set(rule["order"]).issubset(set(steps))
                ][:12],
                "quality_score": 86
            }

    return patterns


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    items = load_code_items()
    by_category, by_language = build_indexes(items)
    graph = build_graph(items, by_category)
    composition_tables = build_composition_tables(
        items,
        graph,
        by_language,
        limit=1200
    )
    patterns = build_patterns(graph, composition_tables)

    write_json(GRAPH_FILE, graph)
    write_json(COMPOSITION_FILE, composition_tables)
    write_json(PATTERNS_FILE, patterns)

    print(json.dumps({
        "code_items": len(items),
        "dependency_graph_nodes": len(graph),
        "composition_rules": len(composition_tables),
        "assembly_patterns": len(patterns)
    }, indent=2))


if __name__ == "__main__":
    main()
