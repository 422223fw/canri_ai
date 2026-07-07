import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DK_DIR = ROOT / "main_ai_canri" / "UnderstandingDk" / "data"
MAIN_DICTIONARY_FILE = DK_DIR / "main_dictionary.json"
CONNECTIONS_FILE = DK_DIR / "Connections_Dictionary.json"
GRAMMAR_FILE = DK_DIR / "Grammar_dictionary.json"


CORE_ENTRIES = [
    {
        "word": "butterfly",
        "type": "noun",
        "definition": "An insect with two pairs of broad, often colorful wings that develops from a caterpillar through metamorphosis.",
        "connections": ["insect", "caterpillar", "metamorphosis", "wings", "pollination", "moth", "larva", "pupa", "nature"]
    },
    {
        "word": "caterpillar",
        "type": "noun",
        "definition": "The larval stage of a butterfly or moth, usually shaped like a soft segmented worm.",
        "connections": ["butterfly", "moth", "larva", "metamorphosis", "pupa", "insect"]
    },
    {
        "word": "metamorphosis",
        "type": "noun",
        "definition": "A biological process in which an animal changes form during development, such as a caterpillar becoming a butterfly.",
        "connections": ["change", "development", "butterfly", "caterpillar", "pupa", "biology"]
    },
    {
        "word": "pupa",
        "type": "noun",
        "definition": "A life stage of some insects between larva and adult, during which the body changes into its adult form.",
        "connections": ["butterfly", "caterpillar", "metamorphosis", "insect", "chrysalis"]
    },
    {
        "word": "chrysalis",
        "type": "noun",
        "definition": "The protective case or pupa stage in which a butterfly develops from a caterpillar into an adult.",
        "connections": ["butterfly", "pupa", "caterpillar", "metamorphosis"]
    },
    {
        "word": "pollination",
        "type": "noun",
        "definition": "The transfer of pollen between flowers, allowing many plants to reproduce.",
        "connections": ["flower", "plant", "bee", "butterfly", "reproduction", "biology"]
    }
]


def load_json(path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def key(text):
    return str(text).strip().lower()


def main():
    entries = load_json(MAIN_DICTIONARY_FILE, [])
    connections = load_json(CONNECTIONS_FILE, {})
    grammar = load_json(GRAMMAR_FILE, {})
    existing = {key(entry.get("word", "")) for entry in entries if isinstance(entry, dict)}
    added = 0

    for item in CORE_ENTRIES:
        word = key(item["word"])
        if word not in existing:
            entries.append({
                "word": word,
                "type": item["type"],
                "meanings": [
                    {
                        "definition": item["definition"]
                    }
                ]
            })
            existing.add(word)
            added += 1

        current = connections.get(word, [])
        merged = []
        for connection in current + item["connections"]:
            clean = key(connection)
            if clean and clean != word and clean not in merged:
                merged.append(clean)
        connections[word] = merged[:40]

        grammar.setdefault(word, {
            "forms": {
                "base": word,
                "singular": word,
                "plural": word + "s"
            },
            "examples": {
                "subject_example": "the " + word,
                "plural_example": "many " + word + "s"
            }
        })

    write_json(MAIN_DICTIONARY_FILE, entries)
    write_json(CONNECTIONS_FILE, connections)
    write_json(GRAMMAR_FILE, grammar)

    print(json.dumps({
        "added_entries": added,
        "total_entries": len(entries),
        "connections": len(connections),
        "grammar_entries": len(grammar)
    }, indent=2))


if __name__ == "__main__":
    main()
