"""Single registry for every Canri brain.

The established brains remain import-compatible at the project root while the
registry gives the application one organized loading boundary. New brains live
inside this package and expose small root-level compatibility modules.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


BRAIN_MODULES = (
    "Main_brain",
    "Manager_brain",
    "Spelling_brain",
    "Understanding_brain",
    "Memory_brain",
    "Research_brain",
    "Reasoning_brain",
    "Response_brain",
    "Creative_brain",
    "Code_brain",
    "Math_brain",
    "Science_brain",
    "Language_brain",
    "History_brain",
    "Geography_brain",
    "Technology_brain",
    "Game_brain",
    "Story_brain",
    "Character_brain",
    "World_brain",
    "Image_brain",
    "Movie_brain",
    "Vision_brain",
    "Voice_brain",
    "Learning_brain",
    "Fact_Check_brain",
    "Quality_Control_brain",
    "Collaboration_brain",
    "Nervous_system_brain",
    "Planner_brain",
    "Emotion_brain",
    "Answer_Enrichment_brain",
    "Security_brain",
    "Project_context_brain",
    "Agent_brain",
)


def load_brain_registry() -> dict[str, Any]:
    registry: dict[str, Any] = {}
    failures: dict[str, str] = {}
    for module_name in BRAIN_MODULES:
        try:
            module = import_module(module_name)
            brain = getattr(module, "brain", None)
            if brain is None:
                failures[module_name] = "module has no brain object"
                continue
            registry[module_name] = brain
        except Exception as error:
            failures[module_name] = f"{type(error).__name__}: {error}"
    registry["_load_failures"] = failures
    return registry

