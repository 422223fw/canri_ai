import json
from pathlib import Path


DATA_DIR = Path("main_ai_canri") / "data"
TRANSLATION_FILE = DATA_DIR / "Translation_dictionary.json"
OUTPUT_FILE = DATA_DIR / "Language_examples.json"


TEMPLATES = [
    {
        "en": "{a} is {b}",
        "he": "{a} הוא {b}",
        "fr": "{a} est {b}",
    },
    {
        "en": "I use {a}",
        "he": "אני משתמש ב{a}",
        "fr": "j'utilise {a}",
    },
    {
        "en": "Canri learns {a}",
        "he": "קאנרי לומד {a}",
        "fr": "Canri apprend {a}",
    },
    {
        "en": "the {a} needs {b}",
        "he": "ה{a} צריך {b}",
        "fr": "le {a} a besoin de {b}",
    },
    {
        "en": "this {a} is important",
        "he": "ה{a} הזה חשוב",
        "fr": "ce {a} est important",
    },
    {
        "en": "build a {a}",
        "he": "בנה {a}",
        "fr": "construire un {a}",
    },
    {
        "en": "research the {a}",
        "he": "חקור את ה{a}",
        "fr": "rechercher le {a}",
    },
    {
        "en": "translate {a}",
        "he": "תרגם {a}",
        "fr": "traduire {a}",
    },
    {
        "en": "{a} and {b}",
        "he": "{a} ו{b}",
        "fr": "{a} et {b}",
    },
    {
        "en": "explain {a}",
        "he": "הסבר {a}",
        "fr": "expliquer {a}",
    },
]


DIRECTIONS = [
    ("en", "he"),
    ("he", "en"),
    ("en", "fr"),
    ("fr", "en"),
    ("he", "fr"),
    ("fr", "he"),
]


def load_translations():
    with TRANSLATION_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_word(entry, language):
    value = entry.get(language)

    if not value:
        return None

    return str(value)


def build_sentence(template, language, first, second):
    return template[language].format(
        a=first,
        b=second,
    )


def build_examples(limit=1000):
    translations = load_translations()

    usable = [
        entry
        for entry in translations.values()
        if all(
            language in entry
            for language in [
                "en",
                "he",
                "fr",
            ]
        )
    ]

    examples = []
    seen = set()
    index = 0

    while len(examples) < limit:
        first = usable[index % len(usable)]
        second = usable[(index * 7 + 3) % len(usable)]
        template = TEMPLATES[index % len(TEMPLATES)]
        source_language, target_language = DIRECTIONS[
            index % len(DIRECTIONS)
        ]

        source_first = get_word(
            first,
            source_language,
        )
        source_second = get_word(
            second,
            source_language,
        )
        target_first = get_word(
            first,
            target_language,
        )
        target_second = get_word(
            second,
            target_language,
        )

        source = build_sentence(
            template,
            source_language,
            source_first,
            source_second,
        )
        target = build_sentence(
            template,
            target_language,
            target_first,
            target_second,
        )

        key = (
            source_language,
            target_language,
            source,
            target,
        )

        if key not in seen:
            examples.append(
                {
                    "language": source_language,
                    "target_language": target_language,
                    "source": source,
                    "target": target,
                    "quality": 90 + (index % 10),
                }
            )
            seen.add(key)

        index += 1

    return examples


def main():
    examples = build_examples(
        limit=1000
    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            examples,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(examples)} examples to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
