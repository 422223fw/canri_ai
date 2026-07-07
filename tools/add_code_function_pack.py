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


FEATURES = [
    "inventory_add_item",
    "inventory_remove_item",
    "inventory_find_item",
    "inventory_count_items",
    "inventory_clear",
    "player_create",
    "player_update_health",
    "player_add_score",
    "player_move",
    "player_level_up",
    "enemy_create",
    "enemy_take_damage",
    "enemy_ai_step",
    "enemy_spawn_wave",
    "enemy_drop_loot",
    "game_loop_step",
    "game_state_create",
    "game_state_update",
    "game_pause",
    "game_resume",
    "save_json",
    "load_json",
    "save_text",
    "load_text",
    "path_normalize",
    "config_load",
    "config_merge",
    "settings_validate",
    "logger_create",
    "logger_write",
    "validate_required",
    "validate_number_range",
    "validate_email",
    "validate_password_strength",
    "sanitize_text",
    "parse_command",
    "parse_arguments",
    "format_response",
    "format_error",
    "format_table",
    "list_filter",
    "list_sort",
    "list_group",
    "list_unique",
    "list_paginate",
    "dict_merge",
    "dict_get_path",
    "dict_set_path",
    "cache_get",
    "cache_set",
    "queue_push",
    "queue_pop",
    "stack_push",
    "stack_pop",
    "priority_queue_push",
    "search_linear",
    "search_binary",
    "sort_quick",
    "sort_merge",
    "sort_bubble",
    "math_clamp",
    "math_lerp",
    "math_distance",
    "math_random_range",
    "math_weighted_choice",
    "vector2_create",
    "vector2_add",
    "vector2_subtract",
    "collision_aabb",
    "collision_circle",
    "timer_start",
    "timer_elapsed",
    "event_subscribe",
    "event_emit",
    "state_machine_create",
    "state_machine_transition",
    "api_get",
    "api_post_json",
    "api_error_handler",
    "http_route",
    "database_connect",
    "database_insert",
    "database_select",
    "database_update",
    "database_delete",
    "auth_login",
    "auth_logout",
    "auth_guard",
    "token_create",
    "token_validate",
    "hash_password",
    "unit_test_assert",
    "unit_test_runner",
    "mock_data_create",
    "html_card",
    "html_form",
    "css_button",
    "css_grid",
    "css_dark_theme",
    "response_builder",
]


