import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Planner_brain import PlannerBrain


brain = PlannerBrain()

report = {
    "understanding": {
        "original_text": "Build a professional Python JSON tool with safe loading, validation, and saving",
        "main_topic": "code",
        "intent": "code_generation",
        "topics": {
            "code": 1,
            "python": 1,
            "json": 1,
            "security": 1
        },
        "possible_tasks": [
            "code_generation",
            "planning",
            "file_io"
        ],
        "words": [
            {
                "word": "python",
                "exists": True,
                "connections": ["code", "function", "script"]
            },
            {
                "word": "json",
                "exists": True,
                "connections": ["file", "validation", "data"]
            }
        ]
    },
    "memory": {
        "memory_found": 1,
        "current_keywords": [
            "python",
            "json",
            "safe load",
            "validation"
        ],
        "ranked_matches": [
            {
                "summary": "Previous JSON code request",
                "keywords": ["python", "json", "file io", "validation"]
            }
        ]
    }
}

result = brain.process(report)
plan = result["plan"]

print(json.dumps({
    "brain": result["brain"],
    "domain": plan["domain"],
    "intent": plan["intent"],
    "scale": plan["scale"],
    "output": plan["output"],
    "steps": plan["estimated_steps"],
    "needed_brains": plan["needed_brains"],
    "risk_level": plan["risk_level"],
    "dependency_graph_used": plan["dependency_graph_used"],
    "memory_context_used": plan["memory_context_used"],
    "confidence": result["confidence"]
}, ensure_ascii=False, indent=2))
