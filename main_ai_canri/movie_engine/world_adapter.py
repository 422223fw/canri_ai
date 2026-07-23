"""Create a consistent production world from World_brain output."""

from __future__ import annotations

from typing import Any

from .models import MovieRequest
from .utils import unique_strings


def build_world(request: MovieRequest, context: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    result = context.get("brain_results", {}).get("World_brain", {})
    world = result.get("world", {}) if isinstance(result, dict) else {}
    if not isinstance(world, dict):
        world = {"description": str(world)}
    evidence_locations = [
        item.get("title")
        for item in context.get("knowledge_evidence", [])
        if isinstance(item, dict) and item.get("title")
    ]
    locations = unique_strings(
        list(world.get("locations", [])) + evidence_locations,
        limit=10,
    )
    if not locations:
        locations = ["Primary lived-in location", "Contrasting public location", "Final confrontation location"]
    return {
        "name": world.get("name") or f"The world of {request.title}",
        "description": world.get("description") or brief.get("premise"),
        "period": world.get("period") or "contemporary",
        "locations": locations,
        "physical_rules": unique_strings(world.get("rules", []), limit=12) or [
            "Physical behavior remains realistic and consistent.",
            "Weather, light, damage, wardrobe, and props persist between connected scenes.",
        ],
        "production_design": world.get("production_design") or (
            "Layered practical sets, motivated lighting, physically plausible materials, and lived-in detail."
        ),
        "cultural_notes": unique_strings(world.get("cultural_notes", []), limit=10),
        "world_brain_used": bool(result),
    }
