"""
Language_brain_8.py
Canri AI

Language Report Builder.

This file receives the raw report from Language_brain.py
and builds a clean final report for Manager_brain / Response_brain.
"""


class LanguageReportBuilder:

    def __init__(self):

        print("Language Report Builder Loaded")

    # =========================
    # SAFE GETTERS
    # =========================

    def safe_get(self, data, path, default=None):

        current = data

        for key in path:

            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current

    def get_engine_confidence(self, data, engine_name):

        engine_data = data.get(
            engine_name,
            {}
        )

        if not isinstance(engine_data, dict):
            return 0

        confidence = engine_data.get(
            "confidence",
            0
        )

        if isinstance(confidence, (int, float)):
            return confidence

        return 0

    # =========================
    # SUMMARY BUILDERS
    # =========================

    def build_language_summary(self, raw_report):

        analysis = raw_report.get(
            "analysis",
            {}
        )

        if not isinstance(analysis, dict):
            analysis = {}

        return {
            "detected_language": analysis.get(
                "detected_language",
                "unknown"
            ),
            "language_name": analysis.get(
                "language_name",
                "unknown"
            ),
            "writing_direction": analysis.get(
                "writing_direction",
                "unknown"
            ),
            "alphabet": analysis.get(
                "alphabet",
                []
            ),
            "text_type": analysis.get(
                "text_type",
                "unknown"
            ),
            "formality": analysis.get(
                "formality",
                {}
            )
        }

    def build_translation_summary(self, raw_report):

        translation = raw_report.get(
            "translation",
            {}
        )

        if not isinstance(translation, dict):
            translation = {}

        result = translation.get(
            "result",
            {}
        )

        if not isinstance(result, dict):
            result = {}

        return {
            "is_translation_request": translation.get(
                "is_translation_request",
                False
            ),
            "target_language": translation.get(
                "target_language",
                "unknown"
            ),
            "translated_text": result.get(
                "translated_text",
                raw_report.get("input_text", "")
            ),
            "found_count": result.get(
                "found_count",
                0
            ),
            "total_words": result.get(
                "total_words",
                0
            ),
            "translated_words": result.get(
                "translated_words",
                []
            ),
            "confidence": translation.get(
                "confidence",
                0
            )
        }

    def build_grammar_summary(self, raw_report):

        grammar = raw_report.get(
            "grammar",
            {}
        )

        if not isinstance(grammar, dict):
            grammar = {}

        input_text = grammar.get(
            "input_text",
            raw_report.get("input_text", "")
        )

        fixed_text = grammar.get(
            "fixed_text",
            input_text
        )

        grammar_changed = (
            input_text != fixed_text
        )

        return {
            "input_text": input_text,
            "fixed_text": fixed_text,
            "grammar_changed": grammar_changed,
            "known_words": grammar.get(
                "known_words",
                0
            ),
            "total_words": grammar.get(
                "total_words",
                0
            ),
            "tenses": grammar.get(
                "tenses",
                {}
            ),
            "base_forms": grammar.get(
                "base_forms",
                {}
            ),
            "confidence": grammar.get(
                "confidence",
                0
            )
        }

    def build_dictionary_summary(self, raw_report):

        dictionary = raw_report.get(
            "dictionary",
            {}
        )

        if not isinstance(dictionary, dict):
            dictionary = {}

        return {
            "definitions": dictionary.get(
                "definitions",
                {}
            ),
            "connections": dictionary.get(
                "connections",
                {}
            ),
            "synonyms": dictionary.get(
                "synonyms",
                {}
            ),
            "antonyms": dictionary.get(
                "antonyms",
                {}
            ),
            "technical_terms": dictionary.get(
                "technical_terms",
                {}
            ),
            "abbreviations": dictionary.get(
                "abbreviations",
                {}
            ),
            "confidence": dictionary.get(
                "confidence",
                0
            )
        }

    def build_expressions_summary(self, raw_report):

        expressions = raw_report.get(
            "expressions",
            {}
        )

        if not isinstance(expressions, dict):
            expressions = {}

        return {
            "idioms": expressions.get(
                "idioms",
                {}
            ),
            "slang": expressions.get(
                "slang",
                {}
            ),
            "emojis": expressions.get(
                "emojis",
                {}
            ),
            "units": expressions.get(
                "units",
                []
            ),
            "summary": expressions.get(
                "summary",
                []
            ),
            "confidence": expressions.get(
                "confidence",
                0
            )
        }

    def build_statistics_summary(self, raw_report):

        statistics = raw_report.get(
            "statistics",
            {}
        )

        if not isinstance(statistics, dict):
            statistics = {}

        return {
            "language": statistics.get(
                "language",
                "unknown"
            ),
            "summary": statistics.get(
                "summary",
                {}
            ),
            "statistics_file": statistics.get(
                "statistics_file",
                ""
            ),
            "history_file": statistics.get(
                "history_file",
                ""
            ),
            "saved": statistics.get(
                "saved",
                False
            ),
            "confidence": statistics.get(
                "confidence",
                0
            )
        }

    # =========================
    # CONFIDENCE ENGINE
    # =========================

    def calculate_final_confidence(self, raw_report):

        confidence_values = []

        for key in [
            "analysis",
            "grammar",
            "translation",
            "dictionary",
            "expressions",
            "statistics"
        ]:

            confidence = self.get_engine_confidence(
                raw_report,
                key
            )

            if confidence > 0:
                confidence_values.append(
                    confidence
                )

        if not confidence_values:
            return 0

        return round(
            sum(confidence_values) / len(confidence_values),
            2
        )

    # =========================
    # WARNINGS
    # =========================

    def collect_warnings(self, raw_report):

        warnings = []

        if not raw_report.get("language_data_loaded"):
            warnings.append(
                "Language data was not loaded."
            )

        for key in [
            "analysis",
            "grammar",
            "translation",
            "dictionary",
            "expressions",
            "statistics"
        ]:

            value = raw_report.get(
                key
            )

            if isinstance(value, dict) and "error" in value:

                warnings.append(
                    f"{key} error: {value.get('error')}"
                )

        translation_confidence = self.get_engine_confidence(
            raw_report,
            "translation"
        )

        if translation_confidence == 0:

            warnings.append(
                "No useful translation was found."
            )

        grammar_confidence = self.get_engine_confidence(
            raw_report,
            "grammar"
        )

        if grammar_confidence == 0:

            warnings.append(
                "Grammar analysis confidence is zero."
            )

        return list(
            dict.fromkeys(warnings)
        )

    # =========================
    # NEEDS HELP
    # =========================

    def detect_needs_help(self, final_confidence, warnings):

        if final_confidence < 30:
            return True

        serious_warnings = [
            warning
            for warning in warnings
            if "error" in warning.lower()
        ]

        if serious_warnings:
            return True

        return False

    # =========================
    # HUMAN READABLE SUMMARY
    # =========================

    def build_human_summary(
        self,
        language_summary,
        translation_summary,
        grammar_summary,
        dictionary_summary,
        expressions_summary,
        final_confidence
    ):

        lines = []

        detected_language = language_summary.get(
            "detected_language",
            "unknown"
        )

        lines.append(
            f"Detected language: {detected_language}"
        )

        if translation_summary.get("is_translation_request"):

            lines.append(
                "Translation request detected."
            )

        translated_text = translation_summary.get(
            "translated_text",
            ""
        )

        if translated_text:

            lines.append(
                f"Translated text: {translated_text}"
            )

        if grammar_summary.get("grammar_changed"):

            lines.append(
                "Grammar was changed."
            )

        if dictionary_summary.get("synonyms"):

            lines.append(
                "Synonyms found."
            )

        if dictionary_summary.get("antonyms"):

            lines.append(
                "Antonyms found."
            )

        if dictionary_summary.get("technical_terms"):

            lines.append(
                "Technical terms found."
            )

        if expressions_summary.get("idioms"):

            lines.append(
                "Idioms found."
            )

        if expressions_summary.get("slang"):

            lines.append(
                "Slang found."
            )

        if expressions_summary.get("emojis"):

            lines.append(
                "Emoji meanings found."
            )

        lines.append(
            f"Final confidence: {final_confidence}"
        )

        return lines

    # =========================
    # MAIN BUILD
    # =========================

    def build(self, raw_report):

        input_text = raw_report.get(
            "input_text",
            ""
        )

        understanding_report = raw_report.get(
            "understanding_report",
            {}
        )

        language_summary = self.build_language_summary(
            raw_report
        )

        translation_summary = self.build_translation_summary(
            raw_report
        )

        grammar_summary = self.build_grammar_summary(
            raw_report
        )

        dictionary_summary = self.build_dictionary_summary(
            raw_report
        )

        expressions_summary = self.build_expressions_summary(
            raw_report
        )

        statistics_summary = self.build_statistics_summary(
            raw_report
        )

        final_confidence = self.calculate_final_confidence(
            raw_report
        )

        warnings = self.collect_warnings(
            raw_report
        )

        needs_help = self.detect_needs_help(
            final_confidence,
            warnings
        )

        human_summary = self.build_human_summary(
            language_summary,
            translation_summary,
            grammar_summary,
            dictionary_summary,
            expressions_summary,
            final_confidence
        )

        return {
            "brain": "Language_brain",

            "input_text": input_text,

            "main_topic": understanding_report.get(
                "main_topic",
                "unknown"
            ) if isinstance(understanding_report, dict) else "unknown",

            "intent": understanding_report.get(
                "intent",
                "unknown"
            ) if isinstance(understanding_report, dict) else "unknown",

            "language": language_summary,

            "translation": translation_summary,

            "grammar": grammar_summary,

            "dictionary": dictionary_summary,

            "expressions": expressions_summary,

            "statistics": statistics_summary,

            "human_summary": human_summary,

            "confidence": final_confidence,

            "warnings": warnings,

            "needs_help": needs_help,

            "raw": raw_report
        }


builder = LanguageReportBuilder()