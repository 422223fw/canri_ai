"""Create a feasible preproduction, photography, and post schedule."""

from __future__ import annotations

import math

from .models import MovieRequest


def build_schedule(request: MovieRequest, scene_count: int, shot_count: int, asset_count: int) -> dict:
    shoot_days = max(3, math.ceil(scene_count / 4))
    preproduction_weeks = max(4, math.ceil(asset_count / 12))
    post_weeks = max(6, math.ceil(shot_count / 100))
    return {
        "preproduction_weeks": preproduction_weeks,
        "principal_photography_days": shoot_days,
        "postproduction_weeks": post_weeks,
        "estimated_total_weeks": preproduction_weeks + math.ceil(shoot_days / 5) + post_weeks,
        "phases": [
            {"name": "development", "deliverables": ["approved brief", "screenplay", "rights and research audit"]},
            {"name": "preproduction", "deliverables": ["cast", "locations", "assets", "storyboards", "safety plans"]},
            {"name": "production", "deliverables": ["picture", "production audio", "metadata", "continuity reports"]},
            {"name": "postproduction", "deliverables": ["edit", "VFX", "sound", "music", "color", "captions"]},
            {"name": "delivery", "deliverables": ["master", "stems", "textless", "archive", "provenance record"]},
        ],
        "duration_target_seconds": request.duration_seconds,
    }
