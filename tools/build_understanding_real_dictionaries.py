import json
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
UNDERSTANDING_DIR = PROJECT_DIR / "main_ai_canri" / "UnderstandingDk" / "data"
LANGUAGE_DIR = PROJECT_DIR / "main_ai_canri" / "data"

TARGET_COUNT = 10000

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "to",
    "used", "with", "within", "without",
}


def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_understanding(name, default):
    clean_path = UNDERSTANDING_DIR / f"{name}.tmp"
    if clean_path.exists():
        return load_json(clean_path, default)
    return load_json(UNDERSTANDING_DIR / name, default)


def save_json(name, data):
    target = UNDERSTANDING_DIR / name
    staged = target.with_suffix(target.suffix + ".new")
    with staged.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    try:
        staged.replace(target)
        return "updated"
    except PermissionError:
        return f"staged: {staged.name}"


def normalize_term(term):
    term = str(term).strip().lower().replace("_", " ")
    term = re.sub(r"\s+", " ", term)
    return term


def safe_key(term):
    return normalize_term(term).replace(" ", "_")


def clean_text(value):
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def add_main_entry(entries, index, word, word_type, definition):
    word = normalize_term(word)
    definition = clean_text(definition)

    if not word or word in index:
        return False
    if definition.startswith("A Canri AI"):
        return False

    entries.append(
        {
            "word": word,
            "type": word_type,
            "meanings": [
                {
                    "definition": definition
                }
            ],
        }
    )
    index.add(word)
    return True


def word_tokens(text):
    tokens = re.findall(r"[a-z][a-z\-]{2,}", normalize_term(text))
    return [
        token
        for token in tokens
        if token not in STOP_WORDS
    ][:6]


def regular_forms(base):
    base = normalize_term(base)
    first, *rest = base.split(" ")
    tail = " ".join(rest)

    irregular = {
        "be": ("was", "been", "being", "is"),
        "begin": ("began", "begun", "beginning", "begins"),
        "break": ("broke", "broken", "breaking", "breaks"),
        "bring": ("brought", "brought", "bringing", "brings"),
        "build": ("built", "built", "building", "builds"),
        "buy": ("bought", "bought", "buying", "buys"),
        "choose": ("chose", "chosen", "choosing", "chooses"),
        "come": ("came", "come", "coming", "comes"),
        "do": ("did", "done", "doing", "does"),
        "draw": ("drew", "drawn", "drawing", "draws"),
        "drink": ("drank", "drunk", "drinking", "drinks"),
        "drive": ("drove", "driven", "driving", "drives"),
        "eat": ("ate", "eaten", "eating", "eats"),
        "fall": ("fell", "fallen", "falling", "falls"),
        "find": ("found", "found", "finding", "finds"),
        "get": ("got", "gotten", "getting", "gets"),
        "give": ("gave", "given", "giving", "gives"),
        "go": ("went", "gone", "going", "goes"),
        "grow": ("grew", "grown", "growing", "grows"),
        "have": ("had", "had", "having", "has"),
        "hear": ("heard", "heard", "hearing", "hears"),
        "hold": ("held", "held", "holding", "holds"),
        "keep": ("kept", "kept", "keeping", "keeps"),
        "know": ("knew", "known", "knowing", "knows"),
        "leave": ("left", "left", "leaving", "leaves"),
        "make": ("made", "made", "making", "makes"),
        "meet": ("met", "met", "meeting", "meets"),
        "read": ("read", "read", "reading", "reads"),
        "run": ("ran", "run", "running", "runs"),
        "say": ("said", "said", "saying", "says"),
        "see": ("saw", "seen", "seeing", "sees"),
        "send": ("sent", "sent", "sending", "sends"),
        "speak": ("spoke", "spoken", "speaking", "speaks"),
        "take": ("took", "taken", "taking", "takes"),
        "teach": ("taught", "taught", "teaching", "teaches"),
        "think": ("thought", "thought", "thinking", "thinks"),
        "understand": ("understood", "understood", "understanding", "understands"),
        "wear": ("wore", "worn", "wearing", "wears"),
        "win": ("won", "won", "winning", "wins"),
        "write": ("wrote", "written", "writing", "writes"),
    }

    if first in irregular:
        past, participle, continuous, third = irregular[first]
    else:
        if first.endswith("e") and not first.endswith("ee"):
            past = f"{first}d"
            continuous = f"{first[:-1]}ing"
        elif first.endswith("y") and len(first) > 1 and first[-2] not in "aeiou":
            past = f"{first[:-1]}ied"
            continuous = f"{first}ing"
        elif (
            len(first) >= 3
            and first[-1] not in "aeiouy"
            and first[-1] not in "wxyz"
            and first[-2] in "aeiou"
            and first[-3] not in "aeiou"
        ):
            past = f"{first}{first[-1]}ed"
            continuous = f"{first}{first[-1]}ing"
        else:
            past = f"{first}ed"
            continuous = f"{first}ing"

        if first.endswith(("s", "sh", "ch", "x", "z", "o")):
            third = f"{first}es"
        elif first.endswith("y") and len(first) > 1 and first[-2] not in "aeiou":
            third = f"{first[:-1]}ies"
        else:
            third = f"{first}s"

        participle = past

    def join(verb):
        return f"{verb} {tail}".strip()

    return {
        "forms": {
            "base": base,
            "past": join(past),
            "past_participle": join(participle),
            "present_continuous": join(continuous),
        },
        "tenses": {
            "present": base,
            "past": join(past),
            "future": f"will {base}",
        },
        "conjugation": {
            "i": base,
            "he_she_it": join(third),
            "we_they": base,
        },
    }


