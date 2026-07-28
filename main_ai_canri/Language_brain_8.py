"""
Language_brain_8.py
Canri AI

Language Report Builder.
Builds the clean report that Manager_brain / Response_brain can use.
"""


class LanguageReportBuilder:

    def __init__(self):
        print("Language Report Builder Loaded")

    def get_engine_confidence(self, data, engine_name):
        engine_data = data.get(engine_name, {})

        if not isinstance(engine_data, dict):
            return 0

        confidence = engine_data.get("confidence", 0)
        return confidence if isinstance(confidence, (int, float)) else 0

    def build_language_summary(self, raw_report):
        analysis = raw_report.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = {}

        return {
            "detected_language": analysis.get("detected_language", "unknown"),
            "language_name": analysis.get("language_name", "unknown"),
            "writing_direction": analysis.get("writing_direction", "unknown"),
            "alphabet": analysis.get("alphabet", []),
            "text_type": analysis.get("text_type", "unknown"),
            "formality": analysis.get("formality", {}),
            "semantic_frame": analysis.get("semantic_frame", {}),
            "discourse": analysis.get("discourse", {}),
            "precision_contract": {
                "quantified_constraints": analysis.get("semantic_frame", {}).get("quantified_constraints", []),
                "explicit_constraints": analysis.get("semantic_frame", {}).get("explicit_constraints", []),
                "output_constraints": analysis.get("semantic_frame", {}).get("output_constraints", []),
                "continuation": analysis.get("semantic_frame", {}).get("continuation", {}),
                "code_fragments": analysis.get("semantic_frame", {}).get("code_fragments", []),
                "understanding_contract_used": analysis.get("semantic_frame", {}).get("understanding_contract_used", False),
                "understanding_requirements": analysis.get("semantic_frame", {}).get("understanding_requirements", []),
                "detail_count": analysis.get("semantic_frame", {}).get("detail_count", 0),
            },
            "word_tags": analysis.get("word_tags", []),
            "context_links": analysis.get("context_links", []),
            "complexity": analysis.get("complexity", {}),
        }

    def build_translation_summary(self, raw_report):
        translation = raw_report.get("translation", {})
        if not isinstance(translation, dict):
            translation = {}

        result = translation.get("result", {})
        if not isinstance(result, dict):
            result = {}

        return {
            "is_translation_request": translation.get("is_translation_request", False),
            "source_language": translation.get("source_language", "unknown"),
            "target_language": translation.get("target_language", "unknown"),
            "translated_text": translation.get("translated_text") or result.get("translated_text", ""),
            "found_count": result.get("found_count", 0),
            "total_words": result.get("total_words", 0),
            "translated_words": translation.get("translated_words") or result.get("translated_words", []),
            "missing_words": translation.get("missing_words") or result.get("missing_words", []),
            "confidence": translation.get("confidence", 0),
        }

    def build_grammar_summary(self, raw_report):
        grammar = raw_report.get("grammar", {})
        if not isinstance(grammar, dict):
            grammar = {}

        input_text = grammar.get("input_text", raw_report.get("input_text", ""))
        fixed_text = grammar.get("fixed_text", input_text)
        grammar_changed = (
            input_text != fixed_text
            and str(input_text).lower() != str(fixed_text).lower()
        )

        return {
            "input_text": input_text,
            "fixed_text": fixed_text,
            "grammar_changed": grammar_changed,
            "known_words": grammar.get("known_words", 0),
            "total_words": grammar.get("total_words", 0),
            "word_type_groups": grammar.get("word_type_groups", {}),
            "grammar_issues": grammar.get("grammar_issues", []),
            "tenses": grammar.get("tenses", {}),
            "base_forms": grammar.get("base_forms", {}),
            "protected_code_spans": grammar.get("protected_code_spans", []),
            "confidence": grammar.get("confidence", 0),
        }

    def build_dictionary_summary(self, raw_report):
        dictionary = raw_report.get("dictionary", {})
        if not isinstance(dictionary, dict):
            dictionary = {}

        return {
            "focus_words": dictionary.get("focus_words", []),
            "is_dictionary_request": dictionary.get("is_dictionary_request", False),
            "definitions": dictionary.get("definitions", {}),
            "connections": dictionary.get("connections", {}),
            "synonyms": dictionary.get("synonyms", {}),
            "antonyms": dictionary.get("antonyms", {}),
            "technical_terms": dictionary.get("technical_terms", {}),
            "abbreviations": dictionary.get("abbreviations", {}),
            "scanner_definitions": dictionary.get("scanner_definitions", []),
            "answer": dictionary.get("answer", ""),
            "confidence": dictionary.get("confidence", 0),
        }

    def build_expressions_summary(self, raw_report):
        expressions = raw_report.get("expressions", {})
        if not isinstance(expressions, dict):
            expressions = {}

        return {
            "idioms": expressions.get("idioms", {}),
            "slang": expressions.get("slang", {}),
            "emojis": expressions.get("emojis", {}),
            "units": expressions.get("units", []),
            "discourse_relations": expressions.get("discourse_relations", []),
            "interaction_signals": expressions.get("interaction_signals", []),
            "enumerations": expressions.get("enumerations", []),
            "summary": expressions.get("summary", []),
            "answer": expressions.get("answer", ""),
            "confidence": expressions.get("confidence", 0),
        }

    def build_statistics_summary(self, raw_report):
        statistics = raw_report.get("statistics", {})
        if not isinstance(statistics, dict):
            statistics = {}

        return {
            "language": statistics.get("language", "unknown"),
            "summary": statistics.get("summary", {}),
            "statistics_file": statistics.get("statistics_file", ""),
            "history_file": statistics.get("history_file", ""),
            "saved": statistics.get("saved", False),
            "confidence": statistics.get("confidence", 0),
        }

    def calculate_final_confidence(self, raw_report):
        values = []

        for key in ["analysis", "grammar", "translation", "dictionary", "expressions", "statistics"]:
            confidence = self.get_engine_confidence(raw_report, key)
            if confidence > 0:
                values.append(confidence)

        return round(sum(values) / len(values), 2) if values else 0

    def collect_warnings(self, raw_report):
        warnings = []

        if not raw_report.get("language_data_loaded"):
            warnings.append("Language data was not loaded.")

        for key in ["analysis", "grammar", "translation", "dictionary", "expressions", "statistics"]:
            value = raw_report.get(key)
            if isinstance(value, dict) and "error" in value:
                warnings.append(f"{key} error: {value.get('error')}")

        analysis = raw_report.get("analysis", {})
        frame = analysis.get("semantic_frame", {}) if isinstance(analysis, dict) else {}
        if isinstance(frame, dict) and frame.get("continuation", {}).get("is_continuation"):
            if not frame.get("continuation", {}).get("must_preserve_previous_result"):
                warnings.append("Continuation was detected without a preservation contract.")

        return list(dict.fromkeys(warnings))

    def detect_needs_help(self, final_confidence, warnings):
        if final_confidence < 30:
            return True

        return any("error" in warning.lower() for warning in warnings)

    def build_human_summary(
        self,
        language_summary,
        translation_summary,
        grammar_summary,
        dictionary_summary,
        expressions_summary,
        final_confidence,
    ):
        lines = [
            f"Detected language: {language_summary.get('detected_language', 'unknown')}",
            f"Text type: {language_summary.get('text_type', 'unknown')}",
        ]

        frame = language_summary.get("semantic_frame", {})
        if frame:
            lines.append(f"Requested output: {frame.get('requested_output', 'answer')}")
            if frame.get("actions"):
                lines.append(f"Actions: {', '.join(frame.get('actions', [])[:5])}")

        if translation_summary.get("is_translation_request"):
            lines.append("Translation request detected.")

        if grammar_summary.get("grammar_changed"):
            lines.append("Grammar was changed.")

        if dictionary_summary.get("answer"):
            lines.append("Dictionary answer built.")

        if expressions_summary.get("answer"):
            lines.append("Expression answer built.")

        lines.append(f"Final confidence: {final_confidence}")
        return lines

    def build_final_answer(
        self,
        translation_summary,
        grammar_summary,
        dictionary_summary,
        expressions_summary,
        language_summary,
    ):
        parts = []

        if translation_summary.get("is_translation_request") and translation_summary.get("translated_text"):
            parts.append(translation_summary["translated_text"])

        if grammar_summary.get("grammar_changed"):
            parts.append(f"Corrected text: {grammar_summary.get('fixed_text')}")

        if dictionary_summary.get("answer"):
            parts.append(dictionary_summary["answer"])

        if expressions_summary.get("answer"):
            parts.append(expressions_summary["answer"])

        if not parts:
            frame = language_summary.get("semantic_frame", {})
            if frame:
                actions = ", ".join(frame.get("actions", [])[:5]) or "none"
                output = frame.get("requested_output", "answer")
                parts.append(f"Language understood. Actions: {actions}. Requested output: {output}.")
            else:
                parts.append("Language understood.")

        return "\n".join(parts)

    def build(self, raw_report):
        input_text = raw_report.get("input_text", "")
        understanding_report = raw_report.get("understanding_report", {})
        language_summary = self.build_language_summary(raw_report)
        translation_summary = self.build_translation_summary(raw_report)
        grammar_summary = self.build_grammar_summary(raw_report)
        dictionary_summary = self.build_dictionary_summary(raw_report)
        expressions_summary = self.build_expressions_summary(raw_report)
        statistics_summary = self.build_statistics_summary(raw_report)
        final_confidence = self.calculate_final_confidence(raw_report)
        warnings = self.collect_warnings(raw_report)
        needs_help = self.detect_needs_help(final_confidence, warnings)
        human_summary = self.build_human_summary(
            language_summary,
            translation_summary,
            grammar_summary,
            dictionary_summary,
            expressions_summary,
            final_confidence,
        )
        final_answer = self.build_final_answer(
            translation_summary,
            grammar_summary,
            dictionary_summary,
            expressions_summary,
            language_summary,
        )

        return {
            "brain": "Language_brain",
            "input_text": input_text,
            "main_topic": understanding_report.get("main_topic", "unknown") if isinstance(understanding_report, dict) else "unknown",
            "intent": understanding_report.get("intent", "unknown") if isinstance(understanding_report, dict) else "unknown",
            "language": language_summary,
            "translation": translation_summary,
            "grammar": grammar_summary,
            "dictionary": dictionary_summary,
            "expressions": expressions_summary,
            "statistics": statistics_summary,
            "precision_contract": language_summary.get("precision_contract", {}),
            "scanner_evidence": raw_report.get("scanner_evidence", []),
            "scanner_usage": raw_report.get("scanner_usage", {}),
            "human_summary": human_summary,
            "answer": final_answer,
            "final_output": final_answer,
            "confidence": final_confidence,
            "warnings": warnings,
            "needs_help": needs_help,
            "raw": raw_report,
        }


builder = LanguageReportBuilder()
