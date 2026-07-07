import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from nltk.corpus import wordnet as wn


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "UnderstandingDk" / "data"
TARGET_COUNT = 10000


POS_TYPES = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}


IRREGULAR_VERBS = {
    "be": ("was", "been", "being", "is"),
    "begin": ("began", "begun", "beginning", "begins"),
    "break": ("broke", "broken", "breaking", "breaks"),
    "bring": ("brought", "brought", "bringing", "brings"),
    "build": ("built", "built", "building", "builds"),
    "buy": ("bought", "bought", "buying", "buys"),
    "catch": ("caught", "caught", "catching", "catches"),
    "choose": ("chose", "chosen", "choosing", "chooses"),
    "come": ("came", "come", "coming", "comes"),
    "do": ("did", "done", "doing", "does"),
    "draw": ("drew", "drawn", "drawing", "draws"),
    "drink": ("drank", "drunk", "drinking", "drinks"),
    "drive": ("drove", "driven", "driving", "drives"),
    "eat": ("ate", "eaten", "eating", "eats"),
    "fall": ("fell", "fallen", "falling", "falls"),
    "feel": ("felt", "felt", "feeling", "feels"),
    "find": ("found", "found", "finding", "finds"),
    "fly": ("flew", "flown", "flying", "flies"),
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
    "pay": ("paid", "paid", "paying", "pays"),
    "put": ("put", "put", "putting", "puts"),
    "read": ("read", "read", "reading", "reads"),
    "run": ("ran", "run", "running", "runs"),
    "say": ("said", "said", "saying", "says"),
    "see": ("saw", "seen", "seeing", "sees"),
    "sell": ("sold", "sold", "selling", "sells"),
    "send": ("sent", "sent", "sending", "sends"),
    "sit": ("sat", "sat", "sitting", "sits"),
    "speak": ("spoke", "spoken", "speaking", "speaks"),
    "stand": ("stood", "stood", "standing", "stands"),
    "take": ("took", "taken", "taking", "takes"),
    "teach": ("taught", "taught", "teaching", "teaches"),
    "tell": ("told", "told", "telling", "tells"),
    "think": ("thought", "thought", "thinking", "thinks"),
    "understand": ("understood", "understood", "understanding", "understands"),
    "wear": ("wore", "worn", "wearing", "wears"),
    "win": ("won", "won", "winning", "wins"),
    "write": ("wrote", "written", "writing", "writes"),
}


def clean_word(value):
    value = str(value).replace("_", " ").lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def safe_key(value):
    return clean_word(value).replace(" ", "_")


def is_plain_english_word(value):
    return bool(re.fullmatch(r"[a-z][a-z\-]{1,24}", value))


def is_plain_english_phrase(value):
    return bool(re.fullmatch(r"[a-z][a-z\-]*( [a-z][a-z\-]*){0,4}", value))


