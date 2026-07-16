"""Seed the scanner with 5,000 broad, non-fiction knowledge queries."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "main_ai_canri" / "data" / "Knowledge_queue.json"
TARGET = 5_000

TOPICS = [
    "artificial intelligence", "machine learning", "computer science", "software engineering",
    "computer security", "cryptography", "computer networks", "databases", "operating systems",
    "programming languages", "robotics", "cloud computing", "data science", "web technology",
    "computer graphics", "human computer interaction", "electronics", "semiconductors",
    "renewable energy", "electric vehicles", "physics", "quantum mechanics", "astronomy",
    "cosmology", "chemistry", "organic chemistry", "materials science", "biology", "genetics",
    "evolution", "ecology", "neuroscience", "medicine", "public health", "nutrition",
    "psychology", "cognitive science", "mathematics", "algebra", "geometry", "calculus",
    "statistics", "probability", "logic", "economics", "finance", "business management",
    "entrepreneurship", "supply chain", "agriculture", "climate science", "meteorology",
    "oceanography", "geology", "geography", "urban planning", "architecture", "civil engineering",
    "mechanical engineering", "chemical engineering", "aerospace engineering", "history of science",
    "ancient history", "medieval history", "modern history", "world history", "archaeology",
    "anthropology", "sociology", "political science", "international relations", "law",
    "education", "linguistics", "English grammar", "translation", "literature", "storytelling",
    "visual art", "music theory", "film studies", "game design", "product design", "photography",
    "communication", "journalism", "transportation", "space exploration", "environmental science",
    "water management", "disaster management", "manufacturing", "biotechnology", "nanotechnology",
    "pharmacology", "epidemiology", "sports science", "ethics", "philosophy", "critical thinking",
]

ASPECTS = [
    "fundamentals", "key concepts", "history", "modern applications", "major discoveries",
    "important researchers", "terminology", "methods", "tools", "systems", "processes",
    "measurement", "data collection", "data analysis", "common models", "theories", "principles",
    "practical examples", "case studies", "benefits", "limitations", "risks", "safety",
    "ethics", "standards", "best practices", "quality control", "testing", "reliability",
    "performance", "design", "implementation", "maintenance", "education", "careers",
    "current research", "future directions", "global impact", "environmental impact",
    "economic impact", "social impact", "health impact", "comparison", "classification",
    "problem solving", "decision making", "common mistakes", "frequently asked questions",
    "glossary", "overview",
]


def save_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    pending = queue.setdefault("pending", [])
    seen_queries = queue.setdefault("seen_queries", [])
    known = {str(value).strip().lower() for value in [*pending, *seen_queries]}
    additions = []

    for topic, aspect in product(TOPICS, ASPECTS):
        query = f"{topic}: {aspect}"
        if query.lower() in known:
            continue
        additions.append(query)
        known.add(query.lower())
        if len(additions) == TARGET:
            break

    if len(additions) != TARGET:
        raise RuntimeError(f"Expected {TARGET} new scanner queries, got {len(additions)}")
    pending.extend(additions)
    save_json(QUEUE_FILE, queue)
    print(json.dumps({"added": len(additions), "pending_total": len(pending)}, indent=2))


if __name__ == "__main__":
    main()
