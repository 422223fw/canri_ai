"""Shared semantic capability detection for code generation and review."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import UnderstandingDk as understanding_dictionary
except Exception:
    understanding_dictionary = None


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ONTOLOGY_FILE = DATA_DIR / "Code_capability_ontology.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


@lru_cache(maxsize=4096)
def dictionary_semantic_terms(token: str) -> tuple[str, ...]:
    """Expand a technical token through Canri's central dictionary graph."""

    normalized = str(token or "").strip().casefold()
    if not normalized or understanding_dictionary is None:
        return ()
    values: list[Any] = []
    try:
        values.extend(understanding_dictionary.related(normalized)[:20])
        for entry in understanding_dictionary.search_word(normalized)[:3]:
            if not isinstance(entry, dict):
                continue
            values.append(entry.get("type"))
            for meaning in entry.get("meanings", [])[:3]:
                values.append(
                    meaning.get("definition")
                    if isinstance(meaning, dict)
                    else meaning
                )
    except (AttributeError, TypeError, ValueError):
        return ()
    return tuple(str(value) for value in values if str(value or "").strip())


class CodeCapabilityDetector:
    """Infer code capabilities from Understanding output and data profiles."""

    def __init__(self, project_profiles: dict[str, Any] | None = None):
        ontology = _load_json(ONTOLOGY_FILE, {})
        self.capabilities = ontology.get("capabilities", {})
        self.classification = ontology.get("classification", {})
        self.project_profiles = project_profiles if isinstance(project_profiles, dict) else {}

    @staticmethod
    def semantic_stem(value: Any) -> str:
        token = re.sub(r"[^a-z0-9]", "", str(value or "").casefold())
        for suffix in (
            "ization", "isation", "ational", "fulness", "iveness",
            "ation", "ition", "ments", "ment", "ingly", "edly",
            "ing", "ers", "ies", "ed", "es", "s",
        ):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[:-len(suffix)]
                break
        return token

    def known_capabilities(self) -> list[str]:
        names = set(self.capabilities)
        profiles = self.project_profiles.get("profiles", {})
        if isinstance(profiles, dict):
            for profile in profiles.values():
                if isinstance(profile, dict):
                    names.update(
                        str(item).casefold()
                        for item in profile.get("required_capabilities", [])
                        if item
                    )
        return sorted(names)

    @staticmethod
    def _report_values(report: dict[str, Any]) -> list[Any]:
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        values: list[Any] = [
            report.get("key_terms", []),
            report.get("semantic_frame", {}),
            contract.get("global_picture", {}),
            contract.get("detail_inventory", {}),
            report.get("code_context", {}),
        ]
        values.extend(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in contract.get("requirements", [])
        )
        for tag in report.get("advanced_word_tags", []):
            if isinstance(tag, dict):
                values.extend([
                    tag.get("word", ""),
                    tag.get("definition_hint", ""),
                    *tag.get("connection_hints", []),
                ])
        return values

    def request_semantics(
        self,
        text: str,
        report: dict[str, Any] | None,
    ) -> tuple[str, set[str], set[str]]:
        # Capability activation is grounded in the actual request. Dictionary
        # connections may strengthen an explicit term, but cannot create a new
        # architecture requirement on their own.
        serialized = str(text or "").casefold()
        raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", serialized)
        dictionary_values: list[str] = []
        for token in list(dict.fromkeys(raw_tokens))[:120]:
            dictionary_values.extend(dictionary_semantic_terms(token))
        dictionary_tokens = re.findall(
            r"[A-Za-z][A-Za-z0-9_-]*",
            " ".join(dictionary_values).casefold(),
        )
        direct_stems = {
            self.semantic_stem(token)
            for token in raw_tokens
            if self.semantic_stem(token)
        }
        expanded_stems = {
            self.semantic_stem(token)
            for token in dictionary_tokens
            if self.semantic_stem(token)
        }
        return serialized, direct_stems, expanded_stems

    @staticmethod
    def requested_file_count(report: dict[str, Any] | None) -> int:
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        counts = []
        details = contract.get("detail_inventory", {})
        if isinstance(details, dict):
            for constraint in details.get("quantified_constraints", []):
                if not isinstance(constraint, dict):
                    continue
                if "file" in str(constraint.get("target", "")):
                    quantity = constraint.get("quantity")
                    if isinstance(quantity, int):
                        counts.append(quantity)
        return max(counts, default=0)

    def _profile_terms(self, name: str) -> tuple[list[str], set[str], int]:
        profile = self.capabilities.get(name, {})
        profile = profile if isinstance(profile, dict) else {}
        phrases = [
            name.replace("_", " "),
            *[str(value) for value in profile.get("signals", [])],
        ]
        stems = {
            self.semantic_stem(token)
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", " ".join(phrases))
            if self.semantic_stem(token)
        }
        minimum = int(profile.get("minimum_term_matches", 2) or 2)
        return phrases, stems, max(1, minimum)

    def detect(
        self,
        text: str,
        report: dict[str, Any] | None = None,
        existing_files: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        semantic_text, direct_stems, expanded_stems = self.request_semantics(text, report)
        detected: dict[str, Any] = {}
        evidence: dict[str, list[str]] = {}

        for name in self.known_capabilities():
            phrases, profile_stems, minimum = self._profile_terms(name)
            direct = [
                phrase.casefold()
                for phrase in phrases
                if len(phrase.split()) <= 5 and phrase.casefold() in semantic_text
            ]
            direct_matches = sorted(profile_stems.intersection(direct_stems))
            expanded_matches = sorted(profile_stems.intersection(expanded_stems))
            detected[name] = bool(
                direct
                or len(direct_matches) >= minimum
            )
            if detected[name]:
                evidence[name] = (direct[:3] or direct_matches[:8])

        file_count = self.requested_file_count(report)
        if file_count > 1:
            detected["multi_file"] = True
            evidence["multi_file"] = [f"requested_file_count:{file_count}"]
        if existing_files:
            detected["existing_project"] = True
            evidence["existing_project"] = ["existing_project_files"]

        changed = True
        while changed:
            changed = False
            for name, profile in self.capabilities.items():
                if not detected.get(name) or not isinstance(profile, dict):
                    continue
                for implied in profile.get("implies", []):
                    if not detected.get(implied):
                        detected[implied] = True
                        evidence.setdefault(implied, []).append(f"implied_by:{name}")
                        changed = True

        advanced_members = self.classification.get("advanced_members", [])
        advanced_count = sum(bool(detected.get(name)) for name in advanced_members)
        advanced_minimum = int(self.classification.get("advanced_minimum", 2) or 2)
        multi_file_minimum = int(self.classification.get("multi_file_minimum", 3) or 3)
        if advanced_count >= multi_file_minimum:
            detected["multi_file"] = True
        if detected.get("multi_file"):
            detected["layered_architecture"] = True

        professional_stems = {
            self.semantic_stem(value)
            for value in self.classification.get("professional_signals", [])
        }
        explicitly_professional = bool(professional_stems.intersection(direct_stems))
        advanced_single = any(
            detected.get(name)
            for name in self.classification.get("advanced_single_capabilities", [])
        )
        detected["professional"] = bool(
            explicitly_professional
            or (detected.get("multi_file") and advanced_count >= advanced_minimum)
        )
        detected["advanced_project"] = bool(
            advanced_count >= advanced_minimum
            or advanced_single
            or (detected.get("existing_project") and explicitly_professional)
        )
        detected["semantic_evidence"] = evidence
        return detected


__all__ = ["CodeCapabilityDetector", "dictionary_semantic_terms"]
