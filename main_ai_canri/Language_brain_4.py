"""
Language_brain_4.py
Canri AI

Dictionary Engine.
Uses:
- Synonyms.json
- Antonyms.json
- Technical_terms.json
- Abbreviations.json
- UnderstandingDk
"""


import re


try:
    import UnderstandingDk as dk
except Exception as e:
    dk = None
    print("[DictionaryEngine] Could not import UnderstandingDk:", e)


class DictionaryEngine:

    def __init__(self):

        print("Dictionary Engine Loaded")

    # =========================
    # BASIC TOOLS
    # =========================

    def clean_word(self, word):

        return word.lower().strip(".,!?;:\"'()[]{}")

    def extract_words(self, text):

        words = re.findall(
            r"\w+",
            text.lower()
        )

        return [
            self.clean_word(word)
            for word in words
            if word.strip()
        ]

    # =========================
    # DATA GETTERS
    # =========================

    def get_synonyms_data(self, language_data):

        return language_data.get(
            "synonyms",
            {}
        )

    def get_antonyms_data(self, language_data):

        return language_data.get(
            "antonyms",
            {}
        )

    def get_terms_data(self, language_data):

        return language_data.get(
            "technical_terms",
            {}
        )

    def get_abbreviations_data(self, language_data):

        return language_data.get(
            "abbreviations",
            {}
        )

    # =========================
    # SYNONYMS
    # =========================

    def find_synonyms(self, word, language_data):

        synonyms = self.get_synonyms_data(
            language_data
        )

        clean = self.clean_word(word)

        result = synonyms.get(
            clean,
            []
        )

        if isinstance(result, str):
            result = [result]

        return result

    def scan_synonyms(self, words, language_data):

        results = {}

        for word in words:

            found = self.find_synonyms(
                word,
                language_data
            )

            if found:
                results[word] = found

        return results

    # =========================
    # ANTONYMS
    # =========================

    def find_antonyms(self, word, language_data):

        antonyms = self.get_antonyms_data(
            language_data
        )

        clean = self.clean_word(word)

        result = antonyms.get(
            clean,
            []
        )

        if isinstance(result, str):
            result = [result]

        return result

    def scan_antonyms(self, words, language_data):

        results = {}

        for word in words:

            found = self.find_antonyms(
                word,
                language_data
            )

            if found:
                results[word] = found

        return results

    # =========================
    # TECHNICAL TERMS
    # =========================

    def find_technical_term(self, word, language_data):

        terms = self.get_terms_data(
            language_data
        )

        clean = self.clean_word(word)

        result = terms.get(
            clean
        )

        return result

    def scan_technical_terms(self, words, language_data):

        results = {}

        for word in words:

            found = self.find_technical_term(
                word,
                language_data
            )

            if found:
                results[word] = found

        return results

    # =========================
    # ABBREVIATIONS
    # =========================

    def find_abbreviation(self, word, language_data):

        abbreviations = self.get_abbreviations_data(
            language_data
        )

        clean = word.strip().upper()

        result = abbreviations.get(
            clean
        )

        if result:
            return result

        clean_lower = word.strip().lower()

        return abbreviations.get(
            clean_lower
        )

    def scan_abbreviations(self, text, language_data):

        words = re.findall(
            r"\b[A-Za-z]{2,10}\b",
            text
        )

        results = {}

        for word in words:

            found = self.find_abbreviation(
                word,
                language_data
            )

            if found:
                results[word] = found

        return results

    # =========================
    # UNDERSTANDING DK HELPERS
    # =========================

    def get_definitions(self, words):

        if dk is None:
            return {}

        results = {}

        for word in words:

            try:
                meanings = dk.get_meanings(
                    word
                )

                if meanings:
                    results[word] = meanings

            except Exception:
                pass

        return results

    def get_connections(self, words):

        if dk is None:
            return {}

        results = {}

        for word in words:

            try:
                connections = dk.related(
                    word
                )

                if connections:
                    results[word] = connections

            except Exception:
                pass

        return results

    def check_words_exist(self, words):

        if dk is None:
            return {}

        results = {}

        for word in words:

            try:
                results[word] = dk.word_exists(
                    word
                )

            except Exception:
                results[word] = False

        return results

    # =========================
    # CONFIDENCE
    # =========================

    def calculate_confidence(
        self,
        words,
        synonyms,
        antonyms,
        technical_terms,
        abbreviations,
        definitions,
        connections
    ):

        if not words:
            return 0

        score = 0

        score += len(synonyms) * 10
        score += len(antonyms) * 10
        score += len(technical_terms) * 15
        score += len(abbreviations) * 15
        score += len(definitions) * 10
        score += len(connections) * 10

        max_score = max(
            len(words) * 20,
            1
        )

        confidence = min(
            (score / max_score) * 100,
            100
        )

        return round(
            confidence,
            2
        )

    # =========================
    # MAIN PROCESS
    # =========================

    def process(self, text, report, language_data):

        words = self.extract_words(
            text
        )

        synonyms = self.scan_synonyms(
            words,
            language_data
        )

        antonyms = self.scan_antonyms(
            words,
            language_data
        )

        technical_terms = self.scan_technical_terms(
            words,
            language_data
        )

        abbreviations = self.scan_abbreviations(
            text,
            language_data
        )

        definitions = self.get_definitions(
            words
        )

        connections = self.get_connections(
            words
        )

        word_exists = self.check_words_exist(
            words
        )

        confidence = self.calculate_confidence(
            words,
            synonyms,
            antonyms,
            technical_terms,
            abbreviations,
            definitions,
            connections
        )

        return {
            "engine": "DictionaryEngine",

            "words": words,

            "word_exists": word_exists,

            "definitions": definitions,

            "connections": connections,

            "synonyms": synonyms,

            "antonyms": antonyms,

            "technical_terms": technical_terms,

            "abbreviations": abbreviations,

            "confidence": confidence
        }


engine = DictionaryEngine()