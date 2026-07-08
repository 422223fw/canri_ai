"""
Character_brain.py
Canri AI

Creates fictional characters and marks real-person cases for verification.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_FILE = DATA_DIR / "Character_templates.json"
TRAITS_FILE = DATA_DIR / "Character_traits.json"
STATS_FILE = DATA_DIR / "Character_statistics.json"


class CharacterBrain:

    def __init__(self):
        self.templates = self.load_json(TEMPLATES_FILE, {})
        self.traits = self.load_json(TRAITS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        print("Character Brain Loaded")

    def load_json(self, path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):
        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def get_understanding_report(self, data):
        if isinstance(data, dict) and isinstance(data.get("understanding"), dict):
            return data["understanding"]
        if isinstance(data, dict):
            return data
        return {"original_text": str(data), "main_topic": "story", "intent": "character_creation"}

    def get_memory_report(self, data):
        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]
        return {}

    def extract_text(self, data, report):
        parts = []
        if isinstance(data, str):
            parts.append(data)
        if isinstance(data, dict):
            for key in ["original_text", "corrected_text", "text", "goal", "character", "name"]:
                if data.get(key):
                    parts.append(str(data[key]))
        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            if report.get(key):
                parts.append(str(report[key]))
        return " ".join(parts)

    def collect_terms(self, report, memory_report, text):
        terms = []
        for key in ["main_topic", "intent"]:
            if report.get(key):
                terms.append(str(report[key]).lower())
        for word_data in report.get("words", []):
            if isinstance(word_data, dict):
                if word_data.get("word"):
                    terms.append(str(word_data["word"]).lower())
                terms.extend(str(x).lower() for x in word_data.get("connections", [])[:8])
        terms.extend(str(x).lower() for x in memory_report.get("current_keywords", [])[:20])
        terms.extend(re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}", text.lower()))
        return list(dict.fromkeys(terms))[:80]

    def real_person_check(self, text, terms):
        lowered = text.lower()
        looks_real = any(term in lowered for term in ["real person", "famous", "celebrity", "אמיתי", "מפורסם"])
        capitalized_names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
        return {
            "needed": looks_real or bool(capitalized_names),
            "possible_names": capitalized_names[:6],
            "rule": "Do not invent facts about real people; use Research_brain and Fact_Check_brain."
        }

    def extract_requested_character(self, text):
        lowered = text.lower()
        named_match = re.search(r"\b(?:named|called)\s+([A-Z][a-zA-Z]+)\b", text)
        name = named_match.group(1) if named_match else None

        role = "character"
        for role_name in ["patient", "boy", "girl", "hero", "doctor", "student", "detective", "inventor", "child"]:
            if role_name in lowered:
                role = role_name
                break

        trait = None
        for trait_name in ["quiet", "shy", "brave", "careful", "curious", "honest", "stubborn", "kind"]:
            if trait_name in lowered:
                trait = trait_name
                break
        if trait is None and role == "patient":
            trait = "resilient"

        age_match = re.search(r"\b(\d{1,2})\s*(?:year|years|year-old|years-old)\b", lowered)
        age = int(age_match.group(1)) if age_match else None

        goal = "understand what changed"
        if "meeting" in lowered:
            goal = "return for the final meeting"
        elif "wake" in lowered:
            goal = "decide whether to wake what is sleeping"
        elif "save" in lowered:
            goal = "save someone before it is too late"
        elif "find" in lowered:
            goal = "find the hidden truth"

        flaw = "hesitates before hard choices"
        if "shy" in lowered:
            flaw = "struggles to speak up"
        elif "quiet" in lowered:
            flaw = "keeps important thoughts inside"
        elif "disappeared" in lowered or "vanished" in lowered:
            flaw = "carries a secret no one understands"
        elif "injured" in lowered or "hurt" in lowered:
            flaw = "must act while physically limited"

        return {
            "requested_name": name,
            "requested_role": role,
            "requested_trait": trait,
            "requested_age": age,
            "requested_goal": goal,
            "requested_flaw": flaw
        }

    def choose_template(self, terms):
        best = None
        best_score = -1
        term_text = " ".join(terms)
        for template in self.templates.values():
            searchable = " ".join([
                template.get("archetype", ""),
                template.get("trait", ""),
                template.get("flaw", ""),
                template.get("goal", ""),
                template.get("conflict_type", ""),
                template.get("voice_style", "")
            ]).lower()
            score = sum(3 for term in terms if term in searchable)
            if template.get("archetype", "") in term_text:
                score += 8
            score += template.get("confidence", 70) / 30
            if score > best_score:
                best_score = score
                best = template
        return best or {}

    def build_character(self, template, real_check, requested=None):
        requested = requested or {}
        name_seed = template.get("archetype", "character").replace("_", " ").title()
        role = requested.get("requested_role") or template.get("archetype")
        trait = requested.get("requested_trait") or template.get("trait")
        goal = requested.get("requested_goal") or template.get("goal")
        flaw = requested.get("requested_flaw") or template.get("flaw")
        name = requested.get("requested_name") or (
            "Daniel Vale" if role == "patient" else
            "Leo" if role == "boy" else
            "Maya" if role == "girl" else
            f"{name_seed} Concept"
        )
        return {
            "name": name,
            "role": role,
            "age": requested.get("requested_age"),
            "archetype": template.get("archetype"),
            "core_trait": trait,
            "flaw": flaw,
            "goal": goal,
            "conflict_type": template.get("conflict_type"),
            "voice_style": template.get("voice_style"),
            "arc": template.get("arc", []),
            "real_person_check": real_check,
            "profile": (
                f"{name} is a {trait} {str(role).replace('_', ' ')} "
                f"who wants to {goal} but struggles because they {flaw}."
            )
        }

    def update_statistics(self, confidence):
        stats = self.statistics.get("Character_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_confidence"] = confidence
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("templates", len(self.templates))
        self.statistics["Character_brain"] = stats
        self.save_statistics()

    def process(self, data):
        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        terms = self.collect_terms(report, memory_report, text)
        template = self.choose_template(terms)
        real_check = self.real_person_check(text, terms)
        requested = self.extract_requested_character(text)
        character = self.build_character(template, real_check, requested)
        confidence = min(100, template.get("confidence", 70) + (10 if terms else 0))
        self.update_statistics(confidence)
        return {
            "brain": "Character_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "terms_used": terms,
            "character": character,
            "confidence": confidence,
            "needs_research": real_check["needed"],
            "suggested_next_brains": [
                brain_name
                for brain_name in [
                    "Research_brain" if real_check["needed"] else None,
                    "Fact_Check_brain" if real_check["needed"] else None,
                    "Story_brain",
                    "Response_brain"
                ]
                if brain_name
            ],
            "rules": [
                "Invent fictional characters freely.",
                "Do not invent facts about real people.",
                "Characters need goal, flaw, conflict, and arc."
            ]
        }


brain = CharacterBrain()
