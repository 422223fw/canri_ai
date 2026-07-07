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
        "math", "calculate", "equation", "number", "algebra", "geometry",
        "probability", "מתמטיקה", "חשב", "משוואה", "מספר"
    ],
    "security": [
        "security", "password", "hack", "malware", "token", "encrypt",
        "suicide", "bomb", "אבטחה", "סיסמה", "פצצה", "התאבד"
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
    "planning": "plan",
    "question": "answer",
    "translation": "translation",
    "correction": "corrected_text",
    "research": "sourced_summary",
    "story_creation": "story",
    "game_design": "game_plan"
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
        if "adverb" in token_type or token.get("is_preposition"):
            return False
        if (
            "adjective" in token_type
            and token.get("tense") not in {"past", "past_participle"}
            and not (word.endswith("ed") and len(word) > 4)
        ):
            return False

        base_guess = None
        if word.endswith("ies") and len(word) > 3:
            base_guess = word[:-3] + "y"
        elif word.endswith("es") and len(word) > 3:
            base_guess = word[:-2]
        elif word.endswith("s") and len(word) > 3:
            base_guess = word[:-1]

        base_is_verb = False
        if base_guess and dk:
            entries = dk.search_word(base_guess)
            base_is_verb = any(
                "verb" in str(entry.get("type", "")).lower()
                for entry in entries
                if isinstance(entry, dict)
            )

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
            if self.is_verb_like(token) and token.get("word") not in AUXILIARY_VERBS
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
            if token.get("is_question_word"):
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

        return {
            "nodes": [
                {
                    "id": token["id"],
                    "word": token["word"],
                    "index": token["index"],
                    "type": token["type"],
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
            "confidence": graph_confidence,
            "rules": [
                "Connect sentence order for content words.",
                "Infer subject/action/object with nearest noun and verb heuristics.",
                "Connect modifiers to nearby nouns.",
                "Connect noun compounds and joined noun lists.",
                "Connect prepositional phrases as relation edges.",
                "Add semantic edges when two sentence words are connected in UnderstandingDk."
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
                elif keyword_lower in word_set or keyword_lower in lowered:
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

        if lowered in {"hello", "hi", "hey", "shalom", "שלום", "היי", "הי"}:
            scores["greeting"] = scores.get("greeting", 0) + 10

        if "?" in text:
            scores["question"] = scores.get("question", 0) + 4

        if main_topic == "code" and any(
            term in lowered
            for term in ["code", "working", "implement", "function", "class", "version"]
        ):
            scores["code_generation"] = scores.get("code_generation", 0) + 8

        if main_topic == "game" and "code" not in lowered:
            scores["game_design"] = scores.get("game_design", 0) + 4

        if not scores:
            return "request", 45, {}

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        intent = sorted_scores[0][0]
        total = max(sum(scores.values()), 1)
        confidence = round((sorted_scores[0][1] / total) * 100, 2)

        return intent, confidence, hits

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

    def possible_tasks(self, main_topic, intent, features):

        tasks = [intent]

        if main_topic not in {"general", "unknown"}:
            tasks.append(f"{main_topic}_analysis")

        if intent == "code_generation":
            tasks.extend(["plan_code_structure", "generate_code", "review_code"])

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

        if intent == "code_generation" or main_topic == "code":
            route.extend(["Planner_brain", "Code_brain", "Security_brain"])

        if main_topic == "game":
            route.extend(["Game_brain"])
            if intent == "code_generation":
                route.append("Code_brain")

        if main_topic == "creative" or intent in {"story_creation", "game_design"}:
            route.append("Creative_brain")

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
        tasks = self.possible_tasks(main_topic, intent, features)
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
            "sentence_graph": sentence_graph,
            "meaning_frame": sentence_graph.get("meaning_frame", {}),
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
                "Build a sentence relation graph so words are connected by meaning, not only split apart.",
                "Return a structured report that every specialist brain can consume.",
                "Keep intent, topic, requested features, and routing hints explicit."
            ]
        }


brain = UnderstandingBrain()
