"""Production safety and content-boundary checks."""

from __future__ import annotations

from typing import Any


def assess_movie_safety(prompt: str, security_result: Any = None) -> dict[str, Any]:
    result = security_result if isinstance(security_result, dict) else {}
    blocked = bool(result.get("blocked") or result.get("allowed") is False)
    return {
        "safe_to_plan": not blocked,
        "blocked": blocked,
        "reason": result.get("reason") if blocked else None,
        "content_rating_required": True,
        "production_rules": [
            "Use qualified coordinators for stunts, intimacy, weapons, water, fire, animals, and minors.",
            "Do not impersonate real people or use protected likenesses without authorization.",
            "Do not present synthetic footage as documentary evidence of a real event.",
            "Record asset licenses, releases, consent, and provenance.",
        ],
        "prompt_received": bool(str(prompt or "").strip()),
    }
