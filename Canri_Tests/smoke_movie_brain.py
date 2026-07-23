"""Focused smoke checks for Movie_brain without copying the runtime tree."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANRI_DIR = ROOT / "main_ai_canri"
if str(CANRI_DIR) not in sys.path:
    sys.path.insert(0, str(CANRI_DIR))

from Movie_brain import brain  # noqa: E402
from movie_engine.duration import parse_duration_seconds  # noqa: E402


def build_payload(prompt: str) -> dict:
    report = {
        "original_text": prompt,
        "corrected_text": prompt,
        "main_topic": "movie",
        "intent": "movie_creation",
        "request_contract": {"requirements": []},
    }
    return {
        "original_text": prompt,
        "understanding": report,
        "_disable_persistence": True,
        "results": {
            "Creative_brain": {
                "final_output": (
                    "A radio engineer receives a warning from tomorrow through "
                    "a broken satellite and must act before the signal erases itself."
                ),
                "confidence": 92,
            },
            "Character_brain": {
                "characters": [
                    {"name": "Nora Hale", "role": "protagonist", "goal": "decode the warning"},
                    {"name": "Eli Voss", "role": "ally", "goal": "keep the station online"},
                ]
            },
            "World_brain": {
                "world": {
                    "name": "Coastal Array",
                    "locations": ["Storm radio station", "Cliff antenna field"],
                    "rules": ["Signals obey physical transmission delay."],
                }
            },
        },
    }


def assert_project(prompt: str, expected_seconds: int) -> None:
    result = brain.process(build_payload(prompt))
    project = result["movie_project"]
    assert result["duration_seconds"] == expected_seconds
    assert result["validation"]["passed"], result["validation"]
    assert sum(scene["duration_seconds"] for scene in project["scenes"]) == expected_seconds
    assert sum(shot["duration_seconds"] for shot in project["shots"]) == expected_seconds
    assert len(project["render_manifest"]["jobs"]) == len(project["shots"])
    assert result["creative_brain_used"] is True
    assert result["render_status"]["rendered"] is False
    assert result["render_status"]["status"] == "backend_required"


def main() -> None:
    assert parse_duration_seconds("Create a 12 hour movie") == 5 * 60 * 60
    assert_project(
        "Create a 2 minute photorealistic science fiction movie called Signal at Dawn",
        120,
    )
    assert_project(
        "Create a 5 hour photorealistic epic movie called Horizon",
        5 * 60 * 60,
    )
    print("movie brain smoke checks passed")


if __name__ == "__main__":
    main()
