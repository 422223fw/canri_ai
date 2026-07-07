"""
Language_brain_5.py
Canri AI

Expressions Engine.
Uses:
- Idioms.json
- Slang_dictionary.json
- Units_dictionary.json
- Emoji_dictionary.json

Responsible for:
- Idiom detection
- Slang detection
- Emoji meaning detection
- Unit detection / translation
"""

import re


class ExpressionsEngine:

    def __init__(self):

        print("Expressions Engine Loaded")

    # =========================
    # BASIC TOOLS
    # =========================

    def clean_text(self, text):

        return str(text).lower().strip()

    def clean_word(self, word):

        return str(word).lower().strip(".,!?;:\"'()[]{}")

    def extract_words(self, text):

        return re.findall(
            r"\w+|[^\w\s]",
            str(text)
        )

    # =========================
    # DATA GETTERS
    # =========================

    def get_idioms_data(self, language_data):

        return language_data.get(
            "idioms",
            {}
        )

    def get_slang_data(self, language_data):

        return language_data.get(
            "slang",
            {}
        )

    def get_units_data(self, language_data):

        return language_data.get(
            "units",
            {}
        )

    def get_emojis_data(self, language_data):

        return language_data.get(
            "emojis",
            {}
        )

    # =========================
    # IDIOMS
    # =========================

    def find_idioms(self, text, language_data):

        idioms = self.get_idioms_data(
            language_data
        )

        text_lower = self.clean_text(
            text
        )

        results = {}

        for idiom, data in idioms.items():

            idiom_lower = idiom.lower()

            if idiom_lower in text_lower:

                results[idiom] = data

        return results

    # =========================
    # SLANG
    # =========================

    def find_slang(self, text, language_data):

        slang = self.get_slang_data(
            language_data
        )

        words = self.extract_words(
            text
        )

        results = {}

        for word in words:

            clean = self.clean_word(
                word
            )

            if clean in slang:

                results[clean] = slang[clean]

        return results

    # =========================
    # EMOJIS
    # =========================

    def find_emojis(self, text, language_data):

        emojis = self.get_emojis_data(
            language_data
        )

        results = {}

        for char in str(text):

            if char in emojis:

                results[char] = emojis[char]

        return results

    # =========================
    # UNITS
    # =========================

    def find_units(self, text, language_data):

        units = self.get_units_data(
            language_data
        )

        results = []

        # דוגמה: 10 km / 5kg / 30 cm / 100 dollars
        pattern = r"(\d+(?:\.\d+)?)\s*([A-Za-zא-ת₪$%°]+)"

        matches = re.findall(
            pattern,
            str(text)
        )

        for value, unit in matches:

            clean_unit = unit.lower().strip()

            if clean_unit in units:

                results.append({
                    "value": value,
                    "unit": clean_unit,
                    "data": units[clean_unit]
                })

        return results

    # =========================
    # EXPRESSION SUMMARY
    # =========================

    def build_expression_summary(
        self,
        idioms,
        slang,
        emojis,
        units
    ):

        summary = []

        if idioms:

            summary.append(
                "Idioms found"
            )

        if slang:

            summary.append(
                "Slang found"
            )

        if emojis:

            summary.append(
                "Emoji meanings found"
            )

        if units:

            summary.append(
                "Units found"
            )

        if not summary:

            summary.append(
                "No special expressions found"
            )

        return summary

    # =========================
    # CONFIDENCE
    # =========================

    def calculate_confidence(
        self,
        idioms,
        slang,
        emojis,
        units
    ):

        score = 0

        score += len(idioms) * 25
        score += len(slang) * 20
        score += len(emojis) * 15
        score += len(units) * 20

        return min(
            score,
            100
        )

    # =========================
    # MAIN PROCESS
    # =========================

    def process(self, text, report, language_data):

        idioms = self.find_idioms(
            text,
            language_data
        )

        slang = self.find_slang(
            text,
            language_data
        )

        emojis = self.find_emojis(
            text,
            language_data
        )

        units = self.find_units(
            text,
            language_data
        )

        summary = self.build_expression_summary(
            idioms,
            slang,
            emojis,
            units
        )

        confidence = self.calculate_confidence(
            idioms,
            slang,
            emojis,
            units
        )

        return {
            "engine": "ExpressionsEngine",

            "idioms": idioms,

            "slang": slang,

            "emojis": emojis,

            "units": units,

            "summary": summary,

            "confidence": confidence
        }


engine = ExpressionsEngine()