def build_main_dictionary():
    base_entries = load_understanding("main_dictionary.json", [])
    entries = []
    index = set()

    for entry in base_entries:
        word = entry.get("word")
        meanings = entry.get("meanings", [])
        if not meanings:
            continue
        definition = meanings[0].get("definition", "")
        add_main_entry(entries, index, word, entry.get("type", "noun"), definition)

    technical_terms = load_json(LANGUAGE_DIR / "Technical_terms.json", {})
    for word, data in technical_terms.items():
        add_main_entry(
            entries,
            index,
            word,
            "noun",
            data.get("meaning", f"A technical term in {data.get('field', 'knowledge')}."),
        )

    abbreviations = load_json(LANGUAGE_DIR / "Abbreviations.json", {})
    for word, data in abbreviations.items():
        add_main_entry(
            entries,
            index,
            word,
            "abbreviation",
            f"An abbreviation for {data.get('full', word)}, used in {data.get('field', 'general language')}.",
        )

    units = load_json(LANGUAGE_DIR / "Units_dictionary.json", {})
    for word, data in units.items():
        add_main_entry(
            entries,
            index,
            word,
            "unit",
            f"A unit of {data.get('type', 'measurement')} named {data.get('name', word)}.",
        )

    idioms = load_json(LANGUAGE_DIR / "Idioms.json", {})
    for word, data in idioms.items():
        add_main_entry(
            entries,
            index,
            word,
            "idiom",
            data.get("meaning", f"An idiomatic expression: {word}."),
        )

    synonyms = load_json(LANGUAGE_DIR / "Synonyms.json", {})
    for word, values in synonyms.items():
        if not isinstance(values, list) or not values:
            continue
        add_main_entry(
            entries,
            index,
            word,
            "noun",
            f"A vocabulary word with close meanings such as {', '.join(map(str, values[:4]))}.",
        )

    antonyms = load_json(LANGUAGE_DIR / "Antonyms.json", {})
    for word, values in antonyms.items():
        if not isinstance(values, list) or not values:
            continue
        add_main_entry(
            entries,
            index,
            word,
            "noun",
            f"A vocabulary word whose opposite meaning includes {', '.join(map(str, values[:3]))}.",
        )

    translations = load_json(LANGUAGE_DIR / "Translation_dictionary.json", {})
    for word, data in translations.items():
        if len(entries) >= TARGET_COUNT:
            break
        if not isinstance(data, dict):
            continue

        he = data.get("he")
        fr = data.get("fr")
        details = []
        if he:
            details.append(f"Hebrew: {he}")
        if fr:
            details.append(f"French: {fr}")
        detail_text = "; ".join(details)
        if not detail_text:
            detail_text = "used as a vocabulary term"

        add_main_entry(
            entries,
            index,
            word,
            "noun",
            f"A vocabulary term with known translations ({detail_text}).",
        )

    return entries[:TARGET_COUNT]


