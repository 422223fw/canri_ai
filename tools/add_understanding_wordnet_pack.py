"""
Add high-quality WordNet entries to UnderstandingDk dictionaries.

This script appends a fixed number of new entries to:
- main_dictionary.json
- Connections_Dictionary.json
- Grammar_dictionary.json

It uses the local NLTK WordNet corpus when available and keeps the
existing JSON structure used by Canri's UnderstandingDk loader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from nltk.corpus import wordnet as wn


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "main_ai_canri" / "UnderstandingDk" / "data"

MAIN_FILE = DATA_DIR / "main_dictionary.json"
CONNECTIONS_FILE = DATA_DIR / "Connections_Dictionary.json"
GRAMMAR_FILE = DATA_DIR / "Grammar_dictionary.json"

ADD_COUNT = 10_000

POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "who",
}

BAD_DEFINITION_MARKERS = (
    "abbreviation",
    "acronym",
    "trademark",
    "genus ",
    "family ",
    "city in",
    "town in",
    "village in",
    "river in",
    "lake in",
    "mountain in",
    "province of",
    "capital of",
    "united states",
    "king of",
    "queen of",
    "president",
    "emperor",
    "(17",
    "(18",
    "(19",
)

IRREGULAR_VERBS = {
    "arise": ("arose", "arisen", "arising"),
    "be": ("was", "been", "being"),
    "bear": ("bore", "borne", "bearing"),
    "beat": ("beat", "beaten", "beating"),
    "become": ("became", "become", "becoming"),
    "begin": ("began", "begun", "beginning"),
    "bend": ("bent", "bent", "bending"),
    "bite": ("bit", "bitten", "biting"),
    "break": ("broke", "broken", "breaking"),
    "bring": ("brought", "brought", "bringing"),
    "build": ("built", "built", "building"),
    "buy": ("bought", "bought", "buying"),
    "catch": ("caught", "caught", "catching"),
    "choose": ("chose", "chosen", "choosing"),
    "come": ("came", "come", "coming"),
    "do": ("did", "done", "doing"),
    "draw": ("drew", "drawn", "drawing"),
    "drink": ("drank", "drunk", "drinking"),
    "drive": ("drove", "driven", "driving"),
    "eat": ("ate", "eaten", "eating"),
    "fall": ("fell", "fallen", "falling"),
    "feel": ("felt", "felt", "feeling"),
    "find": ("found", "found", "finding"),
    "fly": ("flew", "flown", "flying"),
    "forget": ("forgot", "forgotten", "forgetting"),
    "get": ("got", "gotten", "getting"),
    "give": ("gave", "given", "giving"),
    "go": ("went", "gone", "going"),
    "grow": ("grew", "grown", "growing"),
    "have": ("had", "had", "having"),
    "hear": ("heard", "heard", "hearing"),
    "hold": ("held", "held", "holding"),
    "keep": ("kept", "kept", "keeping"),
    "know": ("knew", "known", "knowing"),
    "leave": ("left", "left", "leaving"),
    "make": ("made", "made", "making"),
    "meet": ("met", "met", "meeting"),
    "read": ("read", "read", "reading"),
    "run": ("ran", "run", "running"),
    "say": ("said", "said", "saying"),
    "see": ("saw", "seen", "seeing"),
    "sell": ("sold", "sold", "selling"),
    "send": ("sent", "sent", "sending"),
    "speak": ("spoke", "spoken", "speaking"),
    "take": ("took", "taken", "taking"),
    "teach": ("taught", "taught", "teaching"),
    "think": ("thought", "thought", "thinking"),
    "write": ("wrote", "written", "writing"),
}


def load_json(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return [] if path.name == "main_dictionary.json" else {}

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def clean_word(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().lower()


def is_clean_single_word(value: str) -> bool:
    return value.isalpha() and 3 <= len(value) <= 24


def is_good_wordnet_entry(word: str, synset) -> bool:
    if not is_clean_single_word(word):
        return False
    if len(word) < 4:
        return False
    if len(set(word)) <= 2 and len(word) <= 5:
        return False

    definition = synset.definition().lower()
    if any(marker in definition for marker in BAD_DEFINITION_MARKERS):
        return False

    lexname = synset.lexname()
    if lexname in {"noun.location", "noun.person"}:
        return False

    return True


def unique_keep_order(values: Iterable[str], limit: int) -> List[str]:
    result: List[str] = []
    seen = set()

    for value in values:
        value = clean_word(value)
        if not is_clean_single_word(value):
            continue
        if value in STOPWORDS:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break

    return result


def first_synset_by_word() -> Tuple[Dict[str, object], Dict[str, int]]:
    selected: Dict[str, object] = {}
    scores: Dict[str, int] = {}

    for synset in wn.all_synsets():
        pos = synset.pos()
        if pos not in POS_NAMES:
            continue

        for lemma_obj in synset.lemmas():
            lemma = lemma_obj.name()
            word = clean_word(lemma)
            score = lemma_obj.count()
            if not is_good_wordnet_entry(word, synset):
                continue
            if word not in selected or score > scores.get(word, -1):
                selected[word] = synset
                scores[word] = score

    return selected, scores


def build_main_entry(word: str, synset) -> Dict[str, object]:
    definition = synset.definition().strip()
    examples = [example.strip() for example in synset.examples()[:2]]
    meaning = {"definition": definition}
    if examples:
        meaning["examples"] = examples

    return {
        "word": word,
        "type": POS_NAMES.get(synset.pos(), "word"),
        "meanings": [meaning],
    }


def related_words(word: str, synset, limit: int = 12) -> List[str]:
    candidates: List[str] = []

    candidates.extend(synset.lemma_names())

    for relation in (
        synset.hypernyms(),
        synset.hyponyms(),
        synset.similar_tos(),
        synset.also_sees(),
        synset.member_holonyms(),
        synset.part_holonyms(),
        synset.substance_holonyms(),
    ):
        for related in relation:
            candidates.extend(related.lemma_names())

    definition_words = synset.definition().split()
    candidates.extend(definition_words)

    cleaned = [
        candidate
        for candidate in unique_keep_order(candidates, limit + 1)
        if candidate != word and candidate not in STOPWORDS
    ]
    return cleaned[:limit]


def needs_double_final_consonant(base: str) -> bool:
    vowels = set("aeiou")
    if len(base) < 3:
        return False
    if base[-1] in "wxy":
        return False
    return base[-1] not in vowels and base[-2] in vowels and base[-3] not in vowels


def regular_forms(base: str) -> Tuple[str, str, str, str]:
    if base in IRREGULAR_VERBS:
        past, participle, continuous = IRREGULAR_VERBS[base]
    elif base.endswith("e") and not base.endswith("ee"):
        past = f"{base}d"
        participle = past
        continuous = f"{base[:-1]}ing"
    elif base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        past = f"{base[:-1]}ied"
        participle = past
        continuous = f"{base}ing"
    elif needs_double_final_consonant(base):
        past = f"{base}{base[-1]}ed"
        participle = past
        continuous = f"{base}{base[-1]}ing"
    else:
        past = f"{base}ed"
        participle = past
        continuous = f"{base}ing"

    if base.endswith(("s", "x", "z", "ch", "sh", "o")):
        third_person = f"{base}es"
    elif base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        third_person = f"{base[:-1]}ies"
    else:
        third_person = f"{base}s"

    return past, participle, continuous, third_person


def build_grammar_entry(base: str) -> Dict[str, object]:
    past, participle, continuous, third_person = regular_forms(base)

    return {
        "forms": {
            "base": base,
            "past": past,
            "past_participle": participle,
            "present_continuous": continuous,
            "third_person_singular": third_person,
        },
        "tenses": {
            "present": base,
            "past": past,
            "future": f"will {base}",
            "present_continuous": f"is {continuous}",
            "present_perfect": f"has {participle}",
        },
        "conjugation": {
            "i": base,
            "you": base,
            "he_she_it": third_person,
            "we": base,
            "they": base,
        },
    }


def plural_form(base: str) -> str:
    if base.endswith(("s", "x", "z", "ch", "sh")):
        return f"{base}es"
    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return f"{base[:-1]}ies"
    if base.endswith("f"):
        return f"{base[:-1]}ves"
    if base.endswith("fe"):
        return f"{base[:-2]}ves"
    return f"{base}s"


def adjective_forms(base: str) -> Tuple[str, str]:
    if len(base) <= 2:
        return f"more {base}", f"most {base}"
    if base.endswith("y") and base[-2] not in "aeiou":
        return f"{base[:-1]}ier", f"{base[:-1]}iest"
    if base.endswith("e"):
        return f"{base}r", f"{base}st"
    if len(base) <= 6:
        return f"{base}er", f"{base}est"
    return f"more {base}", f"most {base}"


def build_inflection_entry(base: str, synset) -> Dict[str, object]:
    pos = POS_NAMES.get(synset.pos(), "word")

    if pos == "verb":
        return build_grammar_entry(base)

    if pos == "noun":
        plural = plural_form(base)
        return {
            "forms": {
                "base": base,
                "singular": base,
                "plural": plural,
            },
            "grammar": {
                "part_of_speech": "noun",
                "number": ["singular", "plural"],
            },
            "usage": {
                "subject_example": f"the {base}",
                "plural_example": f"many {plural}",
            },
        }

    if pos == "adjective":
        comparative, superlative = adjective_forms(base)
        return {
            "forms": {
                "base": base,
                "comparative": comparative,
                "superlative": superlative,
            },
            "grammar": {
                "part_of_speech": "adjective",
                "degree": ["positive", "comparative", "superlative"],
            },
            "usage": {
                "modifier_example": f"{base} example",
            },
        }

    return {
        "forms": {
            "base": base,
        },
        "grammar": {
            "part_of_speech": pos,
        },
        "usage": {
            "example": f"use {base} in context",
        },
    }


def add_entries() -> Dict[str, int]:
    main_dictionary = load_json(MAIN_FILE)
    connections = load_json(CONNECTIONS_FILE)
    grammar = load_json(GRAMMAR_FILE)

    existing_main_words = {
        entry.get("word", "").lower()
        for entry in main_dictionary
        if isinstance(entry, dict)
    }
    existing_connections = {str(key).lower() for key in connections}
    existing_grammar = {str(key).lower() for key in grammar}

    synsets_by_word, word_scores = first_synset_by_word()
    candidate_words = sorted(
        synsets_by_word,
        key=lambda word: (-word_scores.get(word, 0), word),
    )

    added_main_words: List[str] = []
    for word in candidate_words:
        if len(added_main_words) >= ADD_COUNT:
            break
        if word in existing_main_words:
            continue

        main_dictionary.append(build_main_entry(word, synsets_by_word[word]))
        existing_main_words.add(word)
        added_main_words.append(word)

    if len(added_main_words) < ADD_COUNT:
        raise RuntimeError(f"Only added {len(added_main_words)} main entries.")

    added_connections = 0
    for word in added_main_words:
        if word in existing_connections:
            continue

        values = related_words(word, synsets_by_word[word])
        if values:
            connections[word] = values
            existing_connections.add(word)
            added_connections += 1

    if added_connections < ADD_COUNT:
        for word in candidate_words:
            if added_connections >= ADD_COUNT:
                break
            if word in existing_connections:
                continue
            values = related_words(word, synsets_by_word[word])
            if not values:
                continue
            connections[word] = values
            existing_connections.add(word)
            added_connections += 1

    if added_connections < ADD_COUNT:
        raise RuntimeError(f"Only added {added_connections} connection entries.")

    added_grammar = 0
    verb_words = []
    for synset in wn.all_synsets("v"):
        for lemma in synset.lemmas():
            word = clean_word(lemma.name())
            if is_good_wordnet_entry(word, synset):
                verb_words.append((word, lemma.count()))

    sorted_verb_words = [
        word
        for word, _score in sorted(
            verb_words,
            key=lambda item: (-item[1], item[0]),
        )
    ]

    for base in unique_keep_order(sorted_verb_words, ADD_COUNT * 3):
        if added_grammar >= ADD_COUNT:
            break
        if base in existing_grammar:
            continue

        grammar[base] = build_grammar_entry(base)
        existing_grammar.add(base)
        added_grammar += 1

    if added_grammar < ADD_COUNT:
        for base in candidate_words:
            if added_grammar >= ADD_COUNT:
                break
            if base in existing_grammar:
                continue

            grammar[base] = build_inflection_entry(base, synsets_by_word[base])
            existing_grammar.add(base)
            added_grammar += 1

    if added_grammar < ADD_COUNT:
        raise RuntimeError(f"Only added {added_grammar} grammar entries.")

    save_json(MAIN_FILE, main_dictionary)
    save_json(CONNECTIONS_FILE, connections)
    save_json(GRAMMAR_FILE, grammar)

    return {
        "main_added": len(added_main_words),
        "connections_added": added_connections,
        "grammar_added": added_grammar,
        "main_total": len(main_dictionary),
        "connections_total": len(connections),
        "grammar_total": len(grammar),
    }


if __name__ == "__main__":
    print(json.dumps(add_entries(), ensure_ascii=False, indent=2))
