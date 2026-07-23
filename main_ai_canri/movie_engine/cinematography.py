"""Cinematography grammar for photorealistic shot design."""

from __future__ import annotations

from typing import Any

from .models import MovieRequest


GENRE_PROFILES = {
    "action": {"lens": [24, 35, 50], "movement": ["tracking", "handheld", "crane"], "contrast": "high"},
    "comedy": {"lens": [28, 35, 50], "movement": ["locked", "dolly", "pan"], "contrast": "medium"},
    "documentary": {"lens": [24, 35, 70], "movement": ["observational handheld", "locked", "slow pan"], "contrast": "natural"},
    "horror": {"lens": [18, 35, 85], "movement": ["slow push", "locked", "controlled handheld"], "contrast": "deep"},
    "science fiction": {"lens": [24, 40, 75], "movement": ["dolly", "crane", "orbital"], "contrast": "sculpted"},
    "drama": {"lens": [35, 50, 85], "movement": ["locked", "slow dolly", "subtle handheld"], "contrast": "naturalistic"},
}


def build_cinematography_plan(request: MovieRequest, world: dict[str, Any]) -> dict[str, Any]:
    profile = GENRE_PROFILES.get(request.genre, GENRE_PROFILES["drama"])
    return {
        "capture_intent": request.realism,
        "camera_system": "large-format digital cinema camera with production-matched virtual camera",
        "lenses_mm": profile["lens"],
        "camera_movements": profile["movement"],
        "lighting_contrast": profile["contrast"],
        "lighting_rule": "Every key light is motivated by a practical, window, sky, flame, or production source.",
        "exposure_rule": "Protect skin tone and highlight texture; avoid synthetic clipped highlights.",
        "depth_rule": "Use depth of field to direct attention without erasing production design.",
        "continuity_rule": "Preserve sun direction, color temperature, weather, lens logic, and screen direction.",
        "world_reference": world.get("production_design"),
        "delivery": dict(request.render_profile),
    }


def shot_grammar(plan: dict[str, Any], index: int) -> tuple[str, int, str, str]:
    framings = ("wide master", "medium two-shot", "medium close-up", "close-up", "insert", "reaction")
    lenses = plan.get("lenses_mm", [35, 50, 85])
    movements = plan.get("camera_movements", ["locked"])
    framing = framings[index % len(framings)]
    lens = int(lenses[index % len(lenses)])
    movement = str(movements[index % len(movements)])
    lighting = f"{plan.get('lighting_contrast', 'naturalistic')} motivated lighting"
    return framing, lens, movement, lighting
