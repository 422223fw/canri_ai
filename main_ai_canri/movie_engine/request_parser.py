"""Turn a natural-language request into an explicit movie contract."""

from __future__ import annotations

import re
from typing import Any

from .constants import DEFAULT_RENDER_PROFILE, SUPPORTED_ASPECT_RATIOS, SUPPORTED_FRAME_RATES
from .duration import parse_duration_seconds
from .models import MovieRequest
from .utils import unique_strings


GENRES = (
    "action", "adventure", "animation", "comedy", "crime", "documentary",
    "drama", "fantasy", "historical", "horror", "mystery", "romance",
    "science fiction", "sci-fi", "thriller", "western",
)


def _extract_text(data: Any, report: dict[str, Any]) -> str:
    values = []
    if isinstance(data, str):
        values.append(data)
    if isinstance(data, dict):
        for key in ("original_text", "corrected_text", "prompt", "text", "goal", "user_message"):
            if data.get(key):
                values.append(str(data[key]))
    for key in ("original_text", "corrected_text"):
        if report.get(key):
            values.append(str(report[key]))
    return "\n".join(unique_strings(values, limit=8)).strip()


def _extract_title(text: str) -> str:
    for pattern in (
        r"(?:title|called|named)\s*[:\-]?\s*[\"']?([^\n\"']{2,80})",
        r"(?:\u05d1\u05e9\u05dd|\u05e9\u05dd \u05d4\u05e1\u05e8\u05d8)\s*[:\-]?\s*[\"']?([^\n\"']{2,80})",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;!?")[:80]
    words = re.findall(r"[A-Za-z0-9\u0590-\u05FF]+", text)
    meaningful = [word for word in words if word.lower() not in {
        "make", "create", "build", "movie", "film", "a", "an", "the", "please"
    }]
    return " ".join(meaningful[:6]).title() or "Untitled Canri Movie"


def _extract_requirements(report: dict[str, Any]) -> list[str]:
    contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
    requirements = contract.get("requirements", []) if isinstance(contract, dict) else []
    values = []
    for item in requirements:
        if isinstance(item, dict):
            values.append(item.get("text") or item.get("requirement"))
        else:
            values.append(item)
    return unique_strings(values, limit=60)


def parse_movie_request(data: Any, report: dict[str, Any]) -> MovieRequest:
    text = _extract_text(data, report)
    lowered = text.lower()
    normalized_words = lowered.replace("-", " ")
    genre = next((item for item in GENRES if item in normalized_words), "drama")
    tone = next((item for item in (
        "dark", "hopeful", "funny", "emotional", "epic", "intimate",
        "suspenseful", "realistic", "surreal", "family-friendly",
    ) if item in lowered), "cinematic")
    language = "Hebrew" if re.search(r"[\u0590-\u05FF]", text) else "English"
    rating_match = re.search(r"\b(G|PG|PG-13|R|NC-17)\b", text, re.IGNORECASE)
    rating = rating_match.group(1).upper() if rating_match else "PG-13"

    render_profile = dict(DEFAULT_RENDER_PROFILE)
    ratio = next((value for value in SUPPORTED_ASPECT_RATIOS if value in text), None)
    if ratio:
        render_profile["aspect_ratio"] = ratio
    fps_match = re.search(r"(23\.976|24|25|30|48|60)\s*(?:fps|frames)", lowered)
    if fps_match:
        frame_rate = float(fps_match.group(1))
        if frame_rate in SUPPORTED_FRAME_RATES:
            render_profile["frame_rate"] = frame_rate
    if "1080p" in lowered:
        render_profile["resolution"] = "1920x1080"
    elif "8k" in lowered:
        render_profile["resolution"] = "7680x4320"

    render_requested = any(marker in lowered for marker in (
        "create movie", "make movie", "generate movie", "render", "produce film",
        "\u05ea\u05db\u05d9\u05df \u05e1\u05e8\u05d8", "\u05e6\u05d5\u05e8 \u05e1\u05e8\u05d8", "\u05dc\u05d9\u05e6\u05d5\u05e8 \u05e1\u05e8\u05d8",
    ))
    return MovieRequest(
        prompt=text,
        title=_extract_title(text),
        duration_seconds=parse_duration_seconds(text),
        genre=genre,
        tone=tone,
        language=language,
        audience_rating=rating,
        realism="photorealistic" if "animation" not in genre else "cinematic animation",
        render_profile=render_profile,
        render_requested=render_requested,
        save_project=True,
        requirements=_extract_requirements(report),
    )
