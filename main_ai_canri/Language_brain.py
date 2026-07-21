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

    def extract_scanner_evidence(self, data, limit=20):
        if not isinstance(data, dict):
            return []

        candidates = []
        scanner_view = data.get("scanner_knowledge", {})
        if isinstance(scanner_view, dict):
            candidates.extend(scanner_view.get("matches", []))

        for key in ["data_context", "full_data_context"]:
            context = data.get(key, {})
            if not isinstance(context, dict):
                continue
            candidates.extend(context.get("scanner_matches", []))
            candidates.extend(context.get("scanner_evidence", []))
            pack = context.get("context_pack", {})
            if isinstance(pack, dict):
                candidates.extend(pack.get("scanner_evidence", []))

        unique = []
        seen = set()
        for item in candidates:
            if not isinstance(item, dict):
                continue
            identity = (
                item.get("url")
                or item.get("source_url")
                or item.get("article_id")
                or item.get("title")
                or str(item)[:160]
            )
            if identity in seen:
                continue
            seen.add(identity)
            unique.append(item)
            if len(unique) >= limit:
                break
        return unique

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
        translation_text = translation.get("translated_text")
        if not translation_text and isinstance(translation.get("result"), dict):
            translation_text = translation["result"].get("translated_text")

        is_translation_request = translation.get("is_translation_request", False)
        corrected_text = grammar.get("corrected_text") or grammar.get("fixed_text")

        if is_translation_request and translation_text:
            answer_parts.append(str(translation_text))

        if corrected_text and corrected_text != text and corrected_text.lower() != text.lower():
            answer_parts.append(f"Corrected text: {corrected_text}")

        if dictionary.get("answer"):
            answer_parts.append(str(dictionary["answer"]))

        if expressions.get("answer"):
            answer_parts.append(str(expressions["answer"]))

        if not answer_parts and isinstance(final_report, dict) and final_report.get("answer"):
            answer_parts.append(str(final_report["answer"]))

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
            "expressions": expressions,
            "language_data_summary": raw_report.get("language_data_summary", {}),
            "precision_contract": analysis.get("semantic_frame", {}),
            "scanner_evidence": raw_report.get("scanner_evidence", []),
            "scanner_usage": raw_report.get("scanner_usage", {})
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
        if not isinstance(language_data, dict):
            language_data = {}
        else:
            language_data = dict(language_data)

        scanner_evidence = self.extract_scanner_evidence(understanding_report)
        language_data["scanner_evidence"] = scanner_evidence

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
                "expressions": expressions_result,
                "scanner_evidence": scanner_evidence,
            },
            default={}
        )

        raw_report = {
            "brain": "Language_brain",
            "input_text": text,
            "understanding_report": understanding_report,
            "language_data_loaded": bool(language_data),
            "language_data_summary": (
                language_data.get("metadata", {})
                if isinstance(language_data, dict)
                else {}
            ),
            "scanner_evidence": scanner_evidence,
            "scanner_usage": {
                "received": len(scanner_evidence),
                "considered_by": [
                    "LanguageAnalysisEngine",
                    "GrammarEngine",
                    "TranslationEngine",
                    "DictionaryEngine",
                    "ExpressionsEngine",
                    "LanguageReportBuilder",
                ],
                "retrieval_mode": "indexed_relevant_excerpts",
            },

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
