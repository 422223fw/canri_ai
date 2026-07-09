"""
Data_context.py
Canri AI

Lightweight local DATA search for every brain.

The goal is not to load every giant JSON file into every request. Instead,
this module builds a small cached profile of the data folder and returns
the files that are most relevant to the current user request.
"""

import json
import re
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"

MAX_FULL_READ_BYTES = 2_000_000
MAX_SAMPLE_BYTES = 220_000
MAX_VALUE_MATCHES = 8
SKIP_EXTENSIONS = {".jsonl", ".pyc"}

_DATA_PROFILE_CACHE = None
_DATA_PROFILE_SIGNATURE = None


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about",
    "what", "when", "where", "which", "while", "there", "their", "have",
    "has", "are", "was", "were", "will", "would", "can", "could", "should",
    "you", "your", "how", "why", "who", "its", "not", "also", "does",
    "make", "made", "give", "tell", "explain", "create", "write"
}


DOMAIN_HINTS = {
    "code": ["code", "function", "python", "javascript", "api", "json", "class"],
    "creative": ["creative", "story", "character", "world", "idea", "plot"],
    "game": ["game", "player", "enemy", "inventory", "level", "mechanic"],
    "planner": ["plan", "task", "step", "dependency", "risk", "schedule"],
    "language": ["language", "translate", "translation", "grammar", "synonym", "antonym"],
    "knowledge": ["knowledge", "article", "source", "research", "fact", "wiki"],
    "memory": ["memory", "chat", "conversation", "session"],
    "science": ["science", "physics", "chemistry", "biology", "experiment"],
    "geography": ["geography", "country", "city", "place", "map", "region"],
    "technology": ["technology", "hardware", "software", "cpu", "gpu", "cloud"],
    "vision": ["vision", "image", "photo", "video", "file"],
    "voice": ["voice", "audio", "sound", "recording", "speech"],
    "reasoning": ["reasoning", "logic", "rule", "pattern", "conclusion"],
    "security": ["security", "risk", "safety", "danger", "policy"],
    "math": ["math", "number", "equation", "calculate", "unit"],
}


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value).replace("_", " ").lower()).strip()


def terms_from_text(text, limit=80):
    terms = []
    for word in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", normalize_text(text)):
        word = word.strip("-")
        if not word or word in STOP_WORDS or word in terms:
            continue
        terms.append(word)
        if len(terms) >= limit:
            break
    return terms


def file_signature():
    items = []
    for path in DATA_DIR.glob("*"):
        if not path.is_file() or path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        stat = path.stat()
        items.append((path.name, stat.st_size, int(stat.st_mtime)))
    return tuple(sorted(items))


def compact_json_summary(data):
    if isinstance(data, dict):
        keys = list(data.keys())
        summary = {
            "shape": "object",
            "items": len(data),
            "top_keys": keys[:30],
        }
        sample_values = []
        for key in keys[:20]:
            value = data.get(key)
            if isinstance(value, dict):
                sample_values.extend(list(value.keys())[:8])
            elif isinstance(value, list):
                sample_values.append(f"{key}:list:{len(value)}")
            elif isinstance(value, (str, int, float, bool)):
                sample_values.append(f"{key}:{value}")
        summary["sample"] = sample_values[:80]
        return summary

    if isinstance(data, list):
        summary = {
            "shape": "array",
            "items": len(data),
            "sample": [],
        }
        for item in data[:30]:
            if isinstance(item, dict):
                summary["sample"].extend(list(item.keys())[:10])
                for key in ["word", "name", "title", "type", "category", "field"]:
                    if item.get(key):
                        summary["sample"].append(str(item[key]))
            elif isinstance(item, (str, int, float, bool)):
                summary["sample"].append(str(item))
        summary["sample"] = summary["sample"][:80]
        return summary

    return {
        "shape": type(data).__name__,
        "items": 1,
        "sample": [str(data)[:300]],
    }


def iter_json_text_values(data, path="", limit=500):
    found = []

    def visit(value, current_path):
        if len(found) >= limit:
            return

        if isinstance(value, dict):
            for key, item in list(value.items())[:80]:
                next_path = f"{current_path}.{key}" if current_path else str(key)
                visit(item, next_path)
        elif isinstance(value, list):
            for index, item in enumerate(value[:80]):
                visit(item, f"{current_path}[{index}]")
        elif isinstance(value, (str, int, float, bool)):
            text = str(value)
            if text.strip():
                found.append({
                    "path": current_path,
                    "text": text[:600]
                })

    visit(data, path)
    return found


