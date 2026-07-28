"""Unified indexed retrieval and lifecycle helpers for all Canri scanners."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

from Web_scanner_core import DATA_DIR, IndexedJsonlStore, load_json

try:
    from Knowledge_collector import search_knowledge
except Exception:
    search_knowledge = None

try:
    import UnderstandingDk as understanding_dictionary
except Exception:
    understanding_dictionary = None


COLLECTIONS = {
    "product": {
        "database": DATA_DIR / "product_scan_database.jsonl",
        "index": DATA_DIR / "product_scan_index.sqlite3",
        "sources": DATA_DIR / "Product_scan_sources.json",
        "max_bytes": 512 * 1024 * 1024,
    },
    "code": {
        "database": DATA_DIR / "code_scan_database.jsonl",
        "index": DATA_DIR / "code_scan_index.sqlite3",
        "sources": DATA_DIR / "Code_scan_sources.json",
        "max_bytes": 2 * 1024 * 1024 * 1024,
    },
    "general": {
        "database": DATA_DIR / "general_scan_database.jsonl",
        "index": DATA_DIR / "general_scan_index.sqlite3",
        "sources": DATA_DIR / "General_scan_sources.json",
        "max_bytes": 2 * 1024 * 1024 * 1024,
    },
}

_STORES: dict[str, IndexedJsonlStore] = {}
_RUNNING_SCANNERS = []


def _semantic_tokens(value: object) -> list[str]:
    """Tokenize retrieval text without maintaining a second domain dictionary."""

    return list(dict.fromkeys(
        token.casefold()
        for token in re.findall(
            r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']+",
            str(value or ""),
        )
        if len(token.strip("-'")) > 1
    ))


def _query_expansion(query_terms: list[str], limit: int = 36) -> tuple[list[str], dict[str, list[str]]]:
    """Expand query concepts from Canri's dictionary meanings and graph links."""

    if understanding_dictionary is None:
        return [], {}
    expanded = []
    by_term = {}
    for term in query_terms:
        term_expansion = []
        try:
            meanings = understanding_dictionary.get_meanings(term)[:3]
            connections = understanding_dictionary.related(term)[:8]
        except Exception:
            continue
        for value in [*meanings, *connections]:
            for candidate in _semantic_tokens(value):
                if candidate in query_terms or candidate in expanded:
                    continue
                if len(candidate) < 4:
                    continue
                try:
                    entries = understanding_dictionary.search_word(candidate)
                except Exception:
                    entries = []
                if not entries or not any(
                    str(entry.get("type", "")).lower() in {
                        "noun", "verb", "adjective", "adverb",
                    }
                    for entry in entries
                    if isinstance(entry, dict)
                ):
                    continue
                expanded.append(candidate)
                term_expansion.append(candidate)
                if len(expanded) >= limit:
                    by_term[term] = term_expansion
                    return expanded, by_term
        if term_expansion:
            by_term[term] = term_expansion
    return expanded, by_term


