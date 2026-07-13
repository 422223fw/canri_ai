"""
Understanding_brain.py
Canri AI

Builds the central understanding report used by the other brains.
It uses UnderstandingDk for dictionary, grammar, and word connections,
then adds Canri-specific intent, topic, task, and routing analysis.
"""

import re
from collections import Counter
from datetime import datetime, timezone

try:
    import UnderstandingDk as dk
except Exception:
    dk = None


WORD_RE = re.compile(r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']*")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "the", "to",
    "with", "you", "your", "please", "can", "could", "would", "should",
    "want", "need", "give", "make", "create", "build", "do", "does",
    "what", "how", "why", "when", "where", "only", "must",
    "אני", "אתה", "את", "של", "על", "מה", "איך", "למה", "זה", "זו",
    "תעשה", "תכין", "רוצה", "לי", "עם", "או", "וגם", "האם"
}

PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their"
}

POSSESSIVES = {
    "my", "your", "his", "her", "its", "our", "their"
}

DETERMINERS = {
    "a", "an", "the", "this", "that", "these", "those", "each", "every",
    "some", "any", "one", "two", "three"
}

CONJUNCTIONS = {
    "and", "or", "but", "so", "because", "while", "although", "then"
}

NEGATIONS = {
    "not", "no", "never", "dont", "don't", "cannot", "can't", "without"
}

PREPOSITIONS = {
    "in", "on", "under", "over", "above", "below", "inside", "outside",
    "near", "beside", "behind", "before", "after", "from", "to", "into",
    "onto", "with", "without", "through", "between", "around", "at", "of",
    "for", "by", "about", "like"
}

AUXILIARY_VERBS = {
    "be", "am", "is", "are", "was", "were", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "will", "would", "should", "may", "might", "must"
}

QUESTION_WORDS = {
    "what", "who", "where", "when", "why", "how"
}

DOMAIN_RULES = {
    "code": [
        "code", "python", "javascript", "java", "function", "class", "api",
        "json", "program", "script", "bug", "debug", "working code",
        "analyze code", "explain code", "review code", "what this code does",
        "קוד", "פייתון", "פונקציה", "מחלקה"
    ],
    "game": [
        "game", "rpg", "player", "enemy", "inventory", "level", "quest",
        "combat", "save", "load", "משחק", "שחקן", "אויב", "שלב"
    ],
    "science": [
        "science", "physics", "chemistry", "biology", "gravity", "atom",
        "energy", "force", "cell", "מדע", "פיזיקה", "כימיה", "ביולוגיה"
    ],
    "technology": [
        "technology", "hardware", "software", "cpu", "gpu", "computer",
        "robot", "network", "device", "טכנולוגיה", "חומרה", "מחשב"
    ],
    "geography": [
        "geography", "country", "city", "capital", "map", "gps", "river",
        "mountain", "location", "located", "where", "france", "paris",
        "גיאוגרפיה", "מדינה", "עיר", "מפה"
    ],
    "history": [
        "history", "war", "empire", "ancient", "king", "century",
        "revolution", "היסטוריה", "מלחמה", "אימפריה", "עתיק"
    ],
    "language": [
        "language", "translate", "translation", "grammar", "synonym",
        "antonym", "word", "sentence", "שפה", "תרגם", "תרגום", "דקדוק"
    ],
    "math": [
        "solve", "step by step", "x^2", "x**2",
        "math", "calculate", "equation", "number", "algebra", "geometry",
        "probability", "מתמטיקה", "חשב", "משוואה", "מספר"
    ],
    "security": [
        "security", "password", "hack", "malware", "token", "encrypt",
        "suicide", "bomb", "אבטחה", "סיסמה", "פצצה", "התאבד"
    ],
    "image_generation": [
        "generate image", "create image", "make image", "draw image",
        "draw", "illustration", "poster", "logo", "icon", "concept art",
        "image prompt", "visual design", "picture of", "image of"
    ],
    "vision": [
        "image", "photo", "picture", "video", "file", "pdf", "png", "jpg",
        "תמונה", "וידאו", "קובץ"
    ],
    "voice": [
        "voice", "audio", "sound", "recording", "microphone", "speech",
        "קול", "אודיו", "הקלטה", "סאונד"
    ],
    "story": [
        "story", "character", "plot", "world", "scene", "dialogue",
        "סיפור", "דמות", "עלילה", "עולם"
    ],
    "creative": [
        "creative", "idea", "invent", "brainstorm", "original", "stuck",
        "יצירתי", "רעיון", "להמציא"
    ],
    "code_analysis": [
        "analyze code", "analyze this code", "explain code", "explain this code",
        "what this code does", "what does this code do", "review this code",
        "walk me through this code"
    ],
    "planning": [
        "plan", "steps", "roadmap", "structure", "architecture",
        "תוכנית", "שלבים", "מבנה", "תכנון"
    ]
}

INTENT_RULES = {
    "code_generation": [
        "write code", "give me code", "working code", "first code", "build",
        "create a program", "implement", "function", "class", "תכתוב קוד"
    ],
    "planning": [
        "plan", "structure", "steps", "roadmap", "architecture",
        "תכנן", "תוכנית", "שלבים"
    ],
    "question": [
        "what", "how", "why", "when", "where", "who", "explain", "?",
        "מה", "איך", "למה", "מתי", "איפה", "מי", "הסבר"
    ],
    "translation": [
        "translate", "translation", "תרגם", "תרגום"
    ],
    "correction": [
        "fix", "correct", "spelling", "grammar", "תקן", "שגיאת", "דקדוק"
    ],
    "research": [
        "research", "sources", "find information", "reliable", "look up",
        "מקורות", "מחקר", "מידע אמין"
    ],
    "story_creation": [
        "write a story", "story", "character", "plot", "סיפור", "דמות"
    ],
    "image_generation": [
        "generate image", "create image", "make image", "draw", "illustration",
        "poster", "logo", "icon", "concept art", "image prompt"
    ],
    "game_design": [
        "game design", "rpg", "game", "player", "enemy", "משחק"
    ],
    "capability_question": [
        "what can you do", "capabilities", "יכולות", "מה אתה יכול"
    ],
    "greeting": [
        "hello", "hi", "hey", "shalom", "שלום", "היי", "הי"
    ]
}

OUTPUT_RULES = {
    "code_generation": "code",
    "code_analysis": "code_explanation",
    "planning": "plan",
    "question": "answer",
    "translation": "translation",
    "correction": "corrected_text",
    "research": "sourced_summary",
    "story_creation": "story",
    "image_generation": "image_asset",
    "game_design": "game_plan",
    "creative_generation": "creative_result"
}

ACTION_COMMANDS = {
    "do": "perform",
    "write": "generate",
    "create": "generate",
    "make": "generate",
    "generate": "generate",
    "draw": "generate",
    "build": "build",
    "implement": "build",
    "invent": "creative_generate",
    "continue": "continue",
    "add": "modify",
    "improve": "modify",
    "upgrade": "modify",
    "fix": "modify",
    "correct": "modify",
    "translate": "translate",
    "plan": "plan",
    "explain": "explain",
    "tell": "explain",
    "show": "show",
    "give": "provide",
    "help": "help",
    "analyze": "analyze",
    "review": "analyze",
    "solve": "solve",
    "calculate": "solve"
}

DICTIONARY_QUERY_MARKERS = {
    "what is",
    "what are",
    "define",
    "definition",
    "meaning of",
    "means",
    "mean"
}


