"""
Language_brain_5.py
Canri AI

Expressions Engine.
Detects idioms, slang, emojis and units.
"""

import re


class ExpressionsEngine:

    def __init__(self):
        print("Expressions Engine Loaded")

    def clean_text(self, text):
        return str(text).lower().strip()

    def clean_word(self, word):
        return str(word).lower().strip(".,!?;:\"'()[]{}")

    def extract_words(self, text):
        return re.findall(r"\w+|[^\w\s]", str(text), flags=re.UNICODE)

    def get_idioms_data(self, language_data):
        return language_data.get("idioms", {})

    def get_slang_data(self, language_data):
        return language_data.get("slang", {})

    def get_units_data(self, language_data):
        return language_data.get("units", {})

    def get_emojis_data(self, language_data):
        return language_data.get("emojis", {})

    def get_precision_data(self, language_data):
        data = language_data.get("precision_patterns", {})
        return data if isinstance(data, dict) else {}

    def find_idioms(self, text, language_data):
        idioms = self.get_idioms_data(language_data)
        text_lower = self.clean_text(text)
        results = {}

        for idiom, data in idioms.items():
            idiom_lower = str(idiom).lower()
            if idiom_lower and idiom_lower in text_lower:
                results[idiom] = data

        return results

    def find_slang(self, text, language_data):
        slang = self.get_slang_data(language_data)
        results = {}

        for word in self.extract_words(text):
            clean = self.clean_word(word)
            if clean in slang:
                results[clean] = slang[clean]

        return results

    def find_emojis(self, text, language_data):
        emojis = self.get_emojis_data(language_data)
        return {
            char: emojis[char]
            for char in str(text)
            if char in emojis
        }

    def find_units(self, text, language_data):
        units = self.get_units_data(language_data)
        results = []
        pattern = r"(\d+(?:\.\d+)?)\s*([A-Za-z%$]+|°[CFcf])"

        for value, unit in re.findall(pattern, str(text)):
            clean_unit = unit.lower().strip()

            if clean_unit in units:
                results.append({
                    "value": value,
                    "unit": clean_unit,
                    "data": units[clean_unit],
                })

        return results

    def find_discourse_relations(self, text, language_data):
        text_lower = self.clean_text(text)
        relation_data = self.get_precision_data(language_data).get("relation_markers", {})
        results = []

        if not isinstance(relation_data, dict):
            return results

        for relation, markers in relation_data.items():
            for marker in markers if isinstance(markers, list) else []:
                marker_text = str(marker).lower()
                if marker_text and marker_text in text_lower:
                    results.append({"relation": relation, "marker": marker})

        return results

    def find_interaction_signals(self, text, language_data):
        text_lower = self.clean_text(text)
        patterns = self.get_precision_data(language_data).get("interaction_patterns", [])
        discourse = language_data.get("discourse_patterns", {})
        if isinstance(discourse, dict):
            patterns = list(patterns) + list(discourse.get("dialogue_acts", []))
        results = []

        for item in patterns if isinstance(patterns, list) else []:
            if not isinstance(item, dict):
                continue
            matches = [
                marker for marker in item.get("markers", [])
                if str(marker).lower() in text_lower
            ]
            if matches:
                results.append({
                    "id": item.get("id"),
                    "meaning": item.get("meaning"),
                    "markers": matches,
                    "preserve_context": item.get("preserve_context"),
                    "route": item.get("route", []),
                })

        unique = {}
        for item in results:
            unique.setdefault(item.get("id") or str(item), item)
        return list(unique.values())

    def find_enumerations(self, text):
        results = []
        pattern = re.compile(
            r"(?:^|\n)\s*(?P<label>\d+[.)]|[-*])\s*(?P<text>[^\n]+)",
            flags=re.MULTILINE,
        )
        for match in pattern.finditer(str(text)):
            results.append({
                "label": match.group("label"),
                "text": match.group("text").strip(),
            })
        return results

    def build_expression_summary(self, idioms, slang, emojis, units):
        summary = []

        if idioms:
            summary.append("Idioms found")
        if slang:
            summary.append("Slang found")
        if emojis:
            summary.append("Emoji meanings found")
        if units:
            summary.append("Units found")
        if not summary:
            summary.append("No special expressions found")

        return summary

    def build_answer(self, idioms, slang, emojis, units):
        lines = []

        for idiom, data in idioms.items():
            if isinstance(data, dict):
                meaning = data.get("meaning") or data.get("en") or data.get("he")
            else:
                meaning = data
            lines.append(f"Idiom '{idiom}' means: {meaning}.")

        for word, data in slang.items():
            if isinstance(data, dict):
                meaning = data.get("meaning") or data.get("en") or data.get("he")
                tone = data.get("tone")
                extra = f" Tone: {tone}." if tone else ""
            else:
                meaning = data
                extra = ""
            lines.append(f"Slang '{word}' means: {meaning}.{extra}")

        for emoji, data in emojis.items():
            if isinstance(data, dict):
                meaning = data.get("meaning") or data.get("he")
            else:
                meaning = data
            lines.append(f"Emoji {emoji} means: {meaning}.")

        for item in units:
            data = item.get("data", {})
            name = data.get("name") if isinstance(data, dict) else item.get("unit")
            lines.append(f"{item.get('value')} {item.get('unit')} is a {name} unit.")

        return "\n".join(lines)

    def calculate_confidence(self, idioms, slang, emojis, units):
        score = 0
        score += len(idioms) * 25
        score += len(slang) * 20
        score += len(emojis) * 15
        score += len(units) * 20
        return min(score, 100)

    def process(self, text, report, language_data):
        idioms = self.find_idioms(text, language_data)
        slang = self.find_slang(text, language_data)
        emojis = self.find_emojis(text, language_data)
        units = self.find_units(text, language_data)
        discourse_relations = self.find_discourse_relations(text, language_data)
        interaction_signals = self.find_interaction_signals(text, language_data)
        enumerations = self.find_enumerations(text)
        summary = self.build_expression_summary(idioms, slang, emojis, units)
        answer = self.build_answer(idioms, slang, emojis, units)
        confidence = self.calculate_confidence(idioms, slang, emojis, units)

        return {
            "engine": "ExpressionsEngine",
            "idioms": idioms,
            "slang": slang,
            "emojis": emojis,
            "units": units,
            "discourse_relations": discourse_relations,
            "interaction_signals": interaction_signals,
            "enumerations": enumerations,
            "summary": summary,
            "answer": answer,
            "confidence": confidence,
        }


engine = ExpressionsEngine()
