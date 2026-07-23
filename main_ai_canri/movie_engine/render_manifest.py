"""Translate shots into provider-neutral render jobs."""

from __future__ import annotations

from pathlib import Path

from .models import AssetRequirement, MovieRequest, RenderJob, Scene, Shot
from .utils import stable_id


def build_render_manifest(
    request: MovieRequest,
    scenes: list[Scene],
    shots: list[Shot],
    assets: list[AssetRequirement],
    cinematography: dict,
    output_directory: Path,
) -> dict:
    scene_map = {scene.scene_id: scene for scene in scenes}
    asset_map = {asset.asset_id: asset for asset in assets}
    jobs = []
    for global_index, shot in enumerate(shots, start=1):
        scene = scene_map[shot.scene_id]
        references = [asset_map[item].name for item in shot.asset_ids if item in asset_map]
        prompt = (
            f"Photorealistic high-budget cinema shot. {shot.framing}, {shot.lens_mm}mm lens, "
            f"{shot.camera_move}. Subject: {shot.subject}. Action: {shot.action}. "
            f"Location: {scene.location}, {scene.time_of_day}. Lighting: {shot.lighting}. "
            f"Preserve identity, wardrobe, props, weather, screen direction, and physical continuity. "
            f"References: {', '.join(references)}."
        )
        jobs.append(RenderJob(
            job_id=stable_id("render", shot.shot_id),
            shot_id=shot.shot_id,
            duration_seconds=shot.duration_seconds,
            prompt=prompt,
            negative_prompt=(
                "identity drift, anatomy errors, extra limbs, warped hands, floating objects, "
                "incorrect reflections, inconsistent wardrobe, text artifacts, temporal flicker, "
                "camera teleportation, synthetic plastic skin, crushed highlights"
            ),
            reference_assets=shot.asset_ids,
            output_file=str(output_directory / "shots" / f"{global_index:05d}_{shot.shot_id}.mov"),
        ))
    return {
        "schema_version": 1,
        "provider_neutral": True,
        "target_duration_seconds": request.duration_seconds,
        "render_profile": dict(request.render_profile),
        "cinematography": cinematography,
        "jobs": [job.__dict__ for job in jobs],
        "assembly": {
            "picture_sequence": [job.output_file for job in jobs],
            "audio_master": str(output_directory / "audio" / "final_mix.wav"),
            "subtitle_file": str(output_directory / "captions" / "captions.srt"),
            "final_master": str(output_directory / f"{output_directory.name}_master.mov"),
            "viewing_copy": str(output_directory / f"{output_directory.name}_viewing_copy.mp4"),
            "animatic_preview": str(output_directory / f"{output_directory.name}_animatic.mp4"),
        },
    }
