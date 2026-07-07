import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Manager_brain import ManagerBrain
from Memory_brain import MEMORY_FILE
from Memory_brain import MemoryBrain


class DummyBrain:
    def __init__(self, name, confidence=80):
        self.name = name
        self.confidence = confidence

    def process(self, data):
        return {
            "brain": self.name,
            "confidence": self.confidence,
            "used_understanding_report": bool(data.get("understanding")),
            "used_memory_report": bool(data.get("memory")),
            "suggested_next_brains": ["Response_brain"]
        }


report = {
    "original_text": "Create Python code that reads JSON and checks if the user asks about Japan",
    "main_topic": "code",
    "intent": "code_generation",
    "topics": {
        "code": 1,
        "python": 1,
        "json": 1,
        "geography": 1
    },
    "possible_tasks": [
        "code_generation",
        "file_io"
    ],
    "words": [
        {
            "word": "python",
            "exists": True,
            "connections": ["code", "json"]
        },
        {
            "word": "japan",
            "exists": True,
            "connections": ["geography", "country"]
        }
    ]
}

memory = MemoryBrain()
memory_result = memory.process(report)

manager = ManagerBrain()

for name in [
    "Emotion_brain",
    "Security_brain",
    "Research_brain",
    "Reasoning_brain",
    "Technology_brain",
    "Code_brain",
    "Fact_Check_brain",
    "Response_brain"
]:
    manager.register_brain(name, DummyBrain(name))

manager_result = manager.process(memory_result)

print(json.dumps({
    "memory_found": memory_result["memory"]["memory_found"],
    "memory_depth": memory_result["memory"]["memory_depth"],
    "domains_detected": manager_result["domains_detected"],
    "brains_used": manager_result["brains_used"],
    "system_confidence": manager_result["system_confidence"],
    "missing_or_skipped": manager_result["missing_or_skipped"]
}, ensure_ascii=False, indent=2))

if MEMORY_FILE.exists():
    database = json.loads(
        MEMORY_FILE.read_text(
            encoding="utf-8"
        )
    )
    database["episodes"] = [
        episode
        for episode in database.get("episodes", [])
        if report["original_text"] not in episode.get("text", "")
    ]
    database["semantic_memory"] = {
        "topics": {},
        "intents": {},
        "keywords": {},
        "tasks": {}
    }
    MEMORY_FILE.write_text(
        json.dumps(
            database,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )
