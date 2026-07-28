"""Compact request contract shared by all specialist packages."""

from __future__ import annotations

from typing import Any


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