def build_connections(main_entries):
    base_connections = load_understanding("Connections_Dictionary.json", {})
    connections = {}

    for key, value in base_connections.items():
        key = normalize_term(key)
        if isinstance(value, list):
            values = [normalize_term(item) for item in value if str(item).strip()]
            if key and values:
                connections[key] = values[:8]

    synonyms = load_json(LANGUAGE_DIR / "Synonyms.json", {})
    for key, value in synonyms.items():
        key = normalize_term(key)
        if isinstance(value, list) and key:
            connections.setdefault(key, [])
            connections[key].extend(normalize_term(item) for item in value[:8])

    antonyms = load_json(LANGUAGE_DIR / "Antonyms.json", {})
    for key, value in antonyms.items():
        key = normalize_term(key)
        if isinstance(value, list) and key:
            connections.setdefault(key, [])
            connections[key].extend(normalize_term(item) for item in value[:4])
            connections[key].append("opposite")

    technical_terms = load_json(LANGUAGE_DIR / "Technical_terms.json", {})
    for key, data in technical_terms.items():
        key = normalize_term(key)
        field = normalize_term(data.get("field", ""))
        meaning_terms = word_tokens(data.get("meaning", ""))
        connections.setdefault(key, [])
        connections[key].extend([field, *meaning_terms])

    translations = load_json(LANGUAGE_DIR / "Translation_dictionary.json", {})
    for key, data in translations.items():
        key = normalize_term(key)
        if not isinstance(data, dict):
            continue
        connections.setdefault(key, [])
        for lang_key in ["en", "he", "fr"]:
            value = data.get(lang_key)
            if value:
                connections[key].append(normalize_term(value))

    for entry in main_entries:
        key = entry["word"]
        definition = entry["meanings"][0]["definition"]
        connections.setdefault(key, [])
        connections[key].extend(word_tokens(definition))
        connections[key].append(entry["type"])

    cleaned = {}
    for key, values in connections.items():
        unique = []
        seen = set()
        for value in values:
            value = normalize_term(value)
            if not value or value == key or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        if unique:
            cleaned[key] = unique[:10]
        if len(cleaned) >= TARGET_COUNT:
            break

    return dict(list(cleaned.items())[:TARGET_COUNT])


def build_grammar():
    base_grammar = load_understanding("Grammar_dictionary.json", {})
    grammar = {}

    for key, value in base_grammar.items():
        forms = value.get("forms", {}) if isinstance(value, dict) else {}
        base = forms.get("base")
        if not base:
            continue
        if " " not in normalize_term(base) and "_" not in normalize_term(base):
            grammar[safe_key(key)] = regular_forms(base)

    actions = [
        "accept", "add", "adjust", "admire", "admit", "advance", "affect",
        "analyze", "answer", "apply", "approve", "arrange", "ask", "assist",
        "build", "calculate", "change", "check", "choose", "clarify",
        "clean", "collect", "combine", "compare", "complete", "connect",
        "consider", "convert", "create", "define", "deliver", "describe",
        "design", "detect", "develop", "discover", "divide", "document",
        "draw", "edit", "evaluate", "examine", "explain", "explore",
        "filter", "find", "fix", "format", "generate", "guide", "identify",
        "improve", "include", "inspect", "install", "interpret", "join",
        "learn", "link", "list", "load", "manage", "map", "measure",
        "monitor", "move", "name", "organize", "parse", "plan", "prepare",
        "process", "protect", "publish", "read", "record", "reduce",
        "remove", "repair", "repeat", "replace", "report", "research",
        "resolve", "review", "run", "save", "search", "select", "send",
        "show", "solve", "sort", "store", "study", "summarize", "support",
        "teach", "test", "translate", "update", "use", "validate", "verify",
        "watch", "write",
    ]

    objects = [
        "ability", "account", "action", "answer", "article", "audio",
        "backup", "book", "budget", "case", "category", "chart", "class",
        "code", "command", "concept", "connection", "content", "context",
        "data", "database", "definition", "design", "detail", "dictionary",
        "document", "email", "entry", "error", "event", "example", "fact",
        "feature", "file", "filter", "form", "function", "goal", "grammar",
        "group", "history", "idea", "image", "index", "information",
        "input", "interface", "issue", "item", "language", "lesson", "line",
        "link", "list", "logic", "map", "meaning", "memory", "message",
        "method", "model", "module", "note", "number", "object", "order",
        "output", "page", "pattern", "phrase", "plan", "problem", "process",
        "program", "project", "question", "record", "report", "request",
        "research", "result", "rule", "sentence", "signal", "source",
        "step", "story", "structure", "summary", "system", "table", "task",
        "term", "test", "text", "topic", "translation", "unit", "value",
        "variable", "version", "video", "view", "voice", "word", "workflow",
    ]

    for action in actions:
        grammar.setdefault(safe_key(action), regular_forms(action))

    for action in actions:
        for obj in objects:
            key = safe_key(f"{action} {obj}")
            grammar.setdefault(key, regular_forms(f"{action} {obj}"))
            if len(grammar) >= TARGET_COUNT:
                return dict(list(grammar.items())[:TARGET_COUNT])

    return dict(list(grammar.items())[:TARGET_COUNT])


def main():
    main_dictionary = build_main_dictionary()
    connections = build_connections(main_dictionary)
    grammar = build_grammar()

    main_status = save_json("main_dictionary.json", main_dictionary)
    connections_status = save_json("Connections_Dictionary.json", connections)
    grammar_status = save_json("Grammar_dictionary.json", grammar)

    print("main_dictionary count:", len(main_dictionary), main_status)
    print("Connections_Dictionary count:", len(connections), connections_status)
    print("Grammar_dictionary count:", len(grammar), grammar_status)


if __name__ == "__main__":
    main()