def unique(values, limit):
    result = []
    seen = set()
    for value in values:
        value = clean_word(value)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def verb_forms(base):
    base = clean_word(base)
    parts = base.split(" ")
    first = parts[0]
    rest = " ".join(parts[1:])

    if first in IRREGULAR_VERBS:
        past, past_participle, continuous, third = IRREGULAR_VERBS[first]
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

        past_participle = past

        if first.endswith(("s", "sh", "ch", "x", "z", "o")):
            third = f"{first}es"
        elif first.endswith("y") and len(first) > 1 and first[-2] not in "aeiou":
            third = f"{first[:-1]}ies"
        else:
            third = f"{first}s"

    def join(form):
        return f"{form} {rest}".strip()

    return {
        "forms": {
            "base": base,
            "past": join(past),
            "past_participle": join(past_participle),
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


def collect_word_data():
    words = {}

    for synset in wn.all_synsets():
        pos = synset.pos()
        word_type = POS_TYPES.get(pos, "word")

        for lemma in synset.lemmas():
            raw_word = lemma.name().replace("_", " ")
            if raw_word != raw_word.lower():
                continue

            word = clean_word(lemma.name())
            if not is_plain_english_word(word):
                continue

            bucket = words.setdefault(
                word,
                {
                    "word": word,
                    "type_scores": defaultdict(int),
                    "definitions": [],
                    "definitions_by_type": defaultdict(list),
                    "examples": [],
                    "examples_by_type": defaultdict(list),
                    "synsets": [],
                    "synsets_by_type": defaultdict(list),
                    "frequency": 0,
                },
            )
            bucket["type_scores"][word_type] += max(1, lemma.count())
            bucket["frequency"] += lemma.count()
            bucket["synsets"].append(synset)
            bucket["synsets_by_type"][word_type].append(synset)

            definition = synset.definition().strip()
            if definition and definition not in bucket["definitions"]:
                bucket["definitions"].append(definition)
            if definition and definition not in bucket["definitions_by_type"][word_type]:
                bucket["definitions_by_type"][word_type].append(definition)

            for example in synset.examples():
                if example not in bucket["examples"]:
                    bucket["examples"].append(example)
                if example not in bucket["examples_by_type"][word_type]:
                    bucket["examples_by_type"][word_type].append(example)

    return words


def choose_words(words):
    ranked = sorted(
        words.values(),
        key=lambda item: (
            -item["frequency"],
            -len(item["synsets"]),
            item["word"],
        ),
    )
    return ranked[:TARGET_COUNT]


def build_main_dictionary(selected):
    entries = []

    for item in selected:
        word_type = max(
            item["type_scores"].items(),
            key=lambda pair: pair[1],
        )[0]

        item["selected_type"] = word_type
        definitions = item["definitions_by_type"].get(word_type) or item["definitions"]
        examples = item["examples_by_type"].get(word_type) or item["examples"]

        meanings = [
            {"definition": definition}
            for definition in definitions[:3]
        ]

        if examples:
            meanings[0]["example"] = examples[0]

        entries.append(
            {
                "word": item["word"],
                "type": word_type,
                "meanings": meanings,
            }
        )

    return entries


def build_connections(selected):
    result = {}
    selected_words = {item["word"] for item in selected}

    for item in selected:
        related = []
        word_type = item.get("selected_type")
        synsets = item["synsets_by_type"].get(word_type) or item["synsets"]

        for synset in synsets[:8]:
            related.extend(lemma.name() for lemma in synset.lemmas())

            for hypernym in synset.hypernyms()[:3]:
                related.extend(lemma.name() for lemma in hypernym.lemmas())

            for hyponym in synset.hyponyms()[:3]:
                related.extend(lemma.name() for lemma in hyponym.lemmas())

            for lemma in synset.lemmas():
                related.extend(
                    antonym.name()
                    for antonym in lemma.antonyms()
                )
                related.extend(
                    form.name()
                    for form in lemma.derivationally_related_forms()
                )

        cleaned = [
            value
            for value in unique(related, 12)
            if value != item["word"]
            and (is_plain_english_word(value) or value in selected_words)
        ]

        result[item["word"]] = cleaned

    return result


def build_grammar(selected):
    verbs = []
    seen = set()

    for item in selected:
        if "verb" not in item["type_scores"]:
            continue
        word = item["word"]
        if word in seen or not is_plain_english_word(word):
            continue
        seen.add(word)
        verbs.append(word)

    for synset in wn.all_synsets("v"):
        for lemma in synset.lemmas():
            word = clean_word(lemma.name())
            if word in seen or not is_plain_english_word(word):
                continue
            seen.add(word)
            verbs.append(word)
            if len(verbs) >= TARGET_COUNT:
                break
        if len(verbs) >= TARGET_COUNT:
            break

    if len(verbs) < TARGET_COUNT:
        for synset in wn.all_synsets("v"):
            for lemma in synset.lemmas():
                phrase = clean_word(lemma.name())
                if phrase in seen or " " not in phrase:
                    continue
                if not is_plain_english_phrase(phrase):
                    continue
                seen.add(phrase)
                verbs.append(phrase)
                if len(verbs) >= TARGET_COUNT:
                    break
            if len(verbs) >= TARGET_COUNT:
                break

    grammar = {
        safe_key(verb): verb_forms(verb)
        for verb in verbs[:TARGET_COUNT]
    }

    return grammar


def save_json(name, data):
    path = DATA_DIR / name
    handle, temp_name = tempfile.mkstemp(
        prefix=f"{name}.",
        suffix=".build",
        dir=PROJECT_DIR,
        text=True,
    )
    temp_path = Path(temp_name)

    with os.fdopen(handle, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    temp_path.replace(path)


def remove_extra_files():
    for pattern in ["*.tmp", "*.new"]:
        for path in DATA_DIR.glob(pattern):
            path.unlink()


def main():
    word_data = collect_word_data()
    selected = choose_words(word_data)

    main_dictionary = build_main_dictionary(selected)
    connections = build_connections(selected)
    grammar = build_grammar(selected)

    if len(main_dictionary) != TARGET_COUNT:
        raise RuntimeError(f"main dictionary count is {len(main_dictionary)}")
    if len(connections) != TARGET_COUNT:
        raise RuntimeError(f"connections count is {len(connections)}")
    if len(grammar) != TARGET_COUNT:
        raise RuntimeError(f"grammar count is {len(grammar)}")

    save_json("main_dictionary.json", main_dictionary)
    save_json("Connections_Dictionary.json", connections)
    save_json("Grammar_dictionary.json", grammar)
    remove_extra_files()

    print("main_dictionary.json:", len(main_dictionary))
    print("Connections_Dictionary.json:", len(connections))
    print("Grammar_dictionary.json:", len(grammar))
    print("extra .tmp/.new files removed")


if __name__ == "__main__":
    main()
