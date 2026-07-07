"""
Language_brain_2.py
Canri AI

Translation Engine.
Uses Translation_dictionary.json and other language data loaded by Language_brain_1.
"""


class TranslationEngine:

    def __init__(self):

        print("Translation Engine Loaded")

    def detect_target_language(self, text, report, language_data):

        text_lower = text.lower()

        if "to hebrew" in text_lower or "עברית" in text_lower:
            return "he"

        if "to english" in text_lower or "אנגלית" in text_lower:
            return "en"

        if isinstance(report, dict):
            target = report.get("target_language")
            if target:
                return target

        return "he"

    def get_translation_table(self, language_data):

        return language_data.get(
            "translations",
            {}
        )

    def translate_word(self, word, target_language, language_data):

        translations = self.get_translation_table(
            language_data
        )

        clean_word = word.lower().strip(".,!?;:\"'()[]{}")

        entry = translations.get(clean_word)

        if not entry:
            return {
                "original": word,
                "translated": word,
                "found": False,
                "confidence": 0
            }

        if isinstance(entry, dict):

            translated = entry.get(
                target_language,
                word
            )

        else:

            translated = entry

        return {
            "original": word,
            "translated": translated,
            "found": translated != word,
            "confidence": 100 if translated != word else 0
        }

    def translate_sentence(self, text, target_language, language_data):

        words = text.split()

        translated_words = []
        word_reports = []

        for word in words:

            result = self.translate_word(
                word,
                target_language,
                language_data
            )

            translated_words.append(
                result["translated"]
            )

            word_reports.append(result)

        translated_text = " ".join(
            translated_words
        )

        found_count = sum(
            1
            for item in word_reports
            if item["found"]
        )

        confidence = 0

        if words:
            confidence = round(
                (found_count / len(words)) * 100,
                2
            )

        return {
            "translated_text": translated_text,
            "target_language": target_language,
            "translated_words": word_reports,
            "found_count": found_count,
            "total_words": len(words),
            "confidence": confidence
        }

    def detect_translation_request(self, text, report):

        text_lower = text.lower()

        if "translate" in text_lower:
            return True

        if "תרגם" in text_lower or "תתרגם" in text_lower:
            return True

        if isinstance(report, dict):

            intent = report.get("intent", "")

            if intent in [
                "translation",
                "translate",
                "language_translation"
            ]:
                return True

        return False

    def process(self, text, report, language_data):

        target_language = self.detect_target_language(
            text,
            report,
            language_data
        )

        is_translation_request = self.detect_translation_request(
            text,
            report
        )

        translation_result = self.translate_sentence(
            text,
            target_language,
            language_data
        )

        return {
            "engine": "TranslationEngine",
            "is_translation_request": is_translation_request,
            "target_language": target_language,
            "result": translation_result,
            "confidence": translation_result.get(
                "confidence",
                0
            )
        }


engine = TranslationEngine()