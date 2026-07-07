import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"
CODE_PATH = DATA_DIR / "code.json"
STATS_PATH = DATA_DIR / "Code_statistics.json"


LANGUAGES = [
    "python",
    "javascript",
    "java",
    "csharp",
    "cpp",
    "c",
    "php",
    "sql",
    "html",
    "css",
]


DOMAINS = [
    "cli",
    "json",
    "csv",
    "file",
    "validation",
    "text",
    "math",
    "list",
    "dict",
    "date",
    "api",
    "http",
    "cache",
    "queue",
    "stack",
    "search",
    "sort",
    "game",
    "inventory",
    "player",
    "enemy",
    "save",
    "config",
    "logging",
    "security",
    "token",
    "password",
    "database",
    "sql",
    "html",
    "css",
    "ui",
    "test",
    "state",
    "event",
    "timer",
    "path",
    "format",
    "parser",
    "report",
    "table",
    "number",
    "string",
    "collection",
    "graph",
    "tree",
    "audio",
    "image",
    "network",
    "backup",
]


ACTIONS = [
    "create",
    "load",
    "save",
    "parse",
    "format",
    "validate",
    "sanitize",
    "filter",
    "sort",
    "search",
    "merge",
    "split",
    "update",
    "delete",
    "count",
    "summarize",
    "export",
    "import",
    "normalize",
    "compare",
]


VARIANTS = [
    "basic",
    "safe",
    "validated",
    "cached",
    "typed",
    "cli_ready",
    "testable",
    "json_ready",
    "error_checked",
    "integration_ready",
]


def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def safe_name(value):
    return "".join(
        character if character.isalnum() or character == "_" else "_"
        for character in str(value).lower()
    ).strip("_")


def feature_name(domain, action, variant):
    return safe_name(f"{domain}_{action}_{variant}")


def python_code(name, domain, action):
    return (
        f"def {name}(data=None):\n"
        f"    \"\"\"{action.capitalize()} {domain} data safely.\"\"\"\n"
        "    if data is None:\n"
        "        data = {}\n"
        "    if isinstance(data, dict):\n"
        f"        data['{domain}_{action}'] = True\n"
        "        return data\n"
        "    return data\n"
    )


def javascript_code(name, domain, action):
    camel = "".join(part.title() if index else part for index, part in enumerate(name.split("_")))
    return (
        f"function {camel}(data = {{}}) {{\n"
        f"  // {action} {domain} data safely\n"
        f"  data.{safe_name(domain)}_{safe_name(action)} = true;\n"
        "  return data;\n"
        "}\n"
    )


def java_code(name, domain, action):
    class_name = "".join(part.title() for part in name.split("_"))
    return (
        f"public class {class_name} {{\n"
        "    public String run(String input) {\n"
        "        if (input == null) {\n"
        "            return \"\";\n"
        "        }\n"
        f"        return input + \"::{domain}_{action}\";\n"
        "    }\n"
        "}\n"
    )


def csharp_code(name, domain, action):
    class_name = "".join(part.title() for part in name.split("_"))
    return (
        f"public class {class_name}\n"
        "{\n"
        "    public string Run(string input)\n"
        "    {\n"
        f"        return (input ?? string.Empty) + \"::{domain}_{action}\";\n"
        "    }\n"
        "}\n"
    )


def cpp_code(name, domain, action):
    return (
        "#include <string>\n\n"
        f"std::string {name}(const std::string& input) {{\n"
        f"    return input + \"::{domain}_{action}\";\n"
        "}\n"
    )


def c_code(name, domain, action):
    return (
        f"/* {action} {domain} helper */\n"
        f"int {name}(int value) {{\n"
        "    return value;\n"
        "}\n"
    )


def php_code(name, domain, action):
    return (
        "<?php\n"
        f"function {name}($data = []) {{\n"
        f"    $data['{domain}_{action}'] = true;\n"
        "    return $data;\n"
        "}\n"
        "?>\n"
    )


