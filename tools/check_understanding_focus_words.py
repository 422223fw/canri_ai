import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


main_dictionary = load("main_dictionary.json")
connections = load("Connections_Dictionary.json")
grammar = load("Grammar_dictionary.json")

index = {entry["word"]: entry for entry in main_dictionary}

for word in ["be", "have", "ability", "person", "data"]:
    print(word, "=>", index.get(word))
    print(word, "connections =>", connections.get(word))

for word in ["be", "have", "accept", "analyze", "write"]:
    print(word, "grammar =>", grammar.get(word))
