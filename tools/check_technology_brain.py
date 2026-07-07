import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Technology_brain import TechnologyBrain


brain = TechnologyBrain()

report = {
    "original_text": "I want to build a robot with a microcontroller, sensors, motors, and safe power.",
    "main_topic": "technology",
    "intent": "architecture_planning",
    "topics": {
        "technology": 1,
        "hardware": 1,
        "robotics": 1
    },
    "possible_tasks": [
        "hardware_planning",
        "system_design"
    ],
    "words": [
        {
            "word": "robot",
            "exists": True,
            "connections": ["robotics", "motor", "sensor", "controller"]
        },
        {
            "word": "microcontroller",
            "exists": True,
            "connections": ["arduino", "gpio", "firmware"]
        },
        {
            "word": "sensor",
            "exists": True,
            "connections": ["voltage", "calibration", "noise"]
        }
    ]
}

result = brain.process(report)

print(json.dumps({
    "brain": result["brain"],
    "used_understanding_report": result["used_understanding_report"],
    "technology_domain": result["technology_domain"],
    "intent": result["intent"],
    "confidence": result["confidence"],
    "local_knowledge_found": result["local_knowledge_found"],
    "needs_code": result["needs_code"],
    "needs_security": result["needs_security"],
    "needs_research": result["needs_research"],
    "needs_hardware_check": result["needs_hardware_check"],
    "suggested_next_brains": result["suggested_next_brains"],
    "top_matches": [
        match["name"]
        for match in result["local_matches"][:3]
    ],
}, ensure_ascii=False, indent=2))

unknown_report = {
    "original_text": "Explain photonic neuromorphic chiplet packaging",
    "main_topic": "technology",
    "intent": "question",
    "topics": {
        "technology": 1
    },
    "words": [
        {
            "word": "photonic",
            "exists": True,
            "connections": ["chiplet", "neuromorphic", "packaging"]
        }
    ]
}

unknown_result = brain.process(unknown_report)

print(json.dumps({
    "unknown_confidence": unknown_result["confidence"],
    "unknown_needs_research": unknown_result["needs_research"],
    "unknown_research_brain": (
        unknown_result["research_fallback"] or {}
    ).get("brain"),
    "unknown_research_links": len(
        (
            unknown_result["research_fallback"] or {}
        ).get("approved_research_links", [])
    )
}, ensure_ascii=False, indent=2))
