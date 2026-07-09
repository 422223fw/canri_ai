"""
Language_brain_6.py
Canri AI

Language Statistics Engine.
Tracks language usage, translation hits, grammar changes and recent language
history without letting the files grow forever.
"""

import json
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
STATISTICS_FILE = DATA_DIR / "Language_statistics.json"
HISTORY_FILE = DATA_DIR / "Language_history.json"


class LanguageStatisticsEngine:

    def __init__(self):
        print("Language Statistics Engine Loaded")
        self.statistics = self.load_json(STATISTICS_FILE, default={})
        self.history = self.load_json(HISTORY_FILE, default=[])

    def load_json(self, path, default):
        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            print(f"[LanguageStatisticsEngine] JSON error in {path.name}: {error}")
            return default
        except OSError as error:
            print(f"[LanguageStatisticsEngine] File error in {path.name}: {error}")
            return default

    def save_json(self, path, data):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            return True
        except OSError as error:
            print(f"[LanguageStatisticsEngine] Save error in {path.name}: {error}")
            return False

    def ensure_statistics_structure(self):
        self.statistics.setdefault("languages_used", {})
        self.statistics.setdefault("translations_used", {})
        self.statistics.setdefault("grammar_fixes", 0)
        self.statistics.setdefault("common_mistakes", {})
        self.statistics.setdefault("translation_success", {})
        self.statistics.setdefault("engine_usage", {})
        self.statistics.setdefault("confidence_history", [])
        self.statistics.setdefault("requests", 0)
        self.statistics.setdefault("last_used_utc", None)

    def increase_counter(self, container, key, amount=1):
        if key:
            container[key] = container.get(key, 0) + amount

    def extract_language(self, results):
        analysis = results.get("analysis", {})
        if isinstance(analysis, dict) and analysis.get("detected_language"):
            return analysis["detected_language"]

        translation = results.get("translation", {})
        if isinstance(translation, dict) and translation.get("target_language"):
            return translation["target_language"]

        return "unknown"

    def extract_translation_data(self, results):
        translation = results.get("translation", {})
        if not isinstance(translation, dict):
            return []

        if isinstance(translation.get("translated_words"), list):
            return translation["translated_words"]

        result = translation.get("result", {})
        if isinstance(result, dict):
            return result.get("translated_words", [])

        return []

    def extract_grammar_data(self, results):
        grammar = results.get("grammar", {})
        if not isinstance(grammar, dict):
            grammar = {}

        return {
            "input_text": grammar.get("input_text", ""),
            "fixed_text": grammar.get("fixed_text", ""),
            "confidence": grammar.get("confidence", 0),
        }

    def update_language_usage(self, language):
        self.increase_counter(self.statistics["languages_used"], language)

    def update_translation_usage(self, translated_words):
        for item in translated_words:
            if not isinstance(item, dict):
                continue

            original = item.get("original")
            translated = item.get("translated")
            found = item.get("found", False)

            if not original:
                continue

            key = f"{original} -> {translated}"
            self.increase_counter(self.statistics["translations_used"], key)
            self.statistics["translation_success"].setdefault(
                original,
                {"success": 0, "fail": 0},
            )

            if found:
                self.statistics["translation_success"][original]["success"] += 1
            else:
                self.statistics["translation_success"][original]["fail"] += 1

    def update_grammar_statistics(self, grammar_data):
        input_text = grammar_data.get("input_text", "")
        fixed_text = grammar_data.get("fixed_text", "")

        if input_text and fixed_text and input_text != fixed_text:
            self.statistics["grammar_fixes"] += 1
            self.increase_counter(
                self.statistics["common_mistakes"],
                f"{input_text} -> {fixed_text}",
            )

    def update_engine_usage(self, results):
        for engine_name, value in results.items():
            if isinstance(value, dict):
                engine = value.get("engine", engine_name)
                self.increase_counter(self.statistics["engine_usage"], engine)

    def update_confidence_history(self, confidence):
        self.statistics["confidence_history"].append({
            "time": datetime.now().isoformat(),
            "confidence": confidence,
        })
        self.statistics["confidence_history"] = self.statistics["confidence_history"][-500:]

    def add_history_record(self, text, report, results, confidence):
        record = {
            "time": datetime.now().isoformat(),
            "input_text": text,
            "main_topic": None,
            "intent": None,
            "language": self.extract_language(results),
            "confidence": confidence,
        }

        if isinstance(report, dict):
            record["main_topic"] = report.get("main_topic")
            record["intent"] = report.get("intent")

        translation = results.get("translation", {})
        if isinstance(translation, dict):
            record["translated_text"] = translation.get("translated_text")
            record["target_language"] = translation.get("target_language")

        grammar = results.get("grammar", {})
        if isinstance(grammar, dict):
            record["grammar_fixed_text"] = grammar.get("fixed_text")

        analysis = results.get("analysis", {})
        if isinstance(analysis, dict):
            frame = analysis.get("semantic_frame", {})
            if isinstance(frame, dict):
                record["requested_output"] = frame.get("requested_output")
                record["actions"] = frame.get("actions", [])

        self.history.append(record)
        self.history = self.history[-1000:]

    def calculate_confidence(self, results):
        scores = []

        for value in results.values():
            if isinstance(value, dict) and isinstance(value.get("confidence"), (int, float)):
                scores.append(value["confidence"])

        return round(sum(scores) / len(scores), 2) if scores else 0

    def build_summary(self, language, translated_words, grammar_data, confidence):
        translated_count = sum(1 for item in translated_words if item.get("found"))
        grammar_changed = (
            grammar_data.get("input_text")
            and grammar_data.get("fixed_text")
            and grammar_data.get("input_text") != grammar_data.get("fixed_text")
        )

        top_languages = sorted(
            self.statistics.get("languages_used", {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]

        return {
            "language_used": language,
            "translated_words_count": translated_count,
            "grammar_changed": bool(grammar_changed),
            "requests": self.statistics.get("requests", 0),
            "top_languages": top_languages,
            "history_records": len(self.history),
            "confidence": confidence,
        }

    def process(self, text, report, results):
        self.ensure_statistics_structure()
        self.statistics["requests"] += 1
        self.statistics["last_used_utc"] = datetime.now().isoformat()

        language = self.extract_language(results)
        translated_words = self.extract_translation_data(results)
        grammar_data = self.extract_grammar_data(results)
        confidence = self.calculate_confidence(results)

        self.update_language_usage(language)
        self.update_translation_usage(translated_words)
        self.update_grammar_statistics(grammar_data)
        self.update_engine_usage(results)
        self.update_confidence_history(confidence)
        self.add_history_record(text, report, results, confidence)

        statistics_saved = self.save_json(STATISTICS_FILE, self.statistics)
        history_saved = self.save_json(HISTORY_FILE, self.history)

        return {
            "engine": "LanguageStatisticsEngine",
            "language": language,
            "summary": self.build_summary(language, translated_words, grammar_data, confidence),
            "statistics_file": str(STATISTICS_FILE),
            "history_file": str(HISTORY_FILE),
            "confidence": confidence,
            "saved": statistics_saved and history_saved,
        }


engine = LanguageStatisticsEngine()
