"""
Language_brain_1.py
Canri AI

Language Loader.
Loads all language JSON files from data/ and keeps a small cache so every
language request does not reread the same large dictionaries.
"""

import json
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"


class LanguageLoader:

    def __init__(self):
        print("Language Loader Loaded")

        self.files = {
            "translations": "Translation_dictionary.json",
            "languages": "Languages.json",
            "statistics": "Language_statistics.json",
            "models": "Language_models.json",
            "rules": "Language_rules.json",
            "examples": "Language_examples.json",
            "synonyms": "Synonyms.json",
            "antonyms": "Antonyms.json",
            "idioms": "Idioms.json",
            "slang": "Slang_dictionary.json",
            "technical_terms": "Technical_terms.json",
            "abbreviations": "Abbreviations.json",
            "units": "Units_dictionary.json",
            "emojis": "Emoji_dictionary.json",
            "history": "Language_history.json",
        }
        self._cache = None
        self._cache_signature = None
        self.last_loaded_utc = None

    def file_signature(self):
        signature = {}

        for key, filename in self.files.items():
            path = DATA_DIR / filename

            if not path.exists():
                signature[key] = None
                continue

            try:
                stat = path.stat()
                signature[key] = (stat.st_size, int(stat.st_mtime))
            except OSError:
                signature[key] = None

        return signature

    def load_json(self, filename, default=None):
        if default is None:
            default = {}

        path = DATA_DIR / filename

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            print(f"[LanguageLoader] JSON error in {filename}: {error}")
            return default
        except OSError as error:
            print(f"[LanguageLoader] File error in {filename}: {error}")
            return default

    def summarize_value(self, value):
        if isinstance(value, dict):
            keys = list(value.keys())
            return {
                "shape": "object",
                "items": len(value),
                "sample_keys": keys[:20],
            }

        if isinstance(value, list):
            return {
                "shape": "array",
                "items": len(value),
                "sample_size": min(len(value), 20),
            }

        return {
            "shape": type(value).__name__,
            "items": 1 if value else 0,
        }

    def normalize_loaded_data(self, data):
        if not isinstance(data, dict):
            return {}

        metadata = {
            "loaded_by": "LanguageLoader",
            "loaded_utc": self.last_loaded_utc,
            "files": {},
        }

        for key, value in data.items():
            metadata["files"][key] = self.summarize_value(value)

        data["metadata"] = metadata
        return data

    def load_all(self):
        signature = self.file_signature()

        if self._cache is not None and signature == self._cache_signature:
            return self._cache

        data = {}
        self.last_loaded_utc = datetime.utcnow().isoformat()

        for key, filename in self.files.items():
            default = [] if key in ["examples", "history"] else {}
            data[key] = self.load_json(filename, default=default)

        data = self.normalize_loaded_data(data)
        self._cache = data
        self._cache_signature = signature
        return data

    def get_metadata(self):
        return self.load_all().get("metadata", {})


loader = LanguageLoader()
