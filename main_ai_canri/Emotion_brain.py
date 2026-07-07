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


DATA_DIR = Path(__file__).parent / "data"
PATTERNS_PATH = DATA_DIR / "Emotion_patterns.json"
STYLES_PATH = DATA_DIR / "Emotion_response_styles.json"
STATISTICS_PATH = DATA_DIR / "Emotion_statistics.json"

NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "לא",
    "בלי",
    "אין"
}

INTENSIFIERS = {
    "very": 12,
    "really": 10,
    "so": 8,
    "extremely": 18,
    "too": 8,
    "מאוד": 12,
    "ממש": 10,
    "כל כך": 12,
    "יותר מדי": 12
}

SOFTENERS = {
    "a little": -10,
    "slightly": -8,
    "kind of": -6,
    "קצת": -12,
    "טיפה": -10,
    "מעט": -8
}


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

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with STATISTICS_PATH.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.statistics,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.write(
                "\n"
            )

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

        return any(
            negation in window.split()
            for negation in NEGATION_WORDS
        )

    def intensity_bonus(
        self,
        text
    ):

        lowered = text.lower()
        bonus = 0

        for word, value in INTENSIFIERS.items():

            if word in lowered:
                bonus += value

        for word, value in SOFTENERS.items():

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

    def detect_emotions(
        self,
        text,
        terms
    ):

        lowered = text.lower()
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

                matched = (
                    keyword_lower in lowered
                    or keyword_lower in terms
                )

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

            if score > 0:

                scores[emotion_id] = score
                evidence[emotion_id] = matches

        if not scores:

            return {
                "primary_emotion": "neutral",
                "emotions": {},
                "evidence": {},
                "intensity": 0
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

        return {
            "primary_emotion": primary,
            "emotions": normalized,
            "evidence": evidence,
            "intensity": intensity
        }

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
        intensity
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
        stats["last_used_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

        self.statistics["Emotion_brain"] = stats

        self._save_statistics()

    # ---------- process ----------

    def process(
        self,
        data
    ):

        report = self.get_understanding_report(
            data
        )

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
            terms
        )

        primary_emotion = detected["primary_emotion"]
        intensity = detected["intensity"]
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

        needs_security = (
            primary_emotion == "self_harm_distress"
            or sensitivity == "crisis"
        )

        self.update_statistics(
            primary_emotion,
            intensity
        )

        return {
            "brain": "Emotion_brain",
            "used_understanding_report": bool(report),
            "primary_emotion": primary_emotion,
            "emotions": detected["emotions"],
            "tone": tone,
            "intensity": intensity,
            "sensitivity": sensitivity,
            "evidence": detected["evidence"],
            "response_style": style.get(
                "response_style",
                "normal_helpful"
            ),
            "response_guidelines": style.get(
                "guidelines",
                []
            ),
            "needs_security": needs_security,
            "suggested_next_brains": [
                brain_name
                for brain_name, enabled in [
                    ("Security_brain", needs_security),
                    ("Response_brain", True)
                ]
                if enabled
            ],
            "terms_used": terms[:30],
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Detect emotion but do not overreact to weak signals.",
                "Adapt response tone, not facts.",
                "Route crisis or self-harm distress to Security_brain.",
                "Keep technical answers clear even when emotion is present."
            ]
        }


brain = EmotionBrain()
