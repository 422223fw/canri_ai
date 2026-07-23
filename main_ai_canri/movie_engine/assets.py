"""Build a deduplicated asset catalog and connect assets to shots."""

from __future__ import annotations

from collections import defaultdict

from .models import AssetRequirement, CharacterProfile, Scene, Shot
from .utils import stable_id


def build_assets(
    characters: list[CharacterProfile],
    scenes: list[Scene],
    shots: list[Shot],
) -> list[AssetRequirement]:
    assets = []
    character_asset_ids = {}
    for character in characters:
        asset_id = stable_id("asset_character", character.character_id)
        character_asset_ids[character.character_id] = asset_id
        assets.append(AssetRequirement(
            asset_id=asset_id,
            asset_type="character_reference",
            name=character.name,
            description=(
                f"Identity-locked reference for {character.name}: {character.appearance}; "
                f"voice and performance: {character.voice}"
            ),
            source="Character_brain_and_casting",
        ))

    location_scenes = defaultdict(list)
    for scene in scenes:
        location_scenes[scene.location].append(scene.scene_id)
    location_asset_ids = {}
    for location, scene_ids in location_scenes.items():
        asset_id = stable_id("asset_location", location)
        location_asset_ids[location] = asset_id
        assets.append(AssetRequirement(
            asset_id=asset_id,
            asset_type="environment",
            name=location,
            description=f"Photorealistic, production-designed environment with day/night and weather continuity for {location}.",
            source="World_brain_and_art_department",
            scenes=scene_ids,
        ))

    scene_map = {scene.scene_id: scene for scene in scenes}
    for shot in shots:
        scene = scene_map[shot.scene_id]
        references = [location_asset_ids[scene.location]]
        references.extend(
            character_asset_ids[character_id]
            for character_id in scene.character_ids
            if character_id in character_asset_ids
        )
        shot.asset_ids = list(dict.fromkeys(references))

    assets.extend([
        AssetRequirement(
            asset_id="asset_global_color_pipeline",
            asset_type="look_development",
            name="Show LUT and color pipeline",
            description="ACES-managed look development, camera transform, grain, halation, and delivery trims.",
            source="cinematography_department",
            scenes=[scene.scene_id for scene in scenes],
        ),
        AssetRequirement(
            asset_id="asset_global_audio_package",
            asset_type="audio",
            name="Production audio and score package",
            description="Dialogue, ADR, room tone, ambience, Foley, sound design, score, and final stems.",
            source="sound_department",
            scenes=[scene.scene_id for scene in scenes],
        ),
    ])
    return assets
