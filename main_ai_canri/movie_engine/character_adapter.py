"""Build a cast bible from Character_brain and request context."""

from __future__ import annotations

from typing import Any

from .models import CharacterProfile, MovieRequest
from .utils import stable_id, unique_strings


def _profile_from_mapping(value: dict[str, Any], index: int, request: MovieRequest) -> CharacterProfile:
    name = str(value.get("name") or value.get("character_name") or f"Character {index}")
    role = str(value.get("role") or ("protagonist" if index == 1 else "supporting"))
    return CharacterProfile(
        character_id=stable_id("character", request.title, name, index),
        name=name,
        role=role,
        goal=str(value.get("goal") or f"Advance the central goal of {request.title}"),
        conflict=str(value.get("conflict") or value.get("flaw") or "A personal limitation collides with external pressure."),
        arc=str(value.get("arc") or "Moves from avoidance to deliberate action."),
        appearance=str(value.get("appearance") or value.get("visual_description") or "Distinct naturalistic wardrobe and silhouette."),
        voice=str(value.get("voice") or value.get("speech_style") or "Grounded, character-specific delivery."),
        continuity=dict(value.get("continuity") or {}),
    )


def build_characters(request: MovieRequest, context: dict[str, Any], brief: dict[str, Any]) -> list[CharacterProfile]:
    result = context.get("brain_results", {}).get("Character_brain", {})
    candidates = []
    if isinstance(result, dict):
        for key in ("characters", "cast"):
            if isinstance(result.get(key), list):
                candidates.extend(item for item in result[key] if isinstance(item, dict))
        if isinstance(result.get("character"), dict):
            candidates.insert(0, result["character"])
    if not candidates:
        candidates = [
            {
                "name": "Alex Morgan",
                "role": "protagonist",
                "goal": brief.get("premise"),
                "conflict": "The safest choice conflicts with the necessary choice.",
                "arc": "Learns to act with courage without losing empathy.",
            },
            {
                "name": "Mara Vale",
                "role": "ally",
                "goal": "Protect the people affected by the central conflict.",
                "conflict": "Trust must be earned under pressure.",
                "arc": "Moves from guarded independence to collaboration.",
            },
            {
                "name": "Director Rowan",
                "role": "opposing force",
                "goal": "Preserve control at any human cost.",
                "conflict": "Control creates the instability it was meant to prevent.",
                "arc": "Escalation exposes the cost of refusing change.",
            },
        ]
    names = unique_strings((item.get("name") for item in candidates), limit=12)
    filtered = []
    for index, item in enumerate(candidates[:12], start=1):
        if str(item.get("name") or "").strip() in names:
            filtered.append(_profile_from_mapping(item, index, request))
    return filtered or [_profile_from_mapping({}, 1, request)]
