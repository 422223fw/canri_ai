"""System constraints and cross-domain handoff for technology tasks."""

from __future__ import annotations

from typing import Any


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    return {
        "requirements": list(contract.get("requirements", []))[:80],
        "entities": list(contract.get("entities", []))[:40],
        "features": list(contract.get("features", []))[:40],
        "integration_checks": [
            "identify hardware, software, protocol, and data boundaries",
            "make platform and dependency assumptions explicit",
            "include failure, timeout, and recovery behavior",
            "route implementation to Code_brain and facts to Fact_Check_brain",
        ],
    }

