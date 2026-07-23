"""Exact validation for duration, references, and production completeness."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .constants import MAX_MOVIE_SECONDS
from .models import MovieProject


def validate_movie_project(project: MovieProject) -> dict[str, Any]:
    errors = []
    warnings = []
    scene_duration = sum(scene.duration_seconds for scene in project.scenes)
    shot_duration = sum(shot.duration_seconds for shot in project.shots)
    target = project.request.duration_seconds
    scene_ids = {scene.scene_id for scene in project.scenes}
    shot_ids = {shot.shot_id for shot in project.shots}
    asset_ids = {asset.asset_id for asset in project.assets}
    jobs = project.render_manifest.get("jobs", [])
    job_shots = {job.get("shot_id") for job in jobs if isinstance(job, dict)}

    if target > MAX_MOVIE_SECONDS:
        errors.append("Movie duration exceeds the five-hour hard limit.")
    if scene_duration != target:
        errors.append(f"Scene timeline is {scene_duration}s, expected {target}s.")
    if shot_duration != target:
        errors.append(f"Shot timeline is {shot_duration}s, expected {target}s.")
    if not project.scenes:
        errors.append("No scenes were generated.")
    if not project.shots:
        errors.append("No shots were generated.")
    if shot_ids != job_shots:
        errors.append("Render jobs do not cover every shot exactly once.")
    for shot in project.shots:
        if shot.scene_id not in scene_ids:
            errors.append(f"{shot.shot_id} references an unknown scene.")
        missing_assets = set(shot.asset_ids) - asset_ids
        if missing_assets:
            errors.append(f"{shot.shot_id} references unknown assets: {sorted(missing_assets)}")
    duplicates = [item for item, count in Counter(shot_ids).items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate shot identifiers: {duplicates[:5]}")
    if len(project.characters) < 2:
        warnings.append("The cast contains fewer than two characters.")
    if not project.creative_brief.get("creative_brain_used"):
        warnings.append("Creative_brain output was unavailable; the request was used as the creative source.")

    checks = {
        "duration_within_limit": target <= MAX_MOVIE_SECONDS,
        "scene_duration_exact": scene_duration == target,
        "shot_duration_exact": shot_duration == target,
        "all_scenes_have_shots": all(any(shot.scene_id == scene.scene_id for shot in project.shots) for scene in project.scenes),
        "render_jobs_cover_shots": shot_ids == job_shots,
        "creative_brain_considered": bool(project.creative_brief.get("creative_brain_used")),
        "continuity_passed": bool(project.production_plan.get("continuity", {}).get("passed")),
    }
    required_passes = [
        checks["duration_within_limit"],
        checks["scene_duration_exact"],
        checks["shot_duration_exact"],
        checks["all_scenes_have_shots"],
        checks["render_jobs_cover_shots"],
    ]
    return {
        "passed": all(required_passes) and not errors,
        "score": round(100 * sum(bool(value) for value in checks.values()) / len(checks)),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "target_duration_seconds": target,
        "scene_duration_seconds": scene_duration,
        "shot_duration_seconds": shot_duration,
    }
