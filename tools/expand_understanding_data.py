import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "UnderstandingDk" / "data"
MAIN_FILE = DATA_DIR / "main_dictionary.json"
GRAMMAR_FILE = DATA_DIR / "Grammar_dictionary.json"
CONNECTIONS_FILE = DATA_DIR / "Connections_Dictionary.json"


DOMAINS = [
    "ai",
    "code",
    "data",
    "memory",
    "logic",
    "math",
    "science",
    "language",
    "security",
    "vision",
    "voice",
    "game",
    "story",
    "world",
    "research",
    "planning",
    "learning",
    "network",
    "system",
    "creative",
    "robot",
    "sensor",
    "cloud",
    "database",
    "interface",
    "analysis",
    "translation",
    "dictionary",
    "grammar",
    "history",
    "geography",
    "emotion",
    "safety",
    "health",
    "physics",
    "chemistry",
    "biology",
    "music",
    "art",
    "law",
    "economy",
    "weather",
    "space",
    "energy",
    "engineer",
    "teacher",
    "student",
    "assistant",
    "conversation",
    "knowledge",
    "fact",
    "sourcecheck",
    "timeline",
    "map",
    "gps",
    "internet",
    "archive",
    "article",
    "book",
    "library",
    "museum",
    "policy",
    "ethics",
    "quality",
    "performance",
    "storage",
    "runtime",
    "compiler",
    "syntax",
    "semantic",
    "dialogue",
    "intentdetect",
    "topicmodel",
    "summary",
    "explanation",
    "comparison",
    "prediction",
    "classification",
    "simulation",
    "calculation",
    "automation",
    "workflow",
    "pipeline",
    "monitor",
    "logger",
    "dashboard",
    "reporting",
    "metadata",
    "dataset",
    "feature",
    "label",
    "embedding",
    "neural",
    "symbolic",
    "hybrid",
    "planner",
    "executor",
    "reviewer",
    "auditor",
    "guardian",
    "translator",
    "speaker",
    "listener",
    "reader",
    "writer",
]


CONCEPTS = [
    "agent",
    "model",
    "signal",
    "pattern",
    "engine",
    "module",
    "context",
    "response",
    "request",
    "intent",
    "topic",
    "token",
    "vector",
    "graph",
    "node",
    "flow",
    "state",
    "memory",
    "rule",
    "score",
    "source",
    "plan",
    "task",
    "result",
    "check",
    "index",
    "search",
    "filter",
    "parser",
    "builder",
    "runner",
    "loader",
    "writer",
    "reader",
    "manager",
    "router",
    "validator",
    "generator",
    "tracker",
    "profile",
    "dataset",
    "record",
    "entry",
    "field",
    "attribute",
    "entity",
    "relation",
    "meaning",
    "definition",
    "example",
    "synonym",
    "antonym",
    "idiom",
    "slang",
    "unit",
    "emoji",
    "abbreviation",
    "term",
    "translation",
    "language",
    "grammar",
    "tense",
    "sentence",
    "paragraph",
    "document",
    "article",
    "source",
    "citation",
    "evidence",
    "confidence",
    "reliability",
    "accuracy",
    "safety",
    "risk",
    "warning",
    "policy",
    "permission",
    "command",
    "operation",
    "function",
    "class",
    "object",
    "method",
    "variable",
    "constant",
    "loop",
    "condition",
    "event",
    "message",
    "packet",
    "request",
    "answer",
    "question",
    "goal",
    "step",
    "dependency",
    "priority",
    "schedule",
    "deadline",
    "version",
    "module",
    "package",
    "library",
    "framework",
    "interface",
    "adapter",
    "connector",
    "plugin",
    "service",
    "endpoint",
    "route",
    "schema",
    "format",
    "template",
    "pattern",
    "strategy",
    "workflow",
    "pipeline",
    "cache",
    "storage",
    "backup",
    "restore",
    "monitor",
    "metric",
    "log",
    "trace",
    "debug",
    "test",
    "assertion",
    "result",
    "output",
    "input",
    "signal",
    "noise",
    "feature",
    "label",
    "cluster",
    "embedding",
    "vector",
    "matrix",
    "probability",
    "estimate",
    "forecast",
    "simulation",
    "calculation",
    "equation",
    "formula",
]