def _rerank_matches(query: str, matches: list[dict]) -> list[dict]:
    """Rerank index hits by actual request coverage and title specificity."""

    query_terms = _semantic_tokens(query)
    if not query_terms:
        return matches
    semantic_expansion, expansion_by_term = _query_expansion(query_terms)

    documents = []
    for item in matches:
        title = str(item.get("title") or "")
        body = " ".join([
            str(item.get("summary") or ""),
            str(item.get("content_excerpt") or ""),
        ])
        documents.append({
            "item": item,
            "title_terms": set(_semantic_tokens(title)),
            "body_terms": set(_semantic_tokens(body)),
            "title_text": " ".join(title.casefold().split()),
            "body_text": " ".join(body.casefold().split()),
        })

    document_frequency = {
        term: sum(
            1
            for document in documents
            if term in document["title_terms"] or term in document["body_terms"]
        )
        for term in query_terms
    }
    count = max(len(documents), 1)
    normalized_query = " ".join(str(query or "").casefold().split())
    ranked = []

    for document in documents:
        item = dict(document["item"])
        title_hits = [term for term in query_terms if term in document["title_terms"]]
        body_hits = [term for term in query_terms if term in document["body_terms"]]
        matched = list(dict.fromkeys(title_hits + body_hits))
        expanded_title_hits = [
            term for term in semantic_expansion
            if term in document["title_terms"]
        ]
        expanded_body_hits = [
            term for term in semantic_expansion
            if term in document["body_terms"]
        ]
        weighted_title = 0.0
        weighted_body = 0.0
        for term in title_hits:
            rarity = math.log((count + 1) / (document_frequency.get(term, 0) + 1)) + 1.0
            weighted_title += rarity * 12.0
        for term in body_hits:
            if term in title_hits:
                continue
            rarity = math.log((count + 1) / (document_frequency.get(term, 0) + 1)) + 1.0
            weighted_body += rarity * 3.0

        semantic_score = min(
            32.0,
            len(expanded_title_hits) * 6.0
            + len(set(expanded_body_hits) - set(expanded_title_hits)) * 5.0,
        )
        unsupported_title_senses = [
            term
            for term in title_hits
            if expansion_by_term.get(term)
            and not set(expansion_by_term[term]).intersection(document["body_terms"])
        ]
        sense_penalty = min(len(unsupported_title_senses) * 16.0, 32.0)

        phrase_bonus = 0.0
        if normalized_query and normalized_query in document["title_text"]:
            phrase_bonus = 30.0
        elif normalized_query and normalized_query in document["body_text"]:
            phrase_bonus = 12.0
        coverage = len(matched) / max(len(query_terms), 1)
        base_score = min(float(item.get("score") or 0), 40.0) * 0.35
        trust_score = float(item.get("trust_score") or 0) * 0.03
        relevance = (
            base_score
            + trust_score
            + weighted_title
            + weighted_body
            + semantic_score
            + phrase_bonus
            + coverage * 16.0
            - sense_penalty
        )
        if not matched:
            relevance -= 30.0

        item["unified_score"] = round(relevance, 2)
        item["retrieval_relevance"] = {
            "query_terms": query_terms,
            "matched_terms": matched,
            "title_matches": title_hits,
            "dictionary_expansion_matches": list(dict.fromkeys(
                expanded_title_hits + expanded_body_hits
            ))[:16],
            "unsupported_title_senses": unsupported_title_senses,
            "coverage": round(coverage * 100.0, 2),
            "phrase_match": bool(phrase_bonus),
            "ranking": "title_specificity_query_coverage_rarity_trust",
        }
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item.get("unified_score", 0),
            item.get("trust_score", 0),
        ),
        reverse=True,
    )
    return ranked


def _store(collection: str, create: bool = False) -> IndexedJsonlStore | None:
    spec = COLLECTIONS.get(collection)
    if not spec:
        return None
    if collection in _STORES:
        return _STORES[collection]
    if not create and (not spec["index"].exists() or not spec["database"].exists()):
        return None
    store = IndexedJsonlStore(
        collection,
        spec["database"],
        spec["index"],
        max_database_bytes=spec["max_bytes"],
    )
    _STORES[collection] = store
    return store


def normalize_collections(collections: Iterable[str] | None) -> list[str]:
    if collections is None:
        return ["trusted_knowledge", "product", "code", "general"]
    return list(dict.fromkeys(
        str(collection).lower()
        for collection in collections
        if str(collection).lower() in {"trusted_knowledge", *COLLECTIONS}
    ))


