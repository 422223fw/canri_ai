"""
Vision_brain.py
Canri AI

Vision_brain is responsible for file and media understanding:
- images
- videos
- audio files
- documents
- code/config/data files
- archives and executables

It identifies and describes files. It does not execute files.
"""

import json
import hashlib
import mimetypes
import os
import re
import struct
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
FILE_PROFILES_FILE = DATA_DIR / "Vision_file_profiles.json"
MAGIC_FILE = DATA_DIR / "Vision_magic_signatures.json"
RISK_FILE = DATA_DIR / "Vision_risk_rules.json"
STATS_FILE = DATA_DIR / "Vision_statistics.json"

MAX_HEADER_BYTES = 128
MAX_TEXT_PREVIEW_BYTES = 32_000

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico", "heic"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "wmv", "flv", "mpeg", "mpg", "m4v"}
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "flac", "aac", "m4a", "wma", "opus", "mid", "amr"}
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "txt", "rtf", "md", "odt", "epub", "ppt", "pptx"}
CODE_EXTENSIONS = {"py", "js", "ts", "html", "css", "java", "cpp", "c", "cs", "php"}
CONFIG_EXTENSIONS = {"json", "yaml", "yml", "toml", "ini", "env", "xml", "lock", "cfg", "conf"}
ARCHIVE_EXTENSIONS = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "jar", "war", "apk"}
EXECUTABLE_EXTENSIONS = {"exe", "dll", "msi", "bat", "cmd", "ps1", "sh", "app", "scr", "com"}
MODEL_EXTENSIONS = {"onnx", "pt", "pth", "h5", "tflite", "pb", "safetensors", "gguf", "bin", "pkl"}
TEXT_LIKE_CATEGORIES = {"code", "config", "document"}
TEXT_PREVIEW_EXTENSIONS = {"txt", "md", "py", "js", "ts", "html", "css", "json", "yaml", "yml", "toml", "ini", "xml", "csv", "log"}


