"""
Language_brain.py
Canri AI

Main Language Brain Manager.
Receives the report from Understanding_brain and manages all language modules.
"""

from pathlib import Path


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

        return final_report


brain = LanguageBrain()