VARIANTS = [
    "basic",
    "safe",
    "validated",
    "cached",
    "async_ready",
    "game_ready",
    "file_ready",
    "api_ready",
    "testable",
    "production_draft",
    "context_aware",
    "memory_enabled",
    "graph_connected",
    "planner_ready",
    "response_ready",
    "security_checked",
    "learning_ready",
    "creative_ready",
    "composition_ready",
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
    return str(value).replace("-", "_").replace(" ", "_")


def python_code(feature, variant):
    name = safe_name(f"{feature}_{variant}")
    readable = feature.replace("_", " ")
    return (
        f"def {name}(data=None):\n"
        f"    \"\"\"{readable} helper, {variant.replace('_', ' ')} variant.\"\"\"\n"
        "    data = data or {}\n"
        f"    data['{feature}'] = data.get('{feature}', True)\n"
        "    return data"
    )


def javascript_code(feature, variant):
    name = safe_name(f"{feature}_{variant}")
    readable = feature.replace("_", " ")
    return (
        f"function {name}(data = {{}}) {{\n"
        f"  // {readable} helper, {variant.replace('_', ' ')} variant\n"
        f"  data.{safe_name(feature)} = data.{safe_name(feature)} ?? true;\n"
        "  return data;\n"
        "}"
    )


def java_code(feature, variant):
    class_name = "".join(part.title() for part in safe_name(f"{feature}_{variant}").split("_"))
    return (
        f"public class {class_name} {{\n"
        "    public String run(String input) {\n"
        "        return input == null ? \"\" : input;\n"
        "    }\n"
        "}"
    )


def csharp_code(feature, variant):
    class_name = "".join(part.title() for part in safe_name(f"{feature}_{variant}").split("_"))
    return (
        f"public class {class_name}\n"
        "{\n"
        "    public string Run(string input)\n"
        "    {\n"
        "        return input ?? string.Empty;\n"
        "    }\n"
        "}"
    )


def cpp_code(feature, variant):
    name = safe_name(f"{feature}_{variant}")
    return (
        "#include <string>\n\n"
        f"std::string {name}(std::string input) {{\n"
        "    return input;\n"
        "}"
    )


def c_code(feature, variant):
    name = safe_name(f"{feature}_{variant}")
    return (
        f"int {name}(int input) {{\n"
        "    return input;\n"
        "}"
    )


def php_code(feature, variant):
    name = safe_name(f"{feature}_{variant}")
    return (
        "<?php\n"
        f"function {name}($data = []) {{\n"
        f"    $data['{feature}'] = $data['{feature}'] ?? true;\n"
        "    return $data;\n"
        "}\n"
        "?>"
    )


def sql_code(feature, variant):
    table = safe_name(feature)
    return (
        f"-- {feature.replace('_', ' ')} {variant.replace('_', ' ')} variant\n"
        f"SELECT * FROM {table} LIMIT 100;"
    )


def html_code(feature, variant):
    class_name = safe_name(f"{feature}_{variant}").replace("_", "-")
    return (
        f"<section class=\"{class_name}\">\n"
        f"  <h2>{feature.replace('_', ' ').title()}</h2>\n"
        "</section>"
    )


def css_code(feature, variant):
    class_name = safe_name(f"{feature}_{variant}").replace("_", "-")
    return (
        f".{class_name} {{\n"
        "  display: block;\n"
        "  gap: 8px;\n"
        "}"
    )


CODE_BUILDERS = {
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


def category_for(feature):
    if feature.startswith("inventory"):
        return "inventory"
    if feature.startswith("player"):
        return "player"
    if feature.startswith("enemy"):
        return "enemy"
    if feature.startswith("game"):
        return "game"
    if feature.startswith("save") or feature.startswith("load") or feature.startswith("path"):
        return "file"
    if feature.startswith("validate") or feature.startswith("sanitize"):
        return "validation"
    if feature.startswith("api") or feature.startswith("http"):
        return "api"
    if feature.startswith("database"):
        return "database"
    if feature.startswith("auth") or feature.startswith("token") or feature.startswith("hash"):
        return "security"
    if feature.startswith("html"):
        return "html"
    if feature.startswith("css"):
        return "css"
    return feature.split("_", 1)[0]


def build_entries(existing_ids):
    entries = []

    for language in LANGUAGES:
        builder = CODE_BUILDERS[language]
        for feature in FEATURES:
            for variant in VARIANTS:
                entry_id = f"{language}_function_{feature}_{variant}"
                if entry_id in existing_ids:
                    continue

                category = category_for(feature)
                entries.append({
                    "id": entry_id,
                    "name": f"{language}_{feature}_{variant}",
                    "language": language,
                    "category": category,
                    "tags": list(dict.fromkeys([
                        "code",
                        "function",
                        "generated_function_pack",
                        language,
                        feature,
                        variant,
                        category,
                        *feature.split("_"),
                    ])),
                    "description": (
                        f"{language} function snippet for {feature.replace('_', ' ')} "
                        f"using the {variant.replace('_', ' ')} variant."
                    ),
                    "code": builder(feature, variant),
                    "difficulty": "intermediate",
                    "safe_to_execute_directly": False,
                    "review_notes": [
                        "Draft snippet for composition.",
                        "Rename and adapt before production use.",
                        "Run Security_brain before execution when file, network, auth, or database behavior is involved."
                    ]
                })

    return entries


def update_stats(items, stats):
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        stats.setdefault(item_id, {
            "times_used": 0,
            "success_rate": 78,
            "trust": 78,
            "language": item.get("language"),
            "category": item.get("category"),
            "source": "generated_function_pack"
        })

    stats["_collection_statistics"] = {
        "total_snippets": len(items),
        "function_pack_snippets": len([
            item
            for item in items
            if "generated_function_pack" in item.get("tags", [])
        ]),
        "languages": sorted(set(item.get("language") for item in items)),
    }

    return stats


def main():
    existing = load_json(CODE_PATH, [])
    stats = load_json(STATS_PATH, {})

    if not isinstance(existing, list):
        raise TypeError("code.json must be a list")

    existing_ids = {item.get("id") for item in existing if isinstance(item, dict)}
    additions = build_entries(existing_ids)

    all_items = existing + additions
    stats = update_stats(all_items, stats)

    save_json(CODE_PATH, all_items)
    save_json(STATS_PATH, stats)

    print(json.dumps({
        "existing": len(existing),
        "added": len(additions),
        "total": len(all_items),
        "target_additions": len(LANGUAGES) * len(FEATURES) * len(VARIANTS)
    }, indent=2))


if __name__ == "__main__":
    main()
