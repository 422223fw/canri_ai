"""Collect bounded, relevant evidence from every participating Canri brain."""

from __future__ import annotations

from typing import Any

from .constants import MAX_CONTEXT_ITEMS
from .utils import split_sentences, unique_strings


USER_FACING_FIELDS = (
    "answer", "final_output", "story", "summary", "explanation", "best_answer",
    "generated_image_prompt", "support_response", "translated_text",
)


def _compact_brain_result(name: str, result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"brain": name, "text": str(result)[:1000]}
    text = ""
    for field in USER_FACING_FIELDS:
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            text = value.strip()[:3000]
            break
    return {
        "brain": name,
        "text": text,
        "confidence": result.get("confidence"),
        "terms": unique_strings(result.get("terms_used", []), limit=20),
        "sources": result.get("sources", [])[:8] if isinstance(result.get("sources"), list) else [],
        "usable": not bool(result.get("error") or result.get("skipped")),
    }


def collect_movie_context(data: Any, report: dict[str, Any]) -> dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    results = payload.get("results", {}) if isinstance(payload.get("results"), dict) else {}
    brain_context = {
        name: _compact_brain_result(name, result)
        for name, result in results.items()
    }

    evidence = []
    knowledge_context = payload.get("_knowledge_context", {})
    if isinstance(knowledge_context, dict):
        evidence.extend(knowledge_context.get("indexed_evidence", []))
    scanner = payload.get("scanner_knowledge", {})
    if isinstance(scanner, dict):
        evidence.extend(scanner.get("matches", []))
    local_data = payload.get("data_context", {})
    if isinstance(local_data, dict):
        evidence.extend(local_data.get("scanner_matches", []))
        evidence.extend(local_data.get("matches", []))

    compact_evidence = []
    seen = set()
    for item in evidence:
        if not isinstance(item, dict):
            continue
        identity = item.get("article_id") or item.get("record_id") or item.get("url") or item.get("title")
        identity = str(identity or item)[:300]
        if identity in seen:
            continue
        seen.add(identity)
        compact_evidence.append({
            "title": item.get("title") or item.get("name"),
            "summary": str(item.get("summary") or item.get("text") or item.get("excerpt") or "")[:1600],
            "url": item.get("url"),
            "trust_score": item.get("trust_score"),
            "collection": item.get("collection") or item.get("source_type"),
        })
        if len(compact_evidence) >= MAX_CONTEXT_ITEMS:
            break

    prompt = str(
        report.get("original_text")
        or report.get("corrected_text")
        or payload.get("original_text")
        or payload.get("prompt")
        or ""
    )
    return {
        "prompt_sentences": split_sentences(prompt, limit=30),
        "brain_results": results,
        "brain_context": brain_context,
        "knowledge_evidence": compact_evidence,
        "dictionary": payload.get("dictionary", {}),
        "shared_context": payload.get("shared_context", {}),
        "memory": payload.get("memory", {}),
        "receipts": {
            "brains_considered": sorted(brain_context),
            "usable_brains": sorted(name for name, value in brain_context.items() if value.get("usable")),
            "knowledge_items_considered": len(compact_evidence),
            "used_lazy_indexed_context": bool(compact_evidence or payload.get("data_context")),
        },
    }
