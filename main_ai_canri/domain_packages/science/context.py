"""Evidence-focused context for scientific answers and calculations."""

from __future__ import annotations

from typing import Any


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    matches = knowledge.get("matches", []) if isinstance(knowledge, dict) else []
    evidence = []
    for item in matches if isinstance(matches, list) else []:
        if not isinstance(item, dict):
            continue
        evidence.append({
            "title": item.get("title"),
            "trust_score": item.get("trust_score", 0),
            "sources": item.get("sources", [])[:3],
            "summary": str(item.get("summary", ""))[:500],
        })
    return {
        "requirements": list(contract.get("requirements", []))[:80],
        "entities": list(contract.get("entities", []))[:30],
        "evidence": evidence[:8],
        "verification_policy": [
            "separate observations, models, and conclusions",
            "prefer primary or authoritative sources",
            "state uncertainty when evidence is incomplete",
            "send factual claims to Fact_Check_brain",
        ],
    }

