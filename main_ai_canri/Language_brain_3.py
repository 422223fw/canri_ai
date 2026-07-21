"""
Language_brain_3.py
Canri AI

Grammar Engine.
Uses UnderstandingDk for word lookup, verb forms, sentence repair and
basic grammatical structure.
"""

import re

try:
    import UnderstandingDk as dk
except Exception as error:
    dk = None
    print("[GrammarEngine] Could not import UnderstandingDk:", error)


class GrammarEngine:

    def __init__(self):
        print("Grammar Engine Loaded")
        self.action_words = {
            "write", "create", "build", "make", "translate", "explain",
            "analyze", "analyse", "fix", "improve", "solve", "continue",
            "summarize", "summarise", "tell", "give", "show", "compare",
            "check", "generate", "plan", "design",
        }

    def clean_word(self, word):
        return str(word).lower().strip(".,!?;:\"'()[]{}")

    def extract_word_tokens(self, text):
        return [
            self.clean_word(token)
            for token in re.findall(r"\w+", str(text), flags=re.UNICODE)
            if token.strip()
        ]

    def extract_protected_spans(self, text):

        pattern = (
            r"```[\s\S]*?```|`[^`\n]+`|https?://[^\s]+|"
            r"\b[A-Za-z_][A-Za-z0-9_]*\([^()\n]*\)|"
            r"\b[\w.-]+\.(?:jsonl?|py|txt|csv|md|html?|css|js|ts|ya?ml)\b"
        )
        return list(dict.fromkeys(re.findall(pattern, str(text), flags=re.IGNORECASE)))

    def protected_word_names(self, text):

        names = set()
        for span in self.extract_protected_spans(text):
            names.update(
                word.lower()
                for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", span)
            )
        return names

    def analyze_words(self, text):
        if dk is None:
            return []

        results = []

        protected_names = self.protected_word_names(text)
        for word in self.extract_word_tokens(text):
            if word in protected_names:
                results.append({
                    "word": word,
                    "exists": True,
                    "grammar_exists": True,
                    "tense": None,
                    "forms": {},
                    "meanings": [],
                    "protected_code_term": True,
                })
                continue
            try:
                results.append({
                    "word": word,
                    "exists": dk.word_exists(word),
                    "grammar_exists": dk.grammar_exists(word),
                    "tense": dk.detect_tense(word),
                    "forms": dk.get_forms(word),
                    "meanings": dk.get_meanings(word),
                })
            except Exception:
                results.append({
                    "word": word,
                    "exists": False,
                    "grammar_exists": False,
                    "tense": None,
                    "forms": {},
                    "meanings": [],
                })

        return results

    def fix_grammar(self, text):
        if dk is None:
            return text

        protected = self.extract_protected_spans(text)
        prepared = str(text)
        placeholders = {}
        for index, span in enumerate(protected):
            placeholder = f"CANRIPROTECTED{index}"
            placeholders[placeholder] = span
            prepared = prepared.replace(span, placeholder)

        try:
            fixed = dk.fix_sentence(prepared)
        except Exception:
            return text

        for placeholder, span in placeholders.items():
            fixed = re.sub(
                re.escape(placeholder),
                lambda _: span,
                fixed,
                flags=re.IGNORECASE,
            )
        return fixed

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

        tenses = {}

        for word in self.extract_word_tokens(text):
            try:
                tense = dk.detect_tense(word)
            except Exception:
                tense = None

            if tense:
                tenses[word] = tense

        return tenses

    def get_base_forms(self, text):
        if dk is None:
            return {}

        bases = {}

        for word in self.extract_word_tokens(text):
            try:
                base = dk.get_verb_base(word)
            except Exception:
                base = None

            if base:
                bases[word] = base

        return bases

    def report_word_tags(self, report):
        if not isinstance(report, dict):
            return []

        tags = report.get("advanced_word_tags")
        if isinstance(tags, list):
            return tags

        nested = report.get("understanding")
        if isinstance(nested, dict):
            tags = nested.get("advanced_word_tags")
            if isinstance(tags, list):
                return tags

        return []

    def build_word_type_groups(self, word_analysis, report):
        groups = {
            "verbs": [],
            "nouns_or_terms": [],
            "unknown": [],
        }

        for tag in self.report_word_tags(report):
            if not isinstance(tag, dict):
                continue

            word = tag.get("word")
            role = tag.get("role") or tag.get("type")

            if not word:
                continue

            if role in ["action", "verb"]:
                groups["verbs"].append(word)
            elif role in ["target", "technical_name", "noun", "concept"]:
                groups["nouns_or_terms"].append(word)

        for item in word_analysis:
            word = item.get("word")
            if not word:
                continue

            if word in self.action_words:
                if word not in groups["verbs"]:
                    groups["verbs"].append(word)
            elif item.get("exists"):
                if word not in groups["nouns_or_terms"]:
                    groups["nouns_or_terms"].append(word)
            else:
                groups["unknown"].append(word)

        for key, value in groups.items():
            groups[key] = list(dict.fromkeys(value))

        return groups

    def find_grammar_issues(self, word_analysis):
        issues = []

        for item in word_analysis:
            if item.get("protected_code_term"):
                continue
            if not item.get("exists"):
                issues.append({
                    "word": item.get("word"),
                    "issue": "word_not_found",
                })

        return issues[:30]

    def process(self, text, report=None):
        if report is None:
            report = {}

        fixed_text = self.fix_grammar(text)
        word_analysis = self.analyze_words(text)
        sentence_analysis = self.analyze_sentence(text)
        tenses = self.detect_tenses(text)
        base_forms = self.get_base_forms(text)
        word_type_groups = self.build_word_type_groups(word_analysis, report)
        grammar_issues = self.find_grammar_issues(word_analysis)
        protected_spans = self.extract_protected_spans(text)

        known_words = sum(1 for item in word_analysis if item.get("exists"))
        total_words = len(word_analysis)
        confidence = round((known_words / total_words) * 100, 2) if total_words else 0

        return {
            "engine": "GrammarEngine",
            "input_text": text,
            "fixed_text": fixed_text,
            "corrected_text": fixed_text,
            "word_analysis": word_analysis,
            "word_type_groups": word_type_groups,
            "grammar_issues": grammar_issues,
            "protected_spans": protected_spans,
            "protected_code_spans": protected_spans,
            "sentence_analysis": sentence_analysis,
            "tenses": tenses,
            "base_forms": base_forms,
            "known_words": known_words,
            "total_words": total_words,
            "confidence": confidence,
        }


engine = GrammarEngine()
