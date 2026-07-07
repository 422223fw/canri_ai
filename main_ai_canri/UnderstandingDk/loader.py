import json
import random
from pathlib import Path
from difflib import get_close_matches

DATA_DIR = Path(__file__).parent / "data"

MAIN_FILE = DATA_DIR / "main_dictionary.json"
CONNECTIONS_FILE = DATA_DIR / "Connections_Dictionary.json"
GRAMMAR_FILE = DATA_DIR / "Grammar_dictionary.json"


# =========================
# INTERNAL CACHE (STABLE)
# =========================
_words = []
_word_index = {}
_type_index = {}
_connections = {}
_grammar = {}

_loaded = False


# =========================
# LOAD ENGINE (SAFE + IDENTITY FIX)
# =========================
def load(force: bool = False):
    global _loaded, _words, _word_index, _type_index, _connections, _grammar

    if _loaded and not force:
        return

    # reset (important for v1.0.0 stability)
    _words = []
    _word_index = {}
    _type_index = {}
    _connections = {}
    _grammar = {}

    # -------- MAIN DICTIONARY --------
    if MAIN_FILE.exists():
        with open(MAIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            word = entry.get("word", "").lower().strip()
            if not word:
                continue

            _words.append(entry)
            _word_index.setdefault(word, []).append(entry)

            word_type = entry.get("type", "").lower().strip()
            if word_type:
                _type_index.setdefault(word_type, []).append(entry)

    # -------- CONNECTIONS --------
    if CONNECTIONS_FILE.exists():
        with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
            _connections = json.load(f)

    # -------- GRAMMAR --------
    if GRAMMAR_FILE.exists():
        with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
            _grammar = json.load(f)

    _loaded = True


# =========================
# CORE SEARCH API (STABLE)
# =========================
def search_word(word: str):
    load()
    return _word_index.get(word.lower().strip(), [])


def search_prefix(prefix: str):
    load()
    prefix = prefix.lower().strip()

    return [
        entry
        for word, entries in _word_index.items()
        if word.startswith(prefix)
        for entry in entries
    ]


def search_ending(ending: str):
    load()
    ending = ending.lower().strip()

    return [
        entry
        for word, entries in _word_index.items()
        if word.endswith(ending)
        for entry in entries
    ]


def search_length(length: int):
    load()
    return [
        entry
        for word, entries in _word_index.items()
        if len(word) == length
        for entry in entries
    ]


def search_length_range(min_length: int, max_length: int):
    load()
    return [
        entry
        for word, entries in _word_index.items()
        if min_length <= len(word) <= max_length
        for entry in entries
    ]


def search_type(word_type: str):
    load()
    return _type_index.get(word_type.lower().strip(), [])


def search_definition(text: str):
    load()
    text = text.lower().strip()

    results = []
    for entry in _words:
        for meaning in entry.get("meanings", []):
            if text in meaning.get("definition", "").lower():
                results.append(entry)
                break

    return results


def search_range(range_text: str):
    load()
    if "-" not in range_text:
        return []

    start, end = range_text.lower().split("-", 1)

    results = []
    for word, entries in _word_index.items():
        if start <= word[:len(start)] <= end:
            results.extend(entries)

    return results


# =========================
# INFO API
# =========================
def get_meanings(word: str):
    load()
    return [
        meaning.get("definition", "")
        for entry in _word_index.get(word.lower().strip(), [])
        for meaning in entry.get("meanings", [])
        if meaning.get("definition")
    ]


def count_words():
    load()
    return len(_word_index)


def get_all_words():
    load()
    return list(_word_index.keys())


def get_word_types():
    load()
    return list(_type_index.keys())


def word_exists(word: str):
    load()
    return word.lower().strip() in _word_index


def stats():
    load()
    return {
        "total_words": len(_words),
        "unique_words": len(_word_index),
        "types": {t: len(v) for t, v in _type_index.items()}
    }


# =========================
# CONNECTIONS
# =========================
def related(word: str):
    load()
    return _connections.get(word.lower().strip(), [])


def suggest(word: str, limit: int = 10):
    load()
    return get_close_matches(
        word.lower().strip(),
        list(_word_index.keys()),
        n=limit,
        cutoff=0.5
    )


def random_word():
    load()
    return random.choice(_words) if _words else None


# =========================
# GRAMMAR ENGINE (v1.0 STABLE)
# =========================
def grammar_exists(word: str):
    load()
    return word.lower().strip() in _grammar


def get_forms(word: str):
    load()
    return _grammar.get(word.lower().strip(), {}).get("forms", {})


def get_tense(word: str, tense: str):
    return get_forms(word).get(tense)


def convert_tense(word: str, to_tense: str):
    return get_forms(word).get(to_tense)


def detect_tense(word: str):
    load()
    word = word.lower().strip()

    for base, data in _grammar.items():
        forms = data.get("forms", {})
        for tense, form in forms.items():
            if form == word:
                return tense

    return None


def get_verb_base(word: str):
    load()
    forms = get_forms(word)
    return forms.get("base")


def get_all_by_tense(tense: str):
    load()
    return {
        word: data["forms"][tense]
        for word, data in _grammar.items()
        if tense in data.get("forms", {})
    }


# =========================
# SENTENCE ENGINE (IMPROVED)
# =========================
def analyze_sentence(sentence: str):
    load()
    words = sentence.lower().split()

    return [
        {
            "word": w,
            "exists": word_exists(w),
            "tense": detect_tense(w)
        }
        for w in words
    ]


def fix_sentence(sentence: str):
    load()
    words = sentence.lower().split()

    fixed = []
    for w in words:
        forms = _grammar.get(w, {}).get("forms", {})
        fixed.append(forms.get("base", w))

    return " ".join(fixed)