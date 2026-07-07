import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Learning_brain import BRAIN_PERFORMANCE_FILE
from Learning_brain import IMPROVEMENT_QUEUE_FILE
from Learning_brain import LEARNING_HISTORY_FILE
from Learning_brain import LEARNING_RULES_FILE
from Learning_brain import LEARNING_STATS_FILE
from Learning_brain import LearningBrain


FILES = [
    LEARNING_HISTORY_FILE,
    LEARNING_STATS_FILE,
    BRAIN_PERFORMANCE_FILE,
    LEARNING_RULES_FILE,
    IMPROVEMENT_QUEUE_FILE
]


def read_originals():
    originals = {}
    for path in FILES:
        originals[path] = path.read_text(encoding="utf-8") if path.exists() else None
    return originals


def restore_originals(originals):
    for path, text in originals.items():
        if text is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(text, encoding="utf-8")


originals = read_originals()

try:
    brain = LearningBrain()

    result = brain.process({
        "understanding": {
            "original_text": "Build a Python RPG game",
            "main_topic": "game",
            "intent": "game_creation"
        },
        "memory": {
            "memory_found": 1,
            "current_keywords": ["game", "python", "rpg"]
        },
        "results": {
            "Game_brain": {
                "brain": "Game_brain",
                "confidence": 92,
                "design": {
                    "game_type": "rpg"
                }
            },
            "Code_brain": {
                "brain": "Code_brain",
                "confidence": 35,
                "needs_creative_brain": True,
                "missing": ["Programming language unclear"]
            }
        }
    })

    print(json.dumps({
        "brain": result["brain"],
        "results_analyzed": result["results_analyzed"],
        "learned_count": len(result["learned"]),
        "weaknesses_count": len(result["weaknesses_found"]),
        "improvements_count": len(result["improvement_suggestions"]),
        "creative_help_count": len(result["creative_help"]),
        "code_reliability": result["reliability"]["Code_brain"],
        "confidence": result["confidence"]
    }, ensure_ascii=False, indent=2))

finally:
    restore_originals(originals)
