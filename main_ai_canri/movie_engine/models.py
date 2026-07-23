"""Serializable domain models for a complete movie project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import to_primitive


@dataclass
class MovieRequest:
    prompt: str
    title: str
    duration_seconds: int
    genre: str = "drama"
    tone: str = "cinematic"
    language: str = "English"
    audience_rating: str = "PG-13"
    realism: str = "photorealistic"
    render_profile: dict[str, Any] = field(default_factory=dict)
    render_requested: bool = True
    save_project: bool = True
    requirements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass
class CharacterProfile:
    character_id: str
    name: str
    role: str
    goal: str
    conflict: str
    arc: str
    appearance: str = ""
    voice: str = ""
    continuity: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    scene_id: str
    sequence_id: str
    act: int
    number: int
    heading: str
    location: str
    time_of_day: str
    duration_seconds: int
    purpose: str
    conflict: str
    turning_point: str
    action: str
    dialogue_beats: list[str] = field(default_factory=list)
    character_ids: list[str] = field(default_factory=list)
    continuity_in: list[str] = field(default_factory=list)
    continuity_out: list[str] = field(default_factory=list)


@dataclass
class Shot:
    shot_id: str
    scene_id: str
    number: int
    duration_seconds: int
    framing: str
    lens_mm: int
    camera_move: str
    subject: str
    action: str
    lighting: str
    audio_cue: str
    vfx_notes: str = ""
    asset_ids: list[str] = field(default_factory=list)


@dataclass
class AssetRequirement:
    asset_id: str
    asset_type: str
    name: str
    description: str
    source: str = "generate_or_produce"
    status: str = "required"
    scenes: list[str] = field(default_factory=list)


@dataclass
class RenderJob:
    job_id: str
    shot_id: str
    duration_seconds: int
    prompt: str
    negative_prompt: str
    reference_assets: list[str]
    output_file: str
    status: str = "pending"


@dataclass
class MovieProject:
    project_id: str
    request: MovieRequest
    creative_brief: dict[str, Any]
    story: dict[str, Any]
    characters: list[CharacterProfile]
    world: dict[str, Any]
    scenes: list[Scene]
    shots: list[Shot]
    assets: list[AssetRequirement]
    audio_plan: dict[str, Any]
    vfx_plan: dict[str, Any]
    production_plan: dict[str, Any]
    render_manifest: dict[str, Any]
    validation: dict[str, Any] = field(default_factory=dict)
    source_receipts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)
