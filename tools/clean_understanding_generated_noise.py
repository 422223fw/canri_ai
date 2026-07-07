import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "UnderstandingDk" / "data"


def load_json(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(name, data):
    target = DATA_DIR / name
    temp = target.with_name(target.name + ".tmp")
    with temp.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    try:
        temp.replace(target)
        return "updated"
    except PermissionError:
        return f"staged: {temp.name}"


def is_generated_main_entry(entry):
    return any(
        str(meaning.get("definition", "")).startswith("A Canri AI")
        for meaning in entry.get("meanings", [])
    )


def is_generated_connection(key, value, generated_words):
    if key in generated_words:
        return True

    if not isinstance(value, list):
        return False

    repeated_canri_tags = {"canri", "ai", "system"}
    return "_" in key and repeated_canri_tags.issubset(set(value))


def is_generated_grammar_entry(key, value):
    if key.startswith("canriverb_extra_"):
        return True

    if not isinstance(value, dict):
        return False

    forms = value.get("forms", {})
    if not isinstance(forms, dict):
        return False

    # Keeps real phrasal verbs like "ask_for" whose forms use spaces,
    # removes synthetic verbs like "analyze_ai_agented".
    return "_" in key and any("_" in str(form_value) for form_value in forms.values())


def main():
    main_dictionary = load_json("main_dictionary.json")
    generated_words = {
        entry.get("word")
        for entry in main_dictionary
        if is_generated_main_entry(entry)
    }

    cleaned_main = [
        entry
        for entry in main_dictionary
        if not is_generated_main_entry(entry)
    ]

    connections = load_json("Connections_Dictionary.json")
    cleaned_connections = {
        key: value
        for key, value in connections.items()
        if not is_generated_connection(key, value, generated_words)
    }

    grammar = load_json("Grammar_dictionary.json")
    cleaned_grammar = {
        key: value
        for key, value in grammar.items()
        if not is_generated_grammar_entry(key, value)
    }

    main_status = save_json("main_dictionary.json", cleaned_main)
    connections_status = save_json("Connections_Dictionary.json", cleaned_connections)
    grammar_status = save_json("Grammar_dictionary.json", cleaned_grammar)

    print("main_dictionary:", len(main_dictionary), "->", len(cleaned_main))
    print("Connections_Dictionary:", len(connections), "->", len(cleaned_connections))
    print("Grammar_dictionary:", len(grammar), "->", len(cleaned_grammar))
    print("removed generated words:", len(generated_words))
    print("main_dictionary status:", main_status)
    print("Connections_Dictionary status:", connections_status)
    print("Grammar_dictionary status:", grammar_status)


if __name__ == "__main__":
    main()
