"""Safe local settings for optional movie-provider rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SETTINGS_FILE = Path(__file__).parent / "data" / "Movie_settings.json"
DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": "runway",
    "model": "gen4.5",
    "budget_usd": 25.0,
    "allow_paid_render": False,
}


def load_movie_settings() -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if isinstance(data, dict):
        settings.update({key: data[key] for key in DEFAULT_SETTINGS if key in data})
    try:
        settings["budget_usd"] = max(0.0, float(settings["budget_usd"]))
    except (TypeError, ValueError):
        settings["budget_usd"] = DEFAULT_SETTINGS["budget_usd"]
    settings["allow_paid_render"] = bool(settings["allow_paid_render"])
    return settings


def save_movie_settings(settings: dict[str, Any]) -> dict[str, Any]:
    clean = dict(DEFAULT_SETTINGS)
    clean.update({key: settings[key] for key in DEFAULT_SETTINGS if key in settings})
    clean["budget_usd"] = max(0.0, float(clean["budget_usd"]))
    clean["allow_paid_render"] = bool(clean["allow_paid_render"])
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(SETTINGS_FILE)
    return clean
