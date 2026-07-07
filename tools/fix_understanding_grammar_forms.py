import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_FILE = ROOT / "main_ai_canri" / "UnderstandingDk" / "data" / "Grammar_dictionary.json"


IRREGULAR_FIXES = {
    "open": ("opened", "opened", "opening"),
    "spin": ("spun", "spun", "spinning"),
    "begin": ("began", "begun", "beginning"),
    "run": ("ran", "run", "running"),
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


def fix_regular_false_double_n(base, entry):
    forms = entry.get("forms", {})
    if not isinstance(forms, dict):
        return False

    past = forms.get("past", "")
    continuous = forms.get("present_continuous", "")

    if (
        len(base) > 4
        and base.endswith(("en", "on"))
        and past == f"{base}ned"
    ):
        forms["past"] = f"{base}ed"
        forms["past_participle"] = f"{base}ed"
        if continuous == f"{base}ning":
            forms["present_continuous"] = f"{base}ing"

        tenses = entry.get("tenses", {})
        if isinstance(tenses, dict):
            if tenses.get("past") == past:
                tenses["past"] = forms["past"]
            if tenses.get("present_continuous") == f"is {continuous}":
                tenses["present_continuous"] = f"is {forms['present_continuous']}"

        return True

    return False


def fix_irregular(base, entry):
    if base not in IRREGULAR_FIXES:
        return False

    past, participle, continuous = IRREGULAR_FIXES[base]
    forms = entry.setdefault("forms", {})
    forms["past"] = past
    forms["past_participle"] = participle
    forms["present_continuous"] = continuous

    tenses = entry.setdefault("tenses", {})
    tenses["past"] = past
    if "present_continuous" in tenses:
        tenses["present_continuous"] = f"is {continuous}"
    if "present_perfect" in tenses:
        tenses["present_perfect"] = f"has {participle}"

    return True


def main():
    grammar = load_json(GRAMMAR_FILE)
    changed = 0

    for base, entry in grammar.items():
        if not isinstance(entry, dict):
            continue
        if fix_irregular(base, entry):
            changed += 1
        if fix_regular_false_double_n(base, entry):
            changed += 1

    write_json(GRAMMAR_FILE, grammar)
    print(json.dumps({"changed": changed, "grammar_total": len(grammar)}, indent=2))


if __name__ == "__main__":
    main()
