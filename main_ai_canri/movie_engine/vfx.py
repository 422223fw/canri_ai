"""Visual-effects plan focused on realism and reproducibility."""

from __future__ import annotations

from .models import MovieRequest, Scene


def build_vfx_plan(request: MovieRequest, scenes: list[Scene]) -> dict:
    heavy_genres = {"action", "adventure", "fantasy", "science fiction", "sci-fi"}
    complexity = "high" if request.genre in heavy_genres else "moderate"
    scene_work = []
    for scene in scenes:
        work = ["cleanup", "screen replacement", "continuity polish"]
        if complexity == "high" and scene.number % 3 == 0:
            work.extend(["environment extension", "simulation or creature pass"])
        scene_work.append({"scene_id": scene.scene_id, "work": work})
    return {
        "complexity": complexity,
        "realism_rules": [
            "Match lens distortion, focus, grain, motion blur, shutter, and exposure.",
            "Use physically plausible scale, inertia, contact, reflection, and shadow.",
            "Maintain character identity, wardrobe, anatomy, and environment continuity.",
            "Prefer invisible effects and practical reference whenever possible.",
        ],
        "scene_work": scene_work,
        "quality_gates": ["plate match", "animation", "lighting", "composite", "color", "final pixel review"],
    }
