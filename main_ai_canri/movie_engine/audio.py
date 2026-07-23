"""Dialogue, ambience, Foley, score, and final-mix planning."""

from __future__ import annotations

from typing import Any

from .models import CharacterProfile, MovieRequest, Scene


def build_audio_plan(
    request: MovieRequest,
    scenes: list[Scene],
    characters: list[CharacterProfile],
    context: dict[str, Any],
) -> dict[str, Any]:
    voice_result = context.get("brain_results", {}).get("Voice_brain", {})
    return {
        "language": request.language,
        "delivery_layout": request.render_profile.get("audio_layout", "5.1"),
        "dialogue": {
            "capture": "isolated production dialogue plus room tone and controlled ADR",
            "cast_voices": {character.character_id: character.voice for character in characters},
            "voice_brain_used": bool(voice_result),
        },
        "ambience": [
            {"scene_id": scene.scene_id, "bed": f"continuous ambience for {scene.location}"}
            for scene in scenes
        ],
        "foley": "Footsteps, cloth, handled props, impacts, and environmental interaction remain perspective-correct.",
        "score": {
            "approach": f"Original {request.tone} score with thematic development across three acts.",
            "themes": ["protagonist motif", "conflict motif", "transformation motif"],
            "rule": "Music supports subtext and transitions; it does not mask unclear storytelling.",
        },
        "mix": {
            "dialogue_target_lufs": -24,
            "true_peak_dbtp": -2,
            "deliverables": ["5.1 full mix", "stereo fold-down", "M&E", "dialogue/music/effects stems"],
        },
    }
