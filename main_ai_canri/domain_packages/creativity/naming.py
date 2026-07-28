"""Context-derived names for stories, projects, modules, and classes."""

from __future__ import annotations

import hashlib
import re
from typing import Any

try:
    import UnderstandingDk as dictionary
except Exception:
    dictionary = None


WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
VOWELS = set("aeiouy")


class ContextualNamingEngine:
    """Build names from request concepts instead of a fixed name bank."""

    @staticmethod
    def _terms(text: str, report: dict[str, Any] | None = None) -> list[str]:
        report = report if isinstance(report, dict) else {}
        concept_candidates = []
        description_candidates = []
        excluded = set()
        for tag in report.get("advanced_word_tags", []):
            if not isinstance(tag, dict):
                continue
            semantic_tag = str(tag.get("semantic_tag") or "")
            word = tag.get("word")
            if semantic_tag in {
                "action", "action_command", "connector", "determiner",
                "function_word", "relation_word", "question_focus",
            }:
                excluded.add(str(word or "").casefold())
                continue
            if semantic_tag in {
                "target_or_concept", "proper_or_technical_name"
            }:
                concept_candidates.append(word)
            elif semantic_tag == "description":
                description_candidates.append(word)
        candidates = [*concept_candidates, *description_candidates]
        if len(candidates) < 3:
            candidates.extend(
                term for term in report.get("key_terms", [])
                if str(term).casefold() not in excluded
            )
        if not candidates:
            for token in WORD_RE.findall(str(text or "")):
                entries = dictionary.search_word(token) if dictionary is not None else []
                word_types = {
                    str(entry.get("type") or "").casefold()
                    for entry in entries
                    if isinstance(entry, dict)
                }
                if word_types and not any(
                    kind in word_type
                    for word_type in word_types
                    for kind in ("noun", "adjective", "proper")
                ):
                    continue
                if not word_types and len(token) < 6:
                    continue
                candidates.append(token)
        clean = []
        for value in candidates:
            token = re.sub(r"[^a-z]", "", str(value or "").casefold())
            if len(token) < 3 or token in clean:
                continue
            clean.append(token)
        return clean[:60]

    @staticmethod
    def _first_vowel(word: str) -> tuple[str, str]:
        for index, letter in enumerate(word):
            if letter in VOWELS:
                following = next(
                    (item for item in word[index + 1:] if item not in VOWELS),
                    "",
                )
                return letter, following
        return "a", word[-1:] if word else "n"

    @staticmethod
    def _onset(word: str) -> str:
        consonants = ""
        for letter in word:
            if letter in VOWELS:
                break
            consonants += letter
            if len(consonants) == 2:
                break
        allowed_clusters = {
            "bl", "br", "ch", "cl", "cr", "dr", "fl", "fr", "gl",
            "gr", "pl", "pr", "qu", "sh", "sl", "st", "th", "tr",
        }
        if consonants in allowed_clusters:
            return consonants
        return consonants[:1] or word[:1] or "n"

    @staticmethod
    def _ending(word: str) -> str:
        letters = [letter for letter in word[-4:] if letter not in VOWELS]
        return "".join(letters[-1:]) or word[-1:] or "n"

    @staticmethod
    def _score_name(name: str, source_terms: list[str]) -> float:
        lowered = name.casefold()
        score = 50.0
        if 4 <= len(name) <= 8:
            score += 20
        if any(letter in VOWELS for letter in lowered):
            score += 12
        if not re.search(r"[^aeiouy]{3,}", lowered):
            score += 10
        transitions = sum(
            (left in VOWELS) != (right in VOWELS)
            for left, right in zip(lowered, lowered[1:])
        )
        score += min(transitions * 2, 12)
        if lowered[-1:] in VOWELS or lowered[-1:] in {"n", "r", "s", "l", "m"}:
            score += 8
        if lowered not in source_terms:
            score += 8
        score += min(len(set(lowered)), 8)
        return score

    def character_candidates(
        self,
        text: str,
        report: dict[str, Any] | None = None,
        count: int = 24,
    ) -> list[dict[str, Any]]:
        terms = self._terms(text, report)
        if not terms:
            digest_letters = "".join(
                chr(97 + byte % 26)
                for byte in hashlib.sha256(str(text).encode("utf-8")).digest()[:12]
            )
            terms = [digest_letters]
        digest = hashlib.sha256("|".join(terms).encode("utf-8")).digest()
        candidates = []
        seen = set()
        for index in range(max(96, int(count) * 16)):
            first = terms[(digest[index % len(digest)] + index) % len(terms)]
            second = terms[(digest[(index + 7) % len(digest)] + index * 3) % len(terms)]
            third = terms[(digest[(index + 13) % len(digest)] + index * 5) % len(terms)]
            first_vowel, _ = self._first_vowel(first)
            second_vowel, _ = self._first_vowel(second)
            third_vowel, _ = self._first_vowel(third)
            patterns = (
                self._onset(first) + second_vowel + self._ending(second) + third_vowel,
                self._onset(first) + first_vowel + self._onset(second) + third_vowel,
                self._onset(first) + second_vowel + self._onset(third) + first_vowel,
                self._onset(second) + third_vowel + self._ending(first) + second_vowel,
            )
            raw = patterns[index % len(patterns)]
            raw = re.sub(r"(.)\1+", r"\1", raw).strip()
            if len(raw) < 4:
                raw += self._first_vowel(third)[0] + self._ending(second)
            name = raw[:9].capitalize()
            if not name.isalpha() or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            candidates.append({
                "name": name,
                "score": round(self._score_name(name, terms), 2),
                "source_concepts": [first, second, third],
            })
        candidates.sort(key=lambda item: (item["score"], item["name"]), reverse=True)
        return candidates[:max(1, int(count))]

    def choose_character_name(
        self,
        text: str,
        report: dict[str, Any] | None = None,
    ) -> str:
        candidates = self.character_candidates(text, report, count=24)
        if candidates:
            return candidates[0]["name"]
        digest = hashlib.sha256(str(text).encode("utf-8")).digest()
        return "".join(chr(97 + byte % 26) for byte in digest[:5]).capitalize()

    def project_names(
        self,
        text: str,
        report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        terms = self._terms(text, report)
        selected = terms[:3] or ["canri", "project"]
        descriptive_slug = "_".join(selected[:3])[:64].strip("_") or "canri_project"
        brand_candidates = self.character_candidates(text, report, count=12)
        brand = (
            brand_candidates[0]["name"]
            if brand_candidates
            else "Canri"
        )
        core_concept = selected[0].capitalize()
        slug = f"{brand.casefold()}_{selected[0]}"[:64].strip("_")
        class_name = f"{brand}{core_concept}"[:64]
        modules = [
            f"{term}.py"
            for term in selected[:6]
            if term.isidentifier()
        ]
        return {
            "project_slug": slug,
            "descriptive_slug": descriptive_slug,
            "display_name": f"{brand} {core_concept}",
            "brand_name": brand,
            "brand_candidates": brand_candidates,
            "class_name": class_name or "CanriProject",
            "module_candidates": list(dict.fromkeys(modules)),
            "source_concepts": selected,
            "generation": "evolved_request_concept_composition",
        }


__all__ = ["ContextualNamingEngine"]
