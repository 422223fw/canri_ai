import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"


def load(name):
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


articles = load("Articles.json")
statistics = load("Articles_statistics.json")
sources = load("research_sources.json")

print("articles:", len(articles))
print("statistics entries:", len(statistics))
print("collection stats:", statistics.get("_collection_statistics", {}))
print("first generated article:", articles[17]["id"], articles[17]["title"])
print("first generated fields:", {
    "field": articles[17].get("field"),
    "subfield": articles[17].get("subfield"),
    "difficulty": articles[17].get("difficulty"),
    "content_length": len(articles[17].get("content", "")),
    "source_recommendations": articles[17].get("source_recommendations"),
})
print("wikipedia source:", [source for source in sources if source.get("id") == "wikipedia"])

sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))
from Science_brain import ScienceBrain


brain = ScienceBrain()
result = brain.process({
    "original_text": "What is quantum entanglement?",
    "main_topic": "physics",
    "topics": {"physics": 1},
    "words": [
        {"word": "quantum", "exists": True, "connections": ["physics", "measurement"]},
        {"word": "entanglement", "exists": True, "connections": ["superposition", "particle"]},
    ],
})

print("science result confidence:", result["confidence"])
print("science result articles_found:", result["articles_found"])
print("science result top:", result["top_article_ids"][:3])