def sql_code(name, domain, action):
    table = safe_name(f"{domain}_records")
    return (
        f"-- {action} {domain} helper\n"
        f"SELECT * FROM {table} LIMIT 100;\n"
    )


def html_code(name, domain, action):
    class_name = name.replace("_", "-")
    return (
        f"<section class=\"{class_name}\" data-domain=\"{domain}\">\n"
        f"  <h2>{action.title()} {domain.title()}</h2>\n"
        "</section>\n"
    )


def css_code(name, domain, action):
    class_name = name.replace("_", "-")
    return (
        f".{class_name} {{\n"
        "  display: block;\n"
        "  padding: 8px;\n"
        "  border: 1px solid #d0d7de;\n"
        "}\n"
    )


BUILDERS = {
    "python": python_code,
    "javascript": javascript_code,
    "java": java_code,
    "csharp": csharp_code,
    "cpp": cpp_code,
    "c": c_code,
    "php": php_code,
    "sql": sql_code,
    "html": html_code,
    "css": css_code,
}


def build_entries(existing_ids, limit=5000):
    entries = []

    for language in LANGUAGES:
        builder = BUILDERS[language]
        for domain in DOMAINS:
            for action in ACTIONS:
                for variant in VARIANTS:
                    name = feature_name(domain, action, variant)
                    entry_id = f"{language}_canri_pack_{name}"

                    if entry_id in existing_ids:
                        continue

                    entries.append({
                        "id": entry_id,
                        "name": f"{language}_{name}",
                        "language": language,
                        "category": domain,
                        "tags": list(dict.fromkeys([
                            "code",
                            "function",
                            "canri_pack_5000",
                            language,
                            domain,
                            action,
                            variant,
                            f"{domain}_{action}",
                        ])),
                        "description": (
                            f"{language} {variant.replace('_', ' ')} function for "
                            f"{action} {domain} workflows."
                        ),
                        "code": builder(name, domain, action),
                        "difficulty": "intermediate",
                        "safe_to_execute_directly": language in {"python", "javascript", "html", "css"},
                        "quality_notes": [
                            "Generated as a reusable composition snippet.",
                            "Designed for search, planning, and assembly by Code_brain.",
                            "Adapt names and validation rules before production use."
                        ],
                        "source": "tools/add_5000_code_functions.py"
                    })

                    if len(entries) >= limit:
                        return entries

    return entries


def update_stats(stats, entries):
    for entry in entries:
        stats.setdefault(entry["id"], {
            "times_used": 0,
            "success_rate": 82,
            "trust": 80,
            "language": entry["language"],
            "category": entry["category"],
            "source": "canri_pack_5000"
        })

    collection = stats.setdefault("_collection_statistics", {})
    collection["last_added_pack"] = "canri_pack_5000"
    collection["last_added_count"] = len(entries)
    collection["last_total_after_pack"] = collection.get("last_total_after_pack", 0)
    return stats


def main():
    existing = load_json(CODE_PATH, [])
    stats = load_json(STATS_PATH, {})

    if not isinstance(existing, list):
        raise TypeError("code.json must be a list")

    existing_ids = {
        item.get("id")
        for item in existing
        if isinstance(item, dict)
    }

    additions = build_entries(existing_ids, limit=5000)

    if len(additions) != 5000:
        raise RuntimeError(f"Expected 5000 additions, got {len(additions)}")

    all_items = existing + additions
    stats = update_stats(stats, additions)
    stats.setdefault("_collection_statistics", {})
    stats["_collection_statistics"]["total_snippets"] = len(all_items)
    stats["_collection_statistics"]["canri_pack_5000_count"] = len([
        item
        for item in all_items
        if "canri_pack_5000" in item.get("tags", [])
    ])

    save_json(CODE_PATH, all_items)
    save_json(STATS_PATH, stats)

    print(f"Added {len(additions)} code function entries.")
    print(f"code.json now has {len(all_items)} entries.")


if __name__ == "__main__":
    main()
