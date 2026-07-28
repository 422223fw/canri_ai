"""
Language_brain_4.py
Canri AI

Dictionary Engine.
Uses synonyms, antonyms, technical terms, abbreviations and UnderstandingDk.
"""

import re

try:
    import UnderstandingDk as dk
except Exception as error:
    dk = None
    print("[DictionaryEngine] Could not import UnderstandingDk:", error)


class DictionaryEngine:

    def __init__(self):
        print("Dictionary Engine Loaded")

    def clean_word(self, word):
        return str(word).lower().strip(".,!?;:\"'()[]{}")

    def extract_words(self, text):
        return [
            self.clean_word(word)
            for word in re.findall(r"\w+", str(text), flags=re.UNICODE)
            if word.strip()
        ]

    def get_synonyms_data(self, language_data):
        return language_data.get("synonyms", {})

    def get_antonyms_data(self, language_data):
        return language_data.get("antonyms", {})

    def get_terms_data(self, language_data):
        return language_data.get("technical_terms", {})

    def get_abbreviations_data(self, language_data):
        return language_data.get("abbreviations", {})

    def as_list(self, value):
        if isinstance(value, list):
            return value
        if value:
            return [value]
        return []

    def find_synonyms(self, word, language_data):
        return self.as_list(self.get_synonyms_data(language_data).get(self.clean_word(word), []))

    def find_antonyms(self, word, language_data):
        return self.as_list(self.get_antonyms_data(language_data).get(self.clean_word(word), []))

    def find_technical_term(self, word, language_data):
        return self.get_terms_data(language_data).get(self.clean_word(word))

    def find_abbreviation(self, word, language_data):
        abbreviations = self.get_abbreviations_data(language_data)
        return abbreviations.get(str(word).strip().upper()) or abbreviations.get(str(word).strip().lower())

    def scan_synonyms(self, words, language_data):
        return {
            word: found
            for word in words
            for found in [self.find_synonyms(word, language_data)]
            if found
        }

    def scan_antonyms(self, words, language_data):
        return {
            word: found
            for word in words
            for found in [self.find_antonyms(word, language_data)]
            if found
        }

    def scan_technical_terms(self, words, language_data):
        results = {
            word: found
            for word in words
            for found in [self.find_technical_term(word, language_data)]
            if found
        }
        terms = self.get_terms_data(language_data)
        if isinstance(terms, dict):
            joined = " ".join(words)
            for term, data in terms.items():
                normalized = str(term).lower().strip()
                if " " in normalized and normalized in joined:
                    results[normalized] = data
        return results

    def scanner_definitions(self, focus_words, language_data):

        focus = {str(word).lower() for word in focus_words if str(word).strip()}
        matches = []
        for item in language_data.get("scanner_evidence", [])[:8]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", ""))
            summary = str(item.get("summary") or item.get("content_excerpt") or "").strip()
            searchable = f"{title} {summary}".lower()
            overlap = sorted(word for word in focus if word in searchable)
            if not summary or not overlap:
                continue
            matches.append({
                "title": title,
                "summary": summary[:700],
                "trust_score": item.get("trust_score", 0),
                "matched_words": overlap,
                "sources": item.get("sources", [])[:3],
            })
        return matches

    def scan_abbreviations(self, text, language_data):
        results = {}

        for word in re.findall(r"\b[A-Za-z]{2,12}\b", str(text)):
            found = self.find_abbreviation(word, language_data)
            if found:
                results[word] = found

        return results

    def get_definitions(self, words):
        if dk is None:
            return {}

        results = {}

        for word in words:
            try:
                meanings = dk.get_meanings(word)
            except Exception:
                meanings = []

            if meanings:
                results[word] = meanings

        return results

    def get_connections(self, words):
        if dk is None:
            return {}

        results = {}

        for word in words:
            try:
                connections = dk.related(word)
            except Exception:
                connections = []

            if connections:
                results[word] = connections

        return results

    def check_words_exist(self, words):
        if dk is None:
            return {}

        results = {}

        for word in words:
            try:
                results[word] = dk.word_exists(word)
            except Exception:
                results[word] = False

        return results

    def detect_dictionary_request(self, text, report):
        text_lower = str(text).lower()
        markers = [
            "define",
            "definition",
            "meaning",
            "what is",
            "what are",
            "synonym",
            "antonym",
            "abbreviation",
            "term",
            "means",
        ]

        if any(marker in text_lower for marker in markers):
            return True

        if isinstance(report, dict):
            intent = str(report.get("intent", "")).lower()
            return intent in ["definition", "dictionary", "explanation", "language"]

        return False

    def extract_focus_words(self, words, report):
        focus = []

        if isinstance(report, dict):
            frame = report.get("semantic_frame", {})
            if isinstance(frame, dict):
                for key in ["targets", "objects", "technical_terms"]:
                    values = frame.get(key, [])
                    if isinstance(values, list):
                        focus.extend(str(value).lower() for value in values)

        stop_words = {
            "what", "is", "are", "the", "a", "an", "of", "to", "in",
            "define", "definition", "meaning", "means", "synonym", "antonym",
            "for", "give", "me", "tell", "explain",
        }
        focus.extend(word for word in words if word not in stop_words)
        return list(dict.fromkeys(focus))

    def first_definition_text(self, definitions, focus_words):
        ordered_words = list(dict.fromkeys(focus_words + list(definitions.keys())))

        for word in ordered_words:
            meanings = definitions.get(word)
            if not meanings:
                continue

            first = meanings[0] if isinstance(meanings, list) else meanings
            if isinstance(first, dict):
                definition = first.get("definition") or first.get("meaning")
                if definition:
                    return word, definition
            elif isinstance(first, str):
                return word, first

        return None, None

    def build_answer(
        self,
        is_dictionary_request,
        focus_words,
        definitions,
        synonyms,
        antonyms,
        technical_terms,
        abbreviations,
        scanner_definitions,
    ):
        if not is_dictionary_request:
            return ""

        lines = []
        word, definition = self.first_definition_text(definitions, focus_words)

        if word and definition:
            lines.append(f"{word} means: {definition}")

        for word in focus_words[:5]:
            if word in technical_terms:
                data = technical_terms[word]
                meaning = data.get("meaning") if isinstance(data, dict) else data
                if meaning:
                    lines.append(f"{word} is a technical term: {meaning}")

            if word in abbreviations:
                data = abbreviations[word]
                full = data.get("full") if isinstance(data, dict) else data
                if full:
                    lines.append(f"{word} stands for {full}.")

            if word in synonyms:
                lines.append(f"Synonyms for {word}: {', '.join(map(str, synonyms[word][:6]))}.")

            if word in antonyms:
                lines.append(f"Antonyms for {word}: {', '.join(map(str, antonyms[word][:6]))}.")

        if not lines and is_dictionary_request:
            if scanner_definitions:
                evidence = scanner_definitions[0]
                lines.append(
                    f"{evidence.get('title')}: {evidence.get('summary')}"
                )
            else:
                lines.append("I checked the local language dictionaries but did not find a strong definition.")

        return "\n".join(lines)

    def calculate_confidence(
        self,
        words,
        synonyms,
        antonyms,
        technical_terms,
        abbreviations,
        scanner_definitions,
        definitions,
        connections,
    ):
        if not words:
            return 0

        score = 0
        score += len(synonyms) * 10
        score += len(antonyms) * 10
        score += len(technical_terms) * 15
        score += len(abbreviations) * 15
        score += len(scanner_definitions) * 8
        score += len(definitions) * 10
        score += len(connections) * 5
        max_score = max(len(words) * 20, 1)
        return round(min((score / max_score) * 100, 100), 2)

    def process(self, text, report, language_data):
        words = self.extract_words(text)
        focus_words = self.extract_focus_words(words, report)
        is_dictionary_request = self.detect_dictionary_request(text, report)
        synonyms = self.scan_synonyms(words, language_data)
        antonyms = self.scan_antonyms(words, language_data)
        technical_terms = self.scan_technical_terms(words, language_data)
        abbreviations = self.scan_abbreviations(text, language_data)
        definitions = self.get_definitions(words)
        connections = self.get_connections(words)
        word_exists = self.check_words_exist(words)
        scanner_matches = self.scanner_definitions(focus_words, language_data)
        confidence = self.calculate_confidence(
            words,
            synonyms,
            antonyms,
            technical_terms,
            abbreviations,
            scanner_matches,
            definitions,
            connections,
        )
        answer = self.build_answer(
            is_dictionary_request,
            focus_words,
            definitions,
            synonyms,
            antonyms,
            technical_terms,
            abbreviations,
            scanner_matches,
        )

        return {
            "engine": "DictionaryEngine",
            "words": words,
            "focus_words": focus_words,
            "is_dictionary_request": is_dictionary_request,
            "word_exists": word_exists,
            "definitions": definitions,
            "connections": connections,
            "synonyms": synonyms,
            "antonyms": antonyms,
            "technical_terms": technical_terms,
            "abbreviations": abbreviations,
            "scanner_definitions": scanner_matches,
            "answer": answer,
            "confidence": confidence,
        }


engine = DictionaryEngine()
