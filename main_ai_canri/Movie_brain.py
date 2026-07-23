"""
Movie_brain.py
Canri AI

Movie_brain coordinates Canri's specialist brains into one production package:
creative concept, screenplay, cast, world, scenes, camera shots, sound, VFX,
continuity, assets, schedule, budget, validation, and a provider-neutral render
manifest. It can hand the package to a host-configured video backend, but it
never claims a photorealistic master was rendered when no such backend exists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Brain_storage import atomic_write_json, load_json_resilient
from movie_engine import MoviePipeline


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "generated_movies"
GENRES_FILE = DATA_DIR / "Movie_genres.json"
CINEMATIC_FILE = DATA_DIR / "Movie_cinematic_profiles.json"
RENDER_FILE = DATA_DIR / "Movie_render_profiles.json"
PRODUCTION_FILE = DATA_DIR / "Movie_production_templates.json"
SAFETY_FILE = DATA_DIR / "Movie_safety_profiles.json"
STATISTICS_FILE = DATA_DIR / "Movie_statistics.json"


class MovieBrain:
    """High-level movie director and production orchestrator."""

    def __init__(self):
        self.genres = load_json_resilient(GENRES_FILE, {})
        self.cinematic_profiles = load_json_resilient(CINEMATIC_FILE, {})
        self.render_profiles = load_json_resilient(RENDER_FILE, {})
        self.production_templates = load_json_resilient(PRODUCTION_FILE, {})
        self.safety_profiles = load_json_resilient(SAFETY_FILE, {})
        self.statistics = load_json_resilient(STATISTICS_FILE, self.default_statistics())
        self.pipeline = MoviePipeline(OUTPUT_DIR)
        print("Movie Brain Loaded")

    @staticmethod
    def default_statistics() -> dict[str, Any]:
        return {
            "schema_version": 1,
            "projects": 0,
            "validated_projects": 0,
            "rendered_projects": 0,
            "total_planned_seconds": 0,
            "total_scenes": 0,
            "total_shots": 0,
            "last_project_utc": None,
        }

    @staticmethod
    def get_understanding_report(data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            for key in ("understanding", "understanding_report"):
                if isinstance(data.get(key), dict):
                    return data[key]
            if "main_topic" in data or "intent" in data:
                return data
        return {
            "original_text": str(data or ""),
            "main_topic": "movie",
            "intent": "movie_creation",
        }

    def update_statistics(self, result: dict[str, Any], disabled: bool) -> None:
        if disabled or result.get("blocked"):
            return
        self.statistics["projects"] = int(self.statistics.get("projects", 0)) + 1
        self.statistics["validated_projects"] = int(self.statistics.get("validated_projects", 0)) + int(
            bool(result.get("validation", {}).get("passed"))
        )
        self.statistics["rendered_projects"] = int(self.statistics.get("rendered_projects", 0)) + int(
            bool(result.get("render_status", {}).get("rendered"))
        )
        self.statistics["total_planned_seconds"] = int(self.statistics.get("total_planned_seconds", 0)) + int(
            result.get("duration_seconds", 0)
        )
        self.statistics["total_scenes"] = int(self.statistics.get("total_scenes", 0)) + int(
            result.get("scene_count", 0)
        )
        self.statistics["total_shots"] = int(self.statistics.get("total_shots", 0)) + int(
            result.get("shot_count", 0)
        )
        self.statistics["last_project_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(STATISTICS_FILE, self.statistics)

    def process(self, data: Any) -> dict[str, Any]:
        report = self.get_understanding_report(data)
        result = self.pipeline.build(data, report)
        result["configuration"] = {
            "genre_profile_available": result.get("movie_project", {}).get("request", {}).get("genre") in self.genres,
            "cinematic_profiles": sorted(self.cinematic_profiles)[:20],
            "render_profiles": sorted(self.render_profiles)[:20],
            "production_templates": sorted(self.production_templates)[:20],
            "safety_profile_loaded": bool(self.safety_profiles),
        }
        result["data_files_used"] = [
            GENRES_FILE.name,
            CINEMATIC_FILE.name,
            RENDER_FILE.name,
            PRODUCTION_FILE.name,
            SAFETY_FILE.name,
        ]
        result["suggested_next_brains"] = [
            "Creative_brain",
            "Story_brain",
            "Character_brain",
            "World_brain",
            "Image_brain",
            "Voice_brain",
            "Technology_brain",
            "Quality_Control_brain",
            "Response_brain",
        ]
        disabled = bool(isinstance(data, dict) and data.get("_disable_persistence"))
        self.update_statistics(result, disabled)
        return result


brain = MovieBrain()
