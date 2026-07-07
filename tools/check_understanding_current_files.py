import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


main_dictionary = load("main_dictionary.json")
connections = load("Connections_Dictionary.json")
grammar = load("Grammar_dictionary.json")

bad_main = [
    entry.get("word")
    for entry in main_dictionary
    if any(
        str(meaning.get("definition", "")).startswith("A Canri AI")
        for meaning in entry.get("meanings", [])
    )
]

bad_connections = [
    key
    for key, values in connections.items()
    if isinstance(values, list)
    and {"canri", "ai", "system"}.issubset(set(values))
]

bad_grammar = [
    key
    for key, data in grammar.items()
    if "_" in key
    and isinstance(data, dict)
    and any(
        "_" in str(value)
        for value in data.get("forms", {}).values()
    )
]

print("main_dictionary count:", len(main_dictionary))
print("Connections_Dictionary count:", len(connections))
print("Grammar_dictionary count:", len(grammar))
print("bad Canri definitions:", len(bad_main), bad_main[:5])
print("bad canri connections:", len(bad_connections), bad_connections[:5])
print("bad underscore grammar:", len(bad_grammar), bad_grammar[:5])
