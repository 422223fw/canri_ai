"""Add 5,000 searchable function terms derived from Canri's code bank."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "main_ai_canri" / "data"
CODE_FILE = DATA_DIR / "code.json"
TERMS_FILE = DATA_DIR / "Code_terms_dictionary.json"
TARGET = 5_000


def save_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    snippets = json.loads(CODE_FILE.read_text(encoding="utf-8"))
    terms = json.loads(TERMS_FILE.read_text(encoding="utf-8"))
    functions = terms.setdefault("functions", [])
    existing = {
        (str(item.get("name", "")).lower(), str(item.get("language", "")).lower())
        for item in functions
        if isinstance(item, dict)
    }
    additions = []

    for item in reversed(snippets):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "").strip()
        language = str(item.get("language") or "unknown").strip().lower()
        key = (name.lower(), language)
        if not name or key in existing:
            continue
        tags = [str(tag).lower() for tag in item.get("tags", []) if tag]
        category = str(item.get("category") or (tags[0] if tags else "general"))
        context = list(dict.fromkeys([category.lower(), *tags]))[:10]
        additions.append({
            "name": name,
            "language": language,
            "category": category,
            "context": context,
            "source_id": item.get("id"),
        })
        existing.add(key)
        if len(additions) == TARGET:
            break

    if len(additions) != TARGET:
        raise RuntimeError(f"Expected {TARGET} new code terms, got {len(additions)}")

    functions.extend(additions)
    terms.setdefault("metadata", {})["derived_code_bank_terms"] = sum(
        1 for item in functions if isinstance(item, dict) and item.get("source_id")
    )
    save_json(TERMS_FILE, terms)
    print(json.dumps({"added": len(additions), "total": len(functions)}, indent=2))


if __name__ == "__main__":
    main()