class VisionBrain:

    def __init__(self):

        self.file_profiles = self.load_json(FILE_PROFILES_FILE, {})
        self.magic_signatures = self.load_json(MAGIC_FILE, {})
        self.risk_rules = self.load_json(RISK_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        print("Vision Brain Loaded")

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

    # ---------- report helpers ----------

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
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "query",
                "text",
                "file_path",
                "image_path",
                "video_path",
                "audio_path"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text", "main_topic", "intent"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_file_inputs(self, data):

        files = []

        if isinstance(data, str):
            if self.looks_like_file(data):
                files.append({"path": data, "source": "string"})
            return files

        if not isinstance(data, dict):
            return files

        for key in [
            "file_path",
            "path",
            "image_path",
            "video_path",
            "audio_path",
            "document_path"
        ]:
            value = data.get(key)
            if value:
                files.append({"path": str(value), "source": key})

        for key in ["files", "attachments", "images", "videos", "documents"]:
            values = data.get(key, [])
            if not isinstance(values, list):
                continue

            for value in values:
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("source", key)
                    files.append(item)
                else:
                    files.append({"path": str(value), "source": key})

        return files

    def looks_like_file(self, value):

        lowered = str(value).lower()

        return bool(
            re.search(r"\.[a-z0-9]{1,8}($|\s)", lowered)
            or "\\" in lowered
            or "/" in lowered
        )

    # ---------- file metadata ----------

    def safe_path(self, path_value):

        try:
            return Path(path_value)
        except (TypeError, ValueError):
            return None

    def read_header(self, path):

        if not path or not path.exists() or not path.is_file():
            return b""

        try:
            with path.open("rb") as file:
                return file.read(MAX_HEADER_BYTES)
        except OSError:
            return b""

    def extension_of(self, path_or_name):

        suffix = Path(str(path_or_name)).suffix.lower().lstrip(".")
        return suffix

    def category_from_extension(self, extension):

        if extension in IMAGE_EXTENSIONS:
            return "image"
        if extension in VIDEO_EXTENSIONS:
            return "video"
        if extension in AUDIO_EXTENSIONS:
            return "audio"
        if extension in DOCUMENT_EXTENSIONS:
            return "document"
        if extension in CODE_EXTENSIONS:
            return "code"
        if extension in CONFIG_EXTENSIONS:
            return "config"
        if extension in ARCHIVE_EXTENSIONS:
            return "archive"
        if extension in EXECUTABLE_EXTENSIONS:
            return "executable"
        if extension in MODEL_EXTENSIONS:
            return "model"

        return "unknown"

    def category_from_magic(self, header):

        if not header:
            return None

        hex_header = header.hex()

        try:
            ascii_header = header.decode("latin-1", errors="ignore")
        except UnicodeDecodeError:
            ascii_header = ""

        for name, signature in self.magic_signatures.items():

            hex_prefix = signature.get("hex_prefix")
            if hex_prefix and hex_header.startswith(hex_prefix.lower()):
                return {
                    "signature": name,
                    "category": signature.get("category"),
                    "mime": signature.get("mime")
                }

            ascii_prefix = signature.get("ascii_prefix")
            if ascii_prefix and ascii_header.startswith(ascii_prefix):
                return {
                    "signature": name,
                    "category": signature.get("category"),
                    "mime": signature.get("mime")
                }

            contains_ascii = signature.get("contains_ascii")
            if contains_ascii and contains_ascii in ascii_header:
                return {
                    "signature": name,
                    "category": signature.get("category"),
                    "mime": signature.get("mime")
                }

        return None

    def get_file_size(self, path):

        if not path or not path.exists() or not path.is_file():
            return None

    def file_fingerprint(self, path, chunk_size=1024 * 1024):

        if not path or not path.exists() or not path.is_file():
            return None
        digest = hashlib.sha256()
        try:
            with path.open("rb") as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    digest.update(chunk)
            return digest.hexdigest()
        except OSError:
            return None

        try:
            return path.stat().st_size
        except OSError:
            return None

    def get_image_dimensions(self, extension, header, path):

        extension = extension.lower()

        try:
            if extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n"):
                width, height = struct.unpack(">II", header[16:24])
                return {"width": width, "height": height, "method": "png_header"}

            if extension == "gif" and header[:3] == b"GIF":
                width, height = struct.unpack("<HH", header[6:10])
                return {"width": width, "height": height, "method": "gif_header"}

            if extension == "webp" and b"WEBP" in header[:16]:
                return {"method": "webp_detected", "note": "WebP detected; dimensions need deeper parsing."}

            if extension == "svg" and path and path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")[:4000]
                width = re.search(r'\bwidth=["\']?(\d+(?:\.\d+)?)', text)
                height = re.search(r'\bheight=["\']?(\d+(?:\.\d+)?)', text)
                viewbox = re.search(r'\bviewBox=["\']([^"\']+)', text)
                result = {"method": "svg_text_header"}
                if width and height:
                    result["width"] = float(width.group(1))
                    result["height"] = float(height.group(1))
                if viewbox:
                    result["viewBox"] = viewbox.group(1)
                return result

            if extension in ["jpg", "jpeg"] and path and path.exists():
                return self.get_jpeg_dimensions(path)

        except (struct.error, OSError, ValueError):
            return {}

        return {}

    def analyze_text_content(self, extension, category, path, is_file, size):

        if not is_file or extension not in TEXT_PREVIEW_EXTENSIONS:
            return {}

        if size and size > MAX_TEXT_PREVIEW_BYTES:
            return {
                "read": False,
                "reason": "file_too_large_for_preview",
                "max_preview_bytes": MAX_TEXT_PREVIEW_BYTES
            }

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {
                "read": False,
                "reason": "read_failed"
            }

        lines = text.splitlines()
        preview = "\n".join(lines[:12])[:1200]
        analysis = {
            "read": True,
            "line_count": len(lines),
            "char_count": len(text),
            "preview": preview,
            "contains_code_block": "```" in text,
            "contains_urls": bool(re.search(r"https?://", text)),
            "contains_possible_secret": bool(re.search(r"(api[_-]?key|secret|password|token)\s*[:=]", text, re.I))
        }

        if extension == "json":
            try:
                parsed = json.loads(text)
                analysis["json_valid"] = True
                analysis["json_shape"] = "object" if isinstance(parsed, dict) else "array" if isinstance(parsed, list) else type(parsed).__name__
                analysis["json_items"] = len(parsed) if isinstance(parsed, (dict, list)) else 1
            except json.JSONDecodeError as error:
                analysis["json_valid"] = False
                analysis["json_error"] = str(error)

        if category == "code":
            analysis["code_signals"] = {
                "functions": len(re.findall(r"\bdef\s+\w+|\bfunction\s+\w+", text)),
                "classes": len(re.findall(r"\bclass\s+\w+", text)),
                "imports": len(re.findall(r"^\s*(import|from|const|let|var|using)\b", text, re.M))
            }

        return analysis

    def build_file_capability_summary(self, category, content_analysis):

        if category == "image":
            return "Can inspect file type, dimensions for common formats, and safety risk."
        if category == "video":
            return "Can identify video files and route audio/visual work; deep frame analysis needs a video model."
        if category == "audio":
            return "Can identify audio and route sound work to Voice_brain."
        if category == "code":
            return "Can preview small code files and route code understanding to Code_brain."
        if content_analysis.get("json_valid") is True:
            return "Can validate JSON structure and preview safe metadata."
        if category == "document":
            return "Can preview small text documents; PDFs/Office files need a document parser for full text."
        return "Can identify file type, risk, and recommended next brain."

    def get_jpeg_dimensions(self, path):

        try:
            with path.open("rb") as file:
                data = file.read(2)
                if data != b"\xff\xd8":
                    return {}

                while True:
                    marker_start = file.read(1)
                    if not marker_start:
                        break
                    if marker_start != b"\xff":
                        continue

                    marker = file.read(1)
                    while marker == b"\xff":
                        marker = file.read(1)

                    if marker in [b"\xc0", b"\xc1", b"\xc2", b"\xc3"]:
                        length = struct.unpack(">H", file.read(2))[0]
                        precision = file.read(1)
                        height, width = struct.unpack(">HH", file.read(4))
                        return {
                            "width": width,
                            "height": height,
                            "method": "jpeg_sof_header",
                            "precision": precision[0] if precision else None
                        }

                    length_bytes = file.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = struct.unpack(">H", length_bytes)[0]
                    file.seek(max(length - 2, 0), os.SEEK_CUR)

        except OSError:
            return {}

        return {}

    # ---------- risk/profile ----------

    def find_profile(self, extension, category, context):

        best = None
        best_score = -1

        for profile in self.file_profiles.values():
            score = 0

            if profile.get("extension") == extension:
                score += 5
            if profile.get("category") == category:
                score += 4
            if profile.get("context") == context:
                score += 2

            if score > best_score:
                best_score = score
                best = profile

        return best or {}

    def find_risk_rule(self, extension, category, context):

        best = None
        best_score = -1

        for rule in self.risk_rules.values():
            score = 0

            if rule.get("extension") == extension:
                score += 5
            if rule.get("category") == category:
                score += 4
            if rule.get("context") == context:
                score += 2

            if score > best_score:
                best_score = score
                best = rule

        return best or {}

    def analyze_file(self, item):

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

        profile = self.find_profile(extension, category, context)
        risk_rule = self.find_risk_rule(extension, category, context)
        risk_score = max(
            profile.get("risk_score", 20 if category == "unknown" else 5),
            risk_rule.get("risk_score", 0)
        )

        dimensions = {}
        if category == "image":
            dimensions = self.get_image_dimensions(extension, header, path)

        content_analysis = self.analyze_text_content(
            extension,
            category,
            path,
            is_file,
            size
        )

        warnings = []

        if not exists and path_value:
            warnings.append("File path was provided but the file was not found.")

        if category == "executable":
            warnings.append("Executable file detected. Do not run it during analysis.")

        if category == "archive":
            warnings.append("Archive detected. Do not extract automatically.")

        if risk_rule.get("warning"):
            warnings.append(risk_rule["warning"])

        if content_analysis.get("contains_possible_secret"):
            warnings.append("Text preview contains possible secret/token/password wording.")

        return {
            "path": str(path_value) if path_value else None,
            "exists": exists,
            "is_file": is_file,
            "extension": extension,
            "category": category,
            "mime": (
                magic.get("mime")
                if magic
                else profile.get("mime_family") or mimetypes.guess_type(str(path_value))[0]
            ),
            "magic_signature": magic.get("signature") if magic else None,
            "size_bytes": size,
            "sha256": self.file_fingerprint(path) if is_file else None,
            "dimensions": dimensions,
            "content_analysis": content_analysis,
            "capability_summary": self.build_file_capability_summary(category, content_analysis),
            "risk_score": risk_score,
            "risk_level": self.risk_level(risk_score),
            "safe_to_execute": False,
            "safe_to_inspect_metadata": risk_score < 90,
            "needs_security": risk_score >= 40 or category in ["executable", "archive", "model"],
            "suggested_tasks": profile.get("expected_tasks", []),
            "suggested_next_brains": profile.get("next_brains", self.default_next_brains(category, risk_score)),
            "warnings": list(dict.fromkeys(warnings)),
            "analysis_status": {
                "real_file_read": is_file,
                "metadata_extracted": bool(header or content_analysis or dimensions),
                "deep_vision_engine_available": False,
                "limitation": (
                    "Metadata and safe text/header analysis completed; object recognition needs an external vision model."
                    if category in {"image", "video"}
                    else None
                )
            }
        }

    def risk_level(self, score):

        if score >= 90:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    def default_next_brains(self, category, risk_score):

        if risk_score >= 40:
            return ["Security_brain", "Response_brain"]
        if category == "audio":
            return ["Voice_brain", "Response_brain"]
        if category in ["code", "config"]:
            return ["Code_brain", "Security_brain", "Response_brain"]
        if category in ["document", "spreadsheet"]:
            return ["Research_brain", "Language_brain", "Response_brain"]
        return ["Response_brain"]

    # ---------- summaries ----------

    def summarize_files(self, files):

        counts = {}
        max_risk = 0
        needs_security = False

        for file_info in files:
            category = file_info.get("category", "unknown")
            counts[category] = counts.get(category, 0) + 1
            max_risk = max(max_risk, file_info.get("risk_score", 0))
            needs_security = needs_security or file_info.get("needs_security", False)

        return {
            "total_files": len(files),
            "categories": counts,
            "max_risk_score": max_risk,
            "max_risk_level": self.risk_level(max_risk),
            "needs_security": needs_security
        }

    def build_human_summary(self, analyzed_files, summary):
        if not analyzed_files:
            return "No visual or file attachments were found to inspect."

        lines = [
            f"Detected {summary.get('total_files', 0)} file(s).",
            f"Categories: {summary.get('categories', {})}.",
            f"Highest risk: {summary.get('max_risk_level')}."
        ]

        for file_info in analyzed_files[:6]:
            detail = f"- {file_info.get('path')}: {file_info.get('category')} ({file_info.get('extension') or 'no extension'})"
            dimensions = file_info.get("dimensions") or {}
            if dimensions.get("width") and dimensions.get("height"):
                detail += f", {dimensions['width']}x{dimensions['height']}"
            if file_info.get("magic_signature"):
                detail += f", signature: {file_info['magic_signature']}"
            content_analysis = file_info.get("content_analysis") or {}
            if content_analysis.get("json_valid") is True:
                detail += f", valid JSON ({content_analysis.get('json_shape')})"
            if content_analysis.get("line_count") is not None:
                detail += f", {content_analysis['line_count']} lines"
            if file_info.get("warnings"):
                detail += f", warning: {file_info['warnings'][0]}"
            lines.append(detail)

        if summary.get("needs_security"):
            lines.append("Security review is recommended before opening, extracting, or executing anything.")

        return "\n".join(lines)

    def update_statistics(self, summary):

        stats = self.statistics.get("Vision_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_total_files"] = summary.get("total_files", 0)
        stats["last_max_risk_level"] = summary.get("max_risk_level", "low")
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("file_profiles", len(self.file_profiles))
        stats.setdefault("magic_signatures", len(self.magic_signatures))
        stats.setdefault("risk_rules", len(self.risk_rules))

        self.statistics["Vision_brain"] = stats
        self.save_statistics()

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)
        file_inputs = self.collect_file_inputs(data)

        if not file_inputs and text:
            for match in re.findall(r"[\w\-.\\/ ]+\.[a-zA-Z0-9]{1,8}", text):
                file_inputs.append({
                    "path": match.strip(),
                    "source": "text"
                })

        analyzed_files = [
            self.analyze_file(item)
            for item in file_inputs
        ]

        summary = self.summarize_files(analyzed_files)
        human_summary = self.build_human_summary(analyzed_files, summary)
        self.update_statistics(summary)

        suggested_next = []
        for file_info in analyzed_files:
            suggested_next.extend(file_info.get("suggested_next_brains", []))

        if summary["needs_security"]:
            suggested_next.insert(0, "Security_brain")

        if not suggested_next:
            suggested_next.append("Response_brain")

        confidence = 30
        if analyzed_files:
            confidence = 75
            if any(file_info.get("exists") for file_info in analyzed_files):
                confidence += 15
            if any(file_info.get("magic_signature") for file_info in analyzed_files):
                confidence += 10

        return {
            "brain": "Vision_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "text_used": text,
            "files_detected": len(analyzed_files),
            "summary": summary,
            "answer": human_summary,
            "final_output": human_summary,
            "files": analyzed_files,
            "engine_status": {
                "metadata_engine": "available",
                "text_file_engine": "available",
                "deep_image_model": "not_configured",
                "video_frame_model": "not_configured"
            },
            "confidence": min(confidence, 100),
            "needs_security": summary["needs_security"],
            "suggested_next_brains": list(dict.fromkeys(suggested_next)),
            "data_files_used": [
                "Vision_file_profiles.json",
                "Vision_magic_signatures.json",
                "Vision_risk_rules.json",
                "Vision_statistics.json"
            ],
            "rules": [
                "Identify files before processing them.",
                "Never execute files in Vision_brain.",
                "Use metadata and magic signatures when possible.",
                "Route executables, archives, model files, and unknown risky files to Security_brain.",
                "Use Voice_brain for audio and Code_brain for code/config files."
            ]
        }


brain = VisionBrain()
