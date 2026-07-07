"""
Language_brain_3.py
Canri AI

Grammar Engine.
Uses UnderstandingDk for grammar, sentence analysis, verb forms and tense detection.
"""

import re

try:
    import UnderstandingDk as dk
except Exception as e:
    dk = None
    print("[GrammarEngine] Could not import UnderstandingDk:", e)


class GrammarEngine:

    def __init__(self):

        print("Grammar Engine Loaded")

    def clean_word(self, word):

        return word.lower().strip(".,!?;:\"'()[]{}")

    def analyze_words(self, text):

        if dk is None:
            return []

        words = re.findall(
            r"\w+|[^\w\s]",
            text.lower()
        )

        results = []

        for word in words:

            if not word.isalpha():
                continue

            clean = self.clean_word(word)

            results.append({
                "word": clean,
                "exists": dk.word_exists(clean),
                "grammar_exists": dk.grammar_exists(clean),
                "tense": dk.detect_tense(clean),
                "forms": dk.get_forms(clean),
                "meanings": dk.get_meanings(clean)
            })

        return results

    def fix_grammar(self, text):

        if dk is None:
            return text

        try:
            return dk.fix_sentence(text)

        except Exception:
            return text

    def analyze_sentence(self, text):

        if dk is None:
            return []

        try:
            return dk.analyze_sentence(text)

        except Exception:
            return []

    def detect_tenses(self, text):

        if dk is None:
            return {}

        words = text.lower().split()

        tenses = {}

        for word in words:

            clean = self.clean_word(word)

            tense = dk.detect_tense(clean)

            if tense:
                tenses[clean] = tense

        return tenses

    def get_base_forms(self, text):

        if dk is None:
            return {}

        words = text.lower().split()

        bases = {}

        for word in words:

            clean = self.clean_word(word)

            base = dk.get_verb_base(clean)

            if base:
                bases[clean] = base

        return bases

    def process(self, text, report=None):

        if report is None:
            report = {}

        fixed_text = self.fix_grammar(text)

        word_analysis = self.analyze_words(text)

        sentence_analysis = self.analyze_sentence(text)

        tenses = self.detect_tenses(text)

        base_forms = self.get_base_forms(text)

        known_words = sum(
            1 for item in word_analysis
            if item.get("exists")
        )

        total_words = len(word_analysis)

        confidence = 0

        if total_words > 0:
            confidence = round(
                (known_words / total_words) * 100,
                2
            )

        return {
            "engine": "GrammarEngine",
            "input_text": text,
            "fixed_text": fixed_text,
            "word_analysis": word_analysis,
            "sentence_analysis": sentence_analysis,
            "tenses": tenses,
            "base_forms": base_forms,
            "known_words": known_words,
            "total_words": total_words,
            "confidence": confidence
        }


engine = GrammarEngine()