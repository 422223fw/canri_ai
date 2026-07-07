import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "main_ai_canri" / "data"
DK_DIR = ROOT / "main_ai_canri" / "UnderstandingDk" / "data"

COMPANY_PRODUCTS_FILE = DATA_DIR / "Company_products.json"
MAIN_DICTIONARY_FILE = DK_DIR / "main_dictionary.json"
CONNECTIONS_FILE = DK_DIR / "Connections_Dictionary.json"


def load_json(path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def normalize_key(text):
    return str(text).strip().lower()


def add_entry(entries, existing_words, word, word_type, definition, example=None):
    key = normalize_key(word)
    if not key or key in existing_words:
        return False

    meaning = {"definition": definition}
    if example:
        meaning["example"] = example

    entries.append({
        "word": key,
        "type": word_type,
        "meanings": [meaning]
    })
    existing_words.add(key)
    return True


def add_connection(connections, word, related):
    key = normalize_key(word)
    if not key:
        return

    current = connections.get(key, [])
    merged = []
    for item in current + related:
        clean = normalize_key(item)
        if clean and clean != key and clean not in merged:
            merged.append(clean)
    connections[key] = merged[:40]


def main():
    company_products = load_json(COMPANY_PRODUCTS_FILE, {})
    entries = load_json(MAIN_DICTIONARY_FILE, [])
    connections = load_json(CONNECTIONS_FILE, {})

    existing_words = {
        normalize_key(entry.get("word", ""))
        for entry in entries
        if isinstance(entry, dict)
    }

    added_entries = 0

    for company_id, company in company_products.get("companies", {}).items():
        name = company.get("name") or company_id
        products = company.get("products", [])
        aliases = company.get("aliases", [])
        description = company.get("description") or f"{name} is a company."

        if add_entry(
            entries,
            existing_words,
            name,
            "proper noun",
            description,
            f"{name} makes products such as {', '.join(products[:4])}."
        ):
            added_entries += 1

        add_connection(
            connections,
            name,
            ["company", company.get("field", ""), "brand"] + products + aliases
        )

        for alias in aliases:
            add_connection(connections, alias, [name, "company", "brand"] + products)

    for product_id, product in company_products.get("products", {}).items():
        name = product.get("name") or product_id
        company = product.get("company", "")
        category = product.get("category", "product")
        description = product.get("description") or f"{name} is a product."
        aliases = product.get("aliases", [])

        if add_entry(
            entries,
            existing_words,
            name,
            "proper noun",
            f"{description} It is associated with {company}.",
            f"{name} is a {category} from {company}."
        ):
            added_entries += 1

        add_connection(
            connections,
            name,
            [company, category, "product"] + aliases
        )

        for alias in aliases:
            add_connection(connections, alias, [name, company, category, "product"])

    write_json(MAIN_DICTIONARY_FILE, entries)
    write_json(CONNECTIONS_FILE, connections)

    print(json.dumps({
        "added_entries": added_entries,
        "total_entries": len(entries),
        "connections": len(connections)
    }, indent=2))


if __name__ == "__main__":
    main()
