"""Local configuration for Canri's project agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent / "data"
SETTINGS_FILE = DATA_DIR / "Agent_settings.local.json"
PROFILE_FILE = DATA_DIR / "Agent_profiles.json"

AGENT_MODES = ("off", "autonomous", "restricted", "approval")

DEFAULT_SETTINGS: dict[str, Any] = {
    "mode": "off",
    "workspace_path": "",
    "allow_file_writes": True,
    "allow_terminal": True,
    "command_timeout_seconds": 120,
    "max_files_per_scan": 600,
    "max_selected_files": 12,
    "max_single_file_bytes": 262144,
    "max_total_context_bytes": 2097152,
}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def normalize_agent_settings(settings: Any) -> dict[str, Any]:
    clean = dict(DEFAULT_SETTINGS)
    if isinstance(settings, dict):
        clean.update({key: settings[key] for key in DEFAULT_SETTINGS if key in settings})

    mode = str(clean.get("mode", "off")).strip().lower()
    clean["mode"] = mode if mode in AGENT_MODES else "off"
    clean["workspace_path"] = str(clean.get("workspace_path", "")).strip()
    clean["allow_file_writes"] = bool(clean.get("allow_file_writes", True))
    clean["allow_terminal"] = bool(clean.get("allow_terminal", True))
    clean["command_timeout_seconds"] = _bounded_int(
        clean.get("command_timeout_seconds"), 120, 5, 900
    )
    clean["max_files_per_scan"] = _bounded_int(
        clean.get("max_files_per_scan"), 600, 20, 5000
    )
    clean["max_selected_files"] = _bounded_int(
        clean.get("max_selected_files"), 12, 1, 40
    )
    clean["max_single_file_bytes"] = _bounded_int(
        clean.get("max_single_file_bytes"), 262144, 4096, 2097152
    )
    clean["max_total_context_bytes"] = _bounded_int(
        clean.get("max_total_context_bytes"), 2097152, 32768, 16777216
    )
    return clean


def load_agent_settings() -> dict[str, Any]:
    try:
        loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    return normalize_agent_settings(loaded)


def save_agent_settings(settings: dict[str, Any]) -> dict[str, Any]:
    clean = normalize_agent_settings(settings)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(SETTINGS_FILE)
    return clean


def load_agent_profiles() -> dict[str, Any]:
    try:
        loaded = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}

