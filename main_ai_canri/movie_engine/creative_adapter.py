"""Convert Creative_brain output into a movie-ready creative brief."""

from __future__ import annotations

from typing import Any

from .models import MovieRequest
from .utils import split_sentences, unique_strings


def _creative_text(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result or "")
    for key in ("best_idea", "final_output", "answer", "best_answer", "creative_fallback"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for nested in ("text", "idea", "concept", "answer"):
                if value.get(nested):
                    return str(value[nested]).strip()
    candidates = result.get("finalists") or result.get("candidates") or []
    if isinstance(candidates, list) and candidates:
        return _creative_text(candidates[0])
    return ""


def build_creative_brief(request: MovieRequest, context: dict[str, Any]) -> dict[str, Any]:
    results = context.get("brain_results", {})
    creative_result = results.get("Creative_brain", {})
    creative_text = _creative_text(creative_result)
    story_result = results.get("Story_brain", {})
    story_text = _creative_text(story_result)
    source_text = creative_text or story_text or request.prompt
    sentences = split_sentences(source_text, limit=20)
    premise = sentences[0] if sentences else request.prompt[:500]
    themes = unique_strings(
        list(creative_result.get("themes", [])) if isinstance(creative_result, dict) else [],
        limit=6,
    )
    if not themes:
        themes = ["choice", "consequence", "human connection"]
    motifs = unique_strings(
        list(creative_result.get("visual_motifs", [])) if isinstance(creative_result, dict) else [],
        limit=6,
    ) or ["recurring practical light", "environmental transformation", "visual contrast"]
    specialist_insights = []
    for brain_name, brain_context in context.get("brain_context", {}).items():
        if not isinstance(brain_context, dict) or not brain_context.get("usable"):
            continue
        sentences = split_sentences(brain_context.get("text", ""), limit=2)
        if sentences:
            specialist_insights.append({
                "brain": brain_name,
                "insight": sentences[0][:500],
                "confidence": brain_context.get("confidence"),
            })
        if len(specialist_insights) >= 16:
            break
    return {
        "title": request.title,
        "premise": premise,
        "logline": (
            f"In a {request.tone} {request.genre} world, a determined protagonist must "
            f"confront the central promise of: {premise.rstrip('.')}"
        ),
        "genre": request.genre,
        "tone": request.tone,
        "audience_rating": request.audience_rating,
        "themes": themes,
        "visual_motifs": motifs,
        "emotional_promise": sentences[1] if len(sentences) > 1 else "Escalating pressure leads to earned transformation.",
        "ending_direction": sentences[-1] if len(sentences) > 2 else "The final choice resolves the external conflict and changes the protagonist.",
        "creative_brain_used": bool(creative_text),
        "creative_source": "Creative_brain" if creative_text else ("Story_brain" if story_text else "request"),
        "creative_confidence": creative_result.get("confidence") if isinstance(creative_result, dict) else None,
        "specialist_insights": specialist_insights,
    }
