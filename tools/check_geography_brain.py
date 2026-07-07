import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Geography_brain import GeographyBrain


brain = GeographyBrain()

japan_report = {
    "original_text": "Where is Japan and what is its capital?",
    "main_topic": "geography",
    "intent": "question",
    "topics": {
        "geography": 1,
        "country": 1
    },
    "possible_tasks": [
        "location_lookup",
        "capital_lookup"
    ],
    "words": [
        {
            "word": "Japan",
            "exists": True,
            "connections": ["country", "East Asia", "Tokyo", "Pacific Ocean"]
        },
        {
            "word": "capital",
            "exists": True,
            "connections": ["city", "government"]
        }
    ]
}

japan_result = brain.process(japan_report)

print(json.dumps({
    "brain": japan_result["brain"],
    "used_understanding_report": japan_result["used_understanding_report"],
    "intent": japan_result["intent"],
    "geography_type": japan_result["geography_type"],
    "place_detected": japan_result["place_detected"],
    "confidence": japan_result["confidence"],
    "needs_research": japan_result["needs_research"],
    "needs_map_or_gps": japan_result["needs_map_or_gps"],
    "facts": japan_result["facts"][:3],
    "top_matches": [
        match["name"]
        for match in japan_result["local_matches"][:3]
    ]
}, ensure_ascii=True, indent=2))

weather_report = {
    "original_text": "What is the weather today in Tokyo?",
    "main_topic": "geography",
    "intent": "question",
    "topics": {
        "geography": 1,
        "weather": 1
    },
    "words": [
        {
            "word": "Tokyo",
            "exists": True,
            "connections": ["Japan", "city", "weather"]
        },
        {
            "word": "weather",
            "exists": True,
            "connections": ["forecast", "current"]
        }
    ]
}

weather_result = brain.process(weather_report)

print(json.dumps({
    "weather_place": weather_result["place_detected"],
    "weather_intent": weather_result["intent"],
    "weather_needs_current_data": weather_result["needs_current_data"],
    "weather_needs_research": weather_result["needs_research"],
    "weather_research_brain": (
        weather_result["research_fallback"] or {}
    ).get("brain"),
    "weather_research_links": len(
        (
            weather_result["research_fallback"] or {}
        ).get("approved_research_links", [])
    )
}, ensure_ascii=True, indent=2))