VERB_ROOTS = [
    "analyze",
    "build",
    "check",
    "create",
    "detect",
    "filter",
    "generate",
    "learn",
    "manage",
    "plan",
    "process",
    "read",
    "reason",
    "search",
    "store",
    "test",
    "track",
    "update",
    "validate",
    "write",
    "connect",
    "convert",
    "classify",
    "compare",
    "compose",
    "compress",
    "expand",
    "extract",
    "format",
    "measure",
    "merge",
    "normalize",
    "organize",
    "predict",
    "rank",
    "review",
    "score",
    "select",
    "summarize",
    "verify",
    "adapt",
    "answer",
    "audit",
    "cache",
    "calculate",
    "clean",
    "combine",
    "compile",
    "complete",
    "count",
    "debug",
    "decide",
    "describe",
    "design",
    "download",
    "edit",
    "encode",
    "evaluate",
    "explain",
    "fetch",
    "guard",
    "identify",
    "import",
    "improve",
    "inspect",
    "interpret",
    "label",
    "link",
    "listen",
    "load",
    "map",
    "match",
    "monitor",
    "parse",
    "protect",
    "publish",
    "query",
    "recommend",
    "record",
    "refine",
    "reject",
    "render",
    "repair",
    "reply",
    "resolve",
    "route",
    "save",
    "schedule",
    "simulate",
    "speak",
    "split",
    "sync",
    "translate",
    "upload",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def regular_forms(verb):
    if verb.endswith("e"):
        past = f"{verb}d"
        continuous = f"{verb[:-1]}ing"
    elif verb.endswith("y"):
        past = f"{verb[:-1]}ied"
        continuous = f"{verb}ing"
    else:
        past = f"{verb}ed"
        continuous = f"{verb}ing"

    return {
        "forms": {
            "base": verb,
            "past": past,
            "past_participle": past,
            "present_continuous": continuous,
        },
        "tenses": {
            "present": verb,
            "past": past,
            "future": f"will {verb}",
        },
        "conjugation": {
            "i": verb,
            "he_she_it": f"{verb}s",
            "we_they": verb,
        },
    }


def build_terms(limit):
    terms = []

    for domain in DOMAINS:
        for concept in CONCEPTS:
            for variant in [
                "",
                "core",
                "advanced",
                "safe",
                "trusted",
                "smart",
                "local",
                "global",
                "dynamic",
                "verified",
            ]:
                word = f"{domain}_{concept}"

                if variant:
                    word = f"{variant}_{word}"

                terms.append(
                    {
                        "word": word,
                        "domain": domain,
                        "concept": concept,
                    }
                )

                if len(terms) == limit:
                    return terms

    return terms


def add_main_dictionary_items(main_data, terms, target_count):
    existing = {
        item.get("word", "").lower()
        for item in main_data
    }

    added = 0

    for term in terms:
        word = term["word"]

        if word in existing:
            continue

        domain = term["domain"]
        concept = term["concept"]

        main_data.append(
            {
                "word": word,
                "type": "noun",
                "meanings": [
                    {
                        "definition": (
                            f"A Canri AI {concept.replace('_', ' ')} "
                            f"related to {domain.replace('_', ' ')}."
                        )
                    }
                ],
            }
        )

        existing.add(word)
        added += 1

        if added == target_count:
            break

    return added


def add_connection_items(connections, terms, target_count):
    added = 0

    for term in terms:
        word = term["word"]

        if word in connections:
            continue

        domain = term["domain"]
        concept = term["concept"]

        connections[word] = [
            domain,
            concept,
            "canri",
            "ai",
            "system",
        ]

        added += 1

        if added == target_count:
            break

    return added


def add_grammar_items(grammar, target_count):
    added = 0

    for root in VERB_ROOTS:
        for domain in DOMAINS:
            for concept in CONCEPTS:
                verb = f"{root}_{domain}_{concept}"

                if verb in grammar:
                    continue

                grammar[verb] = regular_forms(verb)
                added += 1

                if added == target_count:
                    return added

    return added


def main():
    if "--allow-synthetic" not in sys.argv:
        print(
            "This tool is disabled by default because it creates synthetic "
            "Canri template data, not a real language-understanding dictionary."
        )
        print("Use --allow-synthetic only if you intentionally want test noise.")
        return

    target_count = 1000

    if len(sys.argv) > 1:
        numeric_args = [
            arg
            for arg in sys.argv[1:]
            if arg != "--allow-synthetic"
        ]
        if numeric_args:
            target_count = int(numeric_args[0])

    main_data = load_json(MAIN_FILE)
    grammar = load_json(GRAMMAR_FILE)
    connections = load_json(CONNECTIONS_FILE)

    terms = build_terms(target_count * 2)

    main_added = add_main_dictionary_items(
        main_data,
        terms,
        target_count
    )

    connections_added = add_connection_items(
        connections,
        terms,
        target_count
    )

    grammar_added = add_grammar_items(
        grammar,
        target_count
    )

    save_json(MAIN_FILE, main_data)
    save_json(GRAMMAR_FILE, grammar)
    save_json(CONNECTIONS_FILE, connections)

    print(f"main_dictionary.json added: {main_added}")
    print(f"Grammar_dictionary.json added: {grammar_added}")
    print(f"Connections_Dictionary.json added: {connections_added}")
    print(f"main_dictionary.json total: {len(main_data)}")
    print(f"Grammar_dictionary.json total: {len(grammar)}")
    print(f"Connections_Dictionary.json total: {len(connections)}")


if __name__ == "__main__":
    main()
