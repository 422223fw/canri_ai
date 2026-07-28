"""Compact request contract shared by all specialist packages."""

from __future__ import annotations

import re
from typing import Any


TOKEN_RE = re.compile(
    r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']+"
)


def stop_terms(report: dict[str, Any] | None) -> set[str]:
    """Return only the function words already classified by Understanding_brain."""

    report = report if isinstance(report, dict) else {}
    return {
        str(item.get("word") or "").casefold().strip()
        for item in report.get("words", [])
        if isinstance(item, dict)
        and item.get("is_stop_word")
        and str(item.get("word") or "").strip()
    }


def content_terms(
    report: dict[str, Any] | None,
    fallback_text: str = "",
    *,
    include_connections: bool = True,
    limit: int = 120,
) -> list[str]:
    """Reuse Understanding's word roles instead of a specialist stop-word list."""

    report = report if isinstance(report, dict) else {}
    blocked = stop_terms(report)
    values = []
    for item in report.get("words", []):
        if not isinstance(item, dict) or item.get("is_stop_word"):
            continue
        values.append(item.get("word"))
        if include_connections:
            values.extend(item.get("connections", [])[:8])
    meaning = report.get("meaning_frame", {})
    if isinstance(meaning, dict):
        values.extend(meaning.get("content_terms", [])[:40])
    values.extend(report.get("key_terms", [])[:40])

    # Raw fallback is used only for legacy calls that did not receive a full report.
    if not values:
        values.extend(TOKEN_RE.findall(str(fallback_text or "")))

    clean = []
    for value in values:
        term = re.sub(r"\s+", " ", str(value or "").casefold()).strip(" _-'\t\r\n")
        if len(term) <= 1 or term in blocked or term in clean:
            continue
        clean.append(term)
        if len(clean) >= max(1, int(limit)):
            break
    return clean


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    report = report if isinstance(report, dict) else {}
    contract = report.get("request_contract", {})
    contract = contract if isinstance(contract, dict) else {}
    continuation = contract.get("continuation", {})
    continuation = continuation if isinstance(continuation, dict) else {}
    coverage = contract.get("coverage", {})
    coverage = coverage if isinstance(coverage, dict) else {}
    return {
        "topic": report.get("main_topic") or contract.get("topic"),
        "intent": report.get("intent") or contract.get("intent"),
        "action": contract.get("action"),
        "target": contract.get("target"),
        "central_domains": list(contract.get("central_domains", report.get("central_domains", [])))[:6],
        "requirements": list(contract.get("requirements", []))[:80],
        "output_constraints": contract.get("output_constraints", {}),
        "continuation": continuation,
        "whole_input_analyzed": bool(coverage.get("whole_input_analyzed")),
        "small_detail_count": coverage.get("small_detail_count", 0),
        "source": "Understanding_brain.request_contract",
    }


__all__ = ["build_context", "content_terms", "stop_terms"]