class UnderstandingBrain:

    def __init__(self):

        self.dictionary_ready = dk is not None

        print("Understanding Brain Loaded")

    # ---------- input ----------

    def normalize_input(self, data):

        if isinstance(data, str):
            return {
                "original_text": data,
                "corrected_text": data
            }

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "corrected_text": str(data)
            }

        original = (
            data.get("original_text")
            or data.get("user_message")
            or data.get("question")
            or data.get("text")
            or ""
        )

        corrected = data.get("corrected_text") or original

        return {
            "original_text": str(original),
            "corrected_text": str(corrected),
            "attached_files": data.get("attached_files", []),
            "spelling": data.get("spelling", {})
        }

    def extract_words(self, text):

        return [
            match.group(0).strip("'").lower()
            for match in WORD_RE.finditer(text)
            if match.group(0).strip("'")
        ]

    def detect_language(self, text, words):

        hebrew_chars = len(re.findall(r"[\u0590-\u05FF]", text))
        latin_chars = len(re.findall(r"[A-Za-z]", text))

        if hebrew_chars and latin_chars:
            return "mixed"

        if hebrew_chars:
            return "he"

        if latin_chars:
            return "en"

        return "unknown"

    def has_code_payload(self, text):

        text = str(text or "")
        lowered = text.lower()

        code_signals = [
            "```",
            "def ",
            "class ",
            "import ",
            "from ",
            "if __name__",
            "return ",
            "console.log",
            "function ",
            "public static",
            "#include",
            "</",
            "{",
            "};"
        ]

        if any(signal in lowered for signal in code_signals):
            return True

        punctuation_score = sum(
            text.count(mark)
            for mark in ["(", ")", "{", "}", "[", "]", ";", "=", ":"]
        )

        return punctuation_score >= 6 and "\n" in text

    # ---------- word analysis ----------

    def get_word_type(self, word):

        if not dk:
            return "unknown"

        entries = dk.search_word(word)
        if entries:
            return entries[0].get("type", "unknown") or "unknown"

        return "unknown"

    def analyze_word(self, word):

        exists = bool(dk and dk.word_exists(word))
        meanings = dk.get_meanings(word)[:3] if exists else []
        connections = dk.related(word)[:12] if exists else []
        suggestions = [] if exists or not dk else dk.suggest(word, limit=5)
        forms = dk.get_forms(word) if dk and dk.grammar_exists(word) else {}
        tense = dk.detect_tense(word) if dk else None

        return {
            "word": word,
            "exists": exists,
            "type": self.get_word_type(word),
            "meanings": meanings,
            "connections": connections,
            "suggestions": suggestions,
            "forms": forms,
            "tense": tense,
            "is_stop_word": word in STOP_WORDS
        }

    def analyze_words(self, words):

        seen = set()
        analyzed = []

        for word in words:
            if word in seen:
                continue
            seen.add(word)
            analyzed.append(self.analyze_word(word))

            if len(analyzed) >= 80:
                break

        return analyzed

    # ---------- sentence graph ----------

    def token_reports(self, words, word_reports):

        report_by_word = {
            report.get("word"): report
            for report in word_reports
            if isinstance(report, dict)
        }
        tokens = []

        for index, word in enumerate(words):
            report = report_by_word.get(word) or self.analyze_word(word)
            tokens.append({
                "id": f"w{index}",
                "index": index,
                "word": word,
                "type": report.get("type", "unknown"),
                "exists": report.get("exists", False),
                "is_stop_word": word in STOP_WORDS,
                "is_pronoun": word in PRONOUNS,
                "is_possessive": word in POSSESSIVES,
                "is_preposition": word in PREPOSITIONS,
                "is_question_word": word in QUESTION_WORDS,
                "tense": report.get("tense"),
                "connections": report.get("connections", [])[:12],
                "meanings": report.get("meanings", [])[:2]
            })

        return tokens

    def normalize_word_type(self, token):

        token_type = str(
            token.get(
                "type",
                ""
            )
        ).lower()

        if token.get("is_question_word"):
            return "question_word"

        if token.get("is_preposition"):
            return "preposition"

        if token.get("is_possessive"):
            return "possessive"

        if token.get("is_pronoun"):
            return "pronoun"

        if "adverb" in token_type:
            return "adverb"

        if "adjective" in token_type:
            return "adjective"

        if "verb" in token_type or self.is_verb_like(token):
            return "verb"

        if "noun" in token_type:
            return "noun"

        if "number" in token_type:
            return "number"

        if token.get("is_stop_word"):
            return "stop_word"

        return "unknown"

    def build_syntax_profile(self, tokens, subject, main_action, object_token):

        groups = {
            "verbs": [],
            "nouns": [],
            "adjectives": [],
            "adverbs": [],
            "prepositions": [],
            "pronouns": [],
            "question_words": [],
            "unknown": []
        }

        syntax_tokens = []

        for token in tokens:
            normalized_type = self.normalize_word_type(
                token
            )
            word = token.get(
                "word"
            )

            if normalized_type == "verb":
                groups["verbs"].append(word)
            elif normalized_type == "noun":
                groups["nouns"].append(word)
            elif normalized_type == "adjective":
                groups["adjectives"].append(word)
            elif normalized_type == "adverb":
                groups["adverbs"].append(word)
            elif normalized_type == "preposition":
                groups["prepositions"].append(word)
            elif normalized_type == "pronoun":
                groups["pronouns"].append(word)
            elif normalized_type == "question_word":
                groups["question_words"].append(word)
            elif normalized_type == "unknown" and not token.get("is_stop_word"):
                groups["unknown"].append(word)

            roles = []
            if subject and token["id"] == subject["id"]:
                roles.append("subject")
            if main_action and token["id"] == main_action["id"]:
                roles.append("action")
            if object_token and token["id"] == object_token["id"]:
                roles.append("object")
            if self.is_modifier_like(token):
                roles.append("modifier")
            if token.get("is_preposition"):
                roles.append("relation")
            if token.get("is_question_word"):
                roles.append("question_focus")

            syntax_tokens.append({
                "word": word,
                "raw_type": token.get("type"),
                "normalized_type": normalized_type,
                "roles": roles,
                "tense": token.get("tense"),
                "known_word": token.get("exists")
            })

        for key, values in groups.items():
            groups[key] = list(dict.fromkeys(
                value
                for value in values
                if value
            ))

        return {
            "groups": groups,
            "tokens": syntax_tokens[:80],
            "main_subject": subject.get("word") if subject else None,
            "main_action": main_action.get("word") if main_action else None,
            "main_object": object_token.get("word") if object_token else None,
            "has_action": bool(main_action),
            "has_object": bool(object_token),
            "rules": [
                "Use word type from UnderstandingDk, not only word meaning.",
                "Treat verbs as actions the user may want performed.",
                "Use nouns as likely subjects, objects, and requested targets.",
                "Use adjectives and adverbs as constraints or style modifiers.",
                "Use prepositions to connect objects, locations, and relations."
            ]
        }

    def is_noun_like(self, token):

        token_type = str(token.get("type", "")).lower()
        if token.get("is_preposition") or token.get("is_possessive"):
            return False
        return (
            "noun" in token_type
            or token.get("is_pronoun")
            or token_type in {"proper noun", "unknown"}
            and not token.get("is_stop_word")
        )

    def is_verb_like(self, token):

        word = token.get("word", "")
        token_type = str(token.get("type", "")).lower()
        if (
            "adverb" in token_type
            or token.get("is_preposition")
            or (word.endswith("ly") and len(word) > 4)
        ):
            return False
        if (
            "adjective" in token_type
            and token.get("tense") not in {"past", "past_participle"}
            and not (word.endswith("ed") and len(word) > 4)
        ):
            return False

        base_guesses = []
        if word.endswith("ies") and len(word) > 3:
            base_guesses.append(word[:-3] + "y")
        elif word.endswith("es") and len(word) > 3:
            base_guesses.extend([
                word[:-1],
                word[:-2]
            ])
        elif word.endswith("s") and len(word) > 3:
            base_guesses.append(word[:-1])

        base_is_verb = False
        if base_guesses and dk:
            for base_guess in base_guesses:
                entries = dk.search_word(base_guess)
                if any(
                    "verb" in str(entry.get("type", "")).lower()
                    for entry in entries
                    if isinstance(entry, dict)
                ):
                    base_is_verb = True
                    break

        return (
            "verb" in token_type
            or (word.endswith("ed") and len(word) > 4)
            or (word.endswith("ing") and len(word) > 5)
            or base_is_verb
        )

    def is_modifier_like(self, token):

        token_type = str(token.get("type", "")).lower()
        word = token.get("word", "")
        if token.get("is_preposition") or token.get("is_possessive"):
            return False
        if self.is_verb_like(token):
            return False
        return (
            "adjective" in token_type
            or "adverb" in token_type
            or word.endswith("ly")
            or word in {"small", "big", "tiny", "quiet", "glowing", "final", "simple", "real"}
        )

    def is_adverb_like(self, token):

        token_type = str(token.get("type", "")).lower()
        word = token.get("word", "")
        if token.get("is_preposition"):
            return False
        return "adverb" in token_type or word.endswith("ly")

    def nearest_before(self, tokens, index, predicate):

        for token in reversed(tokens[:index]):
            if predicate(token):
                return token
        return None

    def nearest_after(self, tokens, index, predicate):

        for token in tokens[index + 1:]:
            if predicate(token):
                return token
        return None

    def object_after_action(self, tokens, action):

        candidates = []
        for token in tokens[action["index"] + 1:]:
            if candidates and token.get("word") in {"only", "do", "dont", "don't", "must", "should"}:
                break
            if token.get("is_preposition"):
                break
            if self.is_noun_like(token):
                candidates.append(token)
                continue
            if candidates and not self.is_modifier_like(token):
                break

        if not candidates:
            return None

        # In noun phrases like "Python game" or "Python to-do list program",
        # prefer the phrase head, which is usually the last close noun.
        return candidates[-1]

    def add_edge(self, edges, source, relation, target, confidence=70, evidence=None):

        if not source or not target:
            return

        edge = {
            "from": source.get("id"),
            "from_word": source.get("word"),
            "relation": relation,
            "to": target.get("id"),
            "to_word": target.get("word"),
            "confidence": confidence
        }

        if evidence:
            edge["evidence"] = evidence

        if edge not in edges:
            edges.append(edge)

    def build_sentence_graph(self, words, word_reports):

        tokens = self.token_reports(words, word_reports)
        content_tokens = [
            token
            for token in tokens
            if not token.get("is_stop_word")
        ]
        edges = []

        for left, right in zip(content_tokens, content_tokens[1:]):
            self.add_edge(edges, left, "next_meaning_token", right, 45, "sentence_order")

        verbs = [
            token
            for token in tokens
            if self.is_verb_like(token)
            and (
                token.get("word") not in AUXILIARY_VERBS
                or (
                    token.get("word") in ACTION_COMMANDS
                    and token.get("index", 99) <= 3
                )
            )
        ]
        nouns = [
            token
            for token in tokens
            if self.is_noun_like(token)
        ]

        main_action = verbs[0] if verbs else None
        subject = None
        object_token = None

        if main_action:
            subject = self.nearest_before(tokens, main_action["index"], self.is_noun_like)
            object_token = self.object_after_action(tokens, main_action)
            self.add_edge(edges, subject, "does_action", main_action, 82, "nearest noun before main verb")
            self.add_edge(edges, main_action, "acts_on", object_token, 82, "best noun phrase after main verb")
        elif nouns:
            subject = nouns[0]

        for index, token in enumerate(tokens):
            if token.get("word") == "and":
                left = self.nearest_before(tokens, index, self.is_noun_like)
                right = self.nearest_after(tokens, index, self.is_noun_like)
                self.add_edge(edges, left, "coordinated_with", right, 72, "noun list joined by and")
                continue

            if token.get("is_possessive"):
                owned = self.nearest_after(tokens, index, self.is_noun_like)
                self.add_edge(edges, token, "possesses_or_describes_owner", owned, 78, "possessive before noun")

            if self.is_adverb_like(token):
                action = (
                    self.nearest_after(tokens, index, self.is_verb_like)
                    or self.nearest_before(tokens, index, self.is_verb_like)
                )
                if action and abs(action["index"] - token["index"]) <= 3:
                    self.add_edge(edges, token, "modifies_action", action, 77, "adverb near verb")
                continue

            if self.is_modifier_like(token):
                noun = self.nearest_after(tokens, index, self.is_noun_like)
                if noun and noun["index"] - token["index"] <= 3:
                    self.add_edge(edges, token, "describes", noun, 76, "modifier near noun")

            if self.is_noun_like(token) and not token.get("is_pronoun"):
                head = self.nearest_after(tokens, index, self.is_noun_like)
                if head and head["index"] - token["index"] == 1:
                    self.add_edge(edges, token, "compound_modifier", head, 70, "noun phrase head connection")

            if token.get("is_preposition"):
                source = self.nearest_before(tokens, index, lambda item: self.is_noun_like(item) or self.is_verb_like(item))
                target = self.nearest_after(tokens, index, self.is_noun_like)
                relation = f"preposition_{token.get('word')}"
                self.add_edge(edges, source, relation, target, 74, "prepositional phrase")

        token_by_word = {}
        for token in tokens:
            token_by_word.setdefault(token.get("word"), []).append(token)

        for token in content_tokens:
            for connection in token.get("connections", [])[:8]:
                related_word = str(connection).lower()
                if related_word not in token_by_word:
                    continue
                for target in token_by_word[related_word][:2]:
                    if target["id"] != token["id"]:
                        self.add_edge(edges, token, "dictionary_related_in_sentence", target, 62, "UnderstandingDk connection")

        question_focus = None
        for token in tokens:
            if token.get("is_question_word") and token.get("index", 99) <= 2:
                question_focus = token.get("word")
                break

        meaning_frame = {
            "subject": subject.get("word") if subject else None,
            "action": main_action.get("word") if main_action else None,
            "object": object_token.get("word") if object_token else None,
            "question_focus": question_focus,
            "content_terms": [token.get("word") for token in content_tokens[:30]]
        }

        graph_confidence = 45
        if meaning_frame["subject"] and meaning_frame["action"] and meaning_frame["object"]:
            graph_confidence = 86
        elif meaning_frame["action"] and meaning_frame["object"]:
            graph_confidence = 72
        elif len(content_tokens) >= 2:
            graph_confidence = 60

        syntax_profile = self.build_syntax_profile(
            tokens,
            subject,
            main_action,
            object_token
        )

        return {
            "nodes": [
                {
                    "id": token["id"],
                    "word": token["word"],
                    "index": token["index"],
                    "type": token["type"],
                    "normalized_type": self.normalize_word_type(token),
                    "exists": token["exists"],
                    "roles": [
                        role
                        for role, active in {
                            "subject": subject and token["id"] == subject["id"],
                            "action": main_action and token["id"] == main_action["id"],
                            "object": object_token and token["id"] == object_token["id"],
                            "modifier": self.is_modifier_like(token),
                            "preposition": token.get("is_preposition"),
                            "question": token.get("is_question_word")
                        }.items()
                        if active
                    ]
                }
                for token in tokens
            ],
            "edges": edges[:120],
            "meaning_frame": meaning_frame,
            "syntax_profile": syntax_profile,
            "confidence": graph_confidence,
            "rules": [
                "Connect sentence order for content words.",
                "Infer subject/action/object with nearest noun and verb heuristics.",
                "Connect modifiers to nearby nouns.",
                "Connect noun compounds and joined noun lists.",
                "Connect prepositional phrases as relation edges.",
                "Add semantic edges when two sentence words are connected in UnderstandingDk.",
                "Use word types from the dictionary to separate actions, objects, modifiers, and relations."
            ]
        }

    # ---------- topic/intent ----------

    def score_rules(self, text, words, rules):

        lowered = text.lower()
        word_set = set(words)
        scores = {}
        hits = {}

        for name, keywords in rules.items():
            score = 0
            matched = []

            for keyword in keywords:
                keyword_lower = keyword.lower()
                if " " in keyword_lower:
                    if keyword_lower in lowered:
                        score += 5
                        matched.append(keyword)
                elif keyword_lower in word_set:
                    score += 3
                    matched.append(keyword)

            if score:
                scores[name] = score
                hits[name] = list(dict.fromkeys(matched))

        return scores, hits

    def detect_topics(self, text, words, word_reports):

        scores, hits = self.score_rules(text, words, DOMAIN_RULES)
        lowered = text.lower()
        word_set = set(words)

        if (
            re.search(r"\d|\bx\b", lowered)
            and (
                "=" in lowered
                or "^" in lowered
                or "**" in lowered
                or any(term in lowered for term in ["solve", "calculate", "step by step"])
            )
        ):
            scores["math"] = scores.get("math", 0) + 18
            hits.setdefault("math", []).append("math_expression")

        if self.has_code_payload(text):
            scores["code"] = scores.get("code", 0) + 14
            hits.setdefault("code", []).append("code_payload")

        if (
            "capital" in word_set
            or "located" in word_set
            or "where" in word_set
            or any(term in lowered for term in ["where is", "capital of", "located in"])
        ):
            scores["geography"] = scores.get("geography", 0) + 10
            hits.setdefault("geography", []).append("geography_context")

        for report in word_reports:
            for connection in report.get("connections", [])[:8]:
                connection = str(connection).lower()
                for domain, keywords in DOMAIN_RULES.items():
                    if connection in keywords:
                        scores[domain] = scores.get(domain, 0) + 0.25
                        hits.setdefault(domain, []).append(f"related:{connection}")

        if not scores:
            return "general", {}, {}

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        main_topic = sorted_scores[0][0]

        total = max(sum(scores.values()), 1)
        topic_confidence = {
            topic: round((score / total) * 100, 2)
            for topic, score in sorted_scores[:8]
        }

        return main_topic, topic_confidence, hits

    def detect_intent(self, text, words, main_topic):

        scores, hits = self.score_rules(text, words, INTENT_RULES)
        lowered = text.lower().strip()

        code_analysis_markers = [
            "analyze this code",
            "analyze code",
            "explain this code",
            "explain code",
            "what does this code do",
            "what this code does",
            "review this code"
        ]

        if self.has_code_payload(text) and any(marker in lowered for marker in code_analysis_markers):
            scores["code_analysis"] = scores.get("code_analysis", 0) + 18
            hits.setdefault("code_analysis", []).append("code_payload_analysis_request")

        if lowered in {"hello", "hi", "hey", "shalom", "שלום", "היי", "הי"}:
            scores["greeting"] = scores.get("greeting", 0) + 10

        if "?" in text:
            scores["question"] = scores.get("question", 0) + 4

        if main_topic == "code" and any(
            term in lowered
            for term in ["code", "program", "python", "runnable", "working", "implement", "function", "class", "version"]
        ):
            scores["code_generation"] = scores.get("code_generation", 0) + 8

        if main_topic == "code" and (
            self.has_code_payload(text)
            or any(term in lowered for term in ["this code", "the code", "pasted code", "following code"])
        ) and any(
            term in lowered
            for term in ["analyze", "explain", "review", "what does this code"]
        ):
            scores["code_analysis"] = scores.get("code_analysis", 0) + 10

        if main_topic == "game" and "code" not in lowered:
            scores["game_design"] = scores.get("game_design", 0) + 4

        if not scores:
            return "request", 45, {}

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        intent = sorted_scores[0][0]
        total = max(sum(scores.values()), 1)
        confidence = round((sorted_scores[0][1] / total) * 100, 2)

        return intent, confidence, hits

    def is_dictionary_query(self, text):

        lowered = text.lower()

        for marker in DICTIONARY_QUERY_MARKERS:
            if " " in marker:
                pattern = r"(?<![a-z0-9])" + re.escape(marker) + r"(?![a-z0-9])"
            else:
                pattern = r"(?<![a-z0-9])" + re.escape(marker) + r"(?![a-z0-9])"

            if re.search(pattern, lowered):
                return True

        return False

    def infer_action_intent(
        self,
        action_word,
        text,
        words,
        main_topic,
        current_intent
    ):

        lowered = text.lower()
        word_set = set(words)

        story_terms = {
            "story", "stories", "chapter", "character", "plot",
            "scene", "dialogue", "sentences", "sentence"
        }
        code_terms = {
            "code", "program", "python", "javascript", "java",
            "function", "class", "api", "terminal", "runnable"
        }
        game_terms = {
            "game", "rpg", "player", "enemy", "inventory", "combat"
        }
        image_terms = {
            "image", "picture", "photo", "illustration", "poster",
            "logo", "icon", "draw", "concept", "visual", "art"
        }

        has_story = main_topic == "story" or bool(story_terms & word_set)
        has_code = main_topic == "code" or bool(code_terms & word_set)
        has_game = main_topic == "game" or bool(game_terms & word_set)
        has_image = main_topic == "image_generation" or bool(image_terms & word_set)

        if action_word in {"translate"}:
            return "translation"

        if action_word in {"solve", "calculate"}:
            return "math"

        if action_word == "do":
            if has_code:
                return "code_generation"
            if has_image:
                return "image_generation"
            if has_story:
                return "story_creation"
            if has_game:
                return "game_design"
            return "request"

        if action_word in {"analyze", "review"}:
            if has_code or self.has_code_payload(text):
                return "code_analysis"
            return "question"

        if action_word in {"plan"}:
            return "planning"

        if action_word in {"fix", "correct", "improve", "upgrade", "add"}:
            if has_code:
                return "code_generation"
            return "request"

        if action_word in {"explain", "tell", "show", "give", "help"}:
            if self.has_code_payload(text) or any(
                marker in lowered
                for marker in ["this code", "the code", "pasted code", "following code"]
            ):
                return "code_analysis"
            return "question"

        if action_word in {"write", "create", "make", "generate", "invent", "continue"}:
            if has_image and action_word in {"create", "make", "generate", "invent"}:
                return "image_generation"
            if has_code:
                return "code_generation"
            if has_game and any(term in lowered for term in ["code", "program", "python"]):
                return "code_generation"
            if has_story or action_word == "continue":
                return "story_creation"
            if has_game:
                return "game_design"
            return "creative_generation"

        if action_word in {"draw"}:
            return "image_generation"

        if action_word in {"build", "implement"}:
            if has_code or has_game:
                return "code_generation"
            return "planning"

        return current_intent

    def detect_requested_action(
        self,
        text,
        words,
        word_reports,
        sentence_graph,
        main_topic,
        current_intent
    ):

        lowered = text.lower().strip()
        dictionary_query = self.is_dictionary_query(text)

        tokens = sentence_graph.get(
            "nodes",
            []
        )
        meaning_frame = sentence_graph.get(
            "meaning_frame",
            {}
        )

        action_word = meaning_frame.get(
            "action"
        )

        if not action_word:
            report_by_word = {
                report.get("word"): report
                for report in word_reports
                if isinstance(report, dict)
            }

            for word in words[:16]:
                token_type = str(
                    report_by_word.get(
                        word,
                        {}
                    ).get(
                        "type",
                        ""
                    )
                ).lower()

                if word in ACTION_COMMANDS or "verb" in token_type:
                    action_word = word
                    break

        if not action_word:
            for token in tokens[:16]:
                word = token.get(
                    "word"
                )
                if word in ACTION_COMMANDS or "action" in token.get("roles", []):
                    action_word = word
                    break

        if not action_word:
            return {
                "is_action_request": False,
                "dictionary_query": dictionary_query,
                "action_word": None,
                "action_kind": None,
                "target": None,
                "intent_override": None,
                "confidence": 35
            }

        action_word = str(action_word).lower()
        action_kind = ACTION_COMMANDS.get(
            action_word
        )

        if not action_kind:
            report_by_word = {
                report.get("word"): report
                for report in word_reports
                if isinstance(report, dict)
            }
            report = report_by_word.get(action_word, {})
            token_type = str(report.get("type", "")).lower()
            if "verb" in token_type:
                action_kind = "perform"

        if not action_kind:
            return {
                "is_action_request": False,
                "dictionary_query": dictionary_query,
                "action_word": action_word,
                "action_kind": None,
                "target": meaning_frame.get("object"),
                "intent_override": None,
                "confidence": 45
            }

        intent_override = self.infer_action_intent(
            action_word,
            text,
            words,
            main_topic,
            current_intent
        )

        if action_kind == "perform" and intent_override == current_intent:
            if current_intent in {"question", "request"}:
                intent_override = "request"

        is_action_request = not dictionary_query or lowered.startswith(action_word)

        confidence = 78
        if lowered.startswith(action_word):
            confidence += 12
        if meaning_frame.get("object"):
            confidence += 6
        if dictionary_query and not lowered.startswith(action_word):
            confidence -= 35

        return {
            "is_action_request": is_action_request,
            "dictionary_query": dictionary_query,
            "action_word": action_word,
            "action_kind": action_kind,
            "target": meaning_frame.get("object"),
            "intent_override": intent_override if is_action_request else None,
            "confidence": max(
                35,
                min(confidence, 96)
            ),
            "rule": "A dictionary verb in an imperative/request sentence is treated as an action to perform, not as a word to define."
        }

    # ---------- advanced whole-sentence tagging ----------

    def extract_token_stream(self, text):

        tokens = []

        for index, match in enumerate(WORD_RE.finditer(text)):
            raw = match.group(0).strip("'")
            if not raw:
                continue

            tokens.append({
                "id": f"t{index}",
                "index": index,
                "text": raw,
                "word": raw.lower(),
                "start": match.start(),
                "end": match.end()
            })

        return tokens

    def is_technical_name(self, raw, word):

        if raw[:1].isupper() and word not in STOP_WORDS:
            return True

        return word in {
            "python", "javascript", "java", "json", "api", "html", "css",
            "sql", "github", "git", "canri", "ai", "cpu", "gpu", "ram"
        }

    def semantic_tag_for_token(self, stream_token, graph_node, word_report, requested_action):

        word = stream_token.get("word", "")
        raw = stream_token.get("text", word)
        dictionary_type = str(word_report.get("type", "unknown") or "unknown").lower()
        normalized_type = str(
            (graph_node or {}).get("normalized_type")
            or self.normalize_word_type({
                "word": word,
                "type": dictionary_type,
                "is_question_word": word in QUESTION_WORDS,
                "is_preposition": word in PREPOSITIONS,
                "is_possessive": word in POSSESSIVES,
                "is_pronoun": word in PRONOUNS,
                "is_stop_word": word in STOP_WORDS,
                "tense": word_report.get("tense")
            })
        )

        roles = list((graph_node or {}).get("roles", []))
        action_word = None
        if isinstance(requested_action, dict):
            action_word = requested_action.get("action_word")

        if word in DETERMINERS:
            semantic_tag = "determiner"
            grammar_role = "specifier"
        elif word in CONJUNCTIONS:
            semantic_tag = "connector"
            grammar_role = "joins_phrases"
        elif word in NEGATIONS:
            semantic_tag = "negation"
            grammar_role = "constraint"
        elif word in PREPOSITIONS:
            semantic_tag = "relation_word"
            grammar_role = "relation"
        elif word in QUESTION_WORDS:
            semantic_tag = "question_focus"
            grammar_role = "question_word"
        elif word in ACTION_COMMANDS:
            semantic_tag = "action_command"
            grammar_role = "requested_action"
        elif "object" in roles:
            semantic_tag = "target_or_concept"
            grammar_role = "object"
        elif normalized_type == "verb" or "verb" in dictionary_type:
            semantic_tag = "action"
            grammar_role = "verb"
        elif self.is_technical_name(raw, word):
            semantic_tag = "proper_or_technical_name"
            grammar_role = "named_entity"
        elif normalized_type == "noun":
            semantic_tag = "target_or_concept"
            grammar_role = "noun"
        elif normalized_type == "adjective":
            semantic_tag = "description"
            grammar_role = "modifier"
        elif normalized_type == "adverb":
            semantic_tag = "action_modifier"
            grammar_role = "modifier"
        elif normalized_type == "pronoun":
            semantic_tag = "participant_reference"
            grammar_role = "pronoun"
        elif normalized_type == "number":
            semantic_tag = "quantity"
            grammar_role = "number"
        elif word in STOP_WORDS:
            semantic_tag = "function_word"
            grammar_role = "function"
        else:
            semantic_tag = "unknown_context_word"
            grammar_role = "unknown"

        is_dictionary_verb = "verb" in dictionary_type
        can_be_user_action = (
            semantic_tag in {"action_command", "action"}
            or is_dictionary_verb
        )
        should_perform = (
            bool(requested_action.get("is_action_request"))
            if isinstance(requested_action, dict)
            else False
        ) and word == action_word

        return {
            "index": stream_token.get("index"),
            "word": word,
            "text": raw,
            "dictionary_type": dictionary_type,
            "normalized_type": normalized_type,
            "semantic_tag": semantic_tag,
            "grammar_role": grammar_role,
            "sentence_roles": roles,
            "known_word": bool(word_report.get("exists")),
            "is_dictionary_verb": is_dictionary_verb,
            "can_be_user_action": can_be_user_action,
            "should_perform_as_command": should_perform,
            "tense": word_report.get("tense"),
            "definition_hint": (word_report.get("meanings") or [None])[0],
            "connection_hints": word_report.get("connections", [])[:6]
        }

    def build_phrase_chunks(self, tags):

        chunks = []
        current = []

        noun_phrase_tags = {
            "determiner",
            "description",
            "proper_or_technical_name",
            "target_or_concept",
            "quantity"
        }

        def flush():
            if not current:
                return
            words = [item["word"] for item in current]
            head = None
            for item in reversed(current):
                if item["semantic_tag"] in {"target_or_concept", "proper_or_technical_name"}:
                    head = item["word"]
                    break
            chunks.append({
                "type": "noun_phrase",
                "text": " ".join(words),
                "head": head or words[-1],
                "tokens": words,
                "start_index": current[0]["index"],
                "end_index": current[-1]["index"]
            })
            current.clear()

        for tag in tags:
            if tag["semantic_tag"] in noun_phrase_tags:
                current.append(tag)
            else:
                flush()

                if tag["semantic_tag"] in {"action_command", "action"}:
                    chunks.append({
                        "type": "action_phrase",
                        "text": tag["word"],
                        "head": tag["word"],
                        "tokens": [tag["word"]],
                        "start_index": tag["index"],
                        "end_index": tag["index"]
                    })

        flush()

        return chunks[:80]

    def build_semantic_frame(self, tags, phrase_chunks, requested_action, sentence_graph):

        actions = [
            tag
            for tag in tags
            if tag.get("can_be_user_action")
        ]
        targets = [
            tag
            for tag in tags
            if tag.get("semantic_tag") in {"target_or_concept", "proper_or_technical_name"}
        ]
        modifiers = [
            tag
            for tag in tags
            if tag.get("semantic_tag") in {"description", "action_modifier", "quantity", "negation"}
        ]
        relations = [
            tag
            for tag in tags
            if tag.get("semantic_tag") in {"relation_word", "connector"}
        ]

        meaning_frame = sentence_graph.get("meaning_frame", {})
        requested = requested_action if isinstance(requested_action, dict) else {}

        return {
            "main_action": requested.get("action_word") or meaning_frame.get("action"),
            "main_target": requested.get("target") or meaning_frame.get("object"),
            "subject": meaning_frame.get("subject"),
            "question_focus": meaning_frame.get("question_focus"),
            "actions": [
                {
                    "word": tag["word"],
                    "semantic_tag": tag["semantic_tag"],
                    "should_perform": tag["should_perform_as_command"]
                }
                for tag in actions[:20]
            ],
            "targets": [tag["word"] for tag in targets[:30]],
            "modifiers": [tag["word"] for tag in modifiers[:30]],
            "relations": [tag["word"] for tag in relations[:30]],
            "phrase_chunks": phrase_chunks[:40],
            "command_interpretation": {
                "is_action_request": requested.get("is_action_request", False),
                "action_word": requested.get("action_word"),
                "action_kind": requested.get("action_kind"),
                "intent_override": requested.get("intent_override"),
                "rule": "Any dictionary word with type verb can become a user action when the sentence context is a request."
            }
        }

    def build_advanced_understanding(self, text, word_reports, sentence_graph, requested_action):

        stream = self.extract_token_stream(text)
        report_by_word = {
            report.get("word"): report
            for report in word_reports
            if isinstance(report, dict)
        }
        node_by_index = {
            node.get("index"): node
            for node in sentence_graph.get("nodes", [])
            if isinstance(node, dict)
        }

        tags = []
        for stream_token in stream[:160]:
            word = stream_token.get("word")
            word_report = report_by_word.get(word) or self.analyze_word(word)
            graph_node = node_by_index.get(stream_token.get("index"))
            tags.append(
                self.semantic_tag_for_token(
                    stream_token,
                    graph_node,
                    word_report,
                    requested_action
                )
            )

        phrase_chunks = self.build_phrase_chunks(tags)
        semantic_frame = self.build_semantic_frame(
            tags,
            phrase_chunks,
            requested_action,
            sentence_graph
        )

        return {
            "tokens": tags,
            "phrase_chunks": phrase_chunks,
            "semantic_frame": semantic_frame,
            "coverage": {
                "tokens_seen": len(stream),
                "tokens_tagged": len(tags),
                "known_words": sum(1 for tag in tags if tag.get("known_word")),
                "actions_found": sum(1 for tag in tags if tag.get("can_be_user_action")),
                "targets_found": sum(
                    1
                    for tag in tags
                    if tag.get("semantic_tag") in {"target_or_concept", "proper_or_technical_name"}
                )
            },
            "rules": [
                "Tag every word by dictionary type, grammar role, and sentence role.",
                "Read the whole sentence before deciding what each word means.",
                "Treat dictionary verbs as possible user actions.",
                "Treat capitalized or technical words as names when context supports it.",
                "Group nearby determiners, modifiers, and nouns into phrase chunks."
            ]
        }

    # ---------- tasks/entities ----------

    def extract_key_terms(self, words, word_reports):

        counter = Counter()

        for word in words:
            if word not in STOP_WORDS and len(word) > 1:
                counter[word] += 3

        for report in word_reports:
            if report.get("exists") and not report.get("is_stop_word"):
                counter[report["word"]] += 3
            for connection in report.get("connections", [])[:6]:
                connection = str(connection).lower()
                if connection not in STOP_WORDS and len(connection) > 2:
                    counter[connection] += 1

        return [
            term
            for term, _ in counter.most_common(30)
        ]

    def extract_entities(self, original_text):

        entities = []

        for match in re.finditer(r"\b[A-Z][a-zA-Z0-9_#.+-]{2,}\b", original_text):
            value = match.group(0)
            if value.lower() not in STOP_WORDS:
                entities.append({
                    "text": value,
                    "type": "proper_or_technical_term"
                })

        for match in re.finditer(r"\b\d+(?:\.\d+)?\b", original_text):
            entities.append({
                "text": match.group(0),
                "type": "number"
            })

        return entities[:30]

    def detect_requested_features(self, text, words):

        feature_rules = {
            "inventory": ["inventory", "items", "item"],
            "save_load": ["save", "load", "json", "persistence"],
            "command_loop": ["command", "loop", "input"],
            "player_system": ["player", "character", "stats", "hp"],
            "enemy_system": ["enemy", "enemies", "combat", "attack"],
            "planning_first": ["plan", "structure", "steps", "first"],
            "working_version": ["working", "version", "run", "complete"]
        }

        lowered = text.lower()
        word_set = set(words)
        features = []

        for feature, keywords in feature_rules.items():
            if any(keyword in word_set or keyword in lowered for keyword in keywords):
                features.append(feature)

        return features

    def extract_output_constraints(self, text, intent):

        lowered = str(text).lower()
        forbidden = []
        forbidden_rules = {
            "plan": ["do not output a plan", "without a plan", "not a plan"],
            "modules": ["do not output modules", "without modules"],
            "variants": ["do not output variants", "without variants"],
            "helpers": ["do not output helpers", "without helpers"],
            "placeholders": ["do not output placeholders", "without placeholders"],
            "drafts": ["do not output draft", "not a draft", "without draft"],
            "explanation": ["do not output an explanation", "no explanation"],
            "notes": ["do not output notes", "no notes"],
        }

        for name, markers in forbidden_rules.items():
            if any(marker in lowered for marker in markers):
                forbidden.append(name)

        only_output = None
        only_match = re.search(
            r"only\s+output\s+(?:the\s+)?([^\n.!?]{2,100})",
            lowered
        )
        if only_match:
            only_output = only_match.group(1).strip(" ,;:")

        requested_format = OUTPUT_RULES.get(intent, "answer")
        if "code" in str(only_output or "") or any(
            marker in lowered
            for marker in ["code only", "only code", "final working python code"]
        ):
            requested_format = "code"
        elif "table" in lowered:
            requested_format = "table"
        elif "json" in lowered and any(marker in lowered for marker in ["return json", "output json", "as json"]):
            requested_format = "json"
        elif any(marker in lowered for marker in ["bullet list", "as a list", "numbered list"]):
            requested_format = "list"
        elif "step by step" in lowered:
            requested_format = "step_by_step"

        sentence_count = None
        sentence_match = re.search(r"\b(\d+)\s*(?:more\s+)?sentences?\b", lowered)
        if sentence_match:
            sentence_count = int(sentence_match.group(1))

        return {
            "requested_format": requested_format,
            "only_output": only_output,
            "forbidden_sections": forbidden,
            "sentence_count": sentence_count,
            "must_be_runnable": any(
                marker in lowered
                for marker in ["real runnable", "must run", "working program", "working code", "runnable"]
            ),
            "must_be_final": any(
                marker in lowered
                for marker in ["final full", "final working", "only output", "final story", "final answer"]
            ),
            "wants_steps": "step by step" in lowered or "show the steps" in lowered,
        }

    def extract_requirement_clauses(self, text):

        raw = str(text).replace("\r\n", "\n")
        clauses = []
        command_starts = {
            "add", "analyze", "build", "check", "continue", "create",
            "delete", "do", "edit", "explain", "export", "find", "fix",
            "generate", "give", "handle", "include", "keep", "list",
            "load", "make", "mark", "only", "output", "return", "save",
            "search", "show", "solve", "support", "use", "verify", "write"
        }

        def add_clause(value, source="line"):
            normalized = re.sub(r"\s+", " ", str(value)).strip(" .,:;-")
            if len(normalized) < 2:
                return
            key = normalized.lower()
            if any(item["text"].lower() == key for item in clauses):
                return
            clauses.append({
                "text": normalized,
                "source": source
            })

        for line_number, line in enumerate(raw.split("\n"), start=1):
            had_list_marker = bool(re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line))
            cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if not cleaned:
                continue

            lowered = cleaned.lower()
            first_word_match = re.match(r"[a-z]+", lowered)
            first_word = first_word_match.group(0) if first_word_match else ""
            requirement_line = (
                line_number == 1
                or had_list_marker
                or first_word in command_starts
                or " must " in f" {lowered} "
                or " should " in f" {lowered} "
                or "the user can" in lowered
                or "do not" in lowered
                or "without" in lowered
            )
            if not requirement_line:
                continue

            add_clause(cleaned, f"line_{line_number}")

            # Preserve every item in explicit comma/semicolon lists. This is
            # especially important for prompts such as "add, list, search...".
            if "," in cleaned or ";" in cleaned:
                pieces = re.split(r"\s*[,;]\s*|\s+and\s+", cleaned)
                if len(pieces) > 1:
                    for piece in pieces:
                        piece = re.sub(
                            r"^(?:the\s+user\s+can|the\s+program\s+must|must|should)\s+",
                            "",
                            piece,
                            flags=re.IGNORECASE
                        )
                        if 2 <= len(piece.split()) <= 24:
                            add_clause(piece, f"list_item_line_{line_number}")

        if len(clauses) <= 1:
            for sentence_number, sentence in enumerate(
                re.split(r"(?<=[.!?])\s+", raw),
                start=1
            ):
                lowered = sentence.lower()
                if any(
                    marker in lowered
                    for marker in [" must ", " should ", " only output ", " needs to ", " do not "]
                ):
                    add_clause(sentence, f"sentence_{sentence_number}")

        return clauses[:80]

    def extract_detail_inventory(
        self,
        text,
        entities,
        output_constraints,
        advanced_understanding
    ):

        raw = str(text)
        requirement_clauses = self.extract_requirement_clauses(raw)
        semantic_frame = advanced_understanding.get("semantic_frame", {})

        numbers = []
        for match in re.finditer(r"\b\d+(?:\.\d+)?\b", raw):
            line_start = raw.rfind("\n", 0, match.start()) + 1
            before_on_line = raw[line_start:match.start()]
            after_number = raw[match.end():match.end() + 1]
            if not before_on_line.strip() and after_number in {".", ")"}:
                continue
            start = max(0, match.start() - 35)
            end = min(len(raw), match.end() + 35)
            numbers.append({
                "value": match.group(0),
                "context": re.sub(r"\s+", " ", raw[start:end]).strip()
            })

        file_names = list(dict.fromkeys(
            match.group(0)
            for match in re.finditer(
                r"\b[\w.-]+\.(?:jsonl?|py|txt|csv|md|html?|css|js|ts|xml|ya?ml)\b",
                raw,
                flags=re.IGNORECASE
            )
        ))
        quoted_values = list(dict.fromkeys(
            value.strip()
            for match in re.finditer(r"['\"]([^'\"\n]{1,80})['\"]", raw)
            for value in [match.group(1)]
            if value.strip()
        ))
        negative_constraints = [
            item["text"]
            for item in requirement_clauses
            if any(
                marker in item["text"].lower()
                for marker in ["do not", "don't", "never", "without", "no external", "only output"]
            )
        ]

        named_entities = []
        for entity in entities:
            value = str(entity.get("text", "")).strip()
            if not value or value.lower() in ACTION_COMMANDS:
                continue
            if value not in named_entities:
                named_entities.append(value)

        return {
            "explicit_details": requirement_clauses,
            "numbers": numbers[:30],
            "file_names": file_names[:30],
            "quoted_values": quoted_values[:30],
            "named_entities": named_entities[:30],
            "negative_constraints": negative_constraints[:30],
            "actions": semantic_frame.get("actions", [])[:30],
            "targets": semantic_frame.get("targets", [])[:30],
            "modifiers": semantic_frame.get("modifiers", [])[:30],
            "output_constraints": output_constraints,
            "coverage": {
                "explicit_detail_count": len(requirement_clauses),
                "number_count": len(numbers),
                "file_name_count": len(file_names),
                "named_entity_count": len(named_entities),
                "negative_constraint_count": len(negative_constraints)
            }
        }

    def extract_atomic_requirements(self, text, features, output_constraints):

        requirements = []
        seen = set()
        for clause in self.extract_requirement_clauses(text):
            normalized = clause["text"]
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            requirements.append({
                "id": f"explicit_{len(requirements) + 1}",
                "text": normalized,
                "kind": "explicit_constraint",
                "source": clause.get("source", "prompt")
            })

        for feature in features:
            requirements.append({
                "id": f"feature_{feature}",
                "text": f"Implement requested feature: {feature}",
                "kind": "feature",
                "feature": feature
            })

        if output_constraints.get("must_be_runnable"):
            requirements.append({
                "id": "runnable_output",
                "text": "The result must be runnable and complete.",
                "kind": "output_constraint"
            })
        if output_constraints.get("only_output"):
            requirements.append({
                "id": "only_output",
                "text": f"Only return {output_constraints['only_output']}.",
                "kind": "output_constraint"
            })

        unique = []
        ids = set()
        for requirement in requirements:
            if requirement["id"] in ids:
                continue
            ids.add(requirement["id"])
            unique.append(requirement)
        return unique[:80]

    def build_request_contract(
        self,
        text,
        main_topic,
        intent,
        requested_action,
        entities,
        features,
        semantic_frame,
        advanced_understanding
    ):

        lowered = str(text).lower()
        continuation_markers = [
            "continue", "same", "previous", "earlier", "above",
            "improve it", "fix it", "add to it", "that code", "this code",
            "the story", "more sentences", "from the code you just wrote"
        ]
        output_constraints = self.extract_output_constraints(text, intent)
        requirements = self.extract_atomic_requirements(
            text,
            features,
            output_constraints
        )
        detail_inventory = self.extract_detail_inventory(
            text,
            entities,
            output_constraints,
            advanced_understanding
        )

        first_line = next(
            (line.strip() for line in str(text).splitlines() if line.strip()),
            str(text).strip()
        )

        return {
            "action": requested_action.get("action_word") if isinstance(requested_action, dict) else None,
            "action_kind": requested_action.get("action_kind") if isinstance(requested_action, dict) else None,
            "target": (
                requested_action.get("target")
                if isinstance(requested_action, dict)
                else None
            ) or semantic_frame.get("object"),
            "topic": main_topic,
            "intent": intent,
            "entities": entities,
            "features": features,
            "requirements": requirements,
            "output_constraints": output_constraints,
            "global_picture": {
                "goal": first_line[:500],
                "action": requested_action.get("action_word") if isinstance(requested_action, dict) else None,
                "target": (
                    requested_action.get("target")
                    if isinstance(requested_action, dict)
                    else None
                ) or semantic_frame.get("object"),
                "topic": main_topic,
                "intent": intent,
                "requested_format": output_constraints.get("requested_format")
            },
            "detail_inventory": detail_inventory,
            "continuation": {
                "requested": any(marker in lowered for marker in continuation_markers),
                "markers": [marker for marker in continuation_markers if marker in lowered][:8]
            },
            "coverage": {
                "whole_input_analyzed": True,
                "word_count": len(self.extract_words(text)),
                "requirement_count": len(requirements),
                "entity_count": len(entities),
                "feature_count": len(features),
                "small_detail_count": detail_inventory.get("coverage", {}).get(
                    "explicit_detail_count",
                    0
                )
            }
        }

    def possible_tasks(self, main_topic, intent, features, requested_action=None):

        tasks = [intent]

        if isinstance(requested_action, dict) and requested_action.get("is_action_request"):
            action_word = requested_action.get("action_word")
            if action_word:
                tasks.append(f"perform_action_{action_word}")

        if main_topic not in {"general", "unknown"}:
            tasks.append(f"{main_topic}_analysis")

        if intent == "code_generation":
            tasks.extend(["plan_code_structure", "generate_code", "review_code"])

        if intent == "code_analysis":
            tasks.extend(["extract_code", "explain_code", "review_code"])

        if intent in {"story_creation", "creative_generation"}:
            tasks.extend(["generate_final_content", "avoid_dictionary_definition"])

        if intent == "image_generation":
            tasks.extend(["build_image_prompt", "create_image_asset", "check_visual_safety"])

        if "planning_first" in features:
            tasks.append("build_plan_first")

        if "working_version" in features:
            tasks.append("produce_working_draft")

        if "save_load" in features:
            tasks.append("handle_persistence")

        return list(dict.fromkeys(tasks))

    def routing_hints(self, main_topic, intent, features):

        route = ["Memory_brain"]

        if intent in {"question", "research"}:
            route.extend(["Research_brain", "Reasoning_brain"])

        if intent in {"code_generation", "code_analysis"} or main_topic == "code":
            route.extend(["Planner_brain", "Code_brain", "Security_brain"])

        if main_topic == "game":
            route.extend(["Game_brain"])
            if intent == "code_generation":
                route.append("Code_brain")

        if main_topic == "story" or intent == "story_creation":
            route.extend([
                "Creative_brain",
                "Story_brain",
                "Character_brain",
                "World_brain"
            ])

        if main_topic == "creative" or intent in {"game_design", "creative_generation"}:
            route.append("Creative_brain")

        if main_topic == "image_generation" or intent == "image_generation":
            route.extend(["Image_brain", "Creative_brain", "Security_brain"])

        if main_topic in {
            "science", "technology", "geography", "history", "language", "math", "security"
        }:
            route.append(f"{main_topic.capitalize()}_brain")

        route.append("Response_brain")

        return list(dict.fromkeys(route))

    def estimate_confidence(self, words, word_reports, topics, intent_confidence):

        if not words:
            return 20

        known = sum(1 for report in word_reports if report.get("exists"))
        known_ratio = known / max(len(word_reports), 1)
        topic_bonus = 15 if topics else 0
        confidence = (known_ratio * 55) + topic_bonus + min(intent_confidence * 0.3, 30)

        return round(min(max(confidence, 20), 100), 2)

    # ---------- public ----------

    def process(self, data):

        normalized = self.normalize_input(data)
        original_text = normalized["original_text"]
        corrected_text = normalized["corrected_text"]
        text = corrected_text or original_text

        words = self.extract_words(text)
        word_reports = self.analyze_words(words)
        language = self.detect_language(text, words)

        main_topic, topics, topic_hits = self.detect_topics(
            text,
            words,
            word_reports
        )

        intent, intent_confidence, intent_hits = self.detect_intent(
            text,
            words,
            main_topic
        )

        features = self.detect_requested_features(text, words)
        key_terms = self.extract_key_terms(words, word_reports)
        entities = self.extract_entities(original_text)
        sentence_graph = self.build_sentence_graph(words, word_reports)
        syntax_profile = sentence_graph.get(
            "syntax_profile",
            {}
        )

        requested_action = self.detect_requested_action(
            text,
            words,
            word_reports,
            sentence_graph,
            main_topic,
            intent
        )

        if requested_action.get("is_action_request") and requested_action.get("intent_override"):
            intent = requested_action["intent_override"]
            intent_confidence = max(
                intent_confidence,
                requested_action.get(
                    "confidence",
                    60
                )
            )

            if intent == "story_creation":
                main_topic = "story"
            elif intent == "code_generation":
                main_topic = "code"
            elif intent == "code_analysis":
                main_topic = "code"
            elif intent == "translation":
                main_topic = "language"
            elif intent == "math":
                main_topic = "math"
            elif intent == "image_generation":
                main_topic = "image_generation"

        advanced_understanding = self.build_advanced_understanding(
            text,
            word_reports,
            sentence_graph,
            requested_action
        )

        request_contract = self.build_request_contract(
            text,
            main_topic,
            intent,
            requested_action,
            entities,
            features,
            advanced_understanding.get("semantic_frame", {}),
            advanced_understanding
        )

        tasks = self.possible_tasks(
            main_topic,
            intent,
            features,
            requested_action
        )
        output_format = OUTPUT_RULES.get(intent, "answer")
        routes = self.routing_hints(main_topic, intent, features)
        confidence = self.estimate_confidence(
            words,
            word_reports,
            topics,
            intent_confidence
        )

        return {
            "brain": "Understanding_brain",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "original_text": original_text,
            "corrected_text": corrected_text,
            "language": language,
            "main_topic": main_topic,
            "topics": topics,
            "topic_hits": topic_hits,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "intent_hits": intent_hits,
            "key_terms": key_terms,
            "features": features,
            "entities": entities,
            "requested_action": requested_action,
            "request_contract": request_contract,
            "requirements": request_contract.get("requirements", []),
            "output_constraints": request_contract.get("output_constraints", {}),
            "global_picture": request_contract.get("global_picture", {}),
            "detail_inventory": request_contract.get("detail_inventory", {}),
            "advanced_word_tags": advanced_understanding.get(
                "tokens",
                []
            ),
            "phrase_chunks": advanced_understanding.get(
                "phrase_chunks",
                []
            ),
            "semantic_frame": advanced_understanding.get(
                "semantic_frame",
                {}
            ),
            "advanced_understanding": advanced_understanding,
            "sentence_graph": sentence_graph,
            "meaning_frame": sentence_graph.get("meaning_frame", {}),
            "syntax_profile": syntax_profile,
            "word_type_groups": syntax_profile.get(
                "groups",
                {}
            ),
            "graph_confidence": sentence_graph.get("confidence"),
            "words": word_reports,
            "possible_tasks": tasks,
            "output_format": output_format,
            "routing_hints": routes,
            "confidence": confidence,
            "dictionary_ready": self.dictionary_ready,
            "attached_files": normalized.get("attached_files", []),
            "rules": [
                "Use corrected_text as the main input when available.",
                "Use UnderstandingDk for word existence, meanings, grammar, and connections.",
                "Use dictionary word types to understand grammar, not only definitions.",
                "Tag every token with a context-aware grammar role and semantic role.",
                "Build a sentence relation graph so words are connected by meaning, not only split apart.",
                "Treat verbs as requested actions unless the user explicitly asks for a definition.",
                "Use nouns as targets and adjectives/adverbs as constraints or style.",
                "Return a structured report that every specialist brain can consume.",
                "Keep intent, topic, requested features, and routing hints explicit.",
                "Preserve the global goal and every small explicit detail as separate contract data."
            ]
        }


brain = UnderstandingBrain()
