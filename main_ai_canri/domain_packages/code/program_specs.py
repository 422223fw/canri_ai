"""Shared data-driven program-kind recognition for generation and quality."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "Code_program_specs.json"


@lru_cache(maxsize=1)
def load_program_specs() -> dict[str, dict[str, Any]]:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    programs = value.get("programs", {}) if isinstance(value, dict) else {}
    return programs if isinstance(programs, dict) else {}


def detect_program_kind(text: str, extra_aliases: dict[str, list[str]] | None = None) -> str | None:
    lowered = str(text or "").casefold()
    candidates = []
    for kind, profile in load_program_specs().items():
        aliases = profile.get("aliases", []) if isinstance(profile, dict) else []
        aliases = [*aliases, *((extra_aliases or {}).get(kind, []))]
        matches = [str(alias).casefold() for alias in aliases if str(alias).casefold() in lowered]
        if matches:
            candidates.append((max(len(match) for match in matches), kind))
    return max(candidates, default=(0, None))[1]


def detect_existing_program_kind(code: str) -> str | None:
    lowered = str(code or "").casefold()
    candidates = []
    for kind, profile in load_program_specs().items():
        if not isinstance(profile, dict):
            continue
        signatures = [
            str(value).casefold()
            for value in profile.get("existing_signatures", [])
            if str(value).strip()
        ]
        if signatures and all(signature in lowered for signature in signatures):
            candidates.append((sum(len(value) for value in signatures), kind))
    return max(candidates, default=(0, None))[1]


__all__ = ["detect_existing_program_kind", "detect_program_kind", "load_program_specs"]
