import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Emotion_brain import EmotionBrain


brain = EmotionBrain()

report = {
    "original_text": "אני ממש מבולבל ולא הבנתי מה קרה, זה קצת מלחיץ אותי!",
    "main_topic": "technology",
    "intent": "question",
    "topics": {
        "technology": 1
    },
    "words": [
        {
            "word": "מבולבל",
            "exists": True,
            "connections": ["לא הבנתי", "confused"]
        },
        {
            "word": "מלחיץ",
            "exists": True,
            "connections": ["fear", "worried"]
        }
    ]
}

result = brain.process(report)

print(json.dumps({
    "brain": result["brain"],
    "used_understanding_report": result["used_understanding_report"],
    "primary_emotion": result["primary_emotion"],
    "tone": result["tone"],
    "intensity": result["intensity"],
    "response_style": result["response_style"],
    "needs_security": result["needs_security"],
    "suggested_next_brains": result["suggested_next_brains"],
    "evidence": result["evidence"]
}, ensure_ascii=True, indent=2))

crisis = brain.process({
    "original_text": "I want to die and hurt myself",
    "main_topic": "emotion",
    "intent": "help",
    "words": [
        {
            "word": "die",
            "exists": True,
            "connections": ["self harm"]
        }
    ]
})

print(json.dumps({
    "crisis_primary_emotion": crisis["primary_emotion"],
    "crisis_sensitivity": crisis["sensitivity"],
    "crisis_needs_security": crisis["needs_security"],
    "crisis_style": crisis["response_style"]
}, ensure_ascii=True, indent=2))
