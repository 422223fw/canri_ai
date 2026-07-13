"""Small shared helpers for consuming Knowledge_collector evidence in any brain."""


def scanner_matches(data, limit=5):
    if not isinstance(data, dict):
        return []
    scanner = data.get("scanner_knowledge", {})
    if isinstance(scanner, dict) and isinstance(scanner.get("matches"), list):
        return [item for item in scanner["matches"][:limit] if isinstance(item, dict)]
    knowledge = data.get("knowledge_context") or data.get("knowledge") or {}
    if isinstance(knowledge, dict):
        return [item for item in knowledge.get("matches", [])[:limit] if isinstance(item, dict)]
    return []


def scanner_evidence(data, limit=5):
    evidence = []
    for item in scanner_matches(data, limit=limit):
        sources = item.get("sources", [])
        evidence.append({
            "article_id": item.get("article_id"),
            "title": item.get("title"),
            "text": (
                str(item.get("content_excerpt", "")).strip()
                or str(item.get("summary", "")).strip()
            ),
            "summary": str(item.get("summary", "")).strip(),
            "trust_score": item.get("trust_score", 0),
            "source_count": item.get("source_count", len(sources)),
            "sources": sources[:3],
        })
    return evidence


def scanner_source_ids(data, limit=5):
    return list(dict.fromkeys(
        source.get("source_id")
        for item in scanner_evidence(data, limit=limit)
        for source in item.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    ))
