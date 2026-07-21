"""
Language_brain_2.py
Canri AI

Translation Engine.
Uses Translation_dictionary.json and preserves punctuation/case where possible.
"""

import re


class TranslationEngine:

    def __init__(self):
        print("Translation Engine Loaded")
        self.language_aliases = {
            "he": ["he", "hebrew", "עברית"],
            "en": ["en", "english", "אנגלית"],
            "fr": ["fr", "french", "francais", "français", "צרפתית"],
        }

    def get_translation_table(self, language_data):
        return language_data.get("translations", {})

    def detect_source_language(self, text, report):
        if isinstance(report, dict):
            for key in ["source_language", "detected_language", "language"]:
                value = report.get(key)
                if value:
                    return value

        if re.search(r"[\u0590-\u05FF]", str(text)):
            return "he"

        if re.search(r"[A-Za-z]", str(text)):
            return "en"

        return "unknown"

    def detect_target_language(self, text, report, language_data):
        text_lower = str(text).lower()

        if isinstance(report, dict):
            target = report.get("target_language")
            if target:
                return target

        for code, aliases in self.language_aliases.items():
            for alias in aliases:
                alias_lower = alias.lower()
                if (
                    f"to {alias_lower}" in text_lower
                    or f"into {alias_lower}" in text_lower
                    or f"in {alias_lower}" in text_lower
                    or alias_lower in text_lower.split()
                ):
                    return code

        return "he"

    def detect_translation_request(self, text, report):
        text_lower = str(text).lower()

        if "translate" in text_lower or "translation" in text_lower:
            return True

        if "תרגם" in text_lower or "תתרגם" in text_lower:
            return True

        if isinstance(report, dict):
            intent = str(report.get("intent", "")).lower()
            if intent in ["translation", "translate", "language_translation"]:
                return True

        return False

    def tokenize(self, text):
        pattern = (
            r"```[\s\S]*?```|`[^`\n]+`|https?://[^\s]+|"
            r"\b[A-Za-z_][A-Za-z0-9_]*\([^()\n]*\)|"
            r"\b[\w.-]+\.(?:jsonl?|py|txt|csv|md|html?|css|js|ts|ya?ml)\b|"
            r"\w+|[^\w\s]"
        )
        return re.findall(pattern, str(text), flags=re.UNICODE)

    def is_protected_token(self, token):

        value = str(token or "")
        return bool(
            value.startswith(("```", "`", "http://", "https://"))
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\([^()\n]*\)", value)
            or re.fullmatch(
                r"[\w.-]+\.(?:jsonl?|py|txt|csv|md|html?|css|js|ts|ya?ml)",
                value,
                flags=re.IGNORECASE,
            )
            or re.fullmatch(r"--?[A-Za-z][A-Za-z0-9-]*", value)
        )

    def join_tokens(self, tokens):
        text = ""

        for token in tokens:
            token = str(token)
            if not text:
                text = token
            elif re.match(r"^[.,!?;:%)\]\}]$", token):
                text += token
            elif re.match(r"^[(\[\{]$", token):
                text += " " + token
            else:
                text += " " + token

        return text.strip()

    def preserve_case(self, original, translated):
        if not isinstance(translated, str):
            return translated

        if original.isupper() and len(original) > 1:
            return translated.upper()

        if original[:1].isupper():
            return translated[:1].upper() + translated[1:]

        return translated

    def extract_translation_payload(self, text, target_language):
        cleaned = str(text).strip()

        if cleaned.lower().startswith("translate "):
            cleaned = cleaned[10:].strip()

        for alias in self.language_aliases.get(target_language, []):
            alias_lower = alias.lower()
            lower = cleaned.lower()
            for marker in [
                f" to {alias_lower}",
                f" into {alias_lower}",
                f" in {alias_lower}",
            ]:
                if marker in lower:
                    return cleaned[:lower.rfind(marker)].strip()

        return cleaned

    def translate_word(self, word, target_language, language_data):
        translations = self.get_translation_table(language_data)
        clean_word = str(word).lower().strip(".,!?;:\"'()[]{}")
        entry = translations.get(clean_word)

        if not entry:
            return {
                "original": word,
                "translated": word,
                "found": False,
                "confidence": 0,
            }

        if isinstance(entry, dict):
            translated = entry.get(target_language, word)
        else:
            translated = entry

        translated = self.preserve_case(str(word), translated)

        return {
            "original": word,
            "translated": translated,
            "found": translated != word,
            "confidence": 100 if translated != word else 0,
        }

    def translate_sentence(self, text, target_language, language_data):
        source_text = self.extract_translation_payload(text, target_language)
        tokens = self.tokenize(source_text)
        output_tokens = []
        word_reports = []
        protected_tokens = []

        for token in tokens:
            if self.is_protected_token(token):
                output_tokens.append(token)
                protected_tokens.append(token)
                continue
            if not re.search(r"\w", token, flags=re.UNICODE):
                output_tokens.append(token)
                continue

            result = self.translate_word(token, target_language, language_data)
            output_tokens.append(result["translated"])
            word_reports.append(result)

        found_count = sum(1 for item in word_reports if item.get("found"))
        total_words = len(word_reports)
        confidence = round((found_count / total_words) * 100, 2) if total_words else 0

        return {
            "source_text": source_text,
            "translated_text": self.join_tokens(output_tokens),
            "target_language": target_language,
            "translated_words": word_reports,
            "found_count": found_count,
            "total_words": total_words,
            "missing_words": [
                item["original"]
                for item in word_reports
                if not item.get("found")
            ],
            "protected_tokens": protected_tokens,
            "confidence": confidence,
        }

    def process(self, text, report, language_data):
        target_language = self.detect_target_language(text, report, language_data)
        is_translation_request = self.detect_translation_request(text, report)
        translation_result = self.translate_sentence(text, target_language, language_data)
        source_language = self.detect_source_language(text, report)

        return {
            "engine": "TranslationEngine",
            "is_translation_request": is_translation_request,
            "source_language": source_language,
            "target_language": target_language,
            "translated_text": translation_result.get("translated_text", ""),
            "translated_words": translation_result.get("translated_words", []),
            "missing_words": translation_result.get("missing_words", []),
            "protected_tokens": translation_result.get("protected_tokens", []),
            "result": translation_result,
            "confidence": translation_result.get("confidence", 0),
        }


engine = TranslationEngine()
