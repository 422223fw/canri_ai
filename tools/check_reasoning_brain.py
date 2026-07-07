import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Reasoning_brain import ReasoningBrain


brain = ReasoningBrain()

request = {
    "understanding": {
        "original_text": "Why should a Python JSON tool validate data before saving it?",
        "main_topic": "code",
        "intent": "question",
        "topics": {
            "code": 1,
            "python": 1,
            "json": 1,
            "security": 1
        },
        "possible_tasks": [
            "reasoning",
            "code_review"
        ],
        "words": [
            {
                "word": "json",
                "exists": True,
                "connections": ["file", "data", "validation"]
            },
            {
                "word": "validate",
                "exists": True,
                "connections": ["safe", "check", "error"]
            }
        ]
    },
    "memory": {
        "memory_found": 1,
        "current_keywords": ["python", "json", "validation", "safe"],
        "ranked_matches": [
            {
                "summary": "Previous request used JSON loading and validation before saving files.",
                "score": 82,
                "keywords": ["python", "json", "file", "validation"]
            }
        ]
    },
    "facts": [
        "JSON files can contain missing or malformed fields.",
        "Validation checks data shape before the program saves output.",
        "Saving invalid data can create bugs later."
    ]
}

result = brain.process(request)

print(json.dumps({
    "brain": result["brain"],
    "domain": result["main_topic"],
    "intent": result["intent"],
    "mode": result["reasoning_mode"],
    "facts": len(result["facts_used"]),
    "connections": len(result["connections"]),
    "contradictions": len(result["contradictions"]),
    "evidence": result["evidence"]["evidence_level"],
    "conclusions": len(result["conclusions"]),
    "solutions": len(result["solutions"]),
    "confidence": result["confidence"],
    "suggested_next_brains": result["suggested_next_brains"]
}, ensure_ascii=False, indent=2))
