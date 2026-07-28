"""Bounded access to Canri's versioned self-description."""

import json
from pathlib import Path
from typing import Any


PROFILE_FILE = Path(__file__).resolve().parent / "data" / "Canri_self_profile.json"
_cached_profile: dict[str, Any] | None = None
_cached_mtime_ns: int | None = None


def load_canri_identity() -> dict[str, Any]:
    """Load the small structured identity profile without coupling to the UI."""

    global _cached_profile, _cached_mtime_ns
    try:
        mtime_ns = PROFILE_FILE.stat().st_mtime_ns
    except OSError:
        return {}

    if _cached_profile is not None and _cached_mtime_ns == mtime_ns:
        return dict(_cached_profile)

    try:
        loaded = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    _cached_profile = loaded if isinstance(loaded, dict) else {}
    _cached_mtime_ns = mtime_ns
    return dict(_cached_profile)


def release_version(default: str = "1.2.0") -> str:
    """Return one canonical release version for the application."""

    release = load_canri_identity().get("release", {})
    if isinstance(release, dict) and str(release.get("version", "")).strip():
        return str(release["version"]).strip()
    return default
