import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Game_brain import GameBrain


brain = GameBrain()

request = {
    "understanding": {
        "original_text": "Create a 2D RPG game in Python with inventory, enemies, combat, quests, and save system",
        "main_topic": "game",
        "intent": "game_creation",
        "topics": {
            "game": 1,
            "rpg": 1,
            "python": 1,
            "inventory": 1,
            "combat": 1
        },
        "possible_tasks": [
            "game_design",
            "code_generation",
            "planning"
        ],
        "words": [
            {
                "word": "rpg",
                "exists": True,
                "connections": ["quest", "inventory", "combat", "level up"]
            },
            {
                "word": "enemy",
                "exists": True,
                "connections": ["combat", "ai", "health"]
            }
        ]
    },
    "memory": {
        "memory_found": 1,
        "current_keywords": ["python", "rpg", "inventory", "save system"]
    }
}

result = brain.process(request)
design = result["design"]

print(json.dumps({
    "brain": result["brain"],
    "game_type": design["game_type"],
    "perspective": design["perspective"],
    "scope": design["scope"],
    "core_loop": design["core_loop"],
    "systems": [system["system"] for system in design["systems"][:8]],
    "mechanics": [mechanic["mechanic"] for mechanic in design["mechanics"][:8]],
    "balance_rules": len(design["balance_rules"]),
    "graph_nodes": len(design["design_graph"]),
    "confidence": result["confidence"],
    "suggested_next_brains": result["suggested_next_brains"]
}, ensure_ascii=False, indent=2))