def search_json_values(data, query_terms, limit=MAX_VALUE_MATCHES):
    matches = []

    for item in iter_json_text_values(data):
        normalized = normalize_text(item["text"])
        score = 0
        matched = []

        for term in query_terms:
            if term in normalized:
                score += 4
                matched.append(term)

        if score:
            matches.append({
                "path": item["path"],
                "score": score,
                "matched_terms": matched[:8],
                "text": item["text"]
            })

    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


def profile_file(path):
    stat = path.stat()
    profile = {
        "file": path.name,
        "path": str(path),
        "bytes": stat.st_size,
        "extension": path.suffix.lower(),
        "terms": terms_from_text(path.stem, limit=40),
        "summary": {
            "shape": "unknown",
            "items": None,
            "sample": []
        }
    }

    if path.suffix.lower() != ".json":
        return profile

    try:
        if stat.st_size <= MAX_FULL_READ_BYTES:
            data = json.loads(path.read_text(encoding="utf-8"))
            summary = compact_json_summary(data)
            profile["summary"] = summary
            profile["terms"].extend(
                terms_from_text(
                    " ".join(str(item) for item in summary.get("top_keys", []) + summary.get("sample", [])),
                    limit=80
                )
            )
        else:
            with path.open("r", encoding="utf-8", errors="replace") as file:
                sample = file.read(MAX_SAMPLE_BYTES)
            profile["summary"] = {
                "shape": "large_json_sample",
                "items": None,
                "sample": terms_from_text(sample, limit=80)
            }
            profile["terms"].extend(profile["summary"]["sample"])
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        profile["summary"]["error"] = "profile_failed"

    profile["terms"] = list(dict.fromkeys(profile["terms"]))[:160]
    return profile


