"""
Voice_brain.py
Canri AI

Voice_brain handles recordings and sound:
- audio files
- voice recordings
- sound inside video files
- safe metadata inspection
- routing to transcription/language/security tools

It does not fake transcripts. If no transcription engine is available,
it reports that transcription is required.
"""

import json
import os
import re
import wave
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
PROFILES_FILE = DATA_DIR / "Voice_audio_profiles.json"
SIGNATURES_FILE = DATA_DIR / "Voice_magic_signatures.json"
TASKS_FILE = DATA_DIR / "Voice_processing_tasks.json"
STATS_FILE = DATA_DIR / "Voice_statistics.json"

MAX_HEADER_BYTES = 256

AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "aac", "m4a", "opus", "wma", "amr", "mid"}
VIDEO_EXTENSIONS = {"mp4", "mov", "mkv", "webm", "avi", "mpeg", "mpg", "m4v", "wmv", "flv"}

TRANSCRIPTION_TERMS = {
    "transcribe", "transcription", "speech to text", "what does it say",
    "summarize audio", "translate audio", "תמלול", "לתמלל", "מה הוא אומר"
}


class VoiceBrain:

    def __init__(self):

        self.profiles = self.load_json(PROFILES_FILE, {})
        self.signatures = self.load_json(SIGNATURES_FILE, {})
        self.tasks = self.load_json(TASKS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        print("Voice Brain Loaded")

    # ---------- loading ----------

    def load_json(self, path, default):

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {}

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_memory_report(self, data):

        if not isinstance(data, dict):
            return {}

        memory = data.get("memory")

        if isinstance(memory, dict):
            return memory

        return {}

    def extract_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in [
                "original_text", "corrected_text", "user_message", "question",
                "query", "text", "audio_path", "voice_path", "video_path", "file_path"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_media_inputs(self, data):

        media = []

        if isinstance(data, str):
            if self.looks_like_media(data):
                media.append({"path": data, "source": "string"})
            return media

        if not isinstance(data, dict):
            return media

        for key in [
            "audio_path", "voice_path", "recording_path", "video_path",
            "file_path", "path"
        ]:
            value = data.get(key)
            if value:
                media.append({"path": str(value), "source": key})

        for key in ["files", "attachments", "audio_files", "recordings", "videos"]:
            values = data.get(key, [])
            if not isinstance(values, list):
                continue

            for value in values:
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("source", key)
                    media.append(item)
                else:
                    media.append({"path": str(value), "source": key})

        return media

    def looks_like_media(self, value):

        lowered = str(value).lower()
        return bool(re.search(r"\.(wav|mp3|ogg|flac|aac|m4a|opus|mp4|mov|mkv|webm|avi|wmv)($|\s)", lowered))

    # ---------- file metadata ----------

    def safe_path(self, path_value):

        try:
            return Path(path_value)
        except (TypeError, ValueError):
            return None

    def extension_of(self, path_or_name):

        return Path(str(path_or_name)).suffix.lower().lstrip(".")

    def category_from_extension(self, extension):

        if extension in AUDIO_EXTENSIONS:
            return "audio"
        if extension in VIDEO_EXTENSIONS:
            return "video"
        return "unknown"

    def read_header(self, path):

        if not path or not path.exists() or not path.is_file():
            return b""

        try:
            with path.open("rb") as file:
                return file.read(MAX_HEADER_BYTES)
        except OSError:
            return b""

    def get_file_size(self, path):

        if not path or not path.exists() or not path.is_file():
            return None

        try:
            return path.stat().st_size
        except OSError:
            return None

    def category_from_magic(self, header):

        if not header:
            return None

        hex_header = header.hex()
        ascii_header = header.decode("latin-1", errors="ignore")

        for name, signature in self.signatures.items():
            hex_prefix = signature.get("hex_prefix")
            if hex_prefix and hex_header.startswith(hex_prefix.lower()):
                return {
                    "signature": name,
                    "category": signature.get("category"),
                    "mime": signature.get("mime")
                }

            ascii_prefix = signature.get("ascii_prefix")
            contains_ascii = signature.get("contains_ascii")

            if ascii_prefix and not ascii_header.startswith(ascii_prefix):
                continue

            if contains_ascii and contains_ascii not in ascii_header:
                continue

            if ascii_prefix or contains_ascii:
                return {
                    "signature": name,
                    "category": signature.get("category"),
                    "mime": signature.get("mime")
                }

        return None

    def wav_metadata(self, path):

        try:
            with wave.open(str(path), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                duration = frames / frame_rate if frame_rate else 0

                return {
                    "channels": channels,
                    "sample_width_bytes": sample_width,
                    "sample_rate": frame_rate,
                    "frames": frames,
                    "duration_seconds": round(duration, 3),
                    "bit_depth": sample_width * 8
                }
        except (wave.Error, OSError, EOFError):
            return {}

    def assess_audio_quality(self, metadata, size):

        if not metadata:
            return {
                "available": False,
                "rating": "unknown",
                "notes": ["Detailed quality assessment needs readable WAV metadata."]
            }

        notes = []
        score = 70
        sample_rate = metadata.get("sample_rate", 0)
        bit_depth = metadata.get("bit_depth", 0)
        channels = metadata.get("channels", 0)
        duration = metadata.get("duration_seconds", 0)

        if sample_rate >= 44100:
            score += 10
            notes.append("High sample rate.")
        elif sample_rate and sample_rate < 16000:
            score -= 20
            notes.append("Low sample rate can hurt transcription quality.")

        if bit_depth >= 16:
            score += 5
        elif bit_depth:
            score -= 10
            notes.append("Low bit depth can reduce clarity.")

        if channels == 1:
            notes.append("Mono audio is usually fine for speech.")
        elif channels >= 2:
            notes.append("Stereo/multi-channel audio detected.")

        if duration and duration < 0.5:
            score -= 15
            notes.append("Very short audio may not contain enough speech.")
        elif duration and duration > 1800:
            score -= 10
            notes.append("Long audio should be chunked before transcription.")

        if size and duration:
            bitrate = round((size * 8) / max(duration, 0.001))
            metadata["approx_bitrate_bps"] = bitrate

        score = max(0, min(score, 100))
        if score >= 85:
            rating = "good"
        elif score >= 60:
            rating = "usable"
        else:
            rating = "weak"

        return {
            "available": True,
            "rating": rating,
            "score": score,
            "notes": notes or ["No major quality issues detected from metadata."]
        }

    def build_processing_plan(self, category, tasks, quality):

        steps = ["Identify media type and inspect metadata safely."]

        if category == "video" or "extract_audio_from_video" in tasks:
            steps.append("Extract audio track with a trusted tool before transcription.")

        if "speech_to_text" in tasks:
            steps.append("Run a real speech-to-text engine; do not invent transcript text.")

        if "language_detection" in tasks:
            steps.append("Send transcript text to Language_brain for language detection/translation.")

        if "summarize_audio" in tasks:
            steps.append("Summarize only after transcript text exists.")

        if quality.get("rating") == "weak":
            steps.append("Improve audio quality or ask for a cleaner recording before final transcription.")

        return steps

    # ---------- task/profile ----------

    def infer_requested_tasks(self, text, category):

        lowered = text.lower()
        tasks = ["identify_audio", "metadata"]

        if any(term in lowered for term in TRANSCRIPTION_TERMS):
            tasks.append("speech_to_text")
            tasks.append("summarize_audio")

        if "language" in lowered or "translate" in lowered or "תרגם" in lowered:
            tasks.append("language_detection")

        if "speaker" in lowered or "who is speaking" in lowered:
            tasks.append("speaker_check")

        if "noise" in lowered or "quality" in lowered:
            tasks.append("noise_check")

        if category == "video":
            tasks.append("extract_audio_from_video")

        return list(dict.fromkeys(tasks))

    def find_profile(self, extension, category, context, task):

        best = None
        best_score = -1

        for profile in self.profiles.values():
            score = 0

            if profile.get("extension") == extension:
                score += 5
            if profile.get("category") == category:
                score += 4
            if profile.get("context") == context:
                score += 2
            if profile.get("task") == task:
                score += 3

            if score > best_score:
                best_score = score
                best = profile

        return best or {}

    def task_capabilities(self, tasks):

        capability_map = {}

        for task in tasks:
            for task_profile in self.tasks.values():
                if task_profile.get("task") == task:
                    capability_map[task] = {
                        "required_capability": task_profile.get("required_capability"),
                        "steps": task_profile.get("steps", []),
                        "safe_default": task_profile.get("safe_default", True)
                    }
                    break

        return capability_map

    def analyze_media(self, item, text):

        path_value = item.get("path") or item.get("name") or item.get("file_name")
        context = item.get("context") or item.get("source") or "unknown_source"
        path = self.safe_path(path_value)

        extension = self.extension_of(path_value or "")
        category = self.category_from_extension(extension)
        exists = bool(path and path.exists())
        is_file = bool(path and path.exists() and path.is_file())
        size = self.get_file_size(path) if is_file else item.get("size")
        header = self.read_header(path) if is_file else b""
        magic = self.category_from_magic(header)

        if magic and magic.get("category"):
            category = magic["category"]

        tasks = self.infer_requested_tasks(text, category)
        profile_scores = []
        next_brains = []

        for task in tasks:
            profile = self.find_profile(extension, category, context, task)
            if profile:
                profile_scores.append(profile.get("risk_score", 10))
                next_brains.extend(profile.get("recommended_next_brains", []))

        risk_score = max(profile_scores or [20 if category == "unknown" else 10])

        metadata = {}
        if extension == "wav" and is_file:
            metadata = self.wav_metadata(path)

        audio_quality = self.assess_audio_quality(metadata, size)

        needs_transcription = any(task in tasks for task in ["speech_to_text", "summarize_audio", "language_detection"])
        needs_extraction = category == "video" or "extract_audio_from_video" in tasks
        needs_security = risk_score >= 40 or needs_transcription or context in ["attachment", "unknown_source"]

        warnings = []

        if not exists and path_value:
            warnings.append("Media path was provided but the file was not found.")

        if needs_transcription:
            warnings.append("Transcription requires a real transcription engine; Voice_brain will not invent transcript text.")

        if needs_extraction:
            warnings.append("Video audio extraction requires an external extractor such as ffmpeg before transcription.")

        if needs_security:
            warnings.append("Audio can contain private speech or sensitive information; handle carefully.")

        if not next_brains:
            next_brains = self.default_next_brains(category, needs_security, needs_transcription)

        return {
            "path": str(path_value) if path_value else None,
            "exists": exists,
            "is_file": is_file,
            "extension": extension,
            "category": category,
            "mime": magic.get("mime") if magic else None,
            "magic_signature": magic.get("signature") if magic else None,
            "size_bytes": size,
            "metadata": metadata,
            "audio_quality": audio_quality,
            "requested_tasks": tasks,
            "task_capabilities": self.task_capabilities(tasks),
            "processing_plan": self.build_processing_plan(category, tasks, audio_quality),
            "needs_transcription_engine": needs_transcription,
            "needs_video_audio_extraction": needs_extraction,
            "transcript": None,
            "transcription_available": False,
            "risk_score": risk_score,
            "risk_level": self.risk_level(risk_score),
            "needs_security": needs_security,
            "suggested_next_brains": list(dict.fromkeys(next_brains)),
            "warnings": list(dict.fromkeys(warnings))
        }

    def default_next_brains(self, category, needs_security, needs_transcription):

        brains = ["Voice_brain"]

        if category == "video":
            brains.append("Vision_brain")

        if needs_security:
            brains.append("Security_brain")

        if needs_transcription:
            brains.append("Language_brain")

        brains.append("Response_brain")

        return brains

    def risk_level(self, score):

        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    # ---------- summary/statistics ----------

    def summarize_media(self, media_items):

        categories = {}
        max_risk = 0
        needs_security = False
        needs_transcription = False
        needs_extraction = False

        for media in media_items:
            category = media.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
            max_risk = max(max_risk, media.get("risk_score", 0))
            needs_security = needs_security or media.get("needs_security", False)
            needs_transcription = needs_transcription or media.get("needs_transcription_engine", False)
            needs_extraction = needs_extraction or media.get("needs_video_audio_extraction", False)

        return {
            "total_media": len(media_items),
            "categories": categories,
            "max_risk_score": max_risk,
            "max_risk_level": self.risk_level(max_risk),
            "needs_security": needs_security,
            "needs_transcription_engine": needs_transcription,
            "needs_video_audio_extraction": needs_extraction
        }

    def build_human_summary(self, analyzed_media, summary):
        if not analyzed_media:
            return "No audio or video media was found to inspect."

        lines = [
            f"Detected {summary.get('total_media', 0)} media file(s).",
            f"Categories: {summary.get('categories', {})}.",
            f"Highest risk: {summary.get('max_risk_level')}."
        ]

        for media in analyzed_media[:6]:
            detail = f"- {media.get('path')}: {media.get('category')} ({media.get('extension') or 'no extension'})"
            metadata = media.get("metadata") or {}
            if metadata.get("duration_seconds") is not None:
                detail += f", duration: {metadata['duration_seconds']}s"
            if metadata.get("sample_rate"):
                detail += f", sample rate: {metadata['sample_rate']} Hz"
            if media.get("requested_tasks"):
                detail += f", tasks: {', '.join(media['requested_tasks'][:5])}"
            quality = media.get("audio_quality") or {}
            if quality.get("rating") and quality.get("rating") != "unknown":
                detail += f", quality: {quality['rating']}"
            lines.append(detail)

        if summary.get("needs_transcription_engine"):
            lines.append("A real transcription engine is required before I can know what the speaker says.")
        if summary.get("needs_video_audio_extraction"):
            lines.append("Video files need audio extraction before transcription.")
        if summary.get("needs_security"):
            lines.append("Audio may contain private speech, so handle it carefully.")

        return "\n".join(lines)

    def update_statistics(self, summary):

        stats = self.statistics.get("Voice_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_total_media"] = summary.get("total_media", 0)
        stats["last_max_risk_level"] = summary.get("max_risk_level", "low")
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("audio_profiles", len(self.profiles))
        stats.setdefault("magic_signatures", len(self.signatures))
        stats.setdefault("processing_tasks", len(self.tasks))

        self.statistics["Voice_brain"] = stats
        self.save_statistics()

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        media_inputs = self.collect_media_inputs(data)

        if not media_inputs and text:
            for match in re.finditer(r"[\w\-.\\/ ]+\.(?:wav|mp3|ogg|flac|aac|m4a|opus|mp4|mov|mkv|webm|avi|wmv)", text, re.IGNORECASE):
                media_inputs.append({
                    "path": match.group(0).strip(),
                    "source": "text"
                })

        analyzed_media = [
            self.analyze_media(item, text)
            for item in media_inputs
        ]

        summary = self.summarize_media(analyzed_media)
        human_summary = self.build_human_summary(analyzed_media, summary)
        self.update_statistics(summary)

        suggested_next = []
        for media in analyzed_media:
            suggested_next.extend(media.get("suggested_next_brains", []))

        if summary["needs_security"]:
            suggested_next.insert(0, "Security_brain")
        if summary["needs_video_audio_extraction"]:
            suggested_next.insert(0, "Vision_brain")
        if summary["needs_transcription_engine"]:
            suggested_next.append("Language_brain")

        if not suggested_next:
            suggested_next.append("Response_brain")

        confidence = 30
        if analyzed_media:
            confidence = 75
            if any(item.get("exists") for item in analyzed_media):
                confidence += 10
            if any(item.get("metadata") for item in analyzed_media):
                confidence += 10
            if any(item.get("magic_signature") for item in analyzed_media):
                confidence += 5

        return {
            "brain": "Voice_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "text_used": text,
            "media_detected": len(analyzed_media),
            "summary": summary,
            "answer": human_summary,
            "final_output": human_summary,
            "media": analyzed_media,
            "confidence": min(confidence, 100),
            "needs_security": summary["needs_security"],
            "needs_transcription_engine": summary["needs_transcription_engine"],
            "needs_video_audio_extraction": summary["needs_video_audio_extraction"],
            "suggested_next_brains": list(dict.fromkeys(suggested_next)),
            "data_files_used": [
                "Voice_audio_profiles.json",
                "Voice_magic_signatures.json",
                "Voice_processing_tasks.json",
                "Voice_statistics.json"
            ],
            "rules": [
                "Do not fake transcript text.",
                "Inspect metadata before processing audio content.",
                "Route video audio extraction through a real extractor.",
                "Treat speech recordings as potentially private.",
                "Use Security_brain for sensitive or unknown-source audio."
            ]
        }


brain = VoiceBrain()
