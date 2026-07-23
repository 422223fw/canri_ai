"""Parse and allocate movie duration without exceeding five hours."""

from __future__ import annotations

import math
import re

from .constants import (
    ACT_WEIGHTS,
    DEFAULT_MOVIE_SECONDS,
    MAX_MOVIE_SECONDS,
    MIN_MOVIE_SECONDS,
)
from .utils import clamp


def parse_duration_seconds(text: str, default: int = DEFAULT_MOVIE_SECONDS) -> int:
    lowered = str(text or "").lower()
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:hours?|hrs?|hr)\b", 3600),
        (r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:minutes?|mins?|min)\b", 60),
        (r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:seconds?|secs?|sec)\b", 1),
        (r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:\u05e9\u05e2\u05d5\u05ea|\u05e9\u05e2\u05d4)", 3600),
        (r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:\u05d3\u05e7\u05d5\u05ea|\u05d3\u05e7\u05d4)", 60),
    ]
    matches = []
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, lowered):
            matches.append(float(match.group(1)) * multiplier)
    duration = sum(matches) if matches else float(default)
    return int(clamp(round(duration), MIN_MOVIE_SECONDS, MAX_MOVIE_SECONDS))


def allocate_integer_duration(total_seconds: int, item_count: int) -> list[int]:
    if item_count <= 0:
        return []
    total_seconds = max(int(total_seconds), item_count)
    base, remainder = divmod(total_seconds, item_count)
    return [base + (1 if index < remainder else 0) for index in range(item_count)]


def allocate_acts(total_seconds: int) -> list[int]:
    raw = [total_seconds * weight for weight in ACT_WEIGHTS]
    floors = [math.floor(value) for value in raw]
    remainder = total_seconds - sum(floors)
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)[:remainder]:
        floors[index] += 1
    return floors
