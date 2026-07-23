"""Continuity ledger and cross-scene validation."""

from __future__ import annotations

from collections import Counter

from .models import CharacterProfile, Scene, Shot


def build_continuity_ledger(
    scenes: list[Scene],
    shots: list[Shot],
    characters: list[CharacterProfile],
) -> dict:
    shot_counts = Counter(shot.scene_id for shot in shots)
    issues = []
    scene_ids = {scene.scene_id for scene in scenes}
    character_ids = {character.character_id for character in characters}
    for scene in scenes:
        if shot_counts.get(scene.scene_id, 0) == 0:
            issues.append(f"{scene.scene_id} has no shots")
        unknown = set(scene.character_ids) - character_ids
        if unknown:
            issues.append(f"{scene.scene_id} references unknown characters: {sorted(unknown)}")
    for shot in shots:
        if shot.scene_id not in scene_ids:
            issues.append(f"{shot.shot_id} references unknown scene {shot.scene_id}")
    return {
        "character_bibles": {
            character.character_id: {
                "name": character.name,
                "appearance": character.appearance,
                "voice": character.voice,
                "continuity": character.continuity,
            }
            for character in characters
        },
        "scene_transitions": [
            {
                "from": scenes[index].scene_id,
                "to": scenes[index + 1].scene_id,
                "carry": scenes[index].continuity_out,
                "receive": scenes[index + 1].continuity_in,
            }
            for index in range(max(0, len(scenes) - 1))
        ],
        "tracked_departments": [
            "cast performance", "wardrobe", "hair and makeup", "props", "set dressing",
            "weather", "time of day", "damage", "screen direction", "camera and lens", "sound perspective",
        ],
        "issues": issues,
        "passed": not issues,
    }
