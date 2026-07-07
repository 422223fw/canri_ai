import collections
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "UnderstandingDk" / "data"


def load_json(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    main_dictionary = load_json("main_dictionary.json")
    bad_definitions = [
        entry
        for entry in main_dictionary
        if any(
            str(meaning.get("definition", "")).startswith("A Canri AI")
            for meaning in entry.get("meanings", [])
        )
    ]

    connections = load_json("Connections_Dictionary.json")
    repeated_connections = collections.Counter(
        tuple(value)
        for value in connections.values()
        if isinstance(value, list)
    )

    grammar = load_json("Grammar_dictionary.json")
    generated_grammar = [
        key
        for key, value in grammar.items()
        if key.startswith("canriverb_extra_")
        or (
            "_" in key
            and isinstance(value, dict)
            and any(
                "_" in str(form_value)
                for form_value in value.get("forms", {}).values()
            )
        )
    ]

    print("main_dictionary total:", len(main_dictionary))
    print("main_dictionary Canri-template definitions:", len(bad_definitions))
    print("main_dictionary bad samples:")
    for sample in bad_definitions[:3]:
        print(" ", sample)

    print("Connections_Dictionary total:", len(connections))
    print("Connections_Dictionary most repeated lists:")
    for value, count in repeated_connections.most_common(5):
        print(" ", count, list(value))

    print("Grammar_dictionary total:", len(grammar))
    print("Grammar_dictionary generated-looking entries:", len(generated_grammar))
    print("Grammar_dictionary generated samples:", generated_grammar[:10])


if __name__ == "__main__":
    main()
