"""Small deterministic helpers shared by movie modules."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def slugify(value: str, fallback: str = "canri_movie") -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_")
    return value[:80].lower() or fallback


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def unique_strings(values: Iterable[Any], limit: int = 100) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_primitive(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(to_primitive(value), ensure_ascii=False))


def split_sentences(text: str, limit: int = 30) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+|[\r\n]+", str(text or ""))
    return unique_strings((piece.strip() for piece in pieces), limit=limit)
