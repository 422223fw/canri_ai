"""Validate every project JSON file and report important collection sizes."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COUNT_TARGETS = {
    "main_ai_canri/data/code.json": None,
    "main_ai_canri/data/Code_terms_dictionary.json": "functions",
    "main_ai_canri/data/Knowledge_queue.json": "pending",
    "main_ai_canri/UnderstandingDk/data/main_dictionary.json": None,
    "main_ai_canri/UnderstandingDk/data/Connections_Dictionary.json": None,
    "main_ai_canri/UnderstandingDk/data/Grammar_dictionary.json": None,
}


def collection_size(value, collection_key=None):
    if collection_key and isinstance(value, dict):
        selected = value.get(collection_key, [])
        return len(selected) if isinstance(selected, (list, dict)) else 0
    return len(value) if isinstance(value, (list, dict)) else 0


def main() -> int:
    files = sorted(PROJECT_ROOT.rglob("*.json"))
    errors = []
    loaded = {}

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded[path.resolve()] = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append((path, error))

    print(f"JSON files checked: {len(files)}")
    print(f"JSON parse errors: {len(errors)}")
    for path, error in errors[:20]:
        print(f"ERROR {path.relative_to(PROJECT_ROOT)}: {error}")

    for relative, collection_key in COUNT_TARGETS.items():
        path = (PROJECT_ROOT / relative).resolve()
        value = loaded.get(path)
        if value is not None:
            print(f"COUNT {relative}: {collection_size(value, collection_key)}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
