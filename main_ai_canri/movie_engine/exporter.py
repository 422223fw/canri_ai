"""Export a movie project as inspectable, provider-neutral production files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Brain_storage import atomic_write_json

from .models import MovieProject


def _write_text(path: Path, text: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False


def export_movie_project(project: MovieProject, output_directory: Path, disabled: bool = False) -> dict[str, Any]:
    if disabled:
        return {"saved": False, "reason": "persistence_disabled", "directory": str(output_directory)}
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return {
            "saved": False,
            "reason": "output_directory_unavailable",
            "error": f"{type(error).__name__}: {error}",
            "directory": str(output_directory),
        }
    project_dict = project.to_dict()
    files = {
        "project": output_directory / "movie_project.json",
        "screenplay": output_directory / "screenplay.txt",
        "render_manifest": output_directory / "render_manifest.json",
        "shot_list": output_directory / "shot_list.jsonl",
        "production_readme": output_directory / "README.txt",
    }
    statuses = {
        "project": atomic_write_json(files["project"], project_dict),
        "render_manifest": atomic_write_json(files["render_manifest"], project.render_manifest),
        "screenplay": _write_text(files["screenplay"], project.story.get("screenplay", {}).get("document", "")),
        "production_readme": _write_text(
            files["production_readme"],
            (
                f"{project.request.title}\n"
                f"Target duration: {project.request.duration_seconds} seconds\n"
                f"Scenes: {len(project.scenes)}\nShots: {len(project.shots)}\n\n"
                "This directory is a provider-neutral production package. A photorealistic final "
                "master requires a configured video-generation/render backend and licensed assets.\n"
            ),
        ),
    }
    try:
        with files["shot_list"].open("w", encoding="utf-8", newline="\n") as handle:
            for shot in project_dict["shots"]:
                handle.write(json.dumps(shot, ensure_ascii=False) + "\n")
        statuses["shot_list"] = True
    except OSError:
        statuses["shot_list"] = False
    return {
        "saved": all(statuses.values()),
        "directory": str(output_directory),
        "files": {name: str(path) for name, path in files.items()},
        "statuses": statuses,
    }
