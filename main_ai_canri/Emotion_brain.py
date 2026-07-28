"""
Emotion_brain.py
Canri AI

תפקיד:
לזהות רגשות וטון בהודעת המשתמש מתוך דוח Understanding_brain,
ולהחזיר הנחיות איך להתאים את התגובה.

הוא לא מחליף את Security_brain. אם הוא מזהה מצוקה מסוכנת או
self-harm, הוא מסמן שצריך להעביר גם ל-Security_brain.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json


DATA_DIR = Path(__file__).parent / "data"
PATTERNS_PATH = DATA_DIR / "Emotion_patterns.json"
STYLES_PATH = DATA_DIR / "Emotion_response_styles.json"
STATISTICS_PATH = DATA_DIR / "Emotion_statistics.json"
CONVERSATION_PATTERNS_PATH = DATA_DIR / "Conversation_patterns.json"
SUPPORT_STRATEGIES_PATH = DATA_DIR / "Emotional_support_strategies.json"
LANGUAGE_RULES_PATH = DATA_DIR / "Emotion_language_rules.json"

class EmotionBrain:

    def __init__(self):

        self.patterns = self._load_json(
            PATTERNS_PATH,
            {}
        )

        self.styles = self._load_json(
            STYLES_PATH,
            {}
        )

        self.statistics = self._load_json(
            STATISTICS_PATH,
            {}
        )

        self.conversation_patterns = self._load_json(
            CONVERSATION_PATTERNS_PATH,
            {}
        )

        self.support_strategies = self._load_json(
            SUPPORT_STRATEGIES_PATH,
            {}
        )

        self.language_rules = self._load_json(
            LANGUAGE_RULES_PATH,
            {}
        )

        self.conversation_intent_index = self._build_conversation_intent_index()

        print("Emotion Brain Loaded")

    # ---------- loading ----------

    def _load_json(
        self,
        path,
        default
    ):

        if not path.exists():
            return default

        try:

            with path.open(
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(
                    file
                )

        except (OSError, json.JSONDecodeError):
            return default

    def _save_statistics(self):

        atomic_write_json(STATISTICS_PATH, self.statistics)

    def _build_conversation_intent_index(self):

        index = {}
        if not isinstance(self.conversation_patterns, list):
            return index

        for pattern in self.conversation_patterns:
            if not isinstance(pattern, dict):
                continue
            intent = str(pattern.get("intent") or "").strip()
            if not intent:
                continue
            bucket = index.setdefault(intent, set())
            for term in pattern.get("trigger_terms", []):
                normalized = re.sub(r"\s+", " ", str(term).lower()).strip()
                if normalized:
                    bucket.add(normalized)

        return {
            intent: sorted(terms, key=lambda item: (-len(item), item))
            for intent, terms in index.items()
        }

    # ---------- report handling ----------

    def get_understanding_report(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return {}

        understanding = data.get(
            "understanding",
            {}
        )

        if isinstance(
            understanding,
            dict
        ) and (
            "words" in understanding
            or "main_topic" in understanding
            or "intent" in understanding
        ):

            return understanding

        if (
            "words" in data
            or "main_topic" in data
            or "intent" in data
        ):

            return data

        return {}

    def get_memory_report(self, data):

        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]
        return {}

    def extract_text(
        self,
        data,
        report
    ):

        parts = []

        if isinstance(
            data,
            str
        ):

            parts.append(
                data
            )

        if isinstance(
            data,
            dict
        ):

            for key in [
                "user_message",
                "original_text",
                "corrected_text",
                "question",
                "query",
                "text"
            ]:

                value = data.get(
                    key
                )

                if value:
                    parts.append(
                        str(value)
                    )

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value:
                parts.append(
                    str(value)
                )

        return " ".join(
            parts
        ).strip()

    def collect_terms(
        self,
        report,
        text
    ):

        terms = []

        for key in [
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value:
                terms.append(
                    str(value)
                )

        for topic in report.get(
            "topics",
            {}
        ):

            terms.append(
                str(topic)
            )

        meaning_frame = report.get(
            "meaning_frame",
            {}
        )

        if isinstance(
            meaning_frame,
            dict
        ):

            for key in [
                "subject",
                "action",
                "object",
                "question_focus"
            ]:

                value = meaning_frame.get(
                    key
                )

                if value:
                    terms.append(
                        str(value)
                    )

            for value in meaning_frame.get(
                "content_terms",
                []
            )[:30]:
                terms.append(
                    str(value)
                )

        sentence_graph = report.get(
            "sentence_graph",
            {}
        )

        if isinstance(
            sentence_graph,
            dict
        ):

            for edge in sentence_graph.get(
                "edges",
                []
            )[:30]:

                if not isinstance(
                    edge,
                    dict
                ):
                    continue

                for key in [
                    "from_word",
                    "relation",
                    "to_word"
                ]:

                    value = edge.get(
                        key
                    )

                    if value:
                        terms.append(
                            str(value).replace(
                                "_",
                                " "
                            )
                        )

        for task in report.get(
            "possible_tasks",
            []
        ):

            terms.append(
                str(task).replace(
                    "_",
                    " "
                )
            )

        for word_data in report.get(
            "words",
            []
        ):

            if not isinstance(
                word_data,
                dict
            ):

                continue

            word = str(
                word_data.get(
                    "word",
                    ""
                )
            ).strip()

            if word:
                terms.append(
                    word
                )

            for connection in word_data.get(
                "connections",
                []
            )[:6]:

                terms.append(
                    str(connection)
                )

        tokens = re.findall(
            r"[a-zA-Z\u0590-\u05FF][a-zA-Z\u0590-\u05FF'\-]{1,}",
            text
        )

        terms.extend(
            tokens
        )

        clean_terms = []

        for term in terms:

            term = re.sub(
                r"\s+",
                " ",
                term
            ).strip().lower()

            if (
                term
                and term not in clean_terms
            ):

                clean_terms.append(
                    term
                )

        return clean_terms

    # ---------- emotion detection ----------

    def has_negation_before(
        self,
        text,
        keyword
    ):

        lowered = text.lower()
        keyword = keyword.lower()
        index = lowered.find(
            keyword
        )

        if index <= 0:
            return False

        window = lowered[
            max(
                0,
                index - 25
            ):index
        ]

        negations = self.language_rules.get("negations", [])
        return any(
            str(negation).lower() in window.split()
            for negation in negations
        )

    def intensity_bonus(
        self,
        text
    ):

        lowered = text.lower()
        bonus = 0

        for word, value in self.language_rules.get("intensifiers", {}).items():

            if word in lowered:
                bonus += value

        for word, value in self.language_rules.get("softeners", {}).items():

            if word in lowered:
                bonus += value

        exclamation_count = text.count(
            "!"
        )

        question_count = text.count(
            "?"
        )

        bonus += min(
            exclamation_count * 4,
            16
        )

        bonus += min(
            question_count * 2,
            8
        )

        if re.search(
            r"[A-Z]{4,}",
            text
        ):

            bonus += 8

        return max(
            min(
                bonus,
                30
            ),
            -20
        )

    @staticmethod
    def _phrase_in_text(text, phrase):

        normalized = re.sub(r"\s+", " ", str(phrase or "").lower()).strip()
        if not normalized:
            return False
        parts = [re.escape(part) for part in normalized.split(" ") if part]
        if not parts:
            return False
        pattern = r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)"
        return re.search(pattern, str(text or "").lower(), flags=re.UNICODE) is not None

    def _definition_evidence(self, report, semantic_cues):

        matches = []
        cues = [
            str(cue).lower().strip()
            for cue in semantic_cues
            if str(cue).strip()
        ]
        if not cues or not isinstance(report, dict):
            return matches

        for token in report.get("advanced_word_tags", []):
            if not isinstance(token, dict):
                continue
            definition = str(token.get("definition_hint") or "").lower()
            source_word = str(token.get("word") or "").strip()
            if not definition or not source_word:
                continue
            for cue in cues:
                if cue in definition:
                    matches.append(f"{source_word}: {cue}")
                    break
        return matches

    def detect_emotions(
        self,
        text,
        terms,
        report=None
    ):

        _ = terms
        scores = {}
        evidence = {}

        for emotion_id, pattern in self.patterns.items():

            score = 0
            matches = []

            for keyword in pattern.get(
                "keywords",
                []
            ):

                keyword_lower = keyword.lower()

                matched = self._phrase_in_text(text, keyword_lower)

                if not matched:
                    continue

                if keyword in matches:
                    continue

                if self.has_negation_before(
                    text,
                    keyword_lower
                ):

                    score -= 10

                else:

                    score += pattern.get(
                        "default_intensity",
                        50
                    ) / 10

                    matches.append(
                        keyword
                    )

            semantic_matches = self._definition_evidence(
                report,
                pattern.get("semantic_cues", [])
            )
            if semantic_matches:
                score += len(semantic_matches) * (
                    pattern.get("default_intensity", 50) / 25
                )
                matches.extend(semantic_matches)

            if score > 0:

                scores[emotion_id] = score
                evidence[emotion_id] = matches

        if not scores:

            return {
                "primary_emotion": "neutral",
                "emotions": {},
                "evidence": {},
                "intensity": 0,
                "mixed_emotions": [],
                "confidence": self.calculate_emotion_confidence(
                    text,
                    {},
                    {},
                    0
                )
            }

        primary = max(
            scores,
            key=scores.get
        )

        base_intensity = self.patterns.get(
            primary,
            {}
        ).get(
            "default_intensity",
            45
        )

        intensity = min(
            base_intensity
            +
            self.intensity_bonus(
                text
            )
            +
            min(
                int(scores[primary] * 1.3),
                24
            ),
            100
        )

        normalized = {
            emotion: min(
                round(score * 10, 2),
                100
            )
            for emotion, score in scores.items()
        }

        mixed_emotions = [
            emotion
            for emotion, score in sorted(
                normalized.items(),
                key=lambda item: item[1],
                reverse=True
            )[1:4]
            if score >= 35
        ]

        confidence = self.calculate_emotion_confidence(
            text,
            normalized,
            evidence,
            intensity
        )

        return {
            "primary_emotion": primary,
            "emotions": normalized,
            "evidence": evidence,
            "intensity": intensity,
            "mixed_emotions": mixed_emotions,
            "confidence": confidence
        }

    def calculate_emotion_confidence(
        self,
        text,
        emotions,
        evidence,
        intensity
    ):

        if not str(text).strip():
            return 35

        if not emotions:
            return 72

        evidence_count = sum(
            len(items)
            for items in evidence.values()
            if isinstance(items, list)
        )

        confidence = 55
        confidence += min(evidence_count * 8, 28)
        confidence += min(intensity * 0.18, 18)

        if len(emotions) > 2:
            confidence -= 5

        return round(
            max(
                35,
                min(confidence, 96)
            ),
            2
        )

    def classify_tone(
        self,
        primary_emotion
    ):

        if primary_emotion == "neutral":
            return "neutral"

        return self.patterns.get(
            primary_emotion,
            {}
        ).get(
            "tone",
            "neutral"
        )

    def emotional_state(
        self,
        primary_emotion,
        intensity,
        sensitivity
    ):

        valence = self.language_rules.get("valence", {}).get(
            primary_emotion,
            "neutral"
        )

        if sensitivity == "crisis":
            arousal = "crisis"
        elif intensity >= 75:
            arousal = "high"
        elif intensity >= 40:
            arousal = "medium"
        else:
            arousal = "low"

        return {
            "valence": valence,
            "arousal": arousal,
            "needs_gentle_tone": valence in {"negative", "crisis"},
            "needs_fast_answer": primary_emotion == "urgency" or arousal == "high",
            "avoid_overexplaining": primary_emotion in {"anger", "urgency"}
        }

    def get_style(
        self,
        primary_emotion
    ):

        return self.styles.get(
            primary_emotion,
            self.styles.get(
                "neutral",
                {}
            )
        )

    def detect_sensitivity(
        self,
        primary_emotion,
        intensity
    ):

        if primary_emotion == "self_harm_distress":
            return "crisis"

        if intensity >= 85:
            return "high"

        if intensity >= 55:
            return "medium"

        return "low"

    def update_statistics(
        self,
        primary_emotion,
        intensity,
        confidence
    ):

        stats = self.statistics.get(
            "Emotion_brain",
            {}
        )

        stats["uses"] = stats.get(
            "uses",
            0
        ) + 1

        stats["last_primary_emotion"] = primary_emotion
        stats["last_intensity"] = intensity
        stats["last_confidence"] = confidence
        stats["average_confidence"] = round(
            (
                stats.get("average_confidence", 0)
                * (stats["uses"] - 1)
                + confidence
            ) / max(stats["uses"], 1),
            2
        )
        stats["last_used_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

        self.statistics["Emotion_brain"] = stats

        self._save_statistics()

    # ---------- conversation support ----------

    def _conversation_intent_from_context(
        self,
        text,
        primary_emotion,
        sensitivity,
        report
    ):

        if sensitivity == "crisis":
            return "crisis_support"

        scores = {}
        for intent, triggers in self.conversation_intent_index.items():
            matches = [
                trigger
                for trigger in triggers
                if self._phrase_in_text(text, trigger)
            ]
            if matches:
                scores[intent] = sum(max(1, len(item.split())) for item in matches)

        if scores:
            return max(scores, key=scores.get)

        defaults = self.language_rules.get("default_intent_by_emotion", {})
        if primary_emotion in defaults:
            return str(defaults[primary_emotion])

        report = report if isinstance(report, dict) else {}
        routes = {
            str(route)
            for route in report.get("routing_hints", [])
            if route
        }
        requested_action = report.get("requested_action", {})
        contract = report.get("request_contract", {})
        action_requested = bool(
            isinstance(requested_action, dict)
            and requested_action.get("is_action_request")
        ) or bool(
            isinstance(contract, dict)
            and contract.get("action_kind")
        )
        if (
            report.get("main_topic") == "emotion"
            or "Emotion_brain" in routes
        ) and action_requested:
            return "emotional_support"

        return "none"

    def detect_conversation_intent(
        self,
        text,
        primary_emotion,
        sensitivity,
        report=None
    ):

        return self._conversation_intent_from_context(
            text,
            primary_emotion,
            sensitivity,
            report
        )

    def conversation_continuity(self, memory_report):

        conversation = memory_report.get("conversation", {}) if isinstance(memory_report, dict) else {}
        recent_turns = conversation.get("recent_turns", []) if isinstance(conversation, dict) else []
        previous_user_text = ""
        if recent_turns:
            last = recent_turns[-1]
            if isinstance(last, dict):
                previous_user_text = str(last.get("user") or last.get("user_message") or "")[:240]
        return {
            "session_id": conversation.get("session_id") if isinstance(conversation, dict) else None,
            "turn_count": conversation.get("turn_count", len(recent_turns)) if isinstance(conversation, dict) else 0,
            "has_previous_turn": bool(recent_turns),
            "previous_user_text": previous_user_text,
        }

    def select_support_strategy(self, emotion, intensity, intent):

        if not isinstance(self.support_strategies, list):
            return {}
        intensity_band = "high" if intensity >= 75 else "medium" if intensity >= 35 else "low"
        goal = {
            "venting": "listen",
            "reassurance": "stabilize",
            "emotional_support": "clarify",
            "celebration": "encourage",
            "small_talk": "follow_up"
        }.get(intent, "listen")
        for strategy in self.support_strategies:
            if not isinstance(strategy, dict):
                continue
            if (
                strategy.get("emotion") == emotion
                and strategy.get("intensity") == intensity_band
                and strategy.get("goal") == goal
            ):
                return strategy
        return {}

    def build_support_response(self, text, emotion, intent, sensitivity, continuity):

        hebrew = bool(re.search(r"[\u0590-\u05ff]", str(text or "")))
        continuing = continuity.get("has_previous_turn", False)

        if sensitivity == "crisis":
            if hebrew:
                return (
                    "\u05d0\u05e0\u05d9 \u05e9\u05d5\u05de\u05e2 \u05e9\u05d9\u05e9 \u05db\u05d0\u05df \u05de\u05e6\u05d5\u05e7\u05d4 \u05e8\u05e6\u05d9\u05e0\u05d9\u05ea. \u05d7\u05e9\u05d5\u05d1 \u05dc\u05e2\u05e8\u05d1 \u05e2\u05db\u05e9\u05d9\u05d5 \u05d0\u05d3\u05dd \u05e9\u05d0\u05ea\u05d4 \u05e1\u05d5\u05de\u05da \u05e2\u05dc\u05d9\u05d5 "
                    "\u05d0\u05d5 \u05e9\u05d9\u05e8\u05d5\u05ea \u05d7\u05d9\u05e8\u05d5\u05dd \u05de\u05e7\u05d5\u05de\u05d9; \u05d0\u05e0\u05d9 \u05d0\u05e9\u05d0\u05e8 \u05d0\u05d9\u05ea\u05da \u05d5\u05d0\u05e2\u05d6\u05d5\u05e8 \u05d1\u05e6\u05e2\u05d3 \u05d4\u05d1\u05d0."
                )
            return (
                "I hear that this is serious distress. Please involve a trusted person or local emergency/crisis service now; "
                "I can stay with you and help with the next immediate step."
            )

        hebrew_responses = {
            "sadness": "\u05d6\u05d4 \u05e0\u05e9\u05de\u05e2 \u05db\u05d5\u05d0\u05d1, \u05d5\u05dc\u05d0 \u05e6\u05e8\u05d9\u05da \u05dc\u05e4\u05ea\u05d5\u05e8 \u05d4\u05db\u05d5\u05dc \u05d1\u05e8\u05d2\u05e2 \u05d0\u05d7\u05d3. \u05de\u05d4 \u05d4\u05d7\u05dc\u05e7 \u05e9\u05d4\u05db\u05d9 \u05de\u05db\u05d1\u05d9\u05d3 \u05e2\u05dc\u05d9\u05da \u05e2\u05db\u05e9\u05d9\u05d5?",
            "fear": "\u05d4\u05d3\u05d0\u05d2\u05d4 \u05e0\u05e9\u05de\u05e2\u05ea \u05d0\u05de\u05d9\u05ea\u05d9\u05ea. \u05d1\u05d5\u05d0 \u05e0\u05e4\u05e8\u05d9\u05d3 \u05d1\u05d9\u05df \u05de\u05d4 \u05e9\u05e7\u05d5\u05e8\u05d4 \u05e2\u05db\u05e9\u05d9\u05d5 \u05dc\u05d1\u05d9\u05df \u05de\u05d4 \u05e9\u05d0\u05ea\u05d4 \u05d7\u05d5\u05e9\u05e9 \u05e9\u05d9\u05e7\u05e8\u05d4, \u05d5\u05d0\u05d6 \u05e0\u05d1\u05d7\u05e8 \u05e6\u05e2\u05d3 \u05e7\u05d8\u05df \u05d0\u05d7\u05d3.",
            "anger": "\u05de\u05d5\u05d1\u05df \u05e9\u05d0\u05ea\u05d4 \u05de\u05ea\u05d5\u05e1\u05db\u05dc. \u05d0\u05e4\u05e9\u05e8 \u05e7\u05d5\u05d3\u05dd \u05dc\u05d6\u05d4\u05d5\u05ea \u05de\u05d4 \u05d1\u05d3\u05d9\u05d5\u05e7 \u05d4\u05e9\u05ea\u05d1\u05e9, \u05d5\u05d0\u05d6 \u05dc\u05d1\u05d7\u05d5\u05e8 \u05e4\u05e2\u05d5\u05dc\u05d4 \u05d0\u05d7\u05ea \u05e9\u05dc\u05d0 \u05ea\u05d7\u05de\u05d9\u05e8 \u05d0\u05ea \u05d4\u05de\u05e6\u05d1.",
            "confusion": "\u05dc\u05d0 \u05d7\u05d9\u05d9\u05d1\u05d9\u05dd \u05dc\u05d4\u05d1\u05d9\u05df \u05d4\u05db\u05d5\u05dc \u05d1\u05d1\u05ea \u05d0\u05d7\u05ea. \u05db\u05ea\u05d5\u05d1 \u05dc\u05d9 \u05de\u05d4 \u05d9\u05d3\u05d5\u05e2 \u05dc\u05da \u05d5\u05de\u05d4 \u05dc\u05d0 \u05d1\u05e8\u05d5\u05e8, \u05d5\u05e0\u05e2\u05e9\u05d4 \u05d1\u05d6\u05d4 \u05e1\u05d3\u05e8 \u05d9\u05d7\u05d3.",
            "joy": "\u05d6\u05d4 \u05d1\u05d0\u05de\u05ea \u05de\u05e9\u05de\u05d7. \u05de\u05d4 \u05d4\u05d9\u05d4 \u05d4\u05d3\u05d1\u05e8 \u05e9\u05e2\u05d6\u05e8 \u05dc\u05da \u05dc\u05d4\u05e6\u05dc\u05d9\u05d7?",
            "neutral": "\u05d0\u05e0\u05d9 \u05db\u05d0\u05df. \u05d0\u05e4\u05e9\u05e8 \u05dc\u05d3\u05d1\u05e8 \u05e2\u05dc \u05de\u05d4 \u05e9\u05de\u05e2\u05e1\u05d9\u05e7 \u05d0\u05d5\u05ea\u05da, \u05dc\u05e4\u05ea\u05d5\u05e8 \u05d1\u05e2\u05d9\u05d4 \u05d0\u05d5 \u05e4\u05e9\u05d5\u05d8 \u05dc\u05d7\u05e9\u05d5\u05d1 \u05d9\u05d7\u05d3."
        }
        english_responses = {
            "sadness": "That sounds painful, and you do not have to solve all of it at once. What part feels heaviest right now?",
            "fear": "The worry sounds real. Let us separate what is happening now from what you fear might happen, then choose one small step.",
            "anger": "It makes sense that you are frustrated. We can first name exactly what went wrong, then choose one action that will not make it worse.",
            "confusion": "You do not have to understand everything at once. Tell me what you know and what is unclear, and we can sort it out together.",
            "joy": "That is genuinely good news. What helped you make it happen?",
            "neutral": "I am here. We can talk through what is on your mind, solve a problem, or simply think together."
        }
        response = (hebrew_responses if hebrew else english_responses).get(
            emotion,
            (hebrew_responses if hebrew else english_responses)["neutral"]
        )
        if continuing and intent not in {"small_talk", "celebration"}:
            prefix = "\u05d0\u05e0\u05d9 \u05de\u05de\u05e9\u05d9\u05da \u05d0\u05d9\u05ea\u05da \u05de\u05d0\u05d5\u05ea\u05d4 \u05e9\u05d9\u05d7\u05d4. " if hebrew else "I am continuing with you from the same conversation. "
            response = prefix + response
        return response

    # ---------- process ----------

    def process(
        self,
        data
    ):

        report = self.get_understanding_report(
            data
        )

        memory_report = self.get_memory_report(data)

        text = self.extract_text(
            data,
            report
        )

        terms = self.collect_terms(
            report,
            text
        )

        detected = self.detect_emotions(
            text,
            terms,
            report
        )

        primary_emotion = detected["primary_emotion"]
        intensity = detected["intensity"]
        confidence = detected.get(
            "confidence",
            60
        )
        tone = self.classify_tone(
            primary_emotion
        )

        style = self.get_style(
            primary_emotion
        )

        sensitivity = self.detect_sensitivity(
            primary_emotion,
            intensity
        )

        emotional_state = self.emotional_state(
            primary_emotion,
            intensity,
            sensitivity
        )

        needs_security = (
            primary_emotion == "self_harm_distress"
            or sensitivity == "crisis"
        )

        conversation_intent = self.detect_conversation_intent(
            text,
            primary_emotion,
            sensitivity,
            report
        )
        continuity = self.conversation_continuity(memory_report)
        support_response = ""
        support_strategy = self.select_support_strategy(
            primary_emotion,
            intensity,
            conversation_intent
        )
        if conversation_intent != "none":
            support_response = self.build_support_response(
                text,
                primary_emotion,
                conversation_intent,
                sensitivity,
                continuity
            )

        self.update_statistics(
            primary_emotion,
            intensity,
            confidence
        )

        return {
            "brain": "Emotion_brain",
            "used_understanding_report": bool(report),
            "primary_emotion": primary_emotion,
            "dominant_emotion": primary_emotion,
            "emotions": detected["emotions"],
            "mixed_emotions": detected.get(
                "mixed_emotions",
                []
            ),
            "tone": tone,
            "intensity": intensity,
            "sensitivity": sensitivity,
            "emotional_state": emotional_state,
            "evidence": detected["evidence"],
            "response_style": style.get(
                "response_style",
                "normal_helpful"
            ),
            "conversation_intent": conversation_intent,
            "needs_emotional_support": conversation_intent not in {"none", "small_talk"},
            "conversation_continuity": continuity,
            "support_response": support_response,
            "support_strategy": support_strategy,
            "answer": support_response or None,
            "final_output": support_response or None,
            "response_guidelines": style.get(
                "guidelines",
                []
            ),
            "needs_security": needs_security,
            "confidence": confidence,
            "suggested_next_brains": [
                brain_name
                for brain_name, enabled in [
                    ("Security_brain", needs_security),
                    ("Response_brain", True)
                ]
                if enabled
            ],
            "terms_used": terms[:30],
            "data_files_used": [
                "Emotion_patterns.json",
                "Emotion_response_styles.json",
                "Conversation_patterns.json",
                "Emotional_support_strategies.json"
            ],
            "response_adjustments": {
                "tone": tone,
                "style": style.get(
                    "response_style",
                    "normal_helpful"
                ),
                "be_brief": emotional_state["avoid_overexplaining"],
                "be_gentle": emotional_state["needs_gentle_tone"],
                "lead_with_action": emotional_state["needs_fast_answer"]
            },
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Detect emotion but do not overreact to weak signals.",
                "Return confidence so Learning_brain can measure emotional reliability.",
                "Use emotion to adapt tone, pacing, and structure.",
                "Adapt response tone, not facts.",
                "Route crisis or self-harm distress to Security_brain.",
                "Keep technical answers clear even when emotion is present."
            ]
        }


brain = EmotionBrain()
