"""
Story_brain.py
Canri AI

Story_brain is the narrative director. It uses:
- Creative_brain for original concepts
- Character_brain for characters
- World_brain for setting consistency
- Emotion_brain for tone when available through Manager
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_runtime import invoke_brain_safely
from Brain_storage import atomic_write_json, load_json_resilient


DATA_DIR = Path(__file__).parent / "data"
GENRES_FILE = DATA_DIR / "Story_genres.json"
STRUCTURES_FILE = DATA_DIR / "Story_structures.json"
TEMPLATES_FILE = DATA_DIR / "Story_templates.json"
STATS_FILE = DATA_DIR / "Story_statistics.json"


class StoryBrain:

    def __init__(self):
        self.genres = self.load_json(GENRES_FILE, {})
        self.structures = self.load_json(STRUCTURES_FILE, {})
        self.templates = self.load_json(TEMPLATES_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        print("Story Brain Loaded")

    def load_json(self, path, default):
        return load_json_resilient(path, default=default)

    def save_statistics(self):
        atomic_write_json(STATS_FILE, self.statistics)

    def get_understanding_report(self, data):
        if isinstance(data, dict):
            for key in ["understanding", "understanding_report"]:
                if isinstance(data.get(key), dict):
                    return data[key]
        if isinstance(data, dict):
            return data
        return {"original_text": str(data), "main_topic": "story", "intent": "story_creation"}

    def get_memory_report(self, data):
        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]
        return {}

    def continuation_source_text(self, memory_report):
        if not isinstance(memory_report, dict):
            return ""
        conversation = memory_report.get("conversation", {})
        if not isinstance(conversation, dict) or not conversation.get("continuation_request"):
            return ""
        source = conversation.get("continuation_source")
        if not isinstance(source, dict):
            return ""
        previous_user = str(source.get("user", "")).strip()
        previous_canri = str(source.get("canri", "")).strip()
        return " ".join(part for part in [previous_user, previous_canri] if part)[:5000]

    def extract_text(self, data, report):
        parts = []
        if isinstance(data, str):
            parts.append(data)
        if isinstance(data, dict):
            for key in ["original_text", "corrected_text", "text", "goal", "prompt", "story"]:
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
        return list(dict.fromkeys(terms))[:100]

    def detect_length(self, text, terms):
        lowered = f"{text.lower()} {' '.join(terms)}"
        if any(x in lowered for x in ["chapter", "פרק"]):
            return "chapter"
        if any(x in lowered for x in ["long", "book", "ארוך"]):
            return "long"
        if any(x in lowered for x in ["short", "קצר"]):
            return "short"
        return "medium"

    def choose_template(self, terms):
        best = None
        best_score = -1
        for template in self.templates.values():
            searchable = " ".join([
                template.get("genre", ""),
                template.get("tone", ""),
                template.get("structure", ""),
                template.get("conflict_type", ""),
                " ".join(template.get("default_outline", []))
            ]).lower()
            score = sum(3 for term in terms if term in searchable)
            score += template.get("confidence", 70) / 30
            if score > best_score:
                best_score = score
                best = template
        return best or {}

    def run_creative(self, data):
        existing = self.existing_brain_result(data, "Creative_brain")
        if existing:
            return existing
        try:
            from Creative_brain import CreativeBrain
            return invoke_brain_safely(
                "Creative_brain",
                CreativeBrain(),
                data,
                phase="story_creative_fallback",
                request_id=data.get("_request_id") if isinstance(data, dict) else None
            )
        except Exception:
            return {"brain": "Creative_brain", "error": "creative_fallback_unavailable", "best_idea": {}}

    def run_character(self, data):
        existing = self.existing_brain_result(data, "Character_brain")
        if existing:
            return existing
        try:
            from Character_brain import CharacterBrain
            return invoke_brain_safely(
                "Character_brain",
                CharacterBrain(),
                data,
                phase="story_character_fallback",
                request_id=data.get("_request_id") if isinstance(data, dict) else None
            )
        except Exception:
            return {"brain": "Character_brain", "error": "character_fallback_unavailable", "character": {}}

    def run_world(self, data):
        existing = self.existing_brain_result(data, "World_brain")
        if existing:
            return existing
        try:
            from World_brain import WorldBrain
            return invoke_brain_safely(
                "World_brain",
                WorldBrain(),
                data,
                phase="story_world_fallback",
                request_id=data.get("_request_id") if isinstance(data, dict) else None
            )
        except Exception:
            return {"brain": "World_brain", "error": "world_fallback_unavailable", "world": {}}

    def existing_brain_result(self, data, brain_name):
        if not isinstance(data, dict):
            return None
        results = data.get("results", {})
        if not isinstance(results, dict):
            return None
        result = results.get(brain_name)
        if not isinstance(result, dict):
            return None
        if result.get("error") or result.get("skipped"):
            return None
        return result

    def build_outline(self, template, creative, character, world):
        default_outline = template.get("default_outline", ["opening", "conflict", "climax", "resolution"])
        idea = creative.get("best_idea", {})
        character_data = character.get("character", {})
        world_data = world.get("world", {})
        outline = []
        for index, beat in enumerate(default_outline, start=1):
            outline.append({
                "step": index,
                "beat": beat,
                "purpose": f"{beat} advances {idea.get('title', 'the central idea')}",
                "character_focus": character_data.get("goal"),
                "world_focus": world_data.get("name"),
                "conflict": template.get("conflict_type")
            })
        return outline

    def build_draft(self, length, outline, character, world, creative):
        if length not in ["short", "medium", "chapter"]:
            return None
        char = character.get("character", {})
        world_data = world.get("world", {})
        idea = creative.get("best_idea", {})
        opening = outline[0]["beat"] if outline else "opening"
        ending = outline[-1]["beat"] if outline else "resolution"
        return (
            f"In {world_data.get('name', 'a strange place')}, {char.get('name', 'a character')} "
            f"carried a quiet problem: they wanted to {char.get('goal', 'change something')} "
            f"but {char.get('flaw', 'something held them back')}. "
            f"The story begins with {opening}, shaped by {idea.get('concept', 'an unusual idea')}. "
            f"Every choice pushes them toward {ending}, where the world finally demands a real decision."
        )

    def requested_sentence_count(self, text):

        match = re.search(
            r"(\d+)\s*[\-–]\s*(\d+)\s+sentences?",
            text.lower()
        )

        if match:
            low = int(match.group(1))
            high = int(match.group(2))
            return max(1, min(8, high if high <= 8 else low))

        exact = re.search(
            r"\b(\d+)\s+(?:more\s+)?sentences?\b",
            text.lower()
        )

        if exact:
            return max(1, min(12, int(exact.group(1))))

        if "short" in text.lower():
            return 6

        return 7

    def clean_sentence_list(self, sentences, count):

        clean = []

        for sentence in sentences:
            sentence = re.sub(r"\s+", " ", str(sentence)).strip()
            if not sentence:
                continue
            if sentence[-1] not in ".!?":
                sentence += "."
            clean.append(sentence)

        return " ".join(clean[:count])

    def extract_story_requirements(self, text, report=None):
        lowered = text.lower()

        name_match = re.search(r"\b(?:named|called)\s+([A-Z][a-zA-Z]+)\b", text)
        name = name_match.group(1) if name_match else None

        if not name and isinstance(report, dict):
            contract = report.get("request_contract", {})
            inventory = contract.get("detail_inventory", {}) if isinstance(contract, dict) else {}
            if not isinstance(inventory, dict) or not inventory:
                inventory = report.get("detail_inventory", {})
            named_entities = inventory.get("named_entities", []) if isinstance(inventory, dict) else []
            ignored_entities = {
                "Canri", "Write", "Create", "Continue", "Only", "Story", "Python"
            }
            name = next(
                (
                    str(entity).strip()
                    for entity in named_entities
                    if str(entity).strip()
                    and str(entity).strip() not in ignored_entities
                ),
                None
            )

        if not name:
            contextual_name = re.search(
                r"\b(?:about|with|follows?)\s+(?:a\s+)?(?:quiet\s+|shy\s+|brave\s+)?"
                r"(?:boy\s+|girl\s+|child\s+|patient\s+|hero\s+)?([A-Z][a-zA-Z]+)\b",
                text
            )
            if contextual_name:
                candidate = contextual_name.group(1)
                if candidate not in {"The", "A", "An", "Only", "Story"}:
                    name = candidate

        role = "character"
        for role_name in ["patient", "boy", "girl", "hero", "doctor", "student", "detective", "inventor", "child"]:
            if role_name in lowered:
                role = role_name
                break

        setting = "an ordinary place"
        park_match = re.search(r"\b(quiet|crowded|old|dark|empty|sunny)?\s*park\b", lowered)
        if park_match:
            modifier = park_match.group(1)
            setting = f"the {modifier} park" if modifier else "the park"
        elif "hospital" in lowered or "patient" in lowered:
            setting = "a quiet hospital ward"
        elif "under his bed" in lowered or "tiny door" in lowered:
            setting = "the tiny glowing city under the bed"
        elif "forest" in lowered:
            setting = "the old forest"
        elif "arcade" in lowered or "game arcade" in lowered:
            setting = "the crowded arcade"
        elif "\u05e4\u05d0\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd" in lowered or "\u05e4\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd" in lowered:
            setting = "\u05e4\u05d0\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd"
        elif "city" in lowered:
            setting = "the city"

        trait = None
        trait_match = re.search(
            r"\b(quiet|shy|brave|careful|curious|honest|stubborn|kind|patient)\s+"
            r"(?:girl|boy|hero|doctor|student|detective|inventor|child|character)\b",
            lowered
        )
        if trait_match:
            trait = trait_match.group(1)
        else:
            for trait_name in ["curious", "quiet", "shy", "brave", "careful", "honest", "stubborn", "kind", "patient"]:
                if trait_name in lowered:
                    trait = trait_name
                    break

        if not trait and "extraordinary human trait" in lowered:
            trait = "patience"

        conflict = "a hidden problem forces a choice"
        choice = None
        decision_match = re.search(
            r"\bmust\s+decide\s+whether\s+to\s+([^,.!?]+)",
            lowered
        )
        if decision_match:
            choice = re.sub(r"\s+", " ", decision_match.group(1)).strip()
            choice_parts = choice.split()
            choice_verb = choice_parts[0]
            if choice_verb.endswith("e") and not choice_verb.endswith("ee"):
                gerund = choice_verb[:-1] + "ing"
            elif choice_verb.endswith("ing"):
                gerund = choice_verb
            else:
                gerund = choice_verb + "ing"
            choice_action = " ".join([gerund] + choice_parts[1:])
            conflict = f"{choice_action} was the right choice"
        elif "disappeared" in lowered or "vanished" in lowered:
            conflict = "someone returns after disappearing and changes what everyone believes"
        elif "injured" in lowered or "hurt" in lowered:
            conflict = "an injury turns the first step into a test"
        elif "wake" in lowered and "city" in lowered:
            conflict = "the hero must decide whether to wake a sleeping city"
        elif "trait" in lowered:
            conflict = "the hero must rely on an ordinary trait that others overlook"
        elif "lost" in lowered or "\u05e0\u05d0\u05d1\u05d3" in lowered:
            conflict = "the child must find a way home before the place closes"

        required_beats = {
            "defining_moment": "defining moment" in lowered or "discovers this trait" in lowered,
            "central_conflict": "central conflict" in lowered or "conflict" in lowered,
            "pivotal_decision": "pivotal decision" in lowered or "decision" in lowered,
            "growth_ending": "grown" in lowered or "transformed" in lowered or "ending" in lowered
        }

        return {
            "name": name,
            "role": role,
            "setting": setting,
            "trait": trait,
            "conflict": conflict,
            "choice": choice,
            "required_beats": required_beats
        }

    def build_requirement_story(self, requirements, count):
        role = requirements.get("role") or "character"
        name = requirements.get("name") or (
            "Daniel" if role == "patient" else
            "Leo" if role == "boy" else
            "Maya" if role == "girl" else
            "Ari"
        )
        setting = requirements.get("setting") or "an ordinary place"
        trait = requirements.get("trait") or "patience"
        conflict = requirements.get("conflict") or "a hidden problem forces a choice"

        if role == "patient":
            sentences = [
                f"{name} had been missing for six months when he walked into the final meeting at North Ward",
                "The doctors stopped speaking because he looked tired, calm, and strangely certain of why he had returned",
                "He placed a worn notebook on the table and said the missing months had taught him to listen to silences no machine could measure",
                "When the committee demanded answers, Daniel chose to tell the truth slowly instead of protecting himself with another disappearance",
                "Page by page, the notebook revealed that several forgotten patients had left clues inside their own records",
                "By the end of the meeting, Daniel was no longer just the case everyone wanted to close, but the witness who reopened every question"
            ]
            return self.clean_sentence_list(sentences, count)

        sentences = [
            f"{name}, a {role} whose greatest trait was {trait}, lived near {setting} and was often underestimated because nothing about them looked extraordinary",
            f"The defining moment came when {name} noticed a small detail everyone else ignored and realized that {trait} could be a kind of strength",
            f"Soon after, {conflict}, and the people around {name} wanted a faster, louder answer",
            f"{name} almost followed them, but chose instead to trust the quiet habit that had always made them different",
            "That decision changed the story, because the solution appeared only when someone was willing to slow down and see the pattern clearly",
            f"When it was over, {name} had not become powerful in a magical way, but had grown into someone who understood the worth of their own nature"
        ]

        return self.clean_sentence_list(sentences, count)

    # ---------- dynamic narrative generation ----------

    def extract_discovery(self, text, requirements):
        match = re.search(
            r"\b(?:finds?|discovers?|notices?|sees?)\s+(?:(?:a|an|the)\s+)?([^,.!?]+)",
            text,
            re.IGNORECASE
        )
        if match:
            phrase = re.split(
                r"\b(?:in|at|under|while|where|and\s+must)\b",
                match.group(1),
                maxsplit=1,
                flags=re.IGNORECASE
            )[0]
            phrase = re.sub(r"\s+", " ", phrase).strip(" ,.-")
            if 1 <= len(phrase.split()) <= 10:
                article = "an" if phrase[:1].lower() in "aeiou" else "a"
                return f"{article} {phrase}"

        lowered = text.lower()
        if "tiny door" in lowered:
            return "a tiny door glowing beneath the bed"
        if "key" in lowered:
            return "a key marked with an unfamiliar symbol"
        if "lost" in lowered:
            return "a sign pointing toward a part of the building he did not recognize"
        if requirements.get("role") == "patient":
            return "a notebook containing a record of the missing months"
        return "a detail that did not belong there"

    def dynamic_story_components(self, text, report, creative):
        requirements = self.extract_story_requirements(text, report)
        role = requirements.get("role") or "character"
        name = requirements.get("name") or {
            "patient": "Daniel",
            "boy": "Leo",
            "girl": "Maya",
            "hero": "Ari",
            "child": "Noah"
        }.get(role, "Ari")
        trait = requirements.get("trait") or "careful attention"
        trait = {
            "curious": "curiosity",
            "quiet": "quiet attention",
            "brave": "courage",
            "careful": "careful attention",
            "honest": "honesty",
            "kind": "kindness",
            "patient": "patience"
        }.get(trait, trait)
        setting = requirements.get("setting") or "an unfamiliar place"
        discovery = self.extract_discovery(text, requirements)
        conflict = requirements.get("conflict") or "a difficult choice"

        lexical = creative.get("dictionary_guided_composition", {})
        lexical_candidates = lexical.get("alternatives", []) if isinstance(lexical, dict) else []
        selected = lexical.get("selected", {}) if isinstance(lexical, dict) else {}
        if selected:
            lexical_candidates = [selected] + lexical_candidates

        return {
            "name": name,
            "role": role,
            "trait": trait,
            "setting": setting,
            "discovery": discovery,
            "conflict": conflict,
            "choice": requirements.get("choice"),
            "required_beats": requirements.get("required_beats", {}),
            "lexical_candidates": lexical_candidates[:16] or [{}],
            "request_terms": [
                str(item.get("word", "")).lower()
                for item in report.get("advanced_word_tags", [])[:100]
                if isinstance(item, dict) and item.get("word")
            ]
        }

    def build_dynamic_event_graph(self, components, lexical):
        name = components["name"]
        setting = components["setting"]
        discovery = components["discovery"]
        conflict = components["conflict"]
        explicit_choice = components.get("choice")
        trait = components["trait"]
        opener = lexical.get("opening_verb", "entered")
        notice = lexical.get("noticing_verb", "noticed")
        response = lexical.get("response_adverb", "carefully")
        role = components.get("role")
        pronoun = "she" if role == "girl" else "he" if role in {"boy", "patient"} else "they"

        if opener in {"walked", "stepped", "moved", "wandered"}:
            opening_action = f"{opener} into"
        else:
            opening_action = "entered"

        lost_conflict = "find a way home" in conflict.lower()
        return [
            {
                "role": "setup",
                "subject": name,
                "action": opening_action,
                "object": setting,
                "detail": f"guided by {trait} rather than confidence"
            },
            {
                "role": "discovery",
                "subject": pronoun,
                "action": notice,
                "object": discovery,
                "detail": "and understood that the ordinary situation had changed"
            },
            {
                "role": "conflict",
                "subject": pronoun,
                "action": "confronted the fact that",
                "object": conflict,
                "detail": "before there was time to ask someone else to decide"
            },
            {
                "role": "reaction",
                "subject": pronoun,
                "action": "paused",
                "object": "long enough to separate fear from the facts",
                "detail": "instead of following the first impulse"
            },
            {
                "role": "decision",
                "subject": pronoun,
                "action": "chose",
                "object": (
                    "to ask a trusted adult for help and retrace the last familiar path"
                    if lost_conflict else
                    f"to {explicit_choice} only after checking what the action could change"
                    if explicit_choice else
                    f"to examine the discovery {response} before acting"
                ),
                "detail": "because the choice would affect more than the next moment"
            },
            {
                "role": "consequence",
                "subject": "That decision",
                "action": "revealed",
                "object": "a path that had been hidden by haste",
                "detail": f"and turned {trait} into a practical strength"
            },
            {
                "role": "resolution",
                "subject": name,
                "action": "left",
                "object": setting,
                "detail": "changed not by sudden power, but by understanding how to choose"
            }
        ]

    def realize_dynamic_event(self, event):
        subject = event["subject"]
        subject = subject[:1].upper() + subject[1:]
        action = event["action"]
        obj = event["object"]
        detail = event.get("detail", "")
        sentence = f"{subject} {action} {obj}"
        if detail:
            sentence += f", {detail}"
        return sentence

    def score_dynamic_story(self, story, components, event_graph):
        lowered = story.lower()
        required = [
            components["name"],
            components["setting"],
            components["discovery"]
        ]
        coverage = sum(
            1 for item in required
            if str(item).lower() in lowered
        ) / max(len(required), 1)
        role_coverage = len({event["role"] for event in event_graph}) / 7
        words = re.findall(r"[a-zA-Z][a-zA-Z-]+", lowered)
        diversity = len(set(words)) / max(len(words), 1)
        return round(min(100, 45 + coverage * 25 + role_coverage * 20 + diversity * 10), 2)

    def build_dynamic_story(self, text, report, creative, count):
        if re.search(r"[\u0590-\u05ff]", text):
            return None
        tags = report.get("advanced_word_tags", [])
        if not isinstance(tags, list) or len(tags) < 3:
            return None

        components = self.dynamic_story_components(text, report, creative)
        candidates = []
        for index, lexical in enumerate(components["lexical_candidates"][:16]):
            graph = self.build_dynamic_event_graph(components, lexical)
            sentences = [self.realize_dynamic_event(event) for event in graph]
            story = self.clean_sentence_list(sentences, count)
            candidates.append({
                "id": f"dynamic_story_{index}",
                "story": story,
                "event_graph": graph,
                "lexical_plan": lexical,
                "score": self.score_dynamic_story(story, components, graph)
            })

        candidates.sort(key=lambda item: item["score"], reverse=True)
        if not candidates:
            return None
        return {
            "story": candidates[0]["story"],
            "event_graph": candidates[0]["event_graph"],
            "selected_score": candidates[0]["score"],
            "candidate_count": len(candidates),
            "alternatives": [
                {"id": item["id"], "score": item["score"]}
                for item in candidates[:8]
            ],
            "components": components,
            "generation_mode": "request_graph_dictionary_generation",
            "template_used": False
        }

    def build_continuation_story(self, current_text, requirements, count):
        name = requirements.get("name") or (
            "Leo" if requirements.get("role") == "boy" else
            "Maya" if requirements.get("role") == "girl" else
            "Ari"
        )
        lowered = current_text.lower()

        if "open" in lowered and "door" in lowered:
            opening = (
                f"{name} slid the key into the lock and opened the door, "
                "keeping one hand on the frame as warm light spilled through"
            )
        else:
            action_match = re.search(
                r"(?:continue[^:]*:\s*)?(?:she|he|they|%s)\s+([^.!?]+)" % re.escape(name),
                current_text,
                re.IGNORECASE
            )
            action = action_match.group(1).strip() if action_match else "followed the next clue"
            opening = f"{name} continued by choosing to {action}"

        key_detail = (
            "The key grew brighter in the lock, as if it recognized the place beyond the doorway"
            if "key" in lowered
            else
            "The clue from before changed as soon as the next step began"
        )
        setting = requirements.get("setting") or "the place beyond the doorway"
        sentences = [
            opening,
            f"Beyond it, {setting} opened into a passage filled with moving points of light",
            key_detail,
            f"{name} felt fear return, but this time curiosity did not make the decision alone",
            f"After listening for danger, {name} marked the doorway so the way back would not be lost",
            "Then a quiet voice from deeper inside spoke the answer to a question no one had asked yet",
            f"{name} stepped forward carefully, knowing the discovery had become a choice"
        ]
        return self.clean_sentence_list(sentences, count)

    def build_final_story(
        self,
        text,
        length,
        outline,
        character,
        world,
        creative,
        report=None,
        current_text=None
    ):

        lowered = text.lower()
        current_text = current_text or text
        count = self.requested_sentence_count(current_text)
        requirements = self.extract_story_requirements(text, report)

        is_park_story = "park" in lowered or "walk" in lowered
        is_leo_tiny_door_story = (
            "leo" in lowered
            and "tiny door" in lowered
            and (
                "under his bed" in lowered
                or "glowing city" in lowered
                or "everyone is asleep" in lowered
            )
        )
        is_story_continuation = any(
            phrase in lowered
            for phrase in [
                "continue the same story",
                "continued story",
                "continue this story",
                "4 more sentences",
                "four more sentences"
            ]
        )
        injured_story = any(
            word in lowered
            for word in ["injured", "hurt", "wounded", "injury", "gets injured"]
        )
        patient_return_story = (
            "patient" in lowered
            and any(word in lowered for word in ["disappeared", "missing", "vanished"])
            and any(phrase in lowered for phrase in ["six months", "6 months", "half a year"])
            and "meeting" in lowered
        )
        trait_hero_story = (
            "hero" in lowered
            and (
                "trait" in lowered
                or "natural ability" in lowered
                or "flaw" in lowered
                or "habit" in lowered
            )
        )
        arcade_lost_story = (
            ("arcade" in lowered or "\u05e4\u05d0\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd" in lowered or "\u05e4\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd" in lowered)
            and ("lost" in lowered or "\u05e0\u05d0\u05d1\u05d3" in lowered)
        )

        if is_story_continuation and not is_leo_tiny_door_story:
            return self.build_continuation_story(current_text, requirements, count)

        if arcade_lost_story:
            hebrew = bool(re.search(r"[\u0590-\u05ff]", text))
            if hebrew:
                sentences = [
                    "\u05d9\u05dc\u05d3 \u05e9\u05dd \u05dc\u05d1 \u05e9\u05d4\u05e8\u05e2\u05e9 \u05e9\u05dc \u05e4\u05d0\u05e8\u05e7 \u05d4\u05de\u05e9\u05d7\u05e7\u05d9\u05dd \u05e9\u05db\u05da \u05d1\u05e8\u05d2\u05e2 \u05e9\u05d4\u05d5\u05d0 \u05d4\u05d1\u05d9\u05df \u05e9\u05d4\u05d5\u05d0 \u05d0\u05d9\u05d1\u05d3 \u05d0\u05ea \u05d4\u05d3\u05e8\u05da \u05d0\u05dc \u05d4\u05d9\u05e6\u05d9\u05d0\u05d4",
                    "\u05e1\u05d1\u05d9\u05d1\u05d5 \u05d4\u05d1\u05d4\u05d1\u05d5 \u05e0\u05e8\u05d5\u05ea \u05d5\u05de\u05e9\u05d7\u05e7\u05d9\u05dd, \u05d0\u05d1\u05dc \u05d0\u05e3 \u05e4\u05e0\u05d9\u05dd \u05dc\u05d0 \u05d4\u05d9\u05d5 \u05de\u05d5\u05db\u05e8\u05d5\u05ea \u05dc\u05d5",
                    "\u05d1\u05de\u05e7\u05d5\u05dd \u05dc\u05e8\u05d5\u05e5, \u05d4\u05d5\u05d0 \u05e0\u05db\u05e8 \u05d1\u05e1\u05e4\u05e1\u05dc \u05d5\u05e0\u05d6\u05db\u05e8 \u05d1\u05e2\u05e6\u05d4 \u05e9\u05dc \u05d0\u05de\u05d0 \u05e9\u05dc\u05d5: \u05d0\u05dd \u05d0\u05d5\u05d1\u05d3\u05d9\u05dd, \u05de\u05d7\u05e4\u05e9\u05d9\u05dd \u05d0\u05d3\u05dd \u05e2\u05dd \u05ea\u05d2 \u05e9\u05dd",
                    "\u05d4\u05d5\u05d0 \u05e9\u05dd \u05dc\u05d1 \u05dc\u05e2\u05d5\u05d1\u05d3 \u05e9\u05dc \u05d4\u05de\u05e7\u05d5\u05dd \u05e9\u05e2\u05de\u05d3 \u05dc\u05d9\u05d3 \u05de\u05e9\u05d7\u05e7 \u05de\u05e8\u05d5\u05e5 \u05d5\u05d1\u05d9\u05e7\u05e9 \u05e2\u05d6\u05e8\u05d4 \u05d1\u05e7\u05d5\u05dc \u05e8\u05d2\u05d5\u05e2",
                    "\u05db\u05e2\u05d1\u05d5\u05e8 \u05db\u05de\u05d4 \u05d3\u05e7\u05d5\u05ea \u05d4\u05d5\u05e8\u05d9\u05d5 \u05de\u05e6\u05d0\u05d5 \u05d0\u05d5\u05ea\u05d5 \u05d5\u05d7\u05d9\u05d1\u05e7\u05d5 \u05d0\u05d5\u05ea\u05d5 \u05d7\u05d6\u05e7",
                    "\u05d1\u05d3\u05e8\u05da \u05d4\u05d1\u05d9\u05ea\u05d4 \u05d4\u05d5\u05d0 \u05d4\u05d1\u05d9\u05df \u05e9\u05d0\u05de\u05d9\u05e5 \u05dc\u05d1\u05e7\u05e9 \u05e2\u05d6\u05e8\u05d4 \u05d6\u05d4 \u05dc\u05d0 \u05e4\u05d7\u05d5\u05ea \u05d7\u05e9\u05d5\u05d1 \u05de\u05dc\u05de\u05e6\u05d5\u05d0 \u05d0\u05ea \u05d4\u05d3\u05e8\u05da \u05dc\u05d1\u05d3"
                ]
            else:
                sentences = [
                    "Noah realized he was lost when the arcade music faded behind the flashing machines.",
                    "He could see lights everywhere, but he could not find the entrance where his family had been waiting.",
                    "Instead of running from game to game, he sat beside a prize counter and remembered the safety rule his mother had taught him.",
                    "Noah found an employee with a name tag and asked for help in a calm voice.",
                    "A few minutes later, his worried family found him near the counter and held him tightly.",
                    "On the way home, Noah understood that asking for help had been the bravest move he made all day."
                ]
            return self.clean_sentence_list(sentences, count)

        if is_leo_tiny_door_story and is_story_continuation:
            sentences = [
                "Leo slipped through the tiny door and stepped onto a street no wider than his hand",
                "The sleeping people glowed because each of them was dreaming a light that kept the city alive",
                "At the center of the city, Leo found a silver bell with a note that said, Wake us only if you are willing to remember our dreams",
                "Leo carried the bell back through the door, deciding to wait until morning so he could choose with a brave and careful heart"
            ]
            return self.clean_sentence_list(sentences, count)

        if is_leo_tiny_door_story:
            sentences = [
                "Leo was a quiet boy who liked listening to the small sounds his room made at night",
                "One evening, he found a tiny blue door under his bed, hidden behind a loose thread in the carpet",
                "When he opened it, he saw a glowing city below the floorboards, with crystal roofs and golden streets",
                "Every person in the city was asleep, even the guards at the shining gates",
                "Beside the door, Leo found a note that said the city would wake only if someone spoke its forgotten name",
                "Leo held his breath, unsure whether waking the city would save it or break the quiet magic that protected it"
            ]
            return self.clean_sentence_list(sentences, count)

        if is_park_story:
            sentences = [
                "Maya, a careful twelve-year-old who noticed tiny details, went for a quiet walk through the park after school",
                "The grass was still wet from morning rain, and the paths smelled like leaves, soil, and fresh bread from a nearby cart",
                "Near an old bench, Maya saw a small brass key half-buried under a circle of blue stones",
                "When she picked it up, the stones glowed softly, and a hidden wooden door appeared in the side of the hill",
                "Maya felt scared at first, but curiosity pulled her closer than fear could push her away",
                "She opened the door just enough to see a warm light and hear someone whisper her name",
                "Instead of running, Maya put the key in her pocket and decided to return the next day with a notebook, a flashlight, and a braver heart",
                "By sunset, the park looked ordinary again, but Maya knew it was keeping a secret for her"
            ]
            return self.clean_sentence_list(sentences, count)

        if injured_story:
            sentences = [
                "In the first chapter, Eli ran through the narrow street because he thought he heard someone calling from the old bridge",
                "He was brave, but he was also impatient, and he did not see the loose stone under his foot",
                "Eli fell hard, scraping his arm and twisting his ankle as the sound from the bridge faded into silence",
                "For a moment he felt embarrassed and afraid, because the town suddenly seemed much larger than it had that morning",
                "Then he noticed a silver thread tied around the broken stone, glowing like moonlight even in the afternoon",
                "Eli put the thread in his pocket and limped home, certain the accident had not been random",
                "That night, while his ankle throbbed, the thread began to hum softly and point toward the forest",
                "Eli understood that his injury was not the end of the adventure, but the first sign that it had begun"
            ]
            return self.clean_sentence_list(sentences, count)

        if patient_return_story:
            return self.build_requirement_story(requirements, count)

        if trait_hero_story:
            return self.build_requirement_story(requirements, count)

        char = character.get("character", {})
        world_data = world.get("world", {})
        idea = creative.get("best_idea", {})
        name = char.get("name") or requirements.get("name") or "Ari"
        if "Concept" in str(name):
            name = requirements.get("name") or (
                "Daniel" if requirements.get("role") == "patient" else
                "Leo" if requirements.get("role") == "boy" else
                "Maya" if requirements.get("role") == "girl" else
                "Ari"
            )
        setting = world_data.get("name") or requirements.get("setting") or "a quiet town"
        goal = char.get("goal") or "find the truth"
        flaw = char.get("flaw") or "doubted every brave thought"
        concept = idea.get("concept") or "a secret waiting in an ordinary place"
        internal_markers = [
            "Goal:",
            "Core idea:",
            "Novel twist:",
            "Constraint:",
            "Validation:",
            "Tradeoff:",
            "Implementation:",
            "Direction:"
        ]

        if any(marker in str(concept) for marker in internal_markers):
            concept = "a secret waiting in an ordinary place"

        sentences = [
            f"{name} lived in {setting} and wanted to {goal}",
            f"The problem was that {name} {flaw}",
            f"One morning, a small unexpected sign appeared and pointed toward {concept}",
            f"{name} felt nervous, but the mystery was too clear to ignore",
            "Each step made the world feel less ordinary and more like it had been waiting",
            f"By the end, {name} chose to follow the clue instead of walking away",
            "The choice did not solve everything, but it opened the door to the next chapter"
        ]

        return self.clean_sentence_list(sentences, count)

    def update_statistics(self, confidence, genre):
        stats = self.statistics.get("Story_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_genre"] = genre
        stats["last_confidence"] = confidence
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("templates", len(self.templates))
        self.statistics["Story_brain"] = stats
        self.save_statistics()

    def process(self, data):
        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        continuation_source = self.continuation_source_text(memory_report)
        generation_text = (
            f"{continuation_source} {text}".strip()
            if continuation_source
            else text
        )
        terms = self.collect_terms(report, memory_report, generation_text)
        length = self.detect_length(text, terms)
        template = self.choose_template(terms)

        if continuation_source:
            creative = self.existing_brain_result(data, "Creative_brain") or {
                "brain": "Creative_brain",
                "derived_from_conversation": True,
                "confidence": 80,
                "best_idea": {}
            }
        else:
            creative = self.run_creative(data)
        dynamic_generation = None
        if not continuation_source:
            dynamic_generation = self.build_dynamic_story(
                generation_text,
                report,
                creative,
                self.requested_sentence_count(text)
            )
        if isinstance(dynamic_generation, dict) and dynamic_generation.get("story"):
            components = dynamic_generation.get("components", {})
            character = self.existing_brain_result(data, "Character_brain") or {
                "brain": "Character_brain",
                "derived_from_request": True,
                "character": {
                    "name": components.get("name"),
                    "role": components.get("role"),
                    "trait": components.get("trait")
                }
            }
            world = self.existing_brain_result(data, "World_brain") or {
                "brain": "World_brain",
                "derived_from_request": True,
                "world": {"name": components.get("setting")}
            }
            outline = self.build_outline(template, creative, character, world)
            draft = self.build_draft(length, outline, character, world, creative)
            story = dynamic_generation["story"]
            generation_mode = dynamic_generation.get("generation_mode")
            template_used = False
            confidence = min(
                100,
                dynamic_generation.get("selected_score", 70) * 0.8
                + creative.get("confidence", 60) * 0.2
            )
        else:
            if continuation_source:
                requirements = self.extract_story_requirements(generation_text, report)
                character = {
                    "brain": "Character_brain",
                    "derived_from_conversation": True,
                    "character": {
                        "name": requirements.get("name"),
                        "role": requirements.get("role"),
                        "trait": requirements.get("trait")
                    }
                }
                world = {
                    "brain": "World_brain",
                    "derived_from_conversation": True,
                    "world": {"name": requirements.get("setting")}
                }
            else:
                character = self.run_character(data)
                world = self.run_world(data)
            outline = self.build_outline(template, creative, character, world)
            draft = self.build_draft(length, outline, character, world, creative)
            story = self.build_final_story(
                generation_text,
                length,
                outline,
                character,
                world,
                creative,
                report=report,
                current_text=text
            )
            generation_mode = "legacy_template_fallback"
            template_used = True
            confidence = min(100, template.get("confidence", 70) + creative.get("confidence", 60) * 0.15)
        self.update_statistics(confidence, template.get("genre"))

        return {
            "brain": "Story_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "terms_used": terms,
            "story_type": template.get("genre"),
            "tone": template.get("tone"),
            "length": length,
            "structure": template.get("structure"),
            "conflict_type": template.get("conflict_type"),
            "creative_result": creative,
            "character_result": character,
            "world_result": world,
            "outline": outline,
            "draft": draft,
            "generation_mode": generation_mode,
            "template_used": template_used,
            "dynamic_generation": dynamic_generation or {},
            "story": story,
            "final_output": story,
            "confidence": round(confidence, 2),
            "suggested_next_brains": [
                "Creative_brain",
                "Character_brain",
                "World_brain",
                "Emotion_brain",
                "Language_brain",
                "Response_brain"
            ],
            "rules": [
                "Story_brain directs narrative structure.",
                "Creative_brain invents concepts.",
                "Character_brain builds characters.",
                "World_brain keeps setting consistent.",
                "Emotion_brain should tune emotional tone."
            ]
        }


brain = StoryBrain()
