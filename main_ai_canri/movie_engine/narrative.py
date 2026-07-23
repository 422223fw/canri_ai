"""Generate sequence-level narrative architecture."""

from __future__ import annotations

from typing import Any

from .constants import ACT_NAMES
from .duration import allocate_acts
from .models import MovieRequest
from .utils import stable_id


SEQUENCE_PURPOSES = (
    ("Establish ordinary life and the dramatic question.", "A disruption makes inaction costly."),
    ("Commit the protagonist to a difficult course.", "The first irreversible choice closes the easy exit."),
    ("Deliver progress while revealing a deeper cost.", "A partial victory creates a larger problem."),
    ("Tighten opposition and fracture an important relationship.", "New evidence changes what the goal means."),
    ("Force the lowest point and a truthful reassessment.", "The protagonist accepts responsibility."),
    ("Execute the final plan under maximum pressure.", "The decisive choice resolves theme and conflict."),
)


def build_story_architecture(request: MovieRequest, brief: dict[str, Any]) -> dict[str, Any]:
    act_durations = allocate_acts(request.duration_seconds)
    sequence_count = 6 if request.duration_seconds >= 40 * 60 else 3
    sequences = []
    for index in range(sequence_count):
        act = min(3, int(index * 3 / sequence_count) + 1)
        purpose, turn = SEQUENCE_PURPOSES[index * len(SEQUENCE_PURPOSES) // sequence_count]
        sequences.append({
            "sequence_id": stable_id("sequence", request.title, index + 1),
            "number": index + 1,
            "act": act,
            "purpose": purpose,
            "turn": turn,
            "theme": brief.get("themes", ["choice"])[index % len(brief.get("themes", ["choice"]))],
        })
    return {
        "logline": brief.get("logline"),
        "synopsis": brief.get("premise"),
        "structure": "three_act_sequence_structure",
        "acts": [
            {"act": index + 1, "name": ACT_NAMES[index], "duration_seconds": duration}
            for index, duration in enumerate(act_durations)
        ],
        "sequences": sequences,
        "ending": brief.get("ending_direction"),
    }