def search_scanner_knowledge(
    query: str,
    limit: int = 8,
    collections: Iterable[str] | None = None,
) -> list[dict]:
    """Search small indexes only; never load the scanner JSONL databases in full."""

    selected = normalize_collections(collections)
    per_collection = max(2, min(8, int(limit)))
    matches = []
    if "trusted_knowledge" in selected and search_knowledge is not None:
        try:
            for item in search_knowledge(query, limit=per_collection):
                if isinstance(item, dict):
                    normalized = dict(item)
                    normalized.setdefault("collection", "trusted_knowledge")
                    normalized.setdefault("source_type", "curated_knowledge_database")
                    matches.append(normalized)
        except Exception:
            pass

    for collection in selected:
        if collection == "trusted_knowledge":
            continue
        store = _store(collection, create=False)
        if store is None:
            continue
        try:
            matches.extend(store.search(query, limit=per_collection))
        except Exception:
            continue

    unique_matches = []
    seen = set()
    for item in matches:
        identity = (
            str(item.get("url") or "").lower(),
            str(item.get("title") or "").lower(),
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique_matches.append(dict(item))
    ranked = _rerank_matches(query, unique_matches)
    return ranked[:max(1, int(limit))]


def scanner_matches(data, limit=5, collections=None):
    if not isinstance(data, dict):
        return []
    scanner = data.get("scanner_knowledge", {})
    if isinstance(scanner, dict) and isinstance(scanner.get("matches"), list):
        matches = [item for item in scanner["matches"] if isinstance(item, dict)]
    else:
        knowledge = data.get("knowledge_context") or data.get("knowledge") or {}
        matches = (
            [item for item in knowledge.get("matches", []) if isinstance(item, dict)]
            if isinstance(knowledge, dict)
            else []
        )
    wanted = set(normalize_collections(collections)) if collections is not None else set()
    if wanted:
        matches = [item for item in matches if item.get("collection") in wanted]
    return matches[:limit]


def scanner_evidence(data, limit=5, collections=None):
    evidence = []
    for item in scanner_matches(data, limit=limit, collections=collections):
        sources = item.get("sources", [])
        evidence.append({
            "article_id": item.get("article_id") or item.get("record_id"),
            "collection": item.get("collection", "trusted_knowledge"),
            "title": item.get("title"),
            "text": (
                str(item.get("content_excerpt", "")).strip()
                or str(item.get("summary", "")).strip()
            ),
            "summary": str(item.get("summary", "")).strip(),
            "url": item.get("url"),
            "source_type": item.get("source_type"),
            "trust_score": item.get("trust_score", 0),
            "source_count": item.get("source_count", len(sources)),
            "sources": sources[:3],
            "metadata": item.get("metadata", {}),
        })
    return evidence


def scanner_source_ids(data, limit=5):
    return list(dict.fromkeys(
        source.get("source_id")
        for item in scanner_evidence(data, limit=limit)
        for source in item.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    ))


def scanner_status() -> dict:
    collections = {}
    for name, spec in COLLECTIONS.items():
        source_config = load_json(spec["sources"], {})
        store = _store(name, create=False)
        collections[name] = {
            "targets_configured": len(source_config.get("targets", [])),
            "database_exists": spec["database"].exists(),
            "index_exists": spec["index"].exists(),
            "database_bytes": store.database_bytes() if store else 0,
            "records_indexed": store.count() if store else 0,
            "max_database_bytes": spec["max_bytes"],
            "source_quality_policy": source_config.get("source_quality_policy", {}),
        }
    return {"collections": collections, "indexed_retrieval": True}


def start_background_web_scanners() -> list:
    global _RUNNING_SCANNERS
    if _RUNNING_SCANNERS:
        return list(_RUNNING_SCANNERS)
    starters = []
    try:
        from Product_scanner import start_background_product_scanner
        starters.append(start_background_product_scanner)
    except Exception:
        pass
    try:
        from Code_knowledge_scanner import start_background_code_scanner
        starters.append(start_background_code_scanner)
    except Exception:
        pass
    try:
        from General_web_scanner import start_background_general_scanner
        starters.append(start_background_general_scanner)
    except Exception:
        pass
    for starter in starters:
        try:
            scanner = starter()
            if scanner is not None:
                _RUNNING_SCANNERS.append(scanner)
        except Exception:
            continue
    return list(_RUNNING_SCANNERS)


def stop_background_web_scanners() -> None:
    for scanner in list(_RUNNING_SCANNERS):
        try:
            scanner.stop()
        except Exception:
            pass
