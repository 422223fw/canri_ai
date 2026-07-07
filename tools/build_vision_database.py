import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

FILE_PROFILES_FILE = DATA_DIR / "Vision_file_profiles.json"
MAGIC_FILE = DATA_DIR / "Vision_magic_signatures.json"
RISK_FILE = DATA_DIR / "Vision_risk_rules.json"
STATS_FILE = DATA_DIR / "Vision_statistics.json"


CATEGORIES = {
    "image": {
        "extensions": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico", "heic"],
        "mime": "image",
        "next_brains": ["Vision_brain", "Security_brain", "Response_brain"],
        "tasks": ["identify image format", "extract dimensions", "check visual file safety"]
    },
    "video": {
        "extensions": ["mp4", "mov", "avi", "mkv", "webm", "wmv", "flv", "mpeg", "mpg", "m4v"],
        "mime": "video",
        "next_brains": ["Vision_brain", "Security_brain", "Response_brain"],
        "tasks": ["identify video container", "extract basic metadata", "check file risk"]
    },
    "audio": {
        "extensions": ["mp3", "wav", "ogg", "flac", "aac", "m4a", "wma", "opus", "mid", "amr"],
        "mime": "audio",
        "next_brains": ["Voice_brain", "Vision_brain", "Security_brain"],
        "tasks": ["identify audio format", "route speech to Voice_brain", "check file risk"]
    },
    "document": {
        "extensions": ["pdf", "doc", "docx", "txt", "rtf", "md", "odt", "epub", "ppt", "pptx"],
        "mime": "document",
        "next_brains": ["Research_brain", "Language_brain", "Security_brain"],
        "tasks": ["identify document", "extract text if possible", "check macro or attachment risk"]
    },
    "spreadsheet": {
        "extensions": ["xls", "xlsx", "csv", "tsv", "ods", "xlsm", "numbers", "parquet", "feather", "sqlite"],
        "mime": "data",
        "next_brains": ["Research_brain", "Code_brain", "Security_brain"],
        "tasks": ["identify structured data", "check rows or schema", "route analysis"]
    },
    "code": {
        "extensions": ["py", "js", "ts", "html", "css", "java", "cpp", "c", "cs", "php"],
        "mime": "code",
        "next_brains": ["Code_brain", "Security_brain", "Technology_brain"],
        "tasks": ["identify programming language", "scan risky code", "route to Code_brain"]
    },
    "config": {
        "extensions": ["json", "yaml", "yml", "toml", "ini", "env", "xml", "lock", "cfg", "conf"],
        "mime": "configuration",
        "next_brains": ["Code_brain", "Security_brain", "Technology_brain"],
        "tasks": ["identify config format", "validate structure", "check secrets"]
    },
    "archive": {
        "extensions": ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "jar", "war", "apk"],
        "mime": "archive",
        "next_brains": ["Security_brain", "Technology_brain"],
        "tasks": ["identify archive", "avoid automatic extraction", "check suspicious contents"]
    },
    "executable": {
        "extensions": ["exe", "dll", "msi", "bat", "cmd", "ps1", "sh", "app", "scr", "com"],
        "mime": "executable",
        "next_brains": ["Security_brain"],
        "tasks": ["mark executable risk", "do not run", "route to Security_brain"]
    },
    "model": {
        "extensions": ["onnx", "pt", "pth", "h5", "tflite", "pb", "safetensors", "gguf", "bin", "pkl"],
        "mime": "model",
        "next_brains": ["Technology_brain", "Security_brain"],
        "tasks": ["identify model file", "check provenance", "avoid unsafe pickle loading"]
    }
}


CONTEXTS = [
    "upload", "download", "local_project", "attachment", "dataset",
    "generated_asset", "cache", "temporary", "user_file", "unknown_source"
]


def profile_risk(category, extension, context):
    if category == "executable":
        return 95
    if extension in ["xlsm", "doc", "docx", "ppt", "pptx", "pkl", "apk", "jar", "war"]:
        return 75
    if category == "archive":
        return 65
    if extension in ["env", "lock", "sqlite", "bin"]:
        return 55
    if context in ["download", "unknown_source", "attachment"]:
        return 15
    return 5


