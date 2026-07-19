"""Unified indexed retrieval and lifecycle helpers for all Canri scanners."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from Web_scanner_core import DATA_DIR, IndexedJsonlStore, load_json, text_terms

try:
    from Knowledge_collector import search_knowledge
except Exception:
    search_knowledge = None


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

    query_terms = set(text_terms(query, limit=30))
    preferred = set()
    if query_terms.intersection({
        "code", "python", "api", "function", "class", "library", "package",
        "github", "async", "database", "hardware", "sensor", "arduino",
    }):
        preferred.add("code")
    if query_terms.intersection({
        "product", "company", "device", "phone", "laptop", "gpu", "service",
    }):
        preferred.add("product")

    ranked = []
    seen = set()
    for item in matches:
        identity = (
            str(item.get("url") or "").lower(),
            str(item.get("title") or "").lower(),
        )
        if identity in seen:
            continue
        seen.add(identity)
        score = float(item.get("score") or 0)
        score += float(item.get("trust_score") or 0) * 0.05
        if item.get("collection") in preferred:
            score += 12
        item = dict(item)
        item["unified_score"] = round(score, 2)
        ranked.append(item)
    ranked.sort(
        key=lambda item: (
            item.get("unified_score", 0),
            item.get("trust_score", 0),
        ),
        reverse=True,
    )
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
