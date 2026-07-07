"""
Language_brain_1.py
Canri AI

Language Loader.
Loads all language JSON files from data/.
"""

import json
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
            "history": "Language_history.json"
        }

    def load_json(self, filename, default=None):

        if default is None:
            default = {}

        path = DATA_DIR / filename

        if not path.exists():
            return default

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            print(f"[LanguageLoader] JSON error in {filename}: {e}")
            return default

        except OSError as e:
            print(f"[LanguageLoader] File error in {filename}: {e}")
            return default

    def load_all(self):

        data = {}

        for key, filename in self.files.items():

            default = {}

            if key in [
                "examples",
                "history"
            ]:
                default = []

            data[key] = self.load_json(
                filename,
                default=default
            )

        return data


loader = LanguageLoader()