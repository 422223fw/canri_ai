import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Creative_brain import CreativeBrain


brain = CreativeBrain()

request = {
    "understanding": {
        "original_text": "Invent a professional story concept about a child, a forbidden map, and a floating city",
        "main_topic": "story",
        "intent": "story_creation",
        "topics": {
            "story": 1,
            "fantasy": 1,
            "character": 1
        },
        "words": [
            {
                "word": "floating city",
                "exists": True,
                "connections": ["world", "mystery", "adventure"]
            },
            {
                "word": "map",
                "exists": True,
                "connections": ["secret", "quest", "danger"]
            }
        ]
    },
    "memory": {
        "memory_found": 1,
        "current_keywords": ["fantasy", "map", "child", "floating city"],
        "ranked_matches": [
            {
                "summary": "A previous story used a hidden city and a child hero.",
                "keywords": ["hidden city", "child", "quest"],
                "score": 78
            }
        ]
    }
}

result = brain.process(request)
rescue = brain.rescue_brain(
    "Planner_brain",
    "plan has missing story direction",
    request,
    "story plan direction"
)

print(json.dumps({
    "domain": result["domain"],
    "strategy": result["direction_analysis"]["preferred_strategy"],
    "stop_reason": result["evolution"]["stop_reason"],
    "strategic_stop": result["strategic_stop"],
    "best_score": result["quality"]["best_score"],
    "direction_good": result["quality"]["direction_good_enough"],
    "graph_used": result["quality"]["graph_used"],
    "ideas_stored": result["creative_memory"]["ideas_stored"],
    "rescue": {
        "rescued_brain": rescue["rescued_brain"],
        "needed_output": rescue["needed_output"],
        "plan_steps": len(rescue["rescue_plan"]),
        "confidence": rescue["confidence"]
    }
}, ensure_ascii=False, indent=2))
