"""Request and project handoff for the code engineering package."""

from __future__ import annotations

from typing import Any


def build_context(report: dict[str, Any], memory=None, knowledge=None) -> dict[str, Any]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    conversation = memory.get("conversation", {}) if isinstance(memory, dict) else {}
    conversation = conversation if isinstance(conversation, dict) else {}
    return {
        "requirements": list(contract.get("requirements", []))[:80],
        "output_constraints": contract.get("output_constraints", {}),
        "continuation": contract.get("continuation", {}),
        "previous_code_available": bool(conversation.get("usable_previous_code")),
        "previous_agent_project": conversation.get("agent_continuation"),
        "preservation_required": bool(
            contract.get("continuation", {}).get("preserve_previous_behavior")
            if isinstance(contract.get("continuation"), dict) else False
        ),
        "quality_order": [
            "understand every requirement",
            "read the selected project",
            "generate a request-specific change",
            "validate before Agent writes",
        ],
    }

