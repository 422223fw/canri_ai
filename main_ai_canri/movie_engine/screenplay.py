"""Create a readable screenplay document from structured scenes."""

from __future__ import annotations

from .models import CharacterProfile, MovieRequest, Scene


def build_scene_screenplay(scene: Scene, characters: list[CharacterProfile]) -> str:
    cast = {character.character_id: character for character in characters}
    present = [cast[item] for item in scene.character_ids if item in cast]
    lines = [scene.heading, "", scene.action, ""]
    if present:
        first = present[0]
        second = present[1] if len(present) > 1 else present[0]
        lines.extend([
            first.name.upper(),
            f"We need to {first.goal.rstrip('.').lower()}, but not at the cost we keep ignoring.",
            "",
            second.name.upper(),
            f"Then make the choice this moment requires. {scene.conflict}",
            "",
        ])
    lines.extend([
        f"ACTION BEAT: {scene.turning_point}",
        f"CONTINUITY OUT: {', '.join(scene.continuity_out)}",
    ])
    return "\n".join(lines).strip()


def build_screenplay(request: MovieRequest, scenes: list[Scene], characters: list[CharacterProfile]) -> dict:
    scene_pages = [build_scene_screenplay(scene, characters) for scene in scenes]
    document = "\n\n".join(
        [
            request.title.upper(),
            f"Genre: {request.genre} | Tone: {request.tone} | Target: {request.duration_seconds // 60} minutes",
            "",
        ]
        + scene_pages
    )
    return {
        "format": "structured_screenplay_draft",
        "scene_count": len(scenes),
        "target_duration_seconds": request.duration_seconds,
        "document": document,
        "note": (
            "This is a complete scene-level production screenplay. Dialogue remains intentionally "
            "editable during performance development while every scene and turning point is scheduled."
        ),
    }