def load_json_for_search(file_name):
    path = DATA_DIR / file_name
    if not path.exists() or path.suffix.lower() != ".json":
        return None
    if path.stat().st_size > MAX_FULL_READ_BYTES:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def build_data_profile(force=False):
    global _DATA_PROFILE_CACHE, _DATA_PROFILE_SIGNATURE

    signature = file_signature()
    if not force and _DATA_PROFILE_CACHE is not None and signature == _DATA_PROFILE_SIGNATURE:
        return _DATA_PROFILE_CACHE

    profiles = []
    for path in sorted(DATA_DIR.glob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        profiles.append(profile_file(path))

    _DATA_PROFILE_CACHE = profiles
    _DATA_PROFILE_SIGNATURE = signature
    return profiles


def detect_domains(query_terms):
    domains = []
    term_set = set(query_terms)
    for domain, hints in DOMAIN_HINTS.items():
        if term_set.intersection(hints):
            domains.append(domain)
    return domains


def search_data_context(query, limit=10):
    query_terms = terms_from_text(query, limit=60)
    domains = detect_domains(query_terms)
    profiles = build_data_profile()
    scored = []

    for profile in profiles:
        file_terms = set(profile.get("terms", []))
        file_name = normalize_text(profile.get("file", ""))
        score = 0

        for term in query_terms:
            if term in file_terms:
                score += 5
            if term in file_name:
                score += 4

        for domain in domains:
            if domain in file_name:
                score += 8
            if any(hint in file_name for hint in DOMAIN_HINTS.get(domain, [])):
                score += 3

        if score <= 0:
            continue

        summary = profile.get("summary", {})
        value_matches = []
        if score > 0:
            data = load_json_for_search(profile.get("file", ""))
            if data is not None:
                value_matches = search_json_values(data, query_terms)
                if value_matches:
                    score += min(sum(item["score"] for item in value_matches), 25)

        scored.append({
            "file": profile.get("file"),
            "bytes": profile.get("bytes"),
            "score": score,
            "shape": summary.get("shape"),
            "items": summary.get("items"),
            "matched_terms": [
                term
                for term in query_terms
                if term in file_terms or term in file_name
            ][:12],
            "sample": summary.get("sample", [])[:20],
            "value_matches": value_matches,
        })

    scored.sort(key=lambda item: (item["score"], item.get("bytes", 0)), reverse=True)
    return {
        "available": bool(scored),
        "query_terms": query_terms,
        "domains": domains,
        "matches": scored[:limit],
        "profiled_files": len(profiles),
        "total_profiled_bytes": sum(item.get("bytes", 0) for item in profiles),
    }


def compact_match_for_brains(match):
    value_matches = []

    for item in match.get("value_matches", [])[:4]:
        if isinstance(item, dict):
            value_matches.append({
                "path": item.get("path"),
                "matched_terms": item.get("matched_terms", [])[:6],
                "text": str(item.get("text", ""))[:260]
            })
        else:
            value_matches.append(str(item)[:260])

    return {
        "file": match.get("file"),
        "score": match.get("score", 0),
        "shape": match.get("shape"),
        "items": match.get("items"),
        "matched_terms": match.get("matched_terms", [])[:10],
        "sample": match.get("sample", [])[:10],
        "value_matches": value_matches
    }


def recommended_brains_from_domains(domains):
    mapping = {
        "code": ["Code_brain", "Technology_brain", "Quality_Control_brain"],
        "creative": ["Creative_brain", "Quality_Control_brain"],
        "game": ["Game_brain", "Creative_brain", "Quality_Control_brain"],
        "planner": ["Planner_brain", "Reasoning_brain"],
        "language": ["Language_brain", "Spelling_brain"],
        "knowledge": ["Research_brain", "Fact_Check_brain"],
        "memory": ["Memory_brain"],
        "science": ["Science_brain", "Research_brain", "Fact_Check_brain"],
        "geography": ["Geography_brain", "Research_brain"],
        "technology": ["Technology_brain", "Research_brain"],
        "vision": ["Vision_brain", "Security_brain"],
        "voice": ["Voice_brain", "Vision_brain"],
        "reasoning": ["Reasoning_brain", "Quality_Control_brain"],
        "security": ["Security_brain", "Fact_Check_brain"],
        "math": ["Math_brain", "Reasoning_brain", "Quality_Control_brain"],
    }

    brains = []
    for domain in domains:
        brains.extend(mapping.get(domain, []))

    return list(dict.fromkeys(brains))


def build_context_pack(context, query):
    matches = context.get("matches", [])
    domains = context.get("domains", [])
    compact_matches = [
        compact_match_for_brains(match)
        for match in matches[:8]
        if isinstance(match, dict)
    ]
    top_score = compact_matches[0]["score"] if compact_matches else 0

    evidence_snippets = []
    for match in compact_matches:
        for value in match.get("value_matches", [])[:3]:
            if isinstance(value, dict) and value.get("text"):
                evidence_snippets.append({
                    "file": match.get("file"),
                    "path": value.get("path"),
                    "text": value.get("text"),
                    "matched_terms": value.get("matched_terms", [])
                })
        if len(evidence_snippets) >= 10:
            break

    return {
        "query": query,
        "key_terms": context.get("query_terms", [])[:30],
        "domains": domains,
        "data_sources": compact_matches,
        "evidence_snippets": evidence_snippets[:10],
        "recommended_brains": recommended_brains_from_domains(domains),
        "confidence": min(95, 35 + top_score) if compact_matches else 0,
        "usage_policy": [
            "Use local DATA as supporting context, not as the only truth source.",
            "Prefer exact value_matches over broad file-name matches.",
            "If facts are important or high risk, send the result to Fact_Check_brain.",
            "If the DATA is weak or missing, ask Research_brain or Knowledge_collector for stronger context."
        ]
    }


def build_shared_data_context(query, limit=12):
    context = search_data_context(query, limit=limit)
    context["context_pack"] = build_context_pack(context, query)
    return context


def best_data_sources(query, limit=5):
    context = build_shared_data_context(query, limit=limit)
    return [
        {
            "name": match["file"],
            "source_type": "local_data_json",
            "trust_score": min(85, 55 + match.get("score", 0)),
            "supports": match.get("matched_terms", []),
            "notes": f"Local Canri data file. Shape: {match.get('shape')}, items: {match.get('items')}",
            "sample": match.get("value_matches") or match.get("sample", [])
        }
        for match in context.get("matches", [])[:limit]
    ]
