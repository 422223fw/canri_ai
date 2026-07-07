import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Creative_brain import CreativeBrain
from Story_brain import StoryBrain
from Character_brain import CharacterBrain
from World_brain import WorldBrain


request = {
    "understanding": {
        "original_text": "Create a short fantasy story about a clever child who finds a forbidden map",
        "main_topic": "story",
        "intent": "story_creation",
        "topics": {
            "story": 1,
            "fantasy": 1,
            "character": 1,
            "world": 1
        },
        "possible_tasks": [
            "story_creation",
            "character_creation",
            "world_creation"
        ],
        "words": [
            {
                "word": "fantasy",
                "exists": True,
                "connections": ["magic", "quest", "world"]
            },
            {
                "word": "child",
                "exists": True,
                "connections": ["character", "curious", "growth"]
            }
        ]
    },
    "memory": {
        "memory_found": 1,
        "current_keywords": ["fantasy", "map", "child", "secret"],
        "ranked_matches": [
            {
                "summary": "Previous story used a hidden city and a brave child.",
                "score": 78,
                "keywords": ["hidden city", "child", "quest"]
            }
        ]
    }
}

creative = CreativeBrain().process(request)
character = CharacterBrain().process(request)
world = WorldBrain().process(request)
story = StoryBrain().process(request)

print(json.dumps({
    "creative": {
        "domain": creative["domain"],
        "best_score": creative["quality"]["best_score"],
        "stop_reason": creative["evolution"]["stop_reason"]
    },
    "character": {
        "name": character["character"]["name"],
        "needs_research": character["needs_research"]
    },
    "world": {
        "name": world["world"]["name"],
        "checks": len(world["consistency_checks"])
    },
    "story": {
        "type": story["story_type"],
        "tone": story["tone"],
        "outline_steps": len(story["outline"]),
        "has_draft": bool(story["draft"]),
        "confidence": story["confidence"]
    }
}, ensure_ascii=False, indent=2))
