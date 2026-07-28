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

try:
    from Scanner_knowledge import search_scanner_knowledge
except Exception:
    search_scanner_knowledge = None


DATA_DIR = Path(__file__).parent / "data"
UNDERSTANDING_DATA_DIR = Path(__file__).parent / "UnderstandingDk" / "data"
DATA_ROOTS = (DATA_DIR, UNDERSTANDING_DATA_DIR)

MAX_FULL_READ_BYTES = 2_000_000
MAX_SAMPLE_BYTES = 220_000
MAX_VALUE_MATCHES = 8
SKIP_EXTENSIONS = {".jsonl", ".pyc"}

_DATA_PROFILE_CACHE = None
_DATA_PROFILE_SIGNATURE = None


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value).replace("_", " ").lower()).strip()


def terms_from_text(text, limit=80):
    terms = []
    for word in re.findall(
        r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF]{1,}",
        normalize_text(text),
    ):
        word = word.strip("-")
        if not word or word in terms:
            continue
        terms.append(word)
        if len(terms) >= limit:
            break
    return terms


def _append_semantic_value(terms, value, limit):
    if isinstance(value, dict):
        for key in ("word", "text", "name", "title", "domain", "value"):
            if value.get(key):
                _append_semantic_value(terms, value[key], limit)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _append_semantic_value(terms, item, limit)
            if len(terms) >= limit:
                return
        return
    for term in terms_from_text(value, limit=limit):
        if term not in terms:
            terms.append(term)
        if len(terms) >= limit:
            return


