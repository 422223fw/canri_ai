import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


main_dictionary = load("main_dictionary.json")
connections = load("Connections_Dictionary.json")
grammar = load("Grammar_dictionary.json")

print("main first:", main_dictionary[:3])
print("main middle:", main_dictionary[4998:5001])
print("main last:", main_dictionary[-3:])
print("connections first:", list(connections.items())[:3])
print("connections middle:", list(connections.items())[4998:5001])
print("grammar first:", list(grammar.items())[:3])
print("grammar middle:", list(grammar.items())[4998:5001])
