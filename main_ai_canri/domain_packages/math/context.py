"""Verification contract for mathematical work."""

from __future__ import annotations

from typing import Any


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    details = contract.get("detail_inventory", {})
    details = details if isinstance(details, dict) else {}
    return {
        "requirements": list(contract.get("requirements", []))[:80],
        "entities": list(contract.get("entities", []))[:30],
        "code_terms": list(details.get("code_terms", []))[:20],
        "verification_steps": [
            "parse the exact expression or equation",
            "show transformations in a valid order when steps are requested",
            "substitute the result back into the original problem",
            "report domain restrictions and undefined operations",
        ],
    }
