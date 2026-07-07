import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

PATTERNS_FILE = DATA_DIR / "Reasoning_patterns.json"
RULES_FILE = DATA_DIR / "Reasoning_rules.json"
STATS_FILE = DATA_DIR / "Reasoning_statistics.json"


DOMAINS = [
    "code", "science", "language", "geography", "technology",
    "history", "math", "game", "story", "security"
]

INTENTS = [
    "question", "code_generation", "research", "translation", "explanation",
    "debugging", "learning", "comparison", "planning", "creative_creation"
]

MODES = [
    "deductive", "inductive", "causal", "comparative", "diagnostic",
    "step_by_step", "constraint_based", "risk_based", "evidence_based", "creative"
]


MODE_STEPS = {
    "deductive": ["list premises", "apply rule", "derive conclusion", "check exception"],
    "inductive": ["collect examples", "find pattern", "estimate confidence", "avoid overclaim"],
    "causal": ["identify cause", "identify effect", "check alternative causes", "rank explanation"],
    "comparative": ["choose criteria", "compare options", "weigh tradeoffs", "select best fit"],
    "diagnostic": ["observe symptom", "list possible causes", "test likely cause", "recommend fix"],
    "step_by_step": ["break problem down", "solve each part", "combine result", "verify"],
    "constraint_based": ["identify constraints", "remove impossible options", "rank valid options", "explain limits"],
    "risk_based": ["identify risk", "estimate severity", "add mitigation", "route to review"],
    "evidence_based": ["collect evidence", "score source strength", "compare claims", "state uncertainty"],
    "creative": ["define goal", "generate options", "filter by constraints", "choose coherent direction"]
}


DOMAIN_BRAINS = {
    "code": ["Planner_brain", "Technology_brain", "Code_brain", "Security_brain"],
    "science": ["Science_brain", "Research_brain", "Fact_Check_brain"],
    "language": ["Language_brain", "Memory_brain"],
    "geography": ["Geography_brain", "Research_brain", "Fact_Check_brain"],
    "technology": ["Technology_brain", "Research_brain", "Security_brain"],
    "history": ["History_brain", "Research_brain", "Fact_Check_brain"],
    "math": ["Math_brain", "Fact_Check_brain"],
    "game": ["Planner_brain", "Game_brain", "Creative_brain", "Code_brain"],
    "story": ["Creative_brain", "Story_brain", "Character_brain", "World_brain"],
    "security": ["Security_brain", "Response_brain"]
}


def difficulty(domain, intent, mode):
    score = 35
    if domain in ["code", "science", "security", "technology"]:
        score += 15
    if intent in ["research", "debugging", "code_generation", "planning"]:
        score += 12
    if mode in ["diagnostic", "constraint_based", "risk_based", "evidence_based"]:
        score += 10
    return min(score, 100)


def build_pattern(index, domain, intent, mode):
    diff = difficulty(domain, intent, mode)
    return {
        "id": f"reasoning_pattern_{index:04d}_{domain}_{intent}_{mode}",
        "domain": domain,
        "intent": intent,
        "mode": mode,
        "trigger_terms": [domain, intent, mode],
        "steps": MODE_STEPS[mode],
        "needed_brains": DOMAIN_BRAINS[domain],
        "difficulty": diff,
        "confidence": 86 if diff < 75 else 78,
        "quality_checks": [
            "premises are explicit",
            "uncertainty is visible",
            "contradictions are not ignored",
            "conclusion follows from available evidence"
        ]
    }


def build_rule(index, pattern):
    mode = pattern["mode"]
    return {
        "id": f"reasoning_rule_{index:04d}_{pattern['domain']}_{pattern['intent']}_{mode}",
        "domain": pattern["domain"],
        "intent": pattern["intent"],
        "mode": mode,
        "if": [
            f"request domain is {pattern['domain']}",
            f"request intent is {pattern['intent']}",
            f"reasoning mode is {mode}"
        ],
        "then": [
            f"use {mode} reasoning",
            "rank claims by evidence strength",
            "mark missing information",
            "send risky or uncertain claims to the right specialist brain"
        ],
        "avoid": [
            "making facts up",
            "hiding contradictions",
            "claiming certainty without evidence"
        ],
        "confidence": pattern["confidence"]
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    patterns = {}
    rules = {}
    index = 1

    for domain, intent, mode in product(DOMAINS, INTENTS, MODES):
        pattern = build_pattern(index, domain, intent, mode)
        patterns[pattern["id"]] = pattern
        rule = build_rule(index, pattern)
        rules[rule["id"]] = rule
        index += 1

    stats = {
        "Reasoning_brain": {
            "patterns": len(patterns),
            "rules": len(rules),
            "last_build": "generated"
        }
    }

    write_json(PATTERNS_FILE, patterns)
    write_json(RULES_FILE, rules)
    write_json(STATS_FILE, stats)

    print(json.dumps({
        "patterns": len(patterns),
        "rules": len(rules)
    }, indent=2))


if __name__ == "__main__":
    main()
