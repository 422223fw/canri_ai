import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


main_dictionary = load("main_dictionary.json.new")
connections = load("Connections_Dictionary.json.new")
grammar = load("Grammar_dictionary.json.new")

bad_defs = [
    entry
    for entry in main_dictionary
    if any(
        str(meaning.get("definition", "")).startswith("A Canri AI")
        for meaning in entry.get("meanings", [])
    )
]

print("main_dictionary:", len(main_dictionary))
print("Connections_Dictionary:", len(connections))
print("Grammar_dictionary:", len(grammar))
print("bad Canri-template definitions:", len(bad_defs))
print("main samples:", main_dictionary[:3])
print("connection samples:", list(connections.items())[:3])
print("grammar samples:", list(grammar.items())[:3])
