import json
from pathlib import Path


OUTPUT_FILE = Path("main_ai_canri") / "data" / "Slang_dictionary.json"


BASE_SLANG = {
    "lol": {
        "meaning": "laughing out loud",
        "he": "חחח",
        "fr": "mdr",
        "tone": "informal",
    },
    "bro": {
        "meaning": "friend / brother",
        "he": "אחי",
        "fr": "frero",
        "tone": "informal",
    },
    "cool": {
        "meaning": "good or impressive",
        "he": "סבבה",
        "fr": "cool",
        "tone": "informal",
    },
    "wow": {
        "meaning": "surprise or admiration",
        "he": "וואו",
        "fr": "waouh",
        "tone": "informal",
    },
    "ok": {
        "meaning": "okay",
        "he": "בסדר",
        "fr": "ok",
        "tone": "neutral",
    },
    "yep": {
        "meaning": "yes",
        "he": "כן",
        "fr": "ouais",
        "tone": "informal",
    },
    "nope": {
        "meaning": "no",
        "he": "לא",
        "fr": "non",
        "tone": "informal",
    },
    "gg": {
        "meaning": "good game",
        "he": "משחק טוב",
        "fr": "bien joue",
        "tone": "gaming",
    },
    "brb": {
        "meaning": "be right back",
        "he": "תכף חוזר",
        "fr": "je reviens",
        "tone": "chat",
    },
    "btw": {
        "meaning": "by the way",
        "he": "דרך אגב",
        "fr": "au fait",
        "tone": "chat",
    },
    "סבבה": {
        "meaning": "okay / cool",
        "en": "cool",
        "fr": "cool",
        "tone": "informal",
    },
    "חח": {
        "meaning": "laughing",
        "en": "haha",
        "fr": "mdr",
        "tone": "informal",
    },
    "אחי": {
        "meaning": "friend / bro",
        "en": "bro",
        "fr": "frero",
        "tone": "informal",
    },
    "וואלה": {
        "meaning": "really / wow",
        "en": "really",
        "fr": "vraiment",
        "tone": "informal",
    },
    "יאללה": {
        "meaning": "let's go",
        "en": "let's go",
        "fr": "allez",
        "tone": "informal",
    },
    "mdr": {
        "meaning": "laughing",
        "en": "lol",
        "he": "חחח",
        "tone": "informal",
    },
    "frero": {
        "meaning": "bro / close friend",
        "en": "bro",
        "he": "אחי",
        "tone": "informal",
    },
    "ouais": {
        "meaning": "yeah",
        "en": "yep",
        "he": "כן",
        "tone": "informal",
    },
    "bof": {
        "meaning": "meh / not great",
        "en": "meh",
        "he": "ככה ככה",
        "tone": "informal",
    },
    "nickel": {
        "meaning": "perfect / great",
        "en": "perfect",
        "he": "מעולה",
        "tone": "informal",
    },
}


DOMAINS = [
    ("code", "קוד", "code"),
    ("ai", "בינה", "ia"),
    ("data", "דאטה", "data"),
    ("game", "משחק", "jeu"),
    ("chat", "צאט", "chat"),
    ("research", "מחקר", "recherche"),
    ("science", "מדע", "science"),
    ("history", "היסטוריה", "histoire"),
    ("language", "שפה", "langue"),
    ("security", "אבטחה", "securite"),
    ("memory", "זיכרון", "memoire"),
    ("logic", "לוגיקה", "logique"),
    ("web", "ווב", "web"),
    ("robot", "רובוט", "robot"),
    ("creative", "יצירה", "crea"),
]


SLANG_PATTERNS = [
    ("{domain}_vibe", "{domain_he}_וייב", "{domain_fr}_vibe", "good feeling around the topic", "informal"),
    ("mega_{domain}", "מגה_{domain_he}", "mega_{domain_fr}", "very strong or impressive topic", "informal"),
    ("{domain}_mode", "מצב_{domain_he}", "mode_{domain_fr}", "focused on the topic", "chat"),
    ("{domain}_boss", "{domain_he}_בוס", "boss_{domain_fr}", "someone very good at the topic", "informal"),
    ("{domain}_hack", "{domain_he}_טריק", "astuce_{domain_fr}", "quick useful trick", "informal"),
    ("{domain}_pro", "{domain_he}_מקצוען", "pro_{domain_fr}", "skilled at the topic", "informal"),
    ("{domain}_noob", "{domain_he}_מתחיל", "debutant_{domain_fr}", "beginner at the topic", "gaming"),
    ("{domain}_win", "{domain_he}_ניצחון", "victoire_{domain_fr}", "successful result", "gaming"),
    ("{domain}_fail", "{domain_he}_נפילה", "echec_{domain_fr}", "failed attempt", "informal"),
    ("{domain}_boost", "{domain_he}_בוסט", "boost_{domain_fr}", "improvement or upgrade", "chat"),
]


def add_entry(data, key, meaning, en=None, he=None, fr=None, tone="informal"):
    key = key.strip().lower()

    if not key or key in data:
        return False

    entry = {
        "meaning": meaning,
        "tone": tone,
    }

    if en:
        entry["en"] = en

    if he:
        entry["he"] = he

    if fr:
        entry["fr"] = fr

    data[key] = entry

    return True


def build_slang():
    data = dict(BASE_SLANG)

    index = 0

    while len(data) < 2500:
        domain_en, domain_he, domain_fr = DOMAINS[
            index % len(DOMAINS)
        ]
        pattern_en, pattern_he, pattern_fr, meaning, tone = SLANG_PATTERNS[
            index % len(SLANG_PATTERNS)
        ]
        variant = index // len(SLANG_PATTERNS)

        en_key = pattern_en.format(
            domain=domain_en,
            domain_he=domain_he,
            domain_fr=domain_fr,
        )
        he_key = pattern_he.format(
            domain=domain_en,
            domain_he=domain_he,
            domain_fr=domain_fr,
        )
        fr_key = pattern_fr.format(
            domain=domain_en,
            domain_he=domain_he,
            domain_fr=domain_fr,
        )

        if variant:
            en_key = f"{en_key}_{variant}"
            he_key = f"{he_key}_{variant}"
            fr_key = f"{fr_key}_{variant}"

        add_entry(
            data,
            en_key,
            meaning,
            he=he_key,
            fr=fr_key,
            tone=tone,
        )
        add_entry(
            data,
            he_key,
            meaning,
            en=en_key,
            fr=fr_key,
            tone=tone,
        )
        add_entry(
            data,
            fr_key,
            meaning,
            en=en_key,
            he=he_key,
            tone=tone,
        )

        index += 1

    return dict(list(data.items())[:2500])


def main():
    slang = build_slang()

    if len(slang) != 2500:
        raise RuntimeError(
            f"Expected 2500 slang entries, got {len(slang)}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            slang,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(slang)} slang entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
