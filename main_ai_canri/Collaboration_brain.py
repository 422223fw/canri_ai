"""Structured, bounded consultation between Canri specialist brains."""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json, load_json_resilient


DATA_DIR = Path(__file__).parent / "data"
RULES_FILE = DATA_DIR / "Brain_collaboration_rules.json"
STATISTICS_FILE = DATA_DIR / "Brain_collaboration_statistics.json"


class CollaborationBrain:
    """Plans consultations and consolidates their results without calling brains itself."""

    STRUCTURAL_BRAINS = {
        "Collaboration_brain",
        "Manager_brain",
        "Memory_brain",
        "Emotion_brain",
        "Security_brain",
        "Quality_Control_brain",
        "Response_brain",
        "Learning_brain",
    }

    DEFAULT_DOMAIN_TEAMS = {
        "code": ["Code_brain", "Planner_brain", "Reasoning_brain", "Technology_brain"],
        "math": ["Math_brain", "Reasoning_brain"],
        "story": ["Story_brain", "Character_brain", "World_brain", "Creative_brain"],
        "knowledge": ["Research_brain", "Fact_Check_brain", "Reasoning_brain"],
        "science": ["Science_brain", "Research_brain", "Fact_Check_brain"],
        "technology": ["Technology_brain", "Research_brain", "Fact_Check_brain"],
        "geography": ["Geography_brain", "Research_brain", "Fact_Check_brain"],
        "game": ["Game_brain", "Code_brain", "Creative_brain", "Planner_brain"],
        "image_generation": ["Image_brain", "Creative_brain", "Vision_brain"],
        "language": ["Language_brain", "Spelling_brain", "Reasoning_brain"],
        "general": ["Reasoning_brain", "Research_brain", "Fact_Check_brain"],
    }

    def __init__(self):
        self.rules = self._load_json(RULES_FILE, {})
        self.max_participants = max(1, min(5, int(self.rules.get("max_participants", 5))))
        self.max_summary_chars = max(120, int(self.rules.get("max_summary_chars", 480)))
        print("Collaboration Brain Loaded")

    def _load_json(self, path, default):
        value = load_json_resilient(path, default)
        return value if isinstance(value, type(default)) else default

    def _save_statistics(self, result):
        stats = self._load_json(STATISTICS_FILE, {})
        stats["consultations"] = int(stats.get("consultations", 0)) + 1
        stats["last_round"] = result.get("round")
        stats["last_participants"] = result.get("participants", [])
        stats["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(STATISTICS_FILE, stats)

    def _domain(self, data):
        routing = data.get("routing_decision", {})
        if isinstance(routing, dict) and routing.get("primary_domain"):
            return str(routing["primary_domain"]).lower()
        understanding = data.get("understanding", {})
        if isinstance(understanding, dict):
            topic = understanding.get("main_topic") or understanding.get("intent")
            if topic:
                return str(topic).lower()
        return "general"

    def _domains(self, data):
        routing = data.get("routing_decision", {})
        if isinstance(routing, dict) and isinstance(routing.get("domains"), list):
            domains = [
                str(domain).lower()
                for domain in routing["domains"]
                if domain and str(domain).lower() != "memory_context"
            ]
            if domains:
                return list(dict.fromkeys(domains))[:4]
        return [self._domain(data)]

    def _useful_results(self, data):
        results = data.get("results", {})
        if not isinstance(results, dict):
            return {}
        return {
            name: value
            for name, value in results.items()
            if name not in self.STRUCTURAL_BRAINS
            and isinstance(value, dict)
            and not value.get("skipped")
            and not value.get("error")
        }

    def _summary(self, result):
        preferred = [
            "final_answer", "answer", "response", "result", "solution", "explanation",
            "code", "story", "plan", "analysis", "summary", "recommendation"
        ]
        parts = []
        for key in preferred:
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"{key}: {value.strip()}")
            elif isinstance(value, list) and value:
                parts.append(f"{key}: " + "; ".join(str(item) for item in value[:4]))
            if sum(len(item) for item in parts) >= self.max_summary_chars:
                break
        if not parts:
            visible = {
                key: value for key, value in result.items()
                if key not in {"performance", "data_context", "knowledge", "dictionary"}
            }
            parts.append(json.dumps(visible, ensure_ascii=False, default=str))
        return " ".join(parts)[:self.max_summary_chars]

    def _participants(self, domains, results, primary_brain=None):
        candidates = []
        for domain in domains:
            configured = self.rules.get("domain_teams", {}).get(domain, [])
            candidates.extend(
                configured or self.DEFAULT_DOMAIN_TEAMS.get(
                    domain, self.DEFAULT_DOMAIN_TEAMS["general"]
                )
            )
        if primary_brain:
            candidates.insert(0, primary_brain)
        candidates = list(dict.fromkeys(candidates))
        selected = [name for name in candidates if name in results]
        if not selected:
            selected = list(results)[:self.max_participants]
        return selected[:self.max_participants]

    def _question(self, brain_name, domain, primary_brain):
        if brain_name == primary_brain:
            return (
                "Review the peer findings, resolve relevant concerns, and produce an improved "
                "domain result that satisfies every user requirement."
            )
        if brain_name in {"Fact_Check_brain", "Research_brain"}:
            return "Check the other specialists' factual claims and identify unsupported or missing evidence."
        if brain_name == "Planner_brain":
            return "Check completeness, ordering, dependencies, and every small requirement in the proposed solution."
        if brain_name == "Reasoning_brain":
            return "Compare the proposed approaches, find contradictions, and recommend the most coherent solution."
        return f"Review the other {domain} specialists and give concrete corrections or additions."

    def _keywords(self, messages):
        stop = {
            "that", "with", "from", "this", "have", "will", "your", "into", "result",
            "brain", "code", "user", "request", "should", "about", "their", "then"
        }
        words = []
        for message in messages:
            words.extend(
                word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", message)
                if word.lower() not in stop
            )
        return [word for word, count in Counter(words).most_common(12) if count > 1]

    def process(self, data):
        if not isinstance(data, dict):
            data = {"original_text": str(data)}
        domain = self._domain(data)
        domains = self._domains(data)
        results = self._useful_results(data)
        round_name = str(data.get("collaboration_round", "planning"))
        routing = data.get("routing_decision", {})
        primary_brain = routing.get("primary_brain") if isinstance(routing, dict) else None
        participants = self._participants(domains, results, primary_brain)
        if primary_brain not in participants and participants:
            primary_brain = participants[0]

        transcript = []
        for name in participants:
            transcript.append({
                "speaker": name,
                "kind": "specialist_finding" if round_name == "planning" else "consultation_response",
                "message": self._summary(results[name]),
            })

        requests = []
        if round_name == "planning" and len(participants) > 1:
            for name in participants:
                peer_messages = [item for item in transcript if item["speaker"] != name]
                requests.append({
                    "target_brain": name,
                    "question": self._question(name, domain, primary_brain),
                    "peer_messages": peer_messages,
                    "must_preserve_user_requirements": True,
                })

        result = {
            "brain": "Collaboration_brain",
            "round": round_name,
            "domain": domain,
            "domains": domains,
            "participants": participants,
            "primary_brain": primary_brain,
            "transcript": transcript,
            "consultation_requests": requests,
            "consensus_terms": self._keywords([item["message"] for item in transcript]),
            "preferred_brain": primary_brain,
            "confidence": min(92, 60 + len(participants) * 9),
            "bounded": True,
            "user_visible": False,
            "instruction": (
                "Use this consultation to improve the final answer. Do not expose the internal transcript "
                "unless the user explicitly asks for processing details."
            ),
        }
        self._save_statistics(result)
        return result


brain = CollaborationBrain()
