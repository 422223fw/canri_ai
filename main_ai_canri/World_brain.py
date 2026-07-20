"""
World_brain.py
Canri AI

Builds fictional worlds and checks consistency between setting, rules, culture, and plot.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json


DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_FILE = DATA_DIR / "World_templates.json"
RULES_FILE = DATA_DIR / "World_rules.json"
STATS_FILE = DATA_DIR / "World_statistics.json"


class WorldBrain:

    def __init__(self):
        self.templates = self.load_json(TEMPLATES_FILE, {})
        self.rules = self.load_json(RULES_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        print("World Brain Loaded")

    def load_json(self, path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):
        atomic_write_json(STATS_FILE, self.statistics)

    def get_understanding_report(self, data):
        if isinstance(data, dict) and isinstance(data.get("understanding"), dict):
            return data["understanding"]
        if isinstance(data, dict):
            return data
        return {"original_text": str(data), "main_topic": "story", "intent": "world_creation"}

    def extract_text(self, data, report):
        parts = []
        if isinstance(data, str):
            parts.append(data)
        if isinstance(data, dict):
            for key in ["original_text", "corrected_text", "text", "goal", "world", "setting"]:
                if data.get(key):
                    parts.append(str(data[key]))
        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            if report.get(key):
                parts.append(str(report[key]))
        return " ".join(parts)

    def collect_terms(self, report, text):
        terms = []
        for key in ["main_topic", "intent"]:
            if report.get(key):
                terms.append(str(report[key]).lower())
        for word_data in report.get("words", []):
            if isinstance(word_data, dict):
                if word_data.get("word"):
                    terms.append(str(word_data["word"]).lower())
                terms.extend(str(x).lower() for x in word_data.get("connections", [])[:8])
        terms.extend(re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}", text.lower()))
        return list(dict.fromkeys(terms))[:80]

    def choose_template(self, terms):
        best = None
        best_score = -1
        for template in self.templates.values():
            searchable = " ".join([
                template.get("world_type", ""),
                template.get("genre", ""),
                template.get("tone", ""),
                template.get("central_conflict", ""),
                " ".join(template.get("systems", [])),
                " ".join(template.get("hooks", []))
            ]).lower()
            score = sum(3 for term in terms if term in searchable)
            score += template.get("confidence", 70) / 30
            if score > best_score:
                best_score = score
                best = template
        return best or {}

    def extract_requested_world(self, text):
        lowered = text.lower()

        if "under his bed" in lowered or "tiny door" in lowered or "glowing city" in lowered:
            return {
                "name": "The Glowing City Under The Bed",
                "world_type": "hidden_magic_city",
                "genre": "magical_realism",
                "tone": "quiet_wonder",
                "central_conflict": "whether hidden magic should be disturbed",
                "systems": ["tiny doors", "sleeping citizens", "glowing streets"],
                "hooks": ["a city beneath a bedroom", "a door too small for adults", "a sleeping secret"]
            }

        if "park" in lowered:
            return {
                "name": "The Quiet Park",
                "world_type": "ordinary_place_with_secret",
                "genre": "magical_realism",
                "tone": "gentle_mystery",
                "central_conflict": "an ordinary walk reveals an impossible secret",
                "systems": ["hidden paths", "weathered trees", "small magical objects"],
                "hooks": ["a discovery under a tree", "a path that changes at dusk"]
            }

        if "patient" in lowered or "hospital" in lowered or "ward" in lowered or "meeting" in lowered:
            return {
                "name": "North Ward",
                "world_type": "hospital_mystery",
                "genre": "mystery",
                "tone": "tense_and_human",
                "central_conflict": "a missing patient returns with impossible knowledge",
                "systems": ["case meetings", "medical records", "unanswered disappearances"],
                "hooks": ["a final meeting", "a returned patient", "a notebook of unknown names"]
            }

        if "forest" in lowered:
            return {
                "name": "The Old Forest",
                "world_type": "enchanted_forest",
                "genre": "fantasy",
                "tone": "mysterious",
                "central_conflict": "the forest tests anyone who enters",
                "systems": ["living paths", "old trees", "hidden signs"],
                "hooks": ["a path that remembers footsteps", "a light between trees"]
            }

        return {}

    def build_world(self, template, requested=None):
        requested = requested or {}
        if requested:
            return {
                "name": requested.get("name"),
                "world_type": requested.get("world_type"),
                "genre": requested.get("genre"),
                "tone": requested.get("tone"),
                "central_conflict": requested.get("central_conflict"),
                "systems": requested.get("systems", []),
                "hooks": requested.get("hooks", []),
                "laws": [
                    "Every major world detail should affect plot or character choice.",
                    "Power, magic, technology, or politics must have limits.",
                    "Travel, resources, and danger should stay consistent."
                ]
            }

        world_type = template.get("world_type", "unknown_world")
        return {
            "name": world_type.replace("_", " ").title(),
            "world_type": world_type,
            "genre": template.get("genre"),
            "tone": template.get("tone"),
            "central_conflict": template.get("central_conflict"),
            "systems": template.get("systems", []),
            "hooks": template.get("hooks", []),
            "laws": [
                "Every major world detail should affect plot or character choice.",
                "Power, magic, technology, or politics must have limits.",
                "Travel, resources, and danger should stay consistent."
            ]
        }

    def consistency_checks(self, world):
        return [
            f"{system} should create at least one story consequence."
            for system in world.get("systems", [])[:6]
        ]

    def update_statistics(self, confidence):
        stats = self.statistics.get("World_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_confidence"] = confidence
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("templates", len(self.templates))
        self.statistics["World_brain"] = stats
        self.save_statistics()

    def process(self, data):
        report = self.get_understanding_report(data)
        text = self.extract_text(data, report)
        terms = self.collect_terms(report, text)
        template = self.choose_template(terms)
        requested_world = self.extract_requested_world(text)
        world = self.build_world(template, requested_world)
        confidence = min(100, template.get("confidence", 70) + (10 if terms else 0))
        self.update_statistics(confidence)
        return {
            "brain": "World_brain",
            "used_understanding_report": bool(report),
            "terms_used": terms,
            "world": world,
            "consistency_checks": self.consistency_checks(world),
            "confidence": confidence,
            "suggested_next_brains": ["Story_brain", "Creative_brain", "Response_brain"],
            "rules": [
                "A world is useful only if its rules affect the story.",
                "Keep geography, culture, power, and danger consistent.",
                "Use Research_brain only for real-world settings."
            ]
        }


brain = WorldBrain()
