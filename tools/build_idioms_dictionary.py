import json
from pathlib import Path


OUTPUT_FILE = Path("main_ai_canri") / "data" / "Idioms.json"


BASE_IDIOMS = {
    "piece of cake": {
        "meaning": "something very easy",
        "he": "קל מאוד",
        "fr": "tres facile",
        "example": "This test was a piece of cake.",
    },
    "break the ice": {
        "meaning": "start a friendly conversation",
        "he": "לשבור את הקרח",
        "fr": "briser la glace",
        "example": "He told a joke to break the ice.",
    },
    "under the weather": {
        "meaning": "feeling sick",
        "he": "לא מרגיש טוב",
        "fr": "ne pas se sentir bien",
        "example": "She stayed home because she was under the weather.",
    },
    "hit the books": {
        "meaning": "study seriously",
        "he": "לשבת ללמוד",
        "fr": "se mettre a etudier",
        "example": "I need to hit the books before the exam.",
    },
    "once in a blue moon": {
        "meaning": "very rarely",
        "he": "לעיתים רחוקות מאוד",
        "fr": "tres rarement",
        "example": "He visits once in a blue moon.",
    },
    "על הפנים": {
        "meaning": "very bad",
        "en": "terrible",
        "fr": "terrible",
        "example": "המשחק הזה היה על הפנים.",
    },
    "לשבור את הקרח": {
        "meaning": "start a friendly conversation",
        "en": "break the ice",
        "fr": "briser la glace",
        "example": "הבדיחה עזרה לשבור את הקרח.",
    },
    "בראש טוב": {
        "meaning": "in a good mood",
        "en": "in a good mood",
        "fr": "de bonne humeur",
        "example": "היום אני בראש טוב.",
    },
    "briser la glace": {
        "meaning": "start a friendly conversation",
        "en": "break the ice",
        "he": "לשבור את הקרח",
        "example": "Il a raconte une blague pour briser la glace.",
    },
    "coup de main": {
        "meaning": "help",
        "en": "helping hand",
        "he": "עזרה",
        "example": "Peux-tu me donner un coup de main?",
    },
}


DOMAINS = [
    ("code", "קוד", "code"),
    ("science", "מדע", "science"),
    ("history", "היסטוריה", "histoire"),
    ("language", "שפה", "langue"),
    ("research", "מחקר", "recherche"),
    ("memory", "זיכרון", "memoire"),
    ("security", "אבטחה", "securite"),
    ("game", "משחק", "jeu"),
    ("story", "סיפור", "recit"),
    ("math", "מתמטיקה", "mathematiques"),
    ("data", "נתונים", "donnees"),
    ("network", "רשת", "reseau"),
    ("vision", "ראייה", "vision"),
    ("voice", "קול", "voix"),
    ("world", "עולם", "monde"),
    ("logic", "לוגיקה", "logique"),
    ("learning", "למידה", "apprentissage"),
    ("planning", "תכנון", "planification"),
    ("creative", "יצירה", "creation"),
    ("technology", "טכנולוגיה", "technologie"),
]


PATTERNS = [
    {
        "en": "{domain} is a piece of cake",
        "he": "{domain_he} קל מאוד",
        "fr": "{domain_fr} est tres facile",
        "meaning": "the subject feels easy",
        "example": "With practice, {domain} is a piece of cake.",
    },
    {
        "en": "break the {domain} ice",
        "he": "לשבור את הקרח של {domain_he}",
        "fr": "briser la glace de {domain_fr}",
        "meaning": "start working or talking about the subject",
        "example": "A small example can break the {domain} ice.",
    },
    {
        "en": "hit the {domain} books",
        "he": "לשבת ללמוד {domain_he}",
        "fr": "se mettre a etudier {domain_fr}",
        "meaning": "study the subject seriously",
        "example": "Tonight I will hit the {domain} books.",
    },
    {
        "en": "{domain} light bulb moment",
        "he": "רגע הבנה ב{domain_he}",
        "fr": "moment de comprehension en {domain_fr}",
        "meaning": "a sudden understanding",
        "example": "The diagram created a {domain} light bulb moment.",
    },
    {
        "en": "connect the {domain} dots",
        "he": "לחבר את הנקודות ב{domain_he}",
        "fr": "relier les points en {domain_fr}",
        "meaning": "understand how details relate",
        "example": "The report helped connect the {domain} dots.",
    },
    {
        "en": "{domain} on the right track",
        "he": "{domain_he} בכיוון הנכון",
        "fr": "{domain_fr} sur la bonne voie",
        "meaning": "making good progress",
        "example": "The project is {domain} on the right track.",
    },
    {
        "en": "lost in the {domain} weeds",
        "he": "אבוד בפרטים של {domain_he}",
        "fr": "perdu dans les details de {domain_fr}",
        "meaning": "too focused on small details",
        "example": "Do not get lost in the {domain} weeds.",
    },
    {
        "en": "{domain} from scratch",
        "he": "{domain_he} מאפס",
        "fr": "{domain_fr} a partir de zero",
        "meaning": "built from the beginning",
        "example": "We built the {domain} system from scratch.",
    },
    {
        "en": "the heart of {domain}",
        "he": "הלב של {domain_he}",
        "fr": "le coeur de {domain_fr}",
        "meaning": "the most important part",
        "example": "Clear logic is the heart of {domain}.",
    },
    {
        "en": "{domain} in plain language",
        "he": "{domain_he} בשפה פשוטה",
        "fr": "{domain_fr} en langage simple",
        "meaning": "explained simply",
        "example": "Explain {domain} in plain language.",
    },
]


def add_idiom(data, key, entry):
    key = key.strip().lower()

    if not key or key in data:
        return False

    data[key] = entry

    return True


def build_idioms():
    data = dict(BASE_IDIOMS)

    for index in range(1000):
        domain, domain_he, domain_fr = DOMAINS[
            index % len(DOMAINS)
        ]
        pattern = PATTERNS[
            index % len(PATTERNS)
        ]
        variant = index // len(PATTERNS)

        key = pattern["en"].format(
            domain=domain,
            domain_he=domain_he,
            domain_fr=domain_fr,
        )

        if variant:
            key = f"{key} {variant}"

        entry = {
            "meaning": pattern["meaning"],
            "he": pattern["he"].format(
                domain=domain,
                domain_he=domain_he,
                domain_fr=domain_fr,
            ),
            "fr": pattern["fr"].format(
                domain=domain,
                domain_he=domain_he,
                domain_fr=domain_fr,
            ),
            "example": pattern["example"].format(
                domain=domain,
                domain_he=domain_he,
                domain_fr=domain_fr,
            ),
        }

        add_idiom(
            data,
            key,
            entry,
        )

        if len(data) >= 1000:
            return dict(list(data.items())[:1000])

    return data


def main():
    idioms = build_idioms()

    if len(idioms) != 1000:
        raise RuntimeError(
            f"Expected 1000 idioms, got {len(idioms)}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            idioms,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(idioms)} idiom entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
