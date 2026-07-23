"""Truthful boundary between planning and actual video generation."""

from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Any, Callable

from .animatic import create_animatic


def backend_capabilities(data: Any) -> dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    provider = payload.get("movie_video_backend")
    runway_key_available = bool(os.getenv("RUNWAYML_API_SECRET", "").strip())
    return {
        "external_provider_configured": callable(provider) or runway_key_available,
        "runway_available": runway_key_available,
        "ffmpeg_available": bool(shutil.which("ffmpeg")),
        "render_execution_authorized": bool(payload.get("execute_movie_render")),
        "assembly_only": not callable(provider) and not runway_key_available and bool(shutil.which("ffmpeg")),
    }


def execute_render_backend(project: dict[str, Any], data: Any) -> dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    capabilities = backend_capabilities(payload)
    provider: Callable[..., Any] | None = payload.get("movie_video_backend")
    if not callable(provider) and capabilities["runway_available"]:
        from .runway_backend import backend_from_payload

        provider = backend_from_payload(payload)
    if not callable(provider):
        duration = int(project.get("request", {}).get("duration_seconds", 0))
        animatic_allowed = (
            not payload.get("_disable_persistence")
            and capabilities["ffmpeg_available"]
            and bool(payload.get("generate_movie_animatic"))
        )
        if animatic_allowed:
            preview = create_animatic(project)
            if preview.get("created"):
                return {
                    "status": "animatic_rendered",
                    "rendered": False,
                    "preview_rendered": True,
                    "preproduction_complete": True,
                    "capabilities": capabilities,
                    "preview": preview,
                    "preview_file": preview.get("preview_file"),
                    "missing": [
                        "A configured movie_video_backend is still required for photorealistic video generation."
                    ],
                    "truthful_note": (
                        "Canri created a real MP4 storyboard animatic. It is a timing and shot preview, "
                        "not the photorealistic final movie."
                    ),
                }
        return {
            "status": "backend_required",
            "rendered": False,
            "preproduction_complete": True,
            "capabilities": capabilities,
            "missing": [
                "Configure RUNWAYML_API_SECRET or provide a movie_video_backend capable of photorealistic shots.",
                "Licensed character/location references and enough GPU or remote render capacity.",
            ],
            "truthful_note": (
                "Canri created the complete production and render package, but did not claim that a "
                "photorealistic movie file exists without a real video-generation backend."
            ),
        }
    if not capabilities["render_execution_authorized"]:
        return {
            "status": "backend_ready_not_executed",
            "rendered": False,
            "preproduction_complete": True,
            "capabilities": capabilities,
            "missing": ["Set execute_movie_render=True after reviewing cost, safety, rights, and render settings."],
        }
    try:
        result = provider(project)
    except Exception as error:
        return {
            "status": "backend_failed",
            "rendered": False,
            "preproduction_complete": True,
            "capabilities": capabilities,
            "error": f"{type(error).__name__}: {error}",
        }
    if not isinstance(result, dict):
        result = {"output": result}
    output_file = result.get("output_file") or result.get("master_file")
    local_output_exists = False
    if output_file and not str(output_file).lower().startswith(("http://", "https://")):
        try:
            local_output_exists = Path(output_file).is_file()
        except OSError:
            local_output_exists = False
    verified_output = bool(local_output_exists or result.get("verified_output"))
    rendered = bool(result.get("rendered") and output_file and verified_output)
    return {
        "status": "rendered" if rendered else "backend_returned_incomplete_result",
        "rendered": rendered,
        "preproduction_complete": True,
        "capabilities": capabilities,
        "output_file": output_file,
        "verified_output": verified_output,
        "provider_result": result,
    }
