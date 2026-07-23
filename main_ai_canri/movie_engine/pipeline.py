"""End-to-end movie preproduction, render planning, and backend handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .assets import build_assets
from .audio import build_audio_plan
from .budget import estimate_budget
from .character_adapter import build_characters
from .cinematography import build_cinematography_plan
from .continuity import build_continuity_ledger
from .creative_adapter import build_creative_brief
from .exporter import export_movie_project
from .models import MovieProject
from .narrative import build_story_architecture
from .render_backends import execute_render_backend
from .render_manifest import build_render_manifest
from .request_parser import parse_movie_request
from .safety import assess_movie_safety
from .scene_planner import build_scenes
from .schedule import build_schedule
from .screenplay import build_screenplay
from .shot_planner import build_shots
from .source_context import collect_movie_context
from .utils import slugify, stable_id
from .validation import validate_movie_project
from .vfx import build_vfx_plan
from .world_adapter import build_world


class MoviePipeline:
    def __init__(self, output_root: Path):
        self.output_root = Path(output_root)

    def build(self, data: Any, report: dict[str, Any]) -> dict[str, Any]:
        request = parse_movie_request(data, report)
        context = collect_movie_context(data, report)
        security_result = context.get("brain_results", {}).get("Security_brain", {})
        safety = assess_movie_safety(request.prompt, security_result)
        if safety["blocked"]:
            return {
                "brain": "Movie_brain",
                "safe": False,
                "blocked": True,
                "answer": f"Movie production was blocked by Security_brain: {safety.get('reason') or 'unsafe request'}",
                "safety": safety,
                "confidence": 100,
            }

        project_id = stable_id("movie", request.title, request.prompt, request.duration_seconds)
        output_directory = self.output_root / f"{slugify(request.title)}_{project_id[-8:]}"
        brief = build_creative_brief(request, context)
        characters = build_characters(request, context, brief)
        world = build_world(request, context, brief)
        story = build_story_architecture(request, brief)
        scenes = build_scenes(request, story, characters, world)
        story["screenplay"] = build_screenplay(request, scenes, characters)
        cinematography = build_cinematography_plan(request, world)
        shots = build_shots(scenes, characters, cinematography)
        assets = build_assets(characters, scenes, shots)
        audio_plan = build_audio_plan(request, scenes, characters, context)
        vfx_plan = build_vfx_plan(request, scenes)
        continuity = build_continuity_ledger(scenes, shots, characters)
        production_plan = {
            "cinematography": cinematography,
            "continuity": continuity,
            "safety": safety,
            "budget": estimate_budget(request, len(scenes), len(shots), vfx_plan["complexity"]),
            "schedule": build_schedule(request, len(scenes), len(shots), len(assets)),
        }
        render_manifest = build_render_manifest(
            request, scenes, shots, assets, cinematography, output_directory
        )
        project = MovieProject(
            project_id=project_id,
            request=request,
            creative_brief=brief,
            story=story,
            characters=characters,
            world=world,
            scenes=scenes,
            shots=shots,
            assets=assets,
            audio_plan=audio_plan,
            vfx_plan=vfx_plan,
            production_plan=production_plan,
            render_manifest=render_manifest,
            source_receipts=context.get("receipts", {}),
        )
        project.validation = validate_movie_project(project)
        payload = data if isinstance(data, dict) else {}
        render_status = execute_render_backend(project.to_dict(), payload)
        export = export_movie_project(
            project,
            output_directory,
            disabled=bool(payload.get("_disable_persistence") or not request.save_project),
        )
        return {
            "brain": "Movie_brain",
            "safe": True,
            "mode": "movie_production",
            "project_id": project_id,
            "title": request.title,
            "duration_seconds": request.duration_seconds,
            "duration_minutes": round(request.duration_seconds / 60, 2),
            "scene_count": len(scenes),
            "shot_count": len(shots),
            "asset_count": len(assets),
            "creative_brain_used": brief["creative_brain_used"],
            "brains_considered": context.get("receipts", {}).get("brains_considered", []),
            "movie_project": project.to_dict(),
            "validation": project.validation,
            "render_status": render_status,
            "export": export,
            "confidence": project.validation.get("score", 0),
            "answer": self._answer(request.title, request.duration_seconds, len(scenes), len(shots), brief, project.validation, render_status, export),
        }

    @staticmethod
    def _answer(title, duration, scene_count, shot_count, brief, validation, render_status, export):
        lines = [
            f"Movie production package: {title}",
            f"Duration: {duration / 60:.1f} minutes",
            f"Scenes: {scene_count} | Shots: {shot_count}",
            f"Creative_brain used: {'yes' if brief.get('creative_brain_used') else 'fallback to request'}",
            f"Production validation: {'passed' if validation.get('passed') else 'failed'} ({validation.get('score', 0)}/100)",
            f"Render status: {render_status.get('status')}",
        ]
        if export.get("saved"):
            lines.append(f"Project files: {export.get('directory')}")
        if render_status.get("preview_rendered"):
            lines.append(f"Watchable MP4 animatic: {render_status.get('preview_file')}")
        if not render_status.get("rendered"):
            lines.append(
                "The screenplay, scene timeline, shot plan, assets, audio, VFX, budget, schedule, and render "
                "manifest are complete. A configured video-generation backend is still required for a real photorealistic master."
            )
        else:
            lines.append(f"Rendered master: {render_status.get('output_file')}")
        return "\n".join(lines)
