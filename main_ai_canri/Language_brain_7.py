"""
Language_brain_7.py
Canri AI

Language Analysis Engine.

Uses:
- Languages.json
- Language_models.json
- Language_rules.json
- Language_examples.json

Responsible for:
- Language detection
- Writing direction detection
- Alphabet detection
- Language model lookup
- Style detection
- Formal / informal detection
"""


import re


class LanguageAnalysisEngine:

    def __init__(self):

        print("Language Analysis Engine Loaded")

    # =========================
    # BASIC TOOLS
    # =========================

    def normalize_text(self, text):

        return str(text).strip()

    def count_hebrew_chars(self, text):

        return len(
            re.findall(
                r"[א-ת]",
                str(text)
            )
        )

    def count_english_chars(self, text):

        return len(
            re.findall(
                r"[A-Za-z]",
                str(text)
            )
        )

    def count_digits(self, text):

        return len(
            re.findall(
                r"\d",
                str(text)
            )
        )

    def count_symbols(self, text):

        return len(
            re.findall(
                r"[^\w\sא-תA-Za-z]",
                str(text)
            )
        )

    def extract_words(self, text):

        return re.findall(
            r"[A-Za-zא-ת]+",
            str(text)
        )

    # =========================
    # DATA GETTERS
    # =========================

    def get_languages_data(self, language_data):

        return language_data.get(
            "languages",
            {}
        )

    def get_models_data(self, language_data):

        return language_data.get(
            "models",
            {}
        )

    def get_rules_data(self, language_data):

        return language_data.get(
            "rules",
            {}
        )

    def get_examples_data(self, language_data):

        return language_data.get(
            "examples",
            []
        )

    # =========================
    # LANGUAGE DETECTION
    # =========================

    def detect_language_by_chars(self, text):

        hebrew_count = self.count_hebrew_chars(
            text
        )

        english_count = self.count_english_chars(
            text
        )

        if hebrew_count == 0 and english_count == 0:
            return {
                "language": "unknown",
                "reason": "no alphabetic characters",
                "hebrew_chars": hebrew_count,
                "english_chars": english_count
            }

        if hebrew_count > 0 and english_count > 0:
            return {
                "language": "mixed",
                "reason": "hebrew and english characters found",
                "hebrew_chars": hebrew_count,
                "english_chars": english_count
            }

        if hebrew_count > english_count:
            return {
                "language": "he",
                "reason": "more hebrew characters",
                "hebrew_chars": hebrew_count,
                "english_chars": english_count
            }

        return {
            "language": "en",
            "reason": "more english characters",
            "hebrew_chars": hebrew_count,
            "english_chars": english_count
        }

    def detect_language_from_report(self, report):

        if not isinstance(report, dict):
            return None

        for key in [
            "language",
            "detected_language",
            "source_language"
        ]:
            value = report.get(
                key
            )

            if value:
                return value

        return None

    def detect_language_from_models(self, text, language_data):

        models = self.get_models_data(
            language_data
        )

        text_lower = str(text).lower()

        scores = {}

        for language_code, model in models.items():

            score = 0

            alphabet = model.get(
                "alphabet",
                []
            )

            common_words = model.get(
                "common_words",
                []
            )

            special_rules = model.get(
                "special_rules",
                []
            )

            for char in alphabet:

                if char and char in text:
                    score += 1

            for word in common_words:

                if word.lower() in text_lower.split():
                    score += 5

            for rule in special_rules:

                if isinstance(rule, str) and rule.lower() in text_lower:
                    score += 2

            if score > 0:
                scores[language_code] = score

        if not scores:
            return None

        return max(
            scores,
            key=scores.get
        )

    def detect_language(self, text, report, language_data):

        from_report = self.detect_language_from_report(
            report
        )

        if from_report:
            return {
                "detected_language": from_report,
                "method": "understanding_report",
                "confidence": 90
            }

        from_models = self.detect_language_from_models(
            text,
            language_data
        )

        if from_models:
            return {
                "detected_language": from_models,
                "method": "language_models",
                "confidence": 85
            }

        char_result = self.detect_language_by_chars(
            text
        )

        confidence = 70

        if char_result["language"] == "unknown":
            confidence = 0

        if char_result["language"] == "mixed":
            confidence = 60

        return {
            "detected_language": char_result["language"],
            "method": "character_detection",
            "reason": char_result["reason"],
            "hebrew_chars": char_result["hebrew_chars"],
            "english_chars": char_result["english_chars"],
            "confidence": confidence
        }

    # =========================
    # WRITING DIRECTION
    # =========================

    def detect_direction(self, language_code, language_data):

        models = self.get_models_data(
            language_data
        )

        model = models.get(
            language_code,
            {}
        )

        direction = model.get(
            "direction"
        )

        if direction:
            return direction

        if language_code == "he":
            return "rtl"

        if language_code == "mixed":
            return "mixed"

        return "ltr"

    # =========================
    # ALPHABET
    # =========================

    def detect_alphabet(self, text):

        alphabets = []

        if self.count_hebrew_chars(text) > 0:
            alphabets.append(
                "hebrew"
            )

        if self.count_english_chars(text) > 0:
            alphabets.append(
                "latin"
            )

        if self.count_digits(text) > 0:
            alphabets.append(
                "numbers"
            )

        if self.count_symbols(text) > 0:
            alphabets.append(
                "symbols"
            )

        if not alphabets:
            alphabets.append(
                "unknown"
            )

        return alphabets

    # =========================
    # LANGUAGE MODEL
    # =========================

    def get_language_model(self, language_code, language_data):

        models = self.get_models_data(
            language_data
        )

        return models.get(
            language_code,
            {}
        )

    def get_language_name(self, language_code, language_data):

        languages = self.get_languages_data(
            language_data
        )

        if isinstance(languages, dict):

            data = languages.get(
                language_code
            )

            if isinstance(data, dict):

                return data.get(
                    "name",
                    language_code
                )

            if isinstance(data, str):

                return data

        if isinstance(languages, list):

            for item in languages:

                if isinstance(item, dict):

                    if item.get("code") == language_code:

                        return item.get(
                            "name",
                            language_code
                        )

        return language_code

    # =========================
    # STYLE DETECTION
    # =========================

    def detect_formality(self, text):

        text_lower = str(text).lower()

        formal_markers = [
            "please",
            "therefore",
            "however",
            "would you",
            "could you",
            "thank you",
            "בבקשה",
            "לפיכך",
            "עם זאת",
            "תודה",
            "האם תוכל"
        ]

        informal_markers = [
            "yo",
            "bro",
            "lol",
            "haha",
            "חח",
            "אחי",
            "יאללה",
            "סבבה",
            "כאילו"
        ]

        formal_score = 0
        informal_score = 0

        for marker in formal_markers:

            if marker in text_lower:
                formal_score += 1

        for marker in informal_markers:

            if marker in text_lower:
                informal_score += 1

        if formal_score > informal_score:
            return {
                "style": "formal",
                "formal_score": formal_score,
                "informal_score": informal_score
            }

        if informal_score > formal_score:
            return {
                "style": "informal",
                "formal_score": formal_score,
                "informal_score": informal_score
            }

        return {
            "style": "neutral",
            "formal_score": formal_score,
            "informal_score": informal_score
        }

    def detect_text_type(self, text):

        text_str = str(text).strip()

        if not text_str:
            return "empty"

        if text_str.endswith("?"):
            return "question"

        if text_str.endswith("!"):
            return "exclamation"

        if len(text_str.split()) <= 3:
            return "short_phrase"

        return "statement"

    # =========================
    # RULES
    # =========================

    def find_matching_rules(self, text, language_code, language_data):

        rules = self.get_rules_data(
            language_data
        )

        results = []

        if isinstance(rules, dict):

            language_rules = rules.get(
                language_code,
                []
            )

            general_rules = rules.get(
                "general",
                []
            )

            all_rules = []

            if isinstance(general_rules, list):
                all_rules.extend(
                    general_rules
                )

            if isinstance(language_rules, list):
                all_rules.extend(
                    language_rules
                )

            text_lower = str(text).lower()

            for rule in all_rules:

                if isinstance(rule, dict):

                    trigger = rule.get(
                        "trigger"
                    )

                    if trigger and trigger.lower() in text_lower:

                        results.append(rule)

                elif isinstance(rule, str):

                    if rule.lower() in text_lower:

                        results.append({
                            "rule": rule
                        })

        return results

    # =========================
    # EXAMPLES
    # =========================

    def find_related_examples(self, text, language_code, language_data):

        examples = self.get_examples_data(
            language_data
        )

        text_words = set(
            word.lower()
            for word in self.extract_words(text)
        )

        results = []

        if not isinstance(examples, list):
            return results

        for example in examples:

            if not isinstance(example, dict):
                continue

            example_language = example.get(
                "language"
            )

            if example_language and example_language != language_code:
                continue

            source = str(
                example.get("source", "")
            ).lower()

            target = str(
                example.get("target", "")
            ).lower()

            combined_words = set(
                self.extract_words(source + " " + target)
            )

            combined_words = set(
                word.lower()
                for word in combined_words
            )

            overlap = text_words.intersection(
                combined_words
            )

            if overlap:

                results.append({
                    "example": example,
                    "matched_words": list(overlap),
                    "score": len(overlap)
                })

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:5]

    # =========================
    # CONFIDENCE
    # =========================

    def calculate_confidence(
        self,
        language_result,
        alphabet,
        model,
        rules,
        examples
    ):

        confidence = language_result.get(
            "confidence",
            0
        )

        if alphabet and alphabet != ["unknown"]:
            confidence += 5

        if model:
            confidence += 10

        if rules:
            confidence += 5

        if examples:
            confidence += 5

        return min(
            confidence,
            100
        )

    # =========================
    # MAIN ANALYZE
    # =========================

    def analyze(self, text, report, language_data):

        text = self.normalize_text(
            text
        )

        language_result = self.detect_language(
            text,
            report,
            language_data
        )

        language_code = language_result.get(
            "detected_language",
            "unknown"
        )

        direction = self.detect_direction(
            language_code,
            language_data
        )

        alphabet = self.detect_alphabet(
            text
        )

        model = self.get_language_model(
            language_code,
            language_data
        )

        language_name = self.get_language_name(
            language_code,
            language_data
        )

        formality = self.detect_formality(
            text
        )

        text_type = self.detect_text_type(
            text
        )

        rules = self.find_matching_rules(
            text,
            language_code,
            language_data
        )

        examples = self.find_related_examples(
            text,
            language_code,
            language_data
        )

        confidence = self.calculate_confidence(
            language_result,
            alphabet,
            model,
            rules,
            examples
        )

        return {
            "engine": "LanguageAnalysisEngine",

            "input_text": text,

            "detected_language": language_code,

            "language_name": language_name,

            "detection": language_result,

            "writing_direction": direction,

            "alphabet": alphabet,

            "language_model": model,

            "formality": formality,

            "text_type": text_type,

            "matched_rules": rules,

            "related_examples": examples,

            "confidence": confidence
        }


engine = LanguageAnalysisEngine()