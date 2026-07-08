"""
Language_brain.py
Canri AI

Main Language Brain Manager.
Receives the report from Understanding_brain and manages all language modules.
"""

from pathlib import Path
import re


# =========================
# SAFE IMPORT SYSTEM
# =========================

def safe_import(module_name, class_name):
    try:
        module = __import__(module_name)
        return getattr(module, class_name)()
    except Exception as e:
        print(f"[Language_brain] Could not load {module_name}: {e}")
        return None


class LanguageBrain:

    def __init__(self):

        print("Language Brain Loaded")

        # חלק 1 - Loader
        self.loader = safe_import(
            "Language_brain_1",
            "LanguageLoader"
        )

        # חלק 2 - Translation
        self.translation = safe_import(
            "Language_brain_2",
            "TranslationEngine"
        )

        # חלק 3 - Grammar / UnderstandingDk
        self.grammar = safe_import(
            "Language_brain_3",
            "GrammarEngine"
        )

        # חלק 4 - Synonyms / Antonyms / Terms
        self.dictionary = safe_import(
            "Language_brain_4",
            "DictionaryEngine"
        )

        # חלק 5 - Idioms / Slang / Emoji / Units
        self.expressions = safe_import(
            "Language_brain_5",
            "ExpressionsEngine"
        )

        # חלק 6 - Statistics / History
        self.statistics = safe_import(
            "Language_brain_6",
            "LanguageStatisticsEngine"
        )

        # חלק 7 - Language Analysis
        self.analysis = safe_import(
            "Language_brain_7",
            "LanguageAnalysisEngine"
        )

        # חלק 8 - Report Builder
        self.report_builder = safe_import(
            "Language_brain_8",
            "LanguageReportBuilder"
        )

    # =========================
    # TEXT EXTRACTION
    # =========================

    def extract_text(self, data):

        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            return str(data)

        for key in [
            "corrected_text",
            "original_text",
            "user_message",
            "text",
            "query",
            "question"
        ]:
            value = data.get(key)

            if value:
                return str(value)

        understanding = data.get("understanding", {})

        if isinstance(understanding, dict):
            for key in [
                "corrected_text",
                "original_text",
                "user_message",
                "text"
            ]:
                value = understanding.get(key)

                if value:
                    return str(value)

        return ""

    # =========================
    # HELPERS
    # =========================

    def run_module(self, module, method_name, *args, default=None):

        if module is None:
            return default

        method = getattr(module, method_name, None)

        if method is None:
            return default

        try:
            return method(*args)

        except Exception as e:
            return {
                "error": str(e),
                "module": module.__class__.__name__
            }

    def detect_basic_language(self, text):
        hebrew = len(re.findall(r"[\u0590-\u05FF]", str(text)))
        latin = len(re.findall(r"[A-Za-z]", str(text)))

        if hebrew and latin:
            return "mixed"
        if hebrew:
            return "he"
        if latin:
            return "en"
        return "unknown"

    def build_unified_report(self, raw_report, final_report):
        text = raw_report.get("input_text", "")
        analysis = raw_report.get("analysis") if isinstance(raw_report.get("analysis"), dict) else {}
        grammar = raw_report.get("grammar") if isinstance(raw_report.get("grammar"), dict) else {}
        translation = raw_report.get("translation") if isinstance(raw_report.get("translation"), dict) else {}
        dictionary = raw_report.get("dictionary") if isinstance(raw_report.get("dictionary"), dict) else {}
        expressions = raw_report.get("expressions") if isinstance(raw_report.get("expressions"), dict) else {}

        detected_language = (
            analysis.get("detected_language")
            or analysis.get("language")
            or self.detect_basic_language(text)
        )

        direction = "rtl" if detected_language == "he" else "ltr"
        if detected_language == "mixed":
            direction = "mixed"

        confidence_values = []
        for part in [analysis, grammar, translation, dictionary, expressions, final_report]:
            if isinstance(part, dict) and isinstance(part.get("confidence"), (int, float)):
                confidence_values.append(float(part["confidence"]))

        confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 68

        answer_parts = []
        if translation.get("translated_text"):
            answer_parts.append(f"Translation: {translation['translated_text']}")
        if grammar.get("corrected_text"):
            answer_parts.append(f"Grammar: {grammar['corrected_text']}")
        if dictionary.get("answer"):
            answer_parts.append(str(dictionary["answer"]))
        if expressions.get("answer"):
            answer_parts.append(str(expressions["answer"]))

        if not answer_parts:
            answer_parts.append(
                f"Language detected: {detected_language}. Direction: {direction}."
            )

        unified = dict(final_report) if isinstance(final_report, dict) else {}
        unified.update({
            "brain": "Language_brain",
            "input_text": text,
            "detected_language": detected_language,
            "direction": direction,
            "confidence": confidence,
            "answer": "\n".join(answer_parts),
            "final_output": "\n".join(answer_parts),
            "modules_used": {
                "loader": raw_report.get("language_data_loaded", False),
                "analysis": bool(analysis),
                "grammar": bool(grammar),
                "translation": bool(translation),
                "dictionary": bool(dictionary),
                "expressions": bool(expressions)
            },
            "analysis": analysis,
            "grammar": grammar,
            "translation": translation,
            "dictionary": dictionary,
            "expressions": expressions
        })
        return unified

    # =========================
    # MAIN PROCESS
    # =========================

    def process(self, understanding_report):

        text = self.extract_text(
            understanding_report
        )

        # טעינת כל הנתונים
        language_data = self.run_module(
            self.loader,
            "load_all",
            default={}
        )

        # ניתוח שפה
        analysis_result = self.run_module(
            self.analysis,
            "analyze",
            text,
            understanding_report,
            language_data,
            default={}
        )

        # דקדוק דרך UnderstandingDk
        grammar_result = self.run_module(
            self.grammar,
            "process",
            text,
            understanding_report,
            default={}
        )

        # תרגום
        translation_result = self.run_module(
            self.translation,
            "process",
            text,
            understanding_report,
            language_data,
            default={}
        )

        # מילים נרדפות / הפכים / מונחים
        dictionary_result = self.run_module(
            self.dictionary,
            "process",
            text,
            understanding_report,
            language_data,
            default={}
        )

        # ביטויים / סלנג / אימוג'י / יחידות
        expressions_result = self.run_module(
            self.expressions,
            "process",
            text,
            understanding_report,
            language_data,
            default={}
        )

        # סטטיסטיקות
        statistics_result = self.run_module(
            self.statistics,
            "process",
            text,
            understanding_report,
            {
                "analysis": analysis_result,
                "grammar": grammar_result,
                "translation": translation_result,
                "dictionary": dictionary_result,
                "expressions": expressions_result
            },
            default={}
        )

        raw_report = {
            "brain": "Language_brain",
            "input_text": text,
            "understanding_report": understanding_report,
            "language_data_loaded": bool(language_data),

            "analysis": analysis_result,
            "grammar": grammar_result,
            "translation": translation_result,
            "dictionary": dictionary_result,
            "expressions": expressions_result,
            "statistics": statistics_result
        }

        # בניית דוח סופי
        final_report = self.run_module(
            self.report_builder,
            "build",
            raw_report,
            default=raw_report
        )

        return self.build_unified_report(raw_report, final_report)


brain = LanguageBrain()
