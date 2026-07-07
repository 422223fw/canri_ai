import json
from pathlib import Path


LANGUAGES = [
    "python",
    "javascript",
    "html",
    "css",
    "java",
    "csharp",
    "cpp",
    "c",
    "php",
    "sql",
]


CONCEPTS = [
    "hello_world",
    "variable",
    "constant",
    "input",
    "output",
    "if_statement",
    "else_statement",
    "for_loop",
    "while_loop",
    "function",
    "class",
    "constructor",
    "list",
    "array",
    "dictionary",
    "set",
    "tuple",
    "string",
    "number",
    "boolean",
    "math_add",
    "math_subtract",
    "math_multiply",
    "math_divide",
    "random_number",
    "date_time",
    "file_read",
    "file_write",
    "json_read",
    "json_write",
    "csv_read",
    "csv_write",
    "error_handling",
    "try_catch",
    "validation",
    "email_validation",
    "password_validation",
    "sort_list",
    "search_list",
    "filter_list",
    "map_list",
    "reduce_list",
    "stack",
    "queue",
    "linked_list",
    "binary_search",
    "linear_search",
    "bubble_sort",
    "quick_sort",
    "merge_sort",
    "api_get",
    "api_post",
    "http_server",
    "route",
    "database_connect",
    "database_insert",
    "database_select",
    "database_update",
    "database_delete",
    "login",
    "logout",
    "session",
    "token",
    "hash_password",
    "encrypt_text",
    "decrypt_text",
    "read_config",
    "write_config",
    "logger",
    "unit_test",
    "timer",
    "callback",
    "event_listener",
    "dom_select",
    "dom_update",
    "form",
    "button",
    "card",
    "grid",
    "flexbox",
    "animation",
    "media_query",
    "canvas",
    "game_loop",
    "player",
    "enemy",
    "inventory",
    "score",
    "save_game",
    "load_game",
    "vector",
    "matrix",
    "physics_gravity",
    "collision",
    "pathfinding",
    "state_machine",
    "command_line",
    "environment_variable",
    "cache",
    "pagination",
]


def build_code(language, concept):
    readable = concept.replace("_", " ")

    if language == "python":
        if concept == "hello_world":
            return 'print("HELLO")'
        if concept == "function":
            return "def run_task(data):\n    return data"
        if concept == "class":
            return "class Example:\n    def __init__(self):\n        self.ready = True"
        if concept == "for_loop":
            return "for item in items:\n    print(item)"
        if concept == "while_loop":
            return "while running:\n    break"
        if concept == "json_read":
            return "import json\n\nwith open('data.json', 'r', encoding='utf-8') as f:\n    data = json.load(f)"
        if concept == "json_write":
            return "import json\n\nwith open('data.json', 'w', encoding='utf-8') as f:\n    json.dump(data, f, indent=4)"
        return f"# Python example for {readable}\nresult = None"

    if language == "javascript":
        if concept == "hello_world":
            return 'console.log("HELLO");'
        if concept == "function":
            return "function runTask(data) {\n  return data;\n}"
        if concept == "class":
            return "class Example {\n  constructor() {\n    this.ready = true;\n  }\n}"
        if concept == "for_loop":
            return "for (const item of items) {\n  console.log(item);\n}"
        return f"// JavaScript example for {readable}\nconst result = null;"

    if language == "html":
        if concept == "hello_world":
            return "<h1>HELLO</h1>"
        if concept == "button":
            return '<button type="button">Click</button>'
        if concept == "form":
            return '<form>\n  <input name="message" />\n  <button>Send</button>\n</form>'
        return f"<!-- HTML example for {readable} -->\n<div>{readable}</div>"

    if language == "css":
        if concept == "button":
            return ".button {\n  padding: 8px 12px;\n  border: 0;\n  cursor: pointer;\n}"
        if concept == "grid":
            return ".grid {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 12px;\n}"
        if concept == "flexbox":
            return ".row {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n}"
        return f"/* CSS example for {readable} */\n.example {{\n  display: block;\n}}"

    if language == "java":
        if concept == "hello_world":
            return 'System.out.println("HELLO");'
        if concept == "class":
            return "public class Example {\n    private boolean ready = true;\n}"
        if concept == "function":
            return "public String runTask(String data) {\n    return data;\n}"
        return f"// Java example for {readable}\nObject result = null;"

    if language == "csharp":
        if concept == "hello_world":
            return 'Console.WriteLine("HELLO");'
        if concept == "class":
            return "public class Example\n{\n    public bool Ready { get; set; } = true;\n}"
        if concept == "function":
            return "public string RunTask(string data)\n{\n    return data;\n}"
        return f"// C# example for {readable}\nobject result = null;"

    if language == "cpp":
        if concept == "hello_world":
            return 'std::cout << "HELLO" << std::endl;'
        if concept == "function":
            return "std::string runTask(std::string data) {\n    return data;\n}"
        return f"// C++ example for {readable}\nauto result = 0;"

    if language == "c":
        if concept == "hello_world":
            return 'printf("HELLO\\n");'
        if concept == "function":
            return "int run_task(int data) {\n    return data;\n}"
        return f"/* C example for {readable} */\nint result = 0;"

    if language == "php":
        if concept == "hello_world":
            return '<?php echo "HELLO"; ?>'
        if concept == "function":
            return "<?php\nfunction runTask($data) {\n    return $data;\n}\n?>"
        return f"<?php\n// PHP example for {readable}\n$result = null;\n?>"

    if language == "sql":
        if concept == "database_select":
            return "SELECT * FROM users;"
        if concept == "database_insert":
            return "INSERT INTO users (name) VALUES ('Canri');"
        if concept == "database_update":
            return "UPDATE users SET name = 'Canri' WHERE id = 1;"
        if concept == "database_delete":
            return "DELETE FROM users WHERE id = 1;"
        return f"-- SQL example for {readable}\nSELECT 1;"

    return f"// Example for {readable}"


def build_database():
    database = []

    for language in LANGUAGES:
        for index, concept in enumerate(CONCEPTS, start=1):
            database.append(
                {
                    "id": f"{language}_{concept}_{index:03d}",
                    "name": f"{language}_{concept}",
                    "language": language,
                    "category": concept.split("_")[0],
                    "tags": [
                        "code",
                        language,
                        concept,
                        concept.split("_")[0],
                    ],
                    "description": f"{language} starter snippet for {concept.replace('_', ' ')}.",
                    "code": build_code(language, concept),
                }
            )

    return database


def main():
    output = Path("main_ai_canri") / "data" / "code.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    database = build_database()

    with output.open("w", encoding="utf-8") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(database)} code entries to {output}")


if __name__ == "__main__":
    main()
