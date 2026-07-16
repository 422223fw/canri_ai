"""Build reproducible conversation and media knowledge packs for Canri."""

import json
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "main_ai_canri" / "data"


def write_json(name, payload):
    path = DATA_DIR / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return len(payload)


def conversation_patterns():
    intents = {
        "emotional_support": ["i feel", "having a hard time", "need someone"],
        "reassurance": ["i am worried", "will it be okay", "i am scared"],
        "venting": ["i am frustrated", "everything went wrong", "need to vent"],
        "celebration": ["i did it", "great news", "i am proud"],
        "small_talk": ["how are you", "can we talk", "tell me something"],
        "clarification": ["i do not know", "this is confusing", "help me understand"],
    }
    emotions = ["sadness", "fear", "anger", "confusion", "joy", "neutral"]
    intensities = ["low", "medium", "high"]
    stages = ["acknowledge", "reflect", "clarify", "small_step"]
    rows = []
    for intent, emotion, intensity, stage in product(intents, emotions, intensities, stages):
        rows.append({
            "id": f"conversation_{len(rows):04d}",
            "intent": intent,
            "emotion": emotion,
            "intensity": intensity,
            "stage": stage,
            "trigger_terms": intents[intent],
            "response_goal": {
                "acknowledge": "Recognize the user's experience without exaggerating it.",
                "reflect": "Briefly reflect the central feeling and situation.",
                "clarify": "Ask one concrete, non-interrogating question.",
                "small_step": "Offer one optional and realistic next step."
            }[stage],
            "avoid": ["diagnosis", "forced positivity", "invented personal experience", "too many questions"],
            "handoff": "Security_brain" if intensity == "high" and emotion in {"fear", "sadness"} else "Response_brain",
            "confidence": 86 if intent != "clarification" else 78
        })
    return rows


def support_strategies():
    emotions = ["sadness", "fear", "anger", "confusion", "joy", "neutral"]
    intensities = ["low", "medium", "high"]
    goals = ["listen", "stabilize", "clarify", "problem_solve", "encourage", "follow_up"]
    approaches = ["reflective", "practical", "gentle"]
    rows = []
    for emotion, intensity, goal, approach in product(emotions, intensities, goals, approaches):
        rows.append({
            "id": f"support_{len(rows):04d}",
            "emotion": emotion,
            "intensity": intensity,
            "goal": goal,
            "approach": approach,
            "sequence": ["acknowledge", "one useful response", "one optional follow-up"],
            "max_questions": 1,
            "must_not": ["claim consciousness", "replace professional care", "shame the user", "promise an outcome"],
            "escalate_if": ["immediate danger", "self-harm intent", "threat to another person"],
            "quality_checks": ["relevant", "specific", "non-judgmental", "not overly verbose"]
        })
    return rows


def image_profiles():
    purposes = ["portrait", "poster", "logo", "game_sprite", "book_cover", "wallpaper", "concept_art", "product_mockup"]
    media = ["illustration", "photo", "watercolor", "pixel_art", "vector", "3d_render"]
    lighting = ["soft", "studio", "golden_hour", "moonlight", "neon"]
    aspects = ["1:1", "4:3", "16:9", "9:16", "2:3"]
    rows = []
    for purpose, medium, light, aspect in product(purposes, media, lighting, aspects):
        rows.append({
            "id": f"image_profile_{len(rows):04d}",
            "purpose": purpose,
            "medium": medium,
            "lighting": light,
            "aspect_ratio": aspect,
            "prompt_fields": ["subject", "environment", "composition", "camera", "lighting", "palette", "constraints"],
            "quality_checks": ["clear subject", "coherent perspective", "readable silhouette", "no accidental text"],
            "local_fallback": "svg_preview",
            "raster_requirement": "external_image_model"
        })
    return rows


def media_profiles():
    categories = ["image", "video", "document", "code", "config", "archive", "audio", "spreadsheet"]
    tasks = ["identify", "metadata", "content_preview", "structure", "safety"]
    contexts = ["local", "attachment", "unknown_source"]
    rows = []
    for category, task, context in product(categories, tasks, contexts):
        rows.append({
            "id": f"media_analysis_{len(rows):04d}",
            "category": category,
            "task": task,
            "context": context,
            "safe_operation": "read_only",
            "never": ["execute", "automatic extraction", "upload without permission"],
            "fallback": "Report the missing parser or model explicitly.",
            "recommended_brain": {
                "image": "Vision_brain", "video": "Vision_brain", "document": "Research_brain",
                "code": "Code_brain", "config": "Code_brain", "archive": "Security_brain",
                "audio": "Voice_brain", "spreadsheet": "Research_brain"
            }[category]
        })
    return rows


def audio_profiles():
    formats = ["wav", "mp3", "flac", "ogg", "m4a", "aac", "opus", "video_audio"]
    tasks = ["metadata", "signal_quality", "speech_to_text", "language", "summary", "privacy"]
    qualities = ["clean", "noisy", "quiet", "clipped"]
    rows = []
    for audio_format, task, quality in product(formats, tasks, qualities):
        rows.append({
            "id": f"audio_analysis_{len(rows):04d}",
            "format": audio_format,
            "task": task,
            "quality": quality,
            "local_capability": task in {"metadata", "signal_quality", "privacy"} and audio_format == "wav",
            "external_requirement": (
                "speech_to_text_model" if task in {"speech_to_text", "language", "summary"}
                else "ffmpeg" if audio_format == "video_audio"
                else None
            ),
            "truthfulness_rule": "Never invent a transcript.",
            "privacy_level": "high" if task == "privacy" else "normal"
        })
    return rows


def main():
    counts = {
        "Conversation_patterns.json": write_json("Conversation_patterns.json", conversation_patterns()),
        "Emotional_support_strategies.json": write_json("Emotional_support_strategies.json", support_strategies()),
        "Image_generation_profiles.json": write_json("Image_generation_profiles.json", image_profiles()),
        "Media_analysis_profiles.json": write_json("Media_analysis_profiles.json", media_profiles()),
        "Audio_analysis_profiles.json": write_json("Audio_analysis_profiles.json", audio_profiles()),
    }
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
