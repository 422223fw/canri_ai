"""Expand sequences into a complete duration-locked scene timeline."""

from __future__ import annotations

import math
from typing import Any

from .constants import DEFAULT_SCENE_SECONDS, MAX_SCENES
from .duration import allocate_integer_duration
from .models import CharacterProfile, MovieRequest, Scene
from .utils import stable_id


PURPOSE_CYCLE = (
    "establish", "investigate", "complicate", "reveal", "choose", "confront", "recover", "transform"
)
TIME_CYCLE = ("DAWN", "DAY", "LATE AFTERNOON", "NIGHT")


def _scene_count(duration_seconds: int) -> int:
    if duration_seconds <= 10 * 60:
        target_scene_seconds = 45
    elif duration_seconds <= 40 * 60:
        target_scene_seconds = 90
    else:
        target_scene_seconds = DEFAULT_SCENE_SECONDS
    return max(1, min(MAX_SCENES, math.ceil(duration_seconds / target_scene_seconds)))


def build_scenes(
    request: MovieRequest,
    story: dict[str, Any],
    characters: list[CharacterProfile],
    world: dict[str, Any],
) -> list[Scene]:
    count = _scene_count(request.duration_seconds)
    durations = allocate_integer_duration(request.duration_seconds, count)
    sequences = story.get("sequences", []) or [{"sequence_id": "sequence_1", "act": 1}]
    locations = world.get("locations", []) or ["Primary location"]
    scenes = []
    for index, duration in enumerate(durations, start=1):
        sequence = sequences[min(len(sequences) - 1, (index - 1) * len(sequences) // count)]
        location = locations[(index - 1) % len(locations)]
        purpose_word = PURPOSE_CYCLE[(index - 1) % len(PURPOSE_CYCLE)]
        act = int(sequence.get("act", 1))
        character_ids = [character.character_id for character in characters[:2]]
        if len(characters) > 2 and index % 3 == 0:
            character_ids.append(characters[2].character_id)
        scene_id = stable_id("scene", request.title, index)
        next_pressure = "The cost rises and the next scene inherits an unresolved decision."
        scenes.append(Scene(
            scene_id=scene_id,
            sequence_id=str(sequence.get("sequence_id")),
            act=act,
            number=index,
            heading=f"INT./EXT. {str(location).upper()} - {TIME_CYCLE[(index - 1) % len(TIME_CYCLE)]}",
            location=str(location),
            time_of_day=TIME_CYCLE[(index - 1) % len(TIME_CYCLE)],
            duration_seconds=duration,
            purpose=f"{purpose_word.title()} the sequence objective: {sequence.get('purpose', '')}",
            conflict="The immediate objective is blocked by a concrete opposing action.",
            turning_point=str(sequence.get("turn") or next_pressure) if index % max(1, count // len(sequences)) == 0 else next_pressure,
            action=(
                f"The characters pursue the scene objective in {location}. Physical behavior, eyelines, "
                "screen direction, props, weather, and emotional state remain continuous."
            ),
            dialogue_beats=[
                "State the immediate need without explaining the entire plot.",
                "Let resistance expose character and subtext.",
                "End on a choice, discovery, reversal, or unanswered pressure.",
            ],
            character_ids=character_ids,
            continuity_in=[f"emotional_state_from_scene_{max(1, index - 1)}"],
            continuity_out=[f"decision_pressure_for_scene_{min(count, index + 1)}"],
        ))
    return scenes
