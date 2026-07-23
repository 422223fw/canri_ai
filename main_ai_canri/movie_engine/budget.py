"""Transparent high-level budget model for production planning."""

from __future__ import annotations

from .models import MovieRequest


def estimate_budget(
    request: MovieRequest,
    scene_count: int,
    shot_count: int,
    vfx_complexity: str,
) -> dict:
    minutes = request.duration_seconds / 60
    base_per_minute = 180_000 if request.realism == "photorealistic" else 80_000
    vfx_multiplier = {"low": 1.0, "moderate": 1.25, "high": 1.7}.get(vfx_complexity, 1.25)
    estimated = int((minutes * base_per_minute + scene_count * 25_000 + shot_count * 1_500) * vfx_multiplier)
    departments = {
        "development_and_writing": 0.04,
        "cast": 0.12,
        "production_staff": 0.15,
        "locations_and_art": 0.14,
        "camera_grip_and_lighting": 0.10,
        "sound_and_music": 0.06,
        "vfx_and_virtual_production": 0.18,
        "editorial_color_and_delivery": 0.09,
        "insurance_legal_and_safety": 0.04,
        "contingency": 0.08,
    }
    return {
        "currency": "USD",
        "planning_estimate": estimated,
        "range": {"low": int(estimated * 0.72), "high": int(estimated * 1.45)},
        "department_allocations": {
            name: int(estimated * fraction)
            for name, fraction in departments.items()
        },
        "assumptions": [
            "High-end photorealistic production or equivalent synthetic production quality.",
            "Final cost depends on cast, locations, rights, vendors, render volume, and revision count.",
            "This is a planning estimate, not a quote or financing representation.",
        ],
    }
