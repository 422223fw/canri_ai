"""
Language_brain_6.py
Canri AI

Language Statistics Engine.

Uses:
- Language_statistics.json
- Language_history.json

Responsible for:
- Language usage statistics
- Translation usage statistics
- Common mistakes tracking
- Confidence calculation
- Language history updates
"""

import json
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(__file__).parent / "data"

STATISTICS_FILE = DATA_DIR / "Language_statistics.json"
HISTORY_FILE = DATA_DIR / "Language_history.json"


class LanguageStatisticsEngine:

    def __init__(self):

        print("Language Statistics Engine Loaded")

        self.statistics = self.load_json(
            STATISTICS_FILE,
            default={}
        )

        self.history = self.load_json(
            HISTORY_FILE,
            default=[]
        )

    # =========================
    # FILE TOOLS
    # =========================

    def load_json(self, path, default):

        if not path.exists():
            return default

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            print(f"[LanguageStatisticsEngine] JSON error in {path.name}: {e}")
            return default

        except OSError as e:
            print(f"[LanguageStatisticsEngine] File error in {path.name}: {e}")
            return default

    def save_json(self, path, data):

        try:
            DATA_DIR.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

            return True

        except OSError as e:
            print(f"[LanguageStatisticsEngine] Save error in {path.name}: {e}")
            return False

    # =========================
    # SAFE COUNTERS
    # =========================

    def ensure_statistics_structure(self):

        self.statistics.setdefault(
            "languages_used",
            {}
        )

        self.statistics.setdefault(
            "translations_used",
            {}
        )

        self.statistics.setdefault(
            "grammar_fixes",
            0
        )

        self.statistics.setdefault(
            "common_mistakes",
            {}
        )

        self.statistics.setdefault(
            "translation_success",
            {}
        )

        self.statistics.setdefault(
            "engine_usage",
            {}
        )

        self.statistics.setdefault(
            "confidence_history",
            []
        )

    def increase_counter(self, container, key, amount=1):

        if not key:
            return

        container[key] = container.get(
            key,
            0
        ) + amount

    # =========================
    # EXTRACT HELPERS
    # =========================

    def extract_language(self, results):

        analysis = results.get(
            "analysis",
            {}
        )

        language = analysis.get(
            "detected_language"
        )

        if language:
            return language

        translation = results.get(
            "translation",
            {}
        )

        target = translation.get(
            "target_language"
        )

        if target:
            return target

        return "unknown"

    def extract_translation_data(self, results):

        translation = results.get(
            "translation",
            {}
        )

        result = translation.get(
            "result",
            {}
        )

        return result.get(
            "translated_words",
            []
        )

    def extract_grammar_data(self, results):

        grammar = results.get(
            "grammar",
            {}
        )

        return {
            "input_text": grammar.get(
                "input_text",
                ""
            ),
            "fixed_text": grammar.get(
                "fixed_text",
                ""
            ),
            "confidence": grammar.get(
                "confidence",
                0
            )
        }

    # =========================
    # UPDATE STATISTICS
    # =========================

    def update_language_usage(self, language):

        self.ensure_statistics_structure()

        self.increase_counter(
            self.statistics["languages_used"],
            language
        )

    def update_translation_usage(self, translated_words):

        self.ensure_statistics_structure()

        for item in translated_words:

            original = item.get(
                "original"
            )

            translated = item.get(
                "translated"
            )

            found = item.get(
                "found",
                False
            )

            if not original:
                continue

            key = f"{original} -> {translated}"

            self.increase_counter(
                self.statistics["translations_used"],
                key
            )

            if found:

                self.statistics["translation_success"].setdefault(
                    original,
                    {
                        "success": 0,
                        "fail": 0
                    }
                )

                self.statistics["translation_success"][original]["success"] += 1

            else:

                self.statistics["translation_success"].setdefault(
                    original,
                    {
                        "success": 0,
                        "fail": 0
                    }
                )

                self.statistics["translation_success"][original]["fail"] += 1

    def update_grammar_statistics(self, grammar_data):

        self.ensure_statistics_structure()

        input_text = grammar_data.get(
            "input_text",
            ""
        )

        fixed_text = grammar_data.get(
            "fixed_text",
            ""
        )

        if input_text and fixed_text and input_text != fixed_text:

            self.statistics["grammar_fixes"] += 1

            mistake_key = f"{input_text} -> {fixed_text}"

            self.increase_counter(
                self.statistics["common_mistakes"],
                mistake_key
            )

    def update_engine_usage(self, results):

        self.ensure_statistics_structure()

        for engine_name, value in results.items():

            if isinstance(value, dict):

                engine = value.get(
                    "engine",
                    engine_name
                )

                self.increase_counter(
                    self.statistics["engine_usage"],
                    engine
                )

    def update_confidence_history(self, confidence):

        self.ensure_statistics_structure()

        self.statistics["confidence_history"].append({
            "time": datetime.now().isoformat(),
            "confidence": confidence
        })

        # לא לשמור היסטוריה ענקית מדי
        self.statistics["confidence_history"] = (
            self.statistics["confidence_history"][-500:]
        )

    # =========================
    # HISTORY
    # =========================

    def add_history_record(
        self,
        text,
        report,
        results,
        confidence
    ):

        record = {
            "time": datetime.now().isoformat(),
            "input_text": text,
            "main_topic": None,
            "intent": None,
            "language": self.extract_language(
                results
            ),
            "confidence": confidence
        }

        if isinstance(report, dict):

            record["main_topic"] = report.get(
                "main_topic"
            )

            record["intent"] = report.get(
                "intent"
            )

        translation = results.get(
            "translation",
            {}
        )

        if isinstance(translation, dict):

            result = translation.get(
                "result",
                {}
            )

            record["translated_text"] = result.get(
                "translated_text"
            )

            record["target_language"] = translation.get(
                "target_language"
            )

        grammar = results.get(
            "grammar",
            {}
        )

        if isinstance(grammar, dict):

            record["grammar_fixed_text"] = grammar.get(
                "fixed_text"
            )

        self.history.append(record)

        # לא לשמור קובץ ענק מדי
        self.history = self.history[-1000:]

    # =========================
    # CONFIDENCE
    # =========================

    def calculate_confidence(self, results):

        scores = []

        for key, value in results.items():

            if isinstance(value, dict):

                confidence = value.get(
                    "confidence"
                )

                if isinstance(
                    confidence,
                    (int, float)
                ):

                    scores.append(
                        confidence
                    )

        if not scores:
            return 0

        return round(
            sum(scores) / len(scores),
            2
        )

    def build_summary(
        self,
        language,
        translated_words,
        grammar_data,
        confidence
    ):

        translated_count = sum(
            1
            for item in translated_words
            if item.get("found")
        )

        grammar_changed = (
            grammar_data.get("input_text")
            and grammar_data.get("fixed_text")
            and grammar_data.get("input_text") != grammar_data.get("fixed_text")
        )

        return {
            "language_used": language,
            "translated_words_count": translated_count,
            "grammar_changed": bool(grammar_changed),
            "confidence": confidence
        }

    # =========================
    # MAIN PROCESS
    # =========================

    def process(self, text, report, results):

        self.ensure_statistics_structure()

        language = self.extract_language(
            results
        )

        translated_words = self.extract_translation_data(
            results
        )

        grammar_data = self.extract_grammar_data(
            results
        )

        confidence = self.calculate_confidence(
            results
        )

        self.update_language_usage(
            language
        )

        self.update_translation_usage(
            translated_words
        )

        self.update_grammar_statistics(
            grammar_data
        )

        self.update_engine_usage(
            results
        )

        self.update_confidence_history(
            confidence
        )

        self.add_history_record(
            text,
            report,
            results,
            confidence
        )

        self.save_json(
            STATISTICS_FILE,
            self.statistics
        )

        self.save_json(
            HISTORY_FILE,
            self.history
        )

        summary = self.build_summary(
            language,
            translated_words,
            grammar_data,
            confidence
        )

        return {
            "engine": "LanguageStatisticsEngine",

            "language": language,

            "summary": summary,

            "statistics_file": str(STATISTICS_FILE),

            "history_file": str(HISTORY_FILE),

            "confidence": confidence,

            "saved": True
        }


engine = LanguageStatisticsEngine()