def build_profiles():
    profiles = {}
    index = 1

    for category, info in CATEGORIES.items():
        for extension, context in product(info["extensions"], CONTEXTS):
            profile_id = f"vision_profile_{index:04d}_{category}_{extension}_{context}"
            risk = profile_risk(category, extension, context)
            profiles[profile_id] = {
                "id": profile_id,
                "extension": extension,
                "category": category,
                "context": context,
                "mime_family": info["mime"],
                "expected_tasks": info["tasks"],
                "next_brains": info["next_brains"],
                "risk_score": risk,
                "risk_level": "critical" if risk >= 90 else "high" if risk >= 70 else "medium" if risk >= 40 else "low",
                "safe_default": category not in ["executable"] and risk < 80,
                "notes": [
                    "Identify before processing.",
                    "Do not execute files during vision analysis.",
                    "Use Security_brain for risky file types."
                ]
            }
            index += 1

    return profiles


def build_magic_signatures():
    return {
        "png": {"hex_prefix": "89504e470d0a1a0a", "category": "image", "mime": "image/png"},
        "jpg": {"hex_prefix": "ffd8ff", "category": "image", "mime": "image/jpeg"},
        "gif": {"ascii_prefix": "GIF8", "category": "image", "mime": "image/gif"},
        "webp": {"contains_ascii": "WEBP", "category": "image", "mime": "image/webp"},
        "bmp": {"ascii_prefix": "BM", "category": "image", "mime": "image/bmp"},
        "pdf": {"ascii_prefix": "%PDF", "category": "document", "mime": "application/pdf"},
        "zip": {"hex_prefix": "504b0304", "category": "archive", "mime": "application/zip"},
        "rar": {"hex_prefix": "526172211a0700", "category": "archive", "mime": "application/vnd.rar"},
        "7z": {"hex_prefix": "377abcaf271c", "category": "archive", "mime": "application/x-7z-compressed"},
        "exe": {"ascii_prefix": "MZ", "category": "executable", "mime": "application/x-msdownload"},
        "mp3": {"ascii_prefix": "ID3", "category": "audio", "mime": "audio/mpeg"},
        "wav": {"contains_ascii": "WAVE", "category": "audio", "mime": "audio/wav"},
        "mp4": {"contains_ascii": "ftyp", "category": "video", "mime": "video/mp4"},
        "sqlite": {"ascii_prefix": "SQLite format 3", "category": "spreadsheet", "mime": "application/vnd.sqlite3"}
    }


def build_risk_rules():
    rules = {}
    index = 1

    for category, info in CATEGORIES.items():
        for extension, context in product(info["extensions"], CONTEXTS):
            risk = profile_risk(category, extension, context)
            rule_id = f"vision_risk_{index:04d}_{category}_{extension}_{context}"
            rules[rule_id] = {
                "id": rule_id,
                "category": category,
                "extension": extension,
                "context": context,
                "risk_score": risk,
                "block_execution": category == "executable",
                "needs_security": risk >= 40,
                "warning": build_warning(category, extension, risk),
                "mitigations": [
                    "Do not run the file.",
                    "Inspect metadata before deeper processing.",
                    "Route risky files to Security_brain.",
                    "Ask user before extracting archives or reading sensitive files."
                ]
            }
            index += 1

    return rules


def build_warning(category, extension, risk):
    if category == "executable":
        return f".{extension} can execute commands or install software."
    if category == "archive":
        return f".{extension} can contain hidden or unsafe files."
    if extension in ["pkl", "env", "xlsm"]:
        return f".{extension} may contain sensitive or executable content."
    if risk >= 40:
        return f".{extension} should be handled carefully."
    return f".{extension} is usually low risk when only metadata is inspected."


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    profiles = build_profiles()
    magic = build_magic_signatures()
    risks = build_risk_rules()
    stats = {
        "Vision_brain": {
            "file_profiles": len(profiles),
            "magic_signatures": len(magic),
            "risk_rules": len(risks),
            "last_build": "generated"
        }
    }

    write_json(FILE_PROFILES_FILE, profiles)
    write_json(MAGIC_FILE, magic)
    write_json(RISK_FILE, risks)
    write_json(STATS_FILE, stats)

    print(json.dumps({
        "file_profiles": len(profiles),
        "magic_signatures": len(magic),
        "risk_rules": len(risks)
    }, indent=2))


if __name__ == "__main__":
    main()
