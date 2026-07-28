"""Lazy manifest registry for complete specialist domain packages."""

from __future__ import annotations

import json
import re
from importlib import import_module
from functools import lru_cache
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
TOKEN_RE = re.compile(r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']+")


@lru_cache(maxsize=1)
def load_domain_packages() -> dict[str, dict[str, Any]]:
    packages: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(PACKAGE_ROOT.glob("*/manifest.json")):
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(loaded, dict):
            continue
        package_id = str(loaded.get("id") or manifest_path.parent.name).strip().lower()
        loaded["manifest_file"] = manifest_path.relative_to(PACKAGE_ROOT.parent).as_posix()
        packages[package_id] = loaded
    return packages


def _build_runtime_context(package_id, report, memory, knowledge):
    try:
        module = import_module(f".{package_id}.context", __package__)
        builder = getattr(module, "build_context", None)
        if callable(builder):
            context = builder(report or {}, memory or {}, knowledge or {})
            return context if isinstance(context, dict) else {}
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return {}


def _tokens(value: Any) -> set[str]:
    return {
        match.group(0).casefold().strip("_-' ")
        for match in TOKEN_RE.finditer(str(value or ""))
        if len(match.group(0).strip("_-' ")) > 1
    }


def _brain_domain(value: Any) -> str:
    return str(value or "").removesuffix("_brain").casefold().strip("_")


def _package_terms(package: dict[str, Any]) -> set[str]:
    semantic_fields = {
        "id": package.get("id"),
        "name": package.get("name"),
        "primary_brain": package.get("primary_brain"),
        "supporting_brains": package.get("supporting_brains", []),
        "capabilities": package.get("capabilities", []),
        "context_inputs": package.get("context_inputs", []),
        "data_sources": package.get("data_sources", []),
    }
    return _tokens(json.dumps(semantic_fields, ensure_ascii=False))


def _report_routes(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return []
    routes = [str(item) for item in report.get("routing_hints", []) if item]
    selected_domains = {
        str(item.get("domain") if isinstance(item, dict) else item).casefold()
        for item in report.get("central_domains", [])
        if str(item.get("domain") if isinstance(item, dict) else item).strip()
    }
    for detail in report.get("semantic_domain_profiles", []):
        if not isinstance(detail, dict):
            continue
        if selected_domains and str(detail.get("domain", "")).casefold() not in selected_domains:
            continue
        routes.append(str(detail.get("brain") or ""))
        routes.extend(str(item) for item in detail.get("supporting_brains", []) if item)
    return list(dict.fromkeys(route for route in routes if route.endswith("_brain")))


def _select_package_ids(
    domains: list[str],
    packages: dict[str, dict[str, Any]],
    report: dict[str, Any] | None,
) -> list[str]:
    """Resolve packages from Understanding output and manifest semantics."""

    requested = [str(domain or "").casefold().strip() for domain in domains if domain]
    requested_terms = set().union(*(_tokens(domain) for domain in requested)) if requested else set()
    routes = set(_report_routes(report))
    explicit_packages = []
    automatic_support_brains = set()
    if isinstance(report, dict):
        for detail in [
            *report.get("central_domain_details", []),
            *report.get("semantic_domain_profiles", []),
        ]:
            if not isinstance(detail, dict):
                continue
            if requested and str(detail.get("domain", "")).casefold() not in requested:
                continue
            explicit_packages.extend(str(item).casefold() for item in detail.get("packages", []) if item)
            automatic_support_brains.update(
                str(item)
                for item in detail.get("auto_supporting_brains", [])
                if str(item).endswith("_brain")
            )

    selected = [package_id for package_id in explicit_packages if package_id in packages]
    selected.extend(
        package_id
        for package_id, package in packages.items()
        if str(package.get("primary_brain") or "") in automatic_support_brains
    )
    scored = []
    supporting_matches = []
    for package_id, package in packages.items():
        routing_settings = package.get("semantic_routing", {})
        if (
            isinstance(routing_settings, dict)
            and routing_settings.get("select_as_user_domain") is False
        ):
            continue
        score = 0
        primary = str(package.get("primary_brain") or "")
        supporting = {str(item) for item in package.get("supporting_brains", []) if item}
        primary_domain = _brain_domain(primary)
        supporting_domains = {_brain_domain(item) for item in supporting}
        if package_id in requested:
            score += 100
        if primary_domain in requested:
            score += 90
        if primary in routes and primary_domain in requested:
            score += 70
        score += len(requested_terms.intersection(_package_terms(package))) * 4
        if score >= 40:
            scored.append((score, package_id))
        elif supporting_domains.intersection(requested):
            supporting_matches.append((85, package_id))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected.extend(package_id for _, package_id in scored)
    if not selected:
        supporting_matches.sort(key=lambda item: item[1])
        selected.extend(package_id for _, package_id in supporting_matches[:1])

    if not selected:
        contextual = [
            package_id
            for package_id, package in packages.items()
            if isinstance(package.get("semantic_routing"), dict)
            and package["semantic_routing"].get("select_as_user_domain") is False
        ]
        selected.extend(contextual)
    return list(dict.fromkeys(selected))


def build_domain_package_context(
    domains: list[str],
    report: dict[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact packages selected from Understanding_brain domains."""

    packages = load_domain_packages()
    selected_ids = _select_package_ids(domains, packages, report)

    selected: list[dict[str, Any]] = []
    for package_id in selected_ids[:6]:
        package = packages.get(package_id)
        if not package:
            continue
        selected.append({
            "id": package_id,
            "name": package.get("name"),
            "primary_brain": package.get("primary_brain"),
            "supporting_brains": package.get("supporting_brains", [])[:12],
            "capabilities": package.get("capabilities", [])[:16],
            "context_inputs": package.get("context_inputs", [])[:12],
            "data_sources": package.get("data_sources", [])[:16],
            "acceptance_checks": package.get("acceptance_checks", [])[:16],
            "handoff": package.get("handoff", {}),
            "manifest_file": package.get("manifest_file"),
            "runtime_context": _build_runtime_context(
                package_id,
                report,
                memory,
                knowledge,
            ),
        })

    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    return {
        "available": bool(selected),
        "selected_package_ids": [item["id"] for item in selected],
        "packages": selected,
        "selection_source": "Understanding_brain.central_domains",
        "goal": contract.get("global_picture", {}).get("goal")
        if isinstance(contract, dict) and isinstance(contract.get("global_picture"), dict)
        else None,
    }
