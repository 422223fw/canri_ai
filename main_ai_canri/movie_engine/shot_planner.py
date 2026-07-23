"""Expand every scene into a duration-locked camera plan."""

from __future__ import annotations

import math
from typing import Any

from .constants import DEFAULT_SHOT_SECONDS, MAX_SHOTS
from .duration import allocate_integer_duration
from .models import CharacterProfile, Scene, Shot
from .utils import stable_id
from .cinematography import shot_grammar


def build_shots(
    scenes: list[Scene],
    characters: list[CharacterProfile],
    cinematography: dict[str, Any],
) -> list[Shot]:
    cast = {character.character_id: character for character in characters}
    desired_counts = [max(1, math.ceil(scene.duration_seconds / DEFAULT_SHOT_SECONDS)) for scene in scenes]
    total_desired = sum(desired_counts)
    if total_desired > MAX_SHOTS:
        scale = MAX_SHOTS / total_desired
        desired_counts = [max(1, int(count * scale)) for count in desired_counts]

    shots = []
    global_index = 0
    for scene, count in zip(scenes, desired_counts):
        durations = allocate_integer_duration(scene.duration_seconds, count)
        present = [cast[item].name for item in scene.character_ids if item in cast]
        subject = " and ".join(present[:2]) or scene.location
        for local_index, duration in enumerate(durations, start=1):
            framing, lens, movement, lighting = shot_grammar(cinematography, global_index)
            global_index += 1
            shots.append(Shot(
                shot_id=stable_id("shot", scene.scene_id, local_index),
                scene_id=scene.scene_id,
                number=local_index,
                duration_seconds=duration,
                framing=framing,
                lens_mm=lens,
                camera_move=movement,
                subject=subject,
                action=f"Cover beat {local_index} of scene {scene.number}: {scene.purpose}",
                lighting=lighting,
                audio_cue="production dialogue, room tone, controlled Foley, and score transition",
                vfx_notes="Invisible cleanup and continuity support only unless the VFX plan marks the scene.",
            ))
    return shots
