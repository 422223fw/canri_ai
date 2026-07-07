import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

VOICE_PROFILES_FILE = DATA_DIR / "Voice_audio_profiles.json"
VOICE_SIGNATURES_FILE = DATA_DIR / "Voice_magic_signatures.json"
VOICE_TASKS_FILE = DATA_DIR / "Voice_processing_tasks.json"
VOICE_STATS_FILE = DATA_DIR / "Voice_statistics.json"


AUDIO_FORMATS = {
    "wav": {"category": "audio", "codec_family": "pcm", "lossless": True},
    "mp3": {"category": "audio", "codec_family": "mpeg", "lossless": False},
    "ogg": {"category": "audio", "codec_family": "vorbis/opus", "lossless": False},
    "flac": {"category": "audio", "codec_family": "flac", "lossless": True},
    "aac": {"category": "audio", "codec_family": "aac", "lossless": False},
    "m4a": {"category": "audio", "codec_family": "aac/alac", "lossless": False},
    "opus": {"category": "audio", "codec_family": "opus", "lossless": False},
    "wma": {"category": "audio", "codec_family": "windows_media", "lossless": False},
    "amr": {"category": "audio", "codec_family": "speech", "lossless": False},
    "mid": {"category": "music_data", "codec_family": "midi", "lossless": False},
}

VIDEO_FORMATS = {
    "mp4": {"category": "video", "container": "mp4"},
    "mov": {"category": "video", "container": "quicktime"},
    "mkv": {"category": "video", "container": "matroska"},
    "webm": {"category": "video", "container": "webm"},
    "avi": {"category": "video", "container": "avi"},
    "mpeg": {"category": "video", "container": "mpeg"},
    "mpg": {"category": "video", "container": "mpeg"},
    "m4v": {"category": "video", "container": "mp4"},
    "wmv": {"category": "video", "container": "windows_media"},
    "flv": {"category": "video", "container": "flash_video"},
}

CONTEXTS = [
    "recording", "upload", "video_audio", "attachment", "local_project",
    "generated_asset", "dataset", "voice_note", "music", "unknown_source"
]

TASK_TYPES = [
    "identify_audio", "metadata", "speech_to_text", "speaker_check",
    "language_detection", "noise_check", "format_conversion",
    "extract_audio_from_video", "safety_review", "summarize_audio"
]


def risk_score(extension, category, context, task):
    score = 10
    if category == "video":
        score += 10
    if context in ["attachment", "unknown_source", "upload"]:
        score += 15
    if task in ["speech_to_text", "speaker_check"]:
        score += 20
    if extension in ["wma", "flv", "avi"]:
        score += 10
    return min(score, 85)


def build_profiles():
    profiles = {}
    index = 1
    formats = {**AUDIO_FORMATS, **VIDEO_FORMATS}

    for extension, info in formats.items():
        for context, task in product(CONTEXTS, TASK_TYPES):
            category = info["category"]
            score = risk_score(extension, category, context, task)
            profile_id = f"voice_profile_{index:04d}_{extension}_{context}_{task}"
            profiles[profile_id] = {
                "id": profile_id,
                "extension": extension,
                "category": category,
                "context": context,
                "task": task,
                "codec_family": info.get("codec_family"),
                "container": info.get("container"),
                "lossless": info.get("lossless", False),
                "risk_score": score,
                "risk_level": "high" if score >= 70 else "medium" if score >= 40 else "low",
                "needs_security": score >= 40,
                "needs_transcription_engine": task in ["speech_to_text", "summarize_audio", "language_detection"],
                "needs_video_audio_extraction": category == "video" or task == "extract_audio_from_video",
                "recommended_next_brains": recommended_brains(category, task, score),
                "notes": [
                    "Inspect metadata before processing content.",
                    "Do not claim transcription unless a transcription engine produced text.",
                    "Route privacy-sensitive recordings through Security_brain."
                ]
            }
            index += 1

    return profiles


