import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Code_brain import CodeBrain


brain = CodeBrain()

report = {
    "original_text": "Create Python code to safely load a JSON file",
    "main_topic": "code",
    "intent": "code_generation",
    "topics": {
        "code": 1,
        "python": 1,
        "json": 1
    },
    "possible_tasks": [
        "code_generation",
        "file_read"
    ],
    "words": [
        {
            "word": "python",
            "exists": True,
            "connections": ["code", "function"]
        },
        {
            "word": "json",
            "exists": True,
            "connections": ["file", "load", "data"]
        },
        {
            "word": "safe",
            "exists": True,
            "connections": ["error handling", "validation"]
        }
    ]
}

result = brain.process(report)

print(json.dumps({
    "brain": result["brain"],
    "used_understanding_report": result["used_understanding_report"],
    "language": result["language"],
    "task_type": result["task_type"],
    "confidence": result["confidence"],
    "matched_functions": result["matched_functions"],
    "selected": result["selected"][:5],
    "needs_creative_brain": result["needs_creative_brain"],
    "needs_security": result["needs_security"],
    "suggested_next_brains": result["suggested_next_brains"],
    "code_preview": result["generated_code"][:300]
}, ensure_ascii=True, indent=2))

unknown = brain.process({
    "original_text": "Create code for a quantum sandwich compiler in zorb language",
    "main_topic": "code",
    "intent": "code_generation",
    "words": [
        {
            "word": "zorb",
            "exists": False,
            "connections": []
        }
    ]
})

print(json.dumps({
    "unknown_language": unknown["language"],
    "unknown_confidence": unknown["confidence"],
    "unknown_needs_creative": unknown["needs_creative_brain"],
    "unknown_missing": unknown["missing"]
}, ensure_ascii=True, indent=2))
