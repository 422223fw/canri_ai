"""Data-driven semantic routing for Canri.

The router discovers specialist vocabulary from the brains, their declared
data files, and domain-package manifests.  It deliberately does not maintain
another hand-written keyword-to-domain table: Understanding_brain supplies the
request analysis and this module compares it with the capabilities that are
actually present in the project.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import UnderstandingDk as dictionary
except Exception:
    dictionary = None


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PACKAGE_DIR = ROOT / "domain_packages"
TOKEN_RE = re.compile(
    r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']+"
)
DATA_REFERENCE_RE = re.compile(r"[\"']([^\"']+\.(?:json|jsonl))[\"']", re.I)
BRAIN_REFERENCE_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*_brain\b")
SEMANTIC_FIELD_RE = re.compile(
    r'"(?:id|name|title|label|type|category|field|domain|topic|language|function|class|tags|keywords|capabilities|capital)"\s*:\s*'
    r'(?P<value>"(?:\\.|[^"\\])*"|\[[^\]]{0,1200}\])',
    re.I,
)
MAX_SOURCE_CHARS = 96_000
MAX_DATA_SAMPLE_CHARS = 180_000
MAX_STRUCTURED_JSON_BYTES = 2_200_000


def _word_type_is(value: Any, label: str) -> bool:
    return bool(re.search(
        rf"(?<![A-Za-z]){re.escape(label.casefold())}(?![A-Za-z])",
        str(value or "").casefold(),
    ))


def _is_capability_data(path: Path) -> bool:
    """Exclude volatile logs from routing while leaving them available to brains."""

    normalized = path.stem.casefold()
    return not any(
        marker in normalized
        for marker in ("statistics", "history", "memory", "queue", "performance", "audit")
    )


def _structured_data_terms(path: Path) -> set[str]:
    """Read only semantic identity fields, not arbitrary prose from a data file."""

    try:
        if path.suffix.casefold() == ".json" and path.stat().st_size <= MAX_STRUCTURED_JSON_BYTES:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            values = []

            def visit(value, depth=0):
                if depth > 7 or len(values) >= 30_000:
                    return
                if isinstance(value, dict):
                    for key, item in value.items():
                        values.append(str(key))
                        visit(item, depth + 1)
                elif isinstance(value, list):
                    for item in value[:5000]:
                        visit(item, depth + 1)
                elif isinstance(value, str) and len(value) <= 180:
                    values.append(value)

            visit(loaded)
            return set(semantic_tokens(" ".join(values)))
    except (OSError, json.JSONDecodeError, UnicodeError):
        pass

    sample = _read_sample(path, MAX_DATA_SAMPLE_CHARS)
    values = [match.group("value") for match in SEMANTIC_FIELD_RE.finditer(sample)]
    return set(semantic_tokens(" ".join(values)))


def semantic_tokens(value: Any) -> list[str]:
    return list(dict.fromkeys(
        match.group(0).casefold().strip("_-' ")
        for match in TOKEN_RE.finditer(str(value or ""))
        if len(match.group(0).strip("_-' ")) > 1
    ))


def _read_sample(path: Path, limit: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _load_manifests() -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(PACKAGE_DIR.glob("*/manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            value = dict(value)
            value["_path"] = path.as_posix()
            manifests.append(value)
    return manifests


def _declared_data_paths(source: str) -> list[Path]:
    paths = []
    for reference in DATA_REFERENCE_RE.findall(source):
        candidate = Path(reference).name
        path = DATA_DIR / candidate
        if path.exists() and path.is_file() and path not in paths:
            paths.append(path)
    return paths


@lru_cache(maxsize=1)
def load_semantic_profiles() -> dict[str, dict[str, Any]]:
    """Build bounded specialist profiles from the current project files."""

    profiles: dict[str, dict[str, Any]] = {}
    for source_path in sorted(ROOT.glob("*_brain.py")):
        domain = source_path.stem[:-6].casefold().strip("_")
        if not domain:
            continue
        source = _read_sample(source_path, MAX_SOURCE_CHARS)
        identity_terms = set(semantic_tokens(source_path.stem.replace("_", " ")))
        source_terms = set(semantic_tokens(source))
        data_terms = set()
        manifest_terms = set()
        vocabulary = Counter(identity_terms)
        vocabulary.update(source_terms)
        data_sources = []
        for data_path in _declared_data_paths(source):
            data_sources.append(data_path.name)
            data_terms.update(semantic_tokens(data_path.stem.replace("_", " ")))
            if _is_capability_data(data_path):
                data_terms.update(_structured_data_terms(data_path))
        vocabulary.update(data_terms)
        profiles[domain] = {
            "domain": domain,
            "brain": source_path.stem,
            "vocabulary": vocabulary,
            "data_sources": data_sources,
            "packages": [],
            "supporting_brains": list(dict.fromkeys(
                name
                for name in BRAIN_REFERENCE_RE.findall(source)
                if name != source_path.stem
            )),
            "auto_supporting_brains": [],
            "identity_terms": identity_terms,
            "source_terms": source_terms,
            "data_terms": data_terms,
            "manifest_terms": manifest_terms,
            "selectable": any(
                Path(name).stem.casefold().startswith(domain)
                for name in data_sources
            ),
        }

    for manifest in _load_manifests():
        package_id = str(manifest.get("id") or "").casefold().strip()
        primary = str(manifest.get("primary_brain") or "").strip()
        primary_domain = primary.removesuffix("_brain").casefold().strip("_")
        target = profiles.get(primary_domain)
        if target is None and package_id:
            target = profiles.get(package_id)
        if target is None:
            continue
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        target["manifest_terms"].update(semantic_tokens(manifest_text))
        target["vocabulary"].update(target["manifest_terms"])
        for source_name in manifest.get("data_sources", []):
            source_path = DATA_DIR / Path(str(source_name)).name
            if not source_path.exists() or not _is_capability_data(source_path):
                continue
            target["data_terms"].update(_structured_data_terms(source_path))
        target["vocabulary"].update(target["data_terms"])
        target["packages"].append(package_id)
        routing_settings = manifest.get("semantic_routing", {})
        routing_settings = routing_settings if isinstance(routing_settings, dict) else {}
        target["selectable"] = bool(
            routing_settings.get("select_as_user_domain", True)
        )
        target["auto_supporting_brains"].extend(
            str(item)
            for item in routing_settings.get("auto_supporting_brains", [])
            if str(item).endswith("_brain")
        )
        target["auto_supporting_brains"] = list(dict.fromkeys(
            target["auto_supporting_brains"]
        ))
        target["supporting_brains"].extend(
            str(item) for item in manifest.get("supporting_brains", []) if item
        )
        target["supporting_brains"] = list(dict.fromkeys(target["supporting_brains"]))

    return profiles


@lru_cache(maxsize=4096)
def _definition_expansion(term: str) -> tuple[str, ...]:
    """Follow one dictionary-definition edge for semantic classification."""

    if dictionary is None or len(term) < 3:
        return ()
    try:
        if not dictionary.word_exists(term):
            return ()
        meanings = dictionary.get_meanings(term)[:2]
    except Exception:
        return ()
    return tuple(semantic_tokens(" ".join(str(item) for item in meanings))[:32])


def _dictionary_context(
    word_reports: list[dict[str, Any]],
    focus_terms: set[str] | None = None,
) -> list[str]:
    values = []
    meaning_values = []
    reports = [report for report in word_reports if isinstance(report, dict)]
    normalized_focus = {str(term).casefold() for term in (focus_terms or set()) if term}
    if normalized_focus:
        focused_reports = [
            report for report in reports
            if {
                str(report.get("word") or "").casefold(),
                str(report.get("resolved_word") or "").casefold(),
            }.intersection(normalized_focus)
        ]
        if focused_reports:
            reports = focused_reports
    for report in reports:
        if not isinstance(report, dict):
            continue
        report_meanings = report.get("meanings", [])[:3]
        values.extend(report_meanings)
        meaning_values.extend(report_meanings)
        values.extend(report.get("connections", [])[:10])
    meaning_terms = semantic_tokens(" ".join(str(value) for value in meaning_values))
    expanded = []
    for term in meaning_terms[:40]:
        expanded.extend(_definition_expansion(term))
    return list(dict.fromkeys([
        *semantic_tokens(" ".join(str(value) for value in values)),
        *expanded,
    ]))[:220]


def _scanner_context(scanner_matches: list[dict[str, Any]]) -> list[str]:
    values = []
    for item in scanner_matches[:5]:
        if not isinstance(item, dict):
            continue
        relevance = item.get("retrieval_relevance", {})
        if isinstance(relevance, dict) and relevance.get("coverage", 0) <= 0:
            continue
        values.extend([
            item.get("title", ""),
            item.get("summary", ""),
            item.get("content_excerpt", ""),
        ])
    return semantic_tokens(" ".join(str(value) for value in values))[:240]


def rank_semantic_domains(
    text: str,
    word_reports: list[dict[str, Any]] | None = None,
    scanner_matches: list[dict[str, Any]] | None = None,
    code_context: dict[str, Any] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    profiles = load_semantic_profiles()
    stop_terms = {
        str(report.get("word") or "").casefold()
        for report in (word_reports or [])
        if isinstance(report, dict) and report.get("is_stop_word")
    }
    direct_terms = [term for term in semantic_tokens(text) if term not in stop_terms]
    direct_terms.extend(
        str(report.get("resolved_word") or "").casefold()
        for report in (word_reports or [])
        if isinstance(report, dict)
        and report.get("resolved_word")
        and str(report.get("resolved_word")).casefold() not in stop_terms
    )
    direct_terms = list(dict.fromkeys(term for term in direct_terms if term))
    explicit_direct_terms = set(direct_terms)
    inferred_identity_terms = set()
    direct_importance = {}
    ordered_word_reports = [
        report for report in (word_reports or []) if isinstance(report, dict)
    ]
    for report in ordered_word_reports:
        if not isinstance(report, dict):
            continue
        word = str(report.get("word") or "").casefold()
        resolved_word = str(report.get("resolved_word") or word).casefold()
        word_type = str(report.get("type") or "").casefold()
        if not word:
            continue
        if _word_type_is(word_type, "verb"):
            direct_importance[word] = 0.55
        elif _word_type_is(word_type, "noun"):
            direct_importance[word] = 1.25
        elif _word_type_is(word_type, "adjective"):
            direct_importance[word] = 1.0
        else:
            direct_importance[word] = 0.9
        if resolved_word:
            direct_importance[resolved_word] = direct_importance[word]

    identity_terms = set().union(*(
        set(profile.get("identity_terms", set()))
        for profile in profiles.values()
    )) if profiles else set()
    for report in ordered_word_reports:
        word_type = str(report.get("type") or "").casefold()
        if report.get("is_stop_word") or _word_type_is(word_type, "verb"):
            continue
        definition_terms = semantic_tokens(" ".join(
            str(item) for item in report.get("meanings", [])[:3]
        ))
        for identity_term in identity_terms.intersection(definition_terms):
            if identity_term not in direct_terms:
                direct_terms.append(identity_term)
            inferred_identity_terms.add(identity_term)
            direct_importance[identity_term] = max(
                direct_importance.get(identity_term, 1.0),
                3.0,
            )

    # In an action request, the first content word following the request verb
    # is usually the requested target. Give that relation more weight than
    # later audience/style words without maintaining a domain keyword table.
    action_index = next(
        (
            index
            for index, report in enumerate(ordered_word_reports)
            if _word_type_is(report.get("type"), "verb")
            and not report.get("is_stop_word")
        ),
        None,
    )
    if action_index is not None:
        for report in ordered_word_reports[action_index + 1:]:
            if report.get("is_stop_word"):
                continue
            word = str(report.get("word") or "").casefold().strip()
            word_type = str(report.get("type") or "").casefold()
            if word and (
                _word_type_is(word_type, "noun")
                or not word_type
                or word_type == "unknown"
            ):
                direct_importance[word] = max(direct_importance.get(word, 0.9), 4.0)
                resolved_word = str(report.get("resolved_word") or word).casefold()
                direct_importance[resolved_word] = max(
                    direct_importance.get(resolved_word, 0.9),
                    4.0,
                )
                break
    focus_terms = {
        term for term, importance in direct_importance.items()
        if importance >= 4.0
    }
    dictionary_terms = _dictionary_context(word_reports or [], focus_terms=focus_terms)
    scanner_terms = _scanner_context(scanner_matches or [])
    scored = []
    selectable_profiles = [
        profile for profile in profiles.values() if profile.get("selectable")
    ]
    profile_count = max(len(selectable_profiles), 1)
    all_terms = list(dict.fromkeys(direct_terms + dictionary_terms + scanner_terms))
    document_frequency = {
        term: sum(1 for profile in selectable_profiles if term in profile["vocabulary"])
        for term in all_terms
    }

    def term_weight(profile, term, source):
        if (
            source in {"dictionary", "scanner"}
            and document_frequency.get(term, 0) > max(2, profile_count * 0.3)
        ):
            return 0.0
        if term in profile["identity_terms"]:
            base = {"direct": 20.0, "dictionary": 5.0, "scanner": 2.0}[source]
        elif term in profile["manifest_terms"]:
            base = {"direct": 8.0, "dictionary": 2.5, "scanner": 1.0}[source]
        elif term in profile["data_terms"]:
            base = {"direct": 5.0, "dictionary": 1.5, "scanner": 0.5}[source]
            base *= min(1.0, math.sqrt(1800.0 / max(len(profile["data_terms"]), 1)))
        elif term in profile["source_terms"]:
            # Source code contains generic orchestration words shared by many
            # brains. It is supporting evidence only; identity, manifests,
            # declared data, and the user's direct target must dominate.
            base = {"direct": 0.03, "dictionary": 0.005, "scanner": 0.0}[source]
            base *= min(1.0, math.sqrt(700.0 / max(len(profile["source_terms"]), 1)))
        else:
            return 0.0
        rarity = math.log(
            (profile_count + 1) / (document_frequency.get(term, 0) + 1)
        ) + 1.0
        return base * rarity

    for domain, profile in profiles.items():
        if not profile.get("selectable"):
            continue
        vocabulary: Counter = profile["vocabulary"]
        direct_matches = [term for term in direct_terms if term in vocabulary]
        explicit_matches = [
            term for term in direct_matches if term in explicit_direct_terms
        ]
        inferred_matches = [
            term for term in direct_matches if term in inferred_identity_terms
        ]
        dictionary_matches = [term for term in dictionary_terms if term in vocabulary]
        scanner_matches_for_domain = [term for term in scanner_terms if term in vocabulary]
        dictionary_identity_matches = [
            term for term in dictionary_terms
            if term in profile["identity_terms"]
        ]
        score = 0.0
        if domain in direct_terms:
            score += 50.0
        score += min(sum(
            22.0 * (
                math.log(
                    (profile_count + 1) / (document_frequency.get(term, 0) + 1)
                ) + 1.0
            )
            for term in set(dictionary_identity_matches)
        ), 55.0)
        score += min(sum(
            term_weight(profile, term, "direct") * direct_importance.get(term, 1.0)
            for term in set(direct_matches)
        ), 70.0)
        score += min(sum(
            term_weight(profile, term, "dictionary") for term in set(dictionary_matches)
        ), 35.0)
        score += min(sum(
            term_weight(profile, term, "scanner") for term in set(scanner_matches_for_domain)
        ), 4.0)
        if code_context and code_context.get("has_code") and profile.get("brain") == "Code_brain":
            score += 55.0
        if score <= 0:
            continue
        scored.append({
            "domain": domain,
            "brain": profile.get("brain"),
            "score": round(score, 2),
            "direct_evidence": list(dict.fromkeys(direct_matches))[:12],
            "explicit_evidence": list(dict.fromkeys(explicit_matches))[:12],
            "inferred_evidence": list(dict.fromkeys(inferred_matches))[:12],
            "dictionary_evidence": list(dict.fromkeys(dictionary_matches))[:12],
            "scanner_evidence": list(dict.fromkeys(scanner_matches_for_domain))[:12],
            "supporting_brains": profile.get("supporting_brains", [])[:12],
            "auto_supporting_brains": profile.get("auto_supporting_brains", [])[:8],
            "data_sources": profile.get("data_sources", [])[:12],
            "packages": profile.get("packages", [])[:8],
            "source": "discovered_brain_and_data_profile",
        })

    scored.sort(
        key=lambda item: (
            item["score"],
            len(item["direct_evidence"]),
            len(item["dictionary_evidence"]),
        ),
        reverse=True,
    )
    return scored[:max(1, int(limit))]


def routes_for_domains(domain_details: list[dict[str, Any]]) -> list[str]:
    """Route selected domains to their owners, not every referenced helper.

    A source-file import or a package dependency describes availability, not a
    reason to execute that brain for every request. Manager_brain adds shared
    verification and collaboration only when the request contract requires it.
    """

    routes = []
    for item in domain_details:
        if not isinstance(item, dict):
            continue
        brain_name = str(item.get("brain") or "").strip()
        if brain_name.endswith("_brain"):
            routes.append(brain_name)
        routes.extend(
            str(brain)
            for brain in item.get("auto_supporting_brains", [])
            if str(brain).endswith("_brain")
        )
    return list(dict.fromkeys(routes))


def clear_semantic_profile_cache() -> None:
    load_semantic_profiles.cache_clear()


__all__ = [
    "clear_semantic_profile_cache",
    "load_semantic_profiles",
    "rank_semantic_domains",
    "routes_for_domains",
    "semantic_tokens",
]
