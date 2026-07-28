"""Controlled variation context for creative specialist consultation."""

from __future__ import annotations

from typing import Any


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    output = contract.get("output_constraints", {})
    output = output if isinstance(output, dict) else {}
    continuation = contract.get("continuation", {})
    continuation = continuation if isinstance(continuation, dict) else {}
    return {
        "goal": contract.get("global_picture", {}).get("goal")
        if isinstance(contract.get("global_picture"), dict) else None,
        "requirements": list(contract.get("requirements", []))[:80],
        "continuation": continuation,
        "strict_output": bool(output.get("only_output")),
        "consultation_policy": [
            "generate alternatives from the current request, not stock stories",
            "preserve prior project or narrative facts during continuation",
            "remove repeated suggestions before handoff",
            "never replace factual or code validation with novelty scoring",
        ],
    }

