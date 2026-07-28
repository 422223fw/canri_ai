"""Lazy manifest registry for complete specialist domain packages."""

from __future__ import annotations

import json
from importlib import import_module
from functools import lru_cache
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
DOMAIN_ALIASES = {
    "code": "code",
    "game": "code",
    "software": "code",
    "science": "science",
    "knowledge": "science",
    "research": "science",
    "technology": "technology",
    "hardware": "technology",
    "creative": "creativity",
    "story": "creativity",
    "movie": "creativity",
    "image_generation": "creativity",
    "emotion": "creativity",
    "math": "math",
    "reasoning": "math",
    "language": "understanding",
    "planning": "understanding",
    "general": "understanding",
    "understanding": "understanding",
}


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


def build_domain_package_context(
    domains: list[str],
    report: dict[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact packages selected from Understanding_brain domains."""

    packages = load_domain_packages()
    selected_ids: list[str] = []
    for domain in domains:
        package_id = DOMAIN_ALIASES.get(str(domain).strip().lower())
        if package_id and package_id not in selected_ids:
            selected_ids.append(package_id)
    if not selected_ids:
        selected_ids.append("understanding")

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