def terms_from_understanding(understanding, fallback_text="", limit=80):
    """Use Understanding_brain's complete semantic report as retrieval input."""

    report = understanding if isinstance(understanding, dict) else {}
    contract = report.get("request_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    frame = report.get("semantic_frame", {})
    frame = frame if isinstance(frame, dict) else {}
    terms = []

    for tag in report.get("advanced_word_tags", []):
        if not isinstance(tag, dict) or tag.get("is_stop_word"):
            continue
        if tag.get("semantic_tag") in {
            "action", "action_command", "target_or_concept",
            "proper_or_technical_name", "description", "quantity",
        }:
            _append_semantic_value(terms, tag.get("word"), limit)

    for value in (
        report.get("key_terms", []),
        frame.get("main_action"),
        frame.get("main_target"),
        frame.get("targets", []),
        frame.get("modifiers", []),
        contract.get("topic"),
        contract.get("target"),
        contract.get("entities", []),
        contract.get("features", []),
        contract.get("requirements", []),
    ):
        _append_semantic_value(terms, value, limit)
        if len(terms) >= limit:
            break

    if not terms:
        _append_semantic_value(terms, fallback_text, limit)
    return terms[:limit]


def domains_from_understanding(understanding):
    report = understanding if isinstance(understanding, dict) else {}
    contract = report.get("request_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    domains = []
    values = [
        report.get("main_topic"),
        contract.get("topic"),
        *report.get("central_domains", []),
        *contract.get("central_domains", []),
    ]
    for value in values:
        domain = value.get("domain") if isinstance(value, dict) else value
        domain = str(domain or "").strip().lower()
        if domain and domain not in {"unknown", "request", "memory_context"}:
            domains.append(domain)
    return list(dict.fromkeys(domains))[:8]


def file_signature():
    items = []
    for root in DATA_ROOTS:
        if not root.exists():
            continue
        for path in root.glob("*"):
            if not path.is_file() or path.suffix.lower() in SKIP_EXTENSIONS:
                continue
            stat = path.stat()
            items.append((str(path), stat.st_size, int(stat.st_mtime)))
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


def load_json_for_search(path_value):
    path = Path(path_value)
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
    for root in DATA_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.glob("*")):
            if not path.is_file() or path.suffix.lower() in SKIP_EXTENSIONS:
                continue
            profile = profile_file(path)
            profile["source_group"] = (
                "understanding_dictionaries"
                if root == UNDERSTANDING_DATA_DIR
                else "canri_data"
            )
            profiles.append(profile)

    _DATA_PROFILE_CACHE = profiles
    _DATA_PROFILE_SIGNATURE = signature
    return profiles


def search_data_context(query, limit=10, understanding=None):
    query_terms = terms_from_understanding(understanding, query, limit=60)
    domains = domains_from_understanding(understanding)
    profiles = build_data_profile()
    scored = []
    document_frequency = {
        term: sum(
            1
            for profile in profiles
            if term in set(profile.get("terms", []))
            or term in normalize_text(profile.get("file", ""))
        )
        for term in query_terms
    }

    for profile in profiles:
        file_terms = set(profile.get("terms", []))
        file_name = normalize_text(profile.get("file", ""))
        score = 0

        for term in query_terms:
            rarity = max(1, min(8, len(profiles) // max(1, document_frequency.get(term, 1))))
            if term in file_terms:
                score += 3 + rarity
            if term in file_name:
                score += 5 + rarity

        for domain in domains:
            if domain in file_name:
                score += 8
            if domain in file_terms:
                score += 5

        if score <= 0:
            continue

        summary = profile.get("summary", {})
        value_matches = []
        if score > 0:
            data = load_json_for_search(profile.get("path", ""))
            if data is not None:
                value_matches = search_json_values(data, query_terms)
                if value_matches:
                    score += min(sum(item["score"] for item in value_matches), 25)

        scored.append({
            "file": profile.get("file"),
            "source_group": profile.get("source_group"),
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
        "semantic_source": (
            "Understanding_brain.request_contract"
            if isinstance(understanding, dict) and understanding
            else "text_fallback_without_domain_inference"
        ),
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
        "source_group": match.get("source_group"),
        "score": match.get("score", 0),
        "shape": match.get("shape"),
        "items": match.get("items"),
        "matched_terms": match.get("matched_terms", [])[:10],
        "sample": match.get("sample", [])[:10],
        "value_matches": value_matches
    }


def build_context_pack(context, query, understanding=None):
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
        "scanner_evidence": context.get("scanner_matches", [])[:8],
        "recommended_brains": list(dict.fromkeys(
            str(item)
            for item in (
                understanding.get("routing_hints", [])
                if isinstance(understanding, dict) else []
            )
            if str(item).endswith("_brain")
        )),
        "confidence": min(95, 35 + top_score) if compact_matches else 0,
        "usage_policy": [
            "Use local DATA as supporting context, not as the only truth source.",
            "Prefer exact value_matches over broad file-name matches.",
            "If facts are important or high risk, send the result to Fact_Check_brain.",
            "If the DATA is weak or missing, ask Research_brain or Knowledge_collector for stronger context."
        ]
    }


def build_shared_data_context(query, limit=12, understanding=None):
    context = search_data_context(query, limit=limit, understanding=understanding)
    if search_scanner_knowledge is not None:
        try:
            context["scanner_matches"] = search_scanner_knowledge(
                query,
                limit=min(10, max(4, int(limit)))
            )
        except Exception:
            context["scanner_matches"] = []
    else:
        context["scanner_matches"] = []
    context["understanding_contract"] = (
        understanding.get("request_contract", {})
        if isinstance(understanding, dict) else {}
    )
    context["context_pack"] = build_context_pack(context, query, understanding)
    return context


def context_view_for_brain(context, brain_name, max_sources=6):
    """Return a compact, domain-filtered view without losing the full context."""

    if not isinstance(context, dict):
        return {}

    if brain_name == "Creative_brain":
        max_sources = max(max_sources, 12)

    matches = []
    for match in context.get("matches", []):
        if not isinstance(match, dict):
            continue
        file_name = normalize_text(match.get("file", ""))
        if brain_name == "Creative_brain" and any(
            marker in file_name
            for marker in [" rule", " rules", "risk rule", "safety rule", "release criteria"]
        ):
            continue
        matches.append(compact_match_for_brains(match))
        if len(matches) >= max_sources:
            break

    if not matches and context.get("matches"):
        matches = [
            compact_match_for_brains(item)
            for item in context.get("matches", [])[:2]
            if isinstance(item, dict)
        ]

    evidence = []
    for match in matches:
        for item in match.get("value_matches", [])[:2]:
            if isinstance(item, dict) and item.get("text"):
                evidence.append({
                    "file": match.get("file"),
                    "path": item.get("path"),
                    "text": str(item.get("text", ""))[:260],
                    "matched_terms": item.get("matched_terms", [])[:6]
                })

    return {
        "available": bool(matches),
        "brain": brain_name,
        "query_terms": context.get("query_terms", [])[:30],
        "domains": context.get("domains", [])[:12],
        "understanding_contract": context.get("understanding_contract", {}),
        "matches": matches,
        "evidence_snippets": evidence[:8],
        "scanner_matches": [
            {
                "article_id": item.get("article_id") or item.get("record_id"),
                "collection": item.get("collection", "trusted_knowledge"),
                "title": item.get("title"),
                "summary": str(item.get("summary", ""))[:700],
                "content_excerpt": str(item.get("content_excerpt", ""))[:1200],
                "trust_score": item.get("trust_score", 0),
                "score": item.get("score", 0),
                "url": item.get("url"),
                "source_type": item.get("source_type"),
                "source_count": item.get("source_count", len(item.get("sources", []))),
                "sources": item.get("sources", [])[:3],
                "metadata": item.get("metadata", {}),
                "source_quality_policy": item.get("source_quality_policy", {}),
            }
            for item in context.get("scanner_matches", [])[:max_sources]
            if isinstance(item, dict)
        ],
        "scanner_usage_contract": {
            "received_by_every_brain": True,
            "must_consider_relevant_matches": True,
            "must_ignore_irrelevant_matches": True,
            "must_preserve_source_metadata": True,
            "must_fact_check_high_stakes_claims": True,
            "retrieval_mode": "indexed_relevant_excerpts_only"
        },
        "scanner_context_received": True,
        "profiled_files": context.get("profiled_files", 0),
        "total_profiled_bytes": context.get("total_profiled_bytes", 0),
        "selection_policy": "domain_filtered_lazy_context",
        "ranking_policy": "understanding_ranked_relevant_excerpts",
        "full_context_available_to_manager": True
    }


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