def recommended_brains(category, task, score):
    brains = ["Voice_brain"]
    if category == "video" or task == "extract_audio_from_video":
        brains.append("Vision_brain")
    if score >= 40:
        brains.append("Security_brain")
    if task in ["speech_to_text", "summarize_audio", "language_detection"]:
        brains.append("Language_brain")
    brains.append("Response_brain")
    return list(dict.fromkeys(brains))


def build_signatures():
    return {
        "wav": {"ascii_prefix": "RIFF", "contains_ascii": "WAVE", "category": "audio", "mime": "audio/wav"},
        "mp3_id3": {"ascii_prefix": "ID3", "category": "audio", "mime": "audio/mpeg"},
        "mp3_frame": {"hex_prefix": "fffb", "category": "audio", "mime": "audio/mpeg"},
        "ogg": {"ascii_prefix": "OggS", "category": "audio", "mime": "audio/ogg"},
        "flac": {"ascii_prefix": "fLaC", "category": "audio", "mime": "audio/flac"},
        "amr": {"ascii_prefix": "#!AMR", "category": "audio", "mime": "audio/amr"},
        "midi": {"ascii_prefix": "MThd", "category": "music_data", "mime": "audio/midi"},
        "mp4": {"contains_ascii": "ftyp", "category": "video", "mime": "video/mp4"},
        "webm": {"hex_prefix": "1a45dfa3", "category": "video", "mime": "video/webm"},
        "avi": {"ascii_prefix": "RIFF", "contains_ascii": "AVI ", "category": "video", "mime": "video/x-msvideo"},
    }


def build_tasks():
    tasks = {}
    index = 1
    for task, context in product(TASK_TYPES, CONTEXTS):
        task_id = f"voice_task_{index:04d}_{task}_{context}"
        tasks[task_id] = {
            "id": task_id,
            "task": task,
            "context": context,
            "steps": steps_for_task(task),
            "required_capability": capability_for_task(task),
            "safe_default": safe_default_for_task(task, context),
            "quality_checks": [
                "file format is identified",
                "metadata is separated from content claims",
                "privacy-sensitive content is not exposed unnecessarily",
                "uncertain results are marked as uncertain"
            ]
        }
        index += 1
    return tasks


def steps_for_task(task):
    base = ["identify file", "read safe metadata", "estimate risk"]
    if task == "extract_audio_from_video":
        return base + ["check video container", "require extraction tool", "route extracted audio back to Voice_brain"]
    if task == "speech_to_text":
        return base + ["require transcription engine", "transcribe", "mark confidence"]
    if task == "speaker_check":
        return base + ["warn about biometric sensitivity", "avoid identity claims without verified system"]
    if task == "noise_check":
        return base + ["inspect audio properties", "estimate quality limits"]
    return base + ["route to response"]


def capability_for_task(task):
    if task in ["speech_to_text", "summarize_audio", "language_detection"]:
        return "transcription_engine"
    if task == "extract_audio_from_video":
        return "ffmpeg_or_video_audio_extractor"
    if task == "format_conversion":
        return "audio_conversion_tool"
    return "metadata_analysis"


def safe_default_for_task(task, context):
    if task in ["speaker_check", "speech_to_text"] and context in ["attachment", "unknown_source"]:
        return False
    return True


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    profiles = build_profiles()
    signatures = build_signatures()
    tasks = build_tasks()
    stats = {
        "Voice_brain": {
            "audio_profiles": len(profiles),
            "magic_signatures": len(signatures),
            "processing_tasks": len(tasks),
            "last_build": "generated"
        }
    }

    write_json(VOICE_PROFILES_FILE, profiles)
    write_json(VOICE_SIGNATURES_FILE, signatures)
    write_json(VOICE_TASKS_FILE, tasks)
    write_json(VOICE_STATS_FILE, stats)

    print(json.dumps({
        "audio_profiles": len(profiles),
        "magic_signatures": len(signatures),
        "processing_tasks": len(tasks)
    }, indent=2))


if __name__ == "__main__":
    main()
