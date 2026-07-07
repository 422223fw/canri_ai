import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"


COMMON_OVERRIDES = {
    "be": {
        "type": "verb",
        "meanings": [
            {"definition": "To exist or live."},
            {"definition": "To have a particular state, quality, or identity."},
            {"definition": "Used as a helping verb to form continuous tenses and passive forms."},
        ],
        "connections": ["exist", "live", "state", "identity", "become", "remain", "is", "are"],
    },
    "have": {
        "type": "verb",
        "meanings": [
            {"definition": "To own, hold, or possess something."},
            {"definition": "To experience something or be affected by it."},
            {"definition": "Used as a helping verb to form perfect tenses."},
        ],
        "connections": ["own", "possess", "hold", "experience", "contain", "keep", "has", "had"],
    },
    "do": {
        "type": "verb",
        "meanings": [
            {"definition": "To perform an action or activity."},
            {"definition": "To complete or carry out a task."},
            {"definition": "Used as a helping verb in questions and negatives."},
        ],
        "connections": ["perform", "act", "make", "complete", "carry out", "work"],
    },
    "get": {
        "type": "verb",
        "meanings": [
            {"definition": "To receive, obtain, or become the owner of something."},
            {"definition": "To become or start to be in a particular state."},
            {"definition": "To understand something."},
        ],
        "connections": ["receive", "obtain", "become", "understand", "take", "gain"],
    },
    "make": {
        "type": "verb",
        "meanings": [
            {"definition": "To create, build, or produce something."},
            {"definition": "To cause something to happen or exist."},
            {"definition": "To prepare or arrange something."},
        ],
        "connections": ["create", "build", "produce", "cause", "prepare", "form"],
    },
}


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def save(name, data):
    with (DATA_DIR / name).open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    main_dictionary = load("main_dictionary.json")
    connections = load("Connections_Dictionary.json")

    index = {entry["word"]: entry for entry in main_dictionary}

    for word, override in COMMON_OVERRIDES.items():
        if word in index:
            index[word]["type"] = override["type"]
            index[word]["meanings"] = override["meanings"]
        connections[word] = override["connections"]

    save("main_dictionary.json", main_dictionary)
    save("Connections_Dictionary.json", connections)

    print("refined common words:", ", ".join(COMMON_OVERRIDES))


if __name__ == "__main__":
    main()
