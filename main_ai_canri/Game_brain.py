"""
Game_brain.py
Canri AI

Game_brain is Canri's game-design expert.
It defines game type, core loop, systems, mechanics, balance, design graph,
and which brains should continue the work.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json


DATA_DIR = Path(__file__).parent / "data"
TYPES_FILE = DATA_DIR / "Game_types.json"
MECHANICS_FILE = DATA_DIR / "Game_mechanics.json"
SYSTEMS_FILE = DATA_DIR / "Game_systems.json"
BALANCE_FILE = DATA_DIR / "Game_balance_rules.json"
GRAPH_FILE = DATA_DIR / "Game_design_graph.json"
STATS_FILE = DATA_DIR / "Game_statistics.json"

MAX_MATCHES = 8

GENERIC_TERMS = {
    "game", "make", "create", "build", "the", "and", "for", "with",
    "תעשה", "תכין", "לי", "משחק", "של", "את"
}


class GameBrain:

    def __init__(self):

        self.types = self.load_json(TYPES_FILE, {})
        self.mechanics = self.load_json(MECHANICS_FILE, {})
        self.systems = self.load_json(SYSTEMS_FILE, {})
        self.balance_rules = self.load_json(BALANCE_FILE, {})
        self.design_graph = self.load_json(GRAPH_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        print("Game Brain Loaded")

    # ---------- loading ----------

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

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "game",
                "intent": "game_design",
                "words": []
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_memory_report(self, data):

        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]

        return {}

    def extract_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in [
                "original_text", "corrected_text", "user_message", "question",
                "query", "text", "goal", "game", "prompt"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_terms(self, report, memory_report, text):

        terms = []

        for key in ["main_topic", "intent", "language", "target_language"]:
            value = report.get(key)
            if value and value != "unknown":
                terms.append(str(value))

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            terms.extend(str(topic) for topic in topics)

        for task in report.get("possible_tasks", []):
            terms.append(str(task).replace("_", " "))

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            if word_data.get("word"):
                terms.append(str(word_data["word"]))

            terms.extend(str(x) for x in word_data.get("connections", [])[:8])

        terms.extend(str(x) for x in memory_report.get("current_keywords", [])[:20])

        terms.extend(
            re.findall(
                r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
                text
            )
        )

        clean = []
        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip().replace("_", " ")
            if term and len(term) > 1 and term not in GENERIC_TERMS and term not in clean:
                clean.append(term)

        return clean[:100]

    # ---------- detection ----------

    def detect_game_type(self, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        aliases = {
            "platformer": ["platformer", "jump", "platform", "mario"],
            "rpg": ["rpg", "role", "quest", "level up", "inventory"],
            "puzzle": ["puzzle", "solve", "logic", "brain"],
            "survival": ["survival", "craft", "hunger", "survive"],
            "strategy": ["strategy", "resource", "units", "base"],
            "shooter": ["shooter", "gun", "aim", "fps"],
            "racing": ["racing", "car", "track", "speed"],
            "simulation": ["simulation", "simulator", "manage"],
            "card_game": ["card", "deck", "cards"],
            "adventure": ["adventure", "explore", "story"]
        }

        for game_type, words in aliases.items():
            if any(word in lowered for word in words):
                return game_type

        return "rpg" if "game" in lowered else "adventure"

    def detect_perspective(self, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        for perspective in [
            "first_person", "third_person", "top_down", "side_scroller",
            "isometric", "text_based", "grid_based", "turn_based",
            "real_time", "2d"
        ]:
            if perspective.replace("_", " ") in lowered or perspective in lowered:
                return perspective

        if "2d" in lowered:
            return "2d"
        if "turn" in lowered:
            return "turn_based"

        return "2d"

    def detect_target(self, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        for target in [
            "beginner", "casual", "advanced", "children", "teens",
            "speedrunners", "story_players", "competitive", "solo", "co_op"
        ]:
            if target.replace("_", " ") in lowered or target in lowered:
                return target

        return "casual"

    def detect_difficulty(self, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        for difficulty in ["expert", "hard", "adaptive", "normal", "easy"]:
            if difficulty in lowered:
                return difficulty

        return "normal"

    # ---------- search ----------

    def score_item(self, item, terms, desired):

        searchable = " ".join(
            str(value)
            for value in item.values()
            if isinstance(value, (str, int, float))
        ).lower()

        for value in item.values():
            if isinstance(value, list):
                searchable += " " + " ".join(str(x) for x in value).lower()

        score = 0
        matched = []

        for key, value in desired.items():
            if item.get(key) == value:
                score += 20
                matched.append(value)

        for term in terms:
            if term in searchable:
                score += 3
                matched.append(term)

        return score, list(dict.fromkeys(matched))

    def find_best(self, collection, terms, desired):

        matches = []

        for item in collection.values():
            score, matched = self.score_item(item, terms, desired)
            if score > 0:
                matches.append({
                    "score": score,
                    "matched_terms": matched,
                    "item": item
                })

        matches.sort(key=lambda result: result["score"], reverse=True)
        return matches[:MAX_MATCHES]

    # ---------- design building ----------

    def build_core_loop(self, type_match):

        item = type_match.get("item", {}) if type_match else {}
        return item.get("core_loop", ["play", "learn rule", "improve", "win objective"])

    def build_system_plan(self, system_matches, game_type, required_systems=None):

        systems = []
        seen = set()
        required_systems = required_systems or []

        for match in system_matches[:80]:
            item = match["item"]
            system_name = item.get("system")

            if system_name in seen:
                continue

            seen.add(system_name)

            systems.append({
                "system": system_name,
                "responsibility": item.get("responsibility"),
                "depends_on": item.get("depends_on", []),
                "feeds_into": item.get("feeds_into", []),
                "suggested_code_units": item.get("suggested_code_units", []),
                "order": self.system_order(item.get("system"))
            })

            if len(systems) >= 12:
                break

        for required_system in required_systems:
            if required_system in seen:
                continue

            systems.append({
                "system": required_system,
                "responsibility": f"{required_system.replace('_', ' ')} is required for a {game_type} game.",
                "depends_on": [],
                "feeds_into": [],
                "suggested_code_units": [],
                "order": self.system_order(required_system)
            })
            seen.add(required_system)

        if not systems:
            for name in ["input_system", "player_system", "world_system", "ui_system", "save_system"]:
                systems.append({
                    "system": name,
                    "responsibility": f"{name.replace('_', ' ')} for {game_type}",
                    "depends_on": [],
                    "feeds_into": [],
                    "suggested_code_units": [],
                    "order": self.system_order(name)
                })

        systems.sort(key=lambda item: item["order"])
        return systems

    def system_order(self, system):

        order = {
            "input_system": 10,
            "player_system": 20,
            "world_system": 30,
            "level_system": 35,
            "enemy_system": 40,
            "combat_system": 50,
            "inventory_system": 50,
            "quest_system": 60,
            "ui_system": 70,
            "save_system": 85,
            "tutorial_system": 90
        }

        return order.get(system, 55)

    def build_mechanics(self, mechanic_matches):

        mechanics = []
        seen = set()

        for match in mechanic_matches[:12]:
            item = match["item"]
            mechanic_name = item.get("mechanic")

            if mechanic_name in seen:
                continue

            seen.add(mechanic_name)

            mechanics.append({
                "mechanic": mechanic_name,
                "purpose": item.get("purpose"),
                "inputs": item.get("inputs", []),
                "outputs": item.get("outputs", []),
                "quality_checks": item.get("quality_checks", [])
            })

        return mechanics

    def build_balance(self, balance_matches):

        rules = []
        seen = set()

        for match in balance_matches[:16]:
            item = match["item"]
            mechanic = item.get("mechanic")

            if mechanic in seen:
                continue

            seen.add(mechanic)

            rules.append({
                "mechanic": mechanic,
                "rule": item.get("rule"),
                "tuning_values": item.get("tuning_values", {}),
                "signals_to_watch": item.get("signals_to_watch", []),
                "fixes": item.get("fixes", [])
            })

            if len(rules) >= 8:
                break

        return rules

    def build_design_graph(self, graph_matches):

        nodes = []
        seen = set()

        for match in graph_matches[:32]:
            item = match["item"]
            key = (
                item.get("system"),
                item.get("mechanic")
            )

            if key in seen:
                continue

            seen.add(key)

            nodes.append({
                "system": item.get("system"),
                "mechanic": item.get("mechanic"),
                "requires": item.get("requires", []),
                "connects_to": item.get("connects_to", []),
                "design_order": item.get("design_order"),
                "implementation_hint": item.get("implementation_hint")
            })

            if len(nodes) >= 12:
                break

        nodes.sort(key=lambda item: item.get("design_order", 55))
        return nodes

    def call_creative_if_needed(self, data, confidence):

        if confidence >= 65:
            return None

        try:
            from Creative_brain import CreativeBrain
            creative = CreativeBrain()
            return creative.rescue_brain(
                "Game_brain",
                "game concept is weak or underspecified",
                data,
                "game concept direction"
            )
        except Exception as error:
            return {
                "brain": "Creative_brain",
                "error": str(error)
            }

    def estimate_confidence(self, matches):

        score = 35

        for key, value in matches.items():
            if value:
                score += min(value[0].get("score", 0), 30) / 2

        return round(min(score, 100), 2)

    def estimate_scope(self, game_type, systems, mechanics):

        score = 25 + len(systems) * 4 + len(mechanics) * 3

        if game_type in ["rpg", "strategy", "survival", "simulation"]:
            score += 20

        if score >= 85:
            return "large"
        if score >= 60:
            return "medium"
        return "small"

    def needed_brains(self, game_type, systems, creative_used):

        brains = ["Planner_brain", "Code_brain", "Technology_brain", "Security_brain"]

        if creative_used:
            brains.insert(0, "Creative_brain")

        if game_type in ["rpg", "adventure"]:
            brains.extend(["Story_brain", "Character_brain", "World_brain"])

        if any(system.get("system") == "audio_system" for system in systems):
            brains.append("Voice_brain")

        return list(dict.fromkeys(brains + ["Response_brain"]))

    # ---------- stats ----------

    def update_statistics(self, design):

        stats = self.statistics.get("Game_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_game_type"] = design.get("game_type")
        stats["last_scope"] = design.get("scope")
        stats["last_confidence"] = design.get("confidence")
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("types", len(self.types))
        stats.setdefault("mechanics", len(self.mechanics))
        stats.setdefault("systems", len(self.systems))
        stats.setdefault("balance_rules", len(self.balance_rules))
        stats.setdefault("design_graph", len(self.design_graph))
        self.statistics["Game_brain"] = stats
        self.save_statistics()

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        terms = self.collect_terms(report, memory_report, text)

        game_type = self.detect_game_type(terms, text)
        perspective = self.detect_perspective(terms, text)
        target = self.detect_target(terms, text)
        difficulty = self.detect_difficulty(terms, text)

        desired = {
            "game_type": game_type,
            "perspective": perspective,
            "target_audience": target,
            "difficulty_mode": difficulty
        }

        type_matches = self.find_best(self.types, terms, desired)
        mechanic_matches = self.find_best(self.mechanics, terms, {"game_type": game_type, "difficulty_mode": difficulty})
        system_matches = self.find_best(self.systems, terms, {"game_type": game_type, "perspective": perspective})
        balance_matches = self.find_best(self.balance_rules, terms, {"game_type": game_type, "difficulty_mode": difficulty})
        graph_matches = self.find_best(self.design_graph, terms, {"game_type": game_type, "perspective": perspective})

        matches = {
            "types": type_matches,
            "mechanics": mechanic_matches,
            "systems": system_matches,
            "balance": balance_matches,
            "graph": graph_matches
        }

        best_type = type_matches[0] if type_matches else {}
        required_systems = best_type.get("item", {}).get("required_systems", [])

        core_loop = self.build_core_loop(best_type)
        systems = self.build_system_plan(system_matches, game_type, required_systems)
        mechanics = self.build_mechanics(mechanic_matches)
        balance = self.build_balance(balance_matches)
        design_graph = self.build_design_graph(graph_matches)
        confidence = self.estimate_confidence(matches)
        creative_fallback = self.call_creative_if_needed(data, confidence)
        scope = self.estimate_scope(game_type, systems, mechanics)

        design = {
            "game_type": game_type,
            "perspective": perspective,
            "target_audience": target,
            "difficulty_mode": difficulty,
            "scope": scope,
            "core_loop": core_loop,
            "systems": systems,
            "mechanics": mechanics,
            "balance_rules": balance,
            "design_graph": design_graph,
            "win_condition": self.win_condition(game_type),
            "lose_condition": self.lose_condition(game_type),
            "prototype_order": [system["system"] for system in systems[:8]],
            "confidence": confidence
        }

        self.update_statistics(design)

        return {
            "brain": "Game_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "terms_used": terms,
            "design": design,
            "creative_fallback": creative_fallback,
            "confidence": confidence,
            "local_matches": {
                key: len(value)
                for key, value in matches.items()
            },
            "suggested_next_brains": self.needed_brains(game_type, systems, bool(creative_fallback)),
            "data_files_used": [
                "Game_types.json",
                "Game_mechanics.json",
                "Game_systems.json",
                "Game_balance_rules.json",
                "Game_design_graph.json",
                "Game_statistics.json"
            ],
            "rules": [
                "Define gameplay before code.",
                "Core loop must be clear.",
                "Systems must be ordered by dependency.",
                "Balance must include signals to watch.",
                "Use Creative_brain when the concept is weak.",
                "Use Code_brain only after design and plan are clear."
            ]
        }

    def win_condition(self, game_type):

        return {
            "platformer": "reach the end of the level",
            "rpg": "complete quests and defeat major threats",
            "puzzle": "solve the puzzle state",
            "survival": "survive and stabilize resources",
            "strategy": "complete strategic objective",
            "shooter": "clear enemies or objective",
            "racing": "finish with best time or position",
            "simulation": "reach management goal",
            "card_game": "reduce opponent resources or complete win combo",
            "adventure": "resolve story objective"
        }.get(game_type, "complete the main objective")

    def lose_condition(self, game_type):

        return {
            "platformer": "fall, lose health, or run out of attempts",
            "rpg": "party defeat or failed critical objective",
            "puzzle": "invalid state or time limit",
            "survival": "resources or health reach zero",
            "strategy": "base destroyed or objective failed",
            "shooter": "player defeated",
            "racing": "time limit or last place",
            "simulation": "system collapse or failure threshold",
            "card_game": "health, deck, or score condition lost",
            "adventure": "blocked progression or failed story condition"
        }.get(game_type, "fail the main objective")


brain = GameBrain()
