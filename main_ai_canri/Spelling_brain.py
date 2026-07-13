"""
Spelling_brain.py
Canri AI

Context-aware spelling correction using UnderstandingDk:
- main dictionary
- grammar dictionary
- semantic connections dictionary
- conservative edit-distance search
- optional Creative_brain help for ambiguous cases
"""

import json
import re
from pathlib import Path

import UnderstandingDk as dk


COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do",
    "for", "from", "get", "give", "go", "hello", "help", "how", "i", "in",
    "is", "it", "me", "my", "now", "of", "on", "or", "right", "tell",
    "that", "the", "this", "to", "up", "use", "what", "when", "where",
    "who", "why", "will", "with", "you", "your", "canri", "ai", "code",
    "python", "game", "story", "science", "brain", "brains", "create",
    "build", "make", "translate", "explain", "plan", "right"
}

COMMON_CORRECTIONS = {
    "helo": "hello",
    "halo": "hello",
    "hellow": "hello",
    "helow": "hello",
    "wht": "what",
    "wat": "what",
    "whar": "what",
    "whatt": "what",
    "yuo": "you",
    "cn": "can",
    "doo": "do",
    "rigt": "right",
    "rigth": "right",
    "pyton": "python",
    "pyhton": "python",
    "bild": "build",
    "javscript": "javascript",
    "javascrit": "javascript",
    "teh": "the",
    "recieve": "receive",
    "adress": "address",
    "langauge": "language",
    "responce": "response",
    "creativ": "creative",
    "brine": "brain",
    "codeng": "coding"
}

QUESTION_WORDS = {"what", "why", "how", "when", "where", "who"}
AUXILIARY_WORDS = {"can", "do", "does", "did", "will", "would", "should", "could", "is", "are"}
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}

MAX_DEEP_WORDS = 35
MAX_DEEP_CHARS = 320

TECHNICAL_WORDS = {
    "api", "json", "url", "http", "https", "openweathermap", "weather",
    "temperature", "humidity", "condition", "request", "response", "parse",
    "parses", "extract", "extracts", "fetch", "fetches", "online", "invalid",
    "failed", "loop", "command", "beginner", "friendly", "clean", "readable",
    "city", "cities", "data", "displays", "current", "include", "includes"
}

DATA_DIR = Path(__file__).parent / "data"
CODE_TERMS_FILE = DATA_DIR / "Code_terms_dictionary.json"
FUNCTION_CALL_RE = re.compile(
    r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*(?=\()"
)


class SpellingBrain:

    def __init__(self):

        dk.load()
        self.all_words = set(dk.get_all_words())
        self.all_words.update(COMMON_WORDS)
        self.all_words.update(COMMON_CORRECTIONS.values())
        self.code_functions = self.load_code_functions()

        print("Spelling Brain Loaded")

    def load_code_functions(self):

        functions = {}
        if not CODE_TERMS_FILE.exists():
            return functions
        try:
            with CODE_TERMS_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return functions

        for item in data.get("functions", []):
            if not isinstance(item, dict) or not item.get("name"):
                continue
            functions[str(item["name"]).lower()] = item
        return functions

    # ---------- text handling ----------

    def tokenize(self, sentence):

        return re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\w\s]|\s+",
            str(sentence)
        )

    def is_word_token(self, token):

        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(token)))

    def normalize(self, word):

        return str(word).lower().strip()

    def preserve_case(self, original, corrected):

        if original.isupper():
            return corrected.upper()

        if original[:1].isupper():
            return corrected.capitalize()

        return corrected

    def word_exists(self, word):

        lowered = self.normalize(word)

        return (
            lowered in self.all_words
            or lowered in TECHNICAL_WORDS
            or dk.word_exists(lowered)
            or dk.grammar_exists(lowered)
            or dk.detect_tense(lowered) is not None
        )

    # ---------- distance ----------

    def edit_distance(self, left, right, max_distance=3):

        if abs(len(left) - len(right)) > max_distance:
            return max_distance + 1

        previous = list(range(len(right) + 1))

        for i, left_char in enumerate(left, start=1):
            current = [i]
            row_min = current[0]

            for j, right_char in enumerate(right, start=1):
                insert = current[j - 1] + 1
                delete = previous[j] + 1
                replace = previous[j - 1] + (left_char != right_char)
                value = min(insert, delete, replace)
                current.append(value)
                row_min = min(row_min, value)

            if row_min > max_distance:
                return max_distance + 1

            previous = current

        return previous[-1]

    def distance_score(self, word, candidate):

        distance = self.edit_distance(word, candidate, max_distance=3)

        if distance > 3:
            return -100

        score = 70 - distance * 18

        if word[:1] == candidate[:1]:
            score += 8

        if word[-1:] == candidate[-1:]:
            score += 4

        if len(word) == len(candidate):
            score += 4

        return score

    # ---------- candidates ----------

    def candidate_words(self, word):

        lowered = self.normalize(word)
        candidates = set()

        if lowered in COMMON_CORRECTIONS:
            candidates.add(COMMON_CORRECTIONS[lowered])

        if len(lowered) > 18:
            return list(candidates)

        candidates.update(dk.suggest(lowered, limit=8))

        length = len(lowered)
        if 3 <= length <= 12:
            for entry in dk.search_length_range(max(2, length - 1), length + 1)[:500]:
                candidate = str(entry.get("word", "")).lower().strip()
                if not candidate:
                    continue
                if candidate[:1] == lowered[:1] or candidate[-1:] == lowered[-1:]:
                    candidates.add(candidate)

        for word_candidate in COMMON_WORDS:
            if abs(len(word_candidate) - length) <= 2:
                candidates.add(word_candidate)

        return [
            candidate
            for candidate in candidates
            if candidate
            and candidate != lowered
            and self.edit_distance(lowered, candidate, max_distance=3) <= 3
        ][:120]

    def code_function_candidates(self, function_name, sentence):

        lowered = self.normalize(function_name)
        tail = lowered.rsplit(".", 1)[-1]
        sentence_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", sentence.lower()))
        language_hints = set()
        if "python" in sentence_terms or any(marker in sentence for marker in ["def ", "print(", "input("]):
            language_hints.add("python")
        if "javascript" in sentence_terms or any(marker in sentence for marker in ["console.", "const ", "let "]):
            language_hints.add("javascript")

        scored = []
        for key, item in self.code_functions.items():
            candidate_tail = key.rsplit(".", 1)[-1]
            distance = min(
                self.edit_distance(lowered, key, max_distance=3),
                self.edit_distance(tail, candidate_tail, max_distance=3)
            )
            if distance > 3:
                continue

            score = 92 - distance * 20
            if tail[:1] == candidate_tail[:1]:
                score += 9
            if tail[-1:] == candidate_tail[-1:]:
                score += 4
            if len(tail) == len(candidate_tail):
                score += 4
            if item.get("language") in language_hints:
                score += 14
            context_overlap = sentence_terms.intersection(
                str(value).lower()
                for value in item.get("context", [])
            )
            score += min(len(context_overlap) * 7, 21)
            scored.append({
                "name": item.get("name"),
                "language": item.get("language"),
                "category": item.get("category"),
                "distance": distance,
                "score": score,
                "context_overlap": sorted(context_overlap)
            })

        scored.sort(key=lambda item: (item["score"], -item["distance"]), reverse=True)
        return scored[:8]

    def choose_code_function(self, function_name, sentence):

        lowered = self.normalize(function_name)
        if lowered in self.code_functions:
            canonical = str(self.code_functions[lowered].get("name", function_name))
            return {
                "word": canonical,
                "changed": canonical != function_name,
                "reason": (
                    "normalized_known_code_function_case"
                    if canonical != function_name
                    else "known_code_function"
                ),
                "score": 100,
                "candidates": []
            }

        candidates = self.code_function_candidates(function_name, sentence)
        if not candidates:
            return {
                "word": function_name,
                "changed": False,
                "reason": "possible_custom_function",
                "score": 70,
                "candidates": []
            }

        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else {"score": -999}
        confident = (
            best["distance"] <= 2
            and best["score"] >= 68
            and best["score"] - second["score"] >= 7
        )
        if not confident:
            return {
                "word": function_name,
                "changed": False,
                "reason": "ambiguous_or_custom_code_function",
                "score": best["score"],
                "candidates": candidates
            }

        return {
            "word": str(best["name"]),
            "changed": str(best["name"]) != function_name,
            "reason": "contextual_code_function_correction",
            "score": best["score"],
            "candidates": candidates
        }

    def correct_code_function_calls(self, sentence):

        text = str(sentence)
        pieces = []
        corrections = []
        cursor = 0

        for match in FUNCTION_CALL_RE.finditer(text):
            original = match.group(1)
            decision = self.choose_code_function(original, text)
            pieces.append(text[cursor:match.start(1)])
            pieces.append(decision["word"])
            cursor = match.end(1)
            corrections.append({
                "original": original,
                "corrected": decision["word"],
                "changed": decision["changed"],
                "reason": decision["reason"],
                "score": round(decision.get("score", 0), 2),
                "kind": "code_function",
                "top_candidates": [
                    {
                        "word": item["name"],
                        "score": round(item["score"], 2),
                        "distance": item["distance"],
                        "language": item.get("language")
                    }
                    for item in decision.get("candidates", [])[:5]
                ]
            })

        pieces.append(text[cursor:])
        return "".join(pieces), corrections

    def protected_code_spans(self, sentence):

        spans = [(match.start(1), match.end(1)) for match in FUNCTION_CALL_RE.finditer(sentence)]
        spans.extend((match.start(), match.end()) for match in re.finditer(r"`[^`\n]+`", sentence))
        spans.extend((match.start(), match.end()) for match in re.finditer(r"```.*?```", sentence, re.DOTALL))
        return spans

    def token_offsets(self, tokens):

        offsets = []
        cursor = 0
        for token in tokens:
            offsets.append((cursor, cursor + len(token)))
            cursor += len(token)
        return offsets

    # ---------- context scoring ----------

    def context_words(self, word_tokens, index):

        words = []

        for offset, token in enumerate(word_tokens):
            if offset == index:
                continue

            lowered = self.normalize(token)
            if lowered and self.word_exists(lowered):
                words.append(lowered)

        return words

    def local_neighbors(self, word_tokens, index, window=3):

        neighbors = []

        for pos in range(max(0, index - window), min(len(word_tokens), index + window + 1)):
            if pos == index:
                continue
            lowered = self.normalize(word_tokens[pos])
            if lowered:
                neighbors.append(lowered)

        return neighbors

    def semantic_context_score(self, candidate, context_words, neighbors):

        score = 0
        related = set(dk.related(candidate))
        forms = set(dk.get_forms(candidate).values())
        meanings = " ".join(dk.get_meanings(candidate)[:3]).lower()

        for word in context_words:
            if word in related:
                score += 18

            if candidate in dk.related(word):
                score += 14

            if word in forms:
                score += 8

            if word in meanings:
                score += 6

        for neighbor in neighbors:
            if neighbor in related:
                score += 12
            if candidate in dk.related(neighbor):
                score += 10

        return min(score, 70)

    def grammar_context_score(self, candidate, word_tokens, index):

        score = 0
        previous_word = self.normalize(word_tokens[index - 1]) if index > 0 else ""
        next_word = self.normalize(word_tokens[index + 1]) if index + 1 < len(word_tokens) else ""

        entries = dk.search_word(candidate)
        types = {
            str(entry.get("type", "")).lower()
            for entry in entries
            if isinstance(entry, dict)
        }

        if index == 0 and candidate in QUESTION_WORDS:
            score += 35

        if previous_word in QUESTION_WORDS and candidate in AUXILIARY_WORDS:
            score += 25

        if previous_word in AUXILIARY_WORDS and ("verb" in types or candidate in PRONOUNS):
            score += 18

        if candidate in PRONOUNS and (next_word in AUXILIARY_WORDS or "verb" in self.word_types(next_word)):
            score += 16

        if previous_word in {"to", "will", "can", "do", "does", "did"}:
            forms = dk.get_forms(candidate)
            if forms.get("base") == candidate or "verb" in types:
                score += 18

        creation_objects = {
            "game", "code", "system", "project", "app", "website",
            "story", "world", "character", "brain", "file"
        }
        creation_verbs = {
            "build", "create", "make", "generate", "write", "design", "plan"
        }

        if previous_word == "to" and next_word in creation_objects and candidate in creation_verbs:
            score += 45

        if next_word in creation_objects and candidate in creation_verbs:
            score += 25

        if dk.grammar_exists(candidate) or dk.detect_tense(candidate):
            score += 8

        return min(score, 60)

    def word_types(self, word):

        return {
            str(entry.get("type", "")).lower()
            for entry in dk.search_word(word)
            if isinstance(entry, dict)
        }

    def score_candidate(self, original, candidate, word_tokens, index):

        lowered = self.normalize(original)
        context = self.context_words(word_tokens, index)
        neighbors = self.local_neighbors(word_tokens, index)

        score = self.distance_score(lowered, candidate)
        score += self.semantic_context_score(candidate, context, neighbors)
        score += self.grammar_context_score(candidate, word_tokens, index)

        if candidate in COMMON_WORDS:
            score += 8

        if lowered in COMMON_CORRECTIONS and COMMON_CORRECTIONS[lowered] == candidate:
            score += 35

        return score

    def choose_best_candidate(self, word, word_tokens, index):

        lowered = self.normalize(word)

        if lowered in COMMON_CORRECTIONS:
            corrected = self.preserve_case(
                word,
                COMMON_CORRECTIONS[lowered]
            )
            return {
                "word": corrected,
                "changed": corrected != word,
                "reason": "known_typo_with_context_safe_override",
                "score": 120,
                "candidates": [
                    {
                        "candidate": COMMON_CORRECTIONS[lowered],
                        "score": 120,
                        "distance": self.edit_distance(
                            lowered,
                            COMMON_CORRECTIONS[lowered],
                            max_distance=3
                        ),
                        "related": dk.related(COMMON_CORRECTIONS[lowered])[:8],
                        "forms": dk.get_forms(COMMON_CORRECTIONS[lowered])
                    }
                ]
            }

        if self.word_exists(lowered):
            return {
                "word": word,
                "changed": False,
                "reason": "already_valid",
                "score": 100,
                "candidates": []
            }

        candidates = self.candidate_words(lowered)

        if not candidates:
            return {
                "word": word,
                "changed": False,
                "reason": "no_candidate",
                "score": 0,
                "candidates": []
            }

        scored = [
            {
                "candidate": candidate,
                "score": self.score_candidate(lowered, candidate, word_tokens, index),
                "distance": self.edit_distance(lowered, candidate, max_distance=3),
                "related": dk.related(candidate)[:8],
                "forms": dk.get_forms(candidate)
            }
            for candidate in candidates
        ]
        scored.sort(key=lambda item: item["score"], reverse=True)

        best = scored[0]
        second = scored[1] if len(scored) > 1 else {"score": -999}

        confident = (
            best["score"] >= 58
            and best["score"] - second["score"] >= 8
        )

        if not confident:
            return {
                "word": word,
                "changed": False,
                "reason": "ambiguous_context",
                "score": best["score"],
                "candidates": scored[:5]
            }

        corrected = self.preserve_case(word, best["candidate"])

        return {
            "word": corrected,
            "changed": corrected != word,
            "reason": "contextual_best_match",
            "score": best["score"],
            "candidates": scored[:5]
        }

    def ask_creative_for_hint(self, word, word_tokens, candidates=None):

        # Creative help is deliberately optional and lightweight here.
        # Spelling correction must stay deterministic even if Creative_brain is unavailable.
        try:
            from Creative_brain import brain as creative_brain

            return creative_brain.solve_brain_task(
                "Spelling_brain",
                {
                    "problem": f"Find intended word for typo: {word}",
                    "goal": "choose the most context-compatible spelling correction",
                    "context_words": word_tokens,
                    "candidate_words": candidates or [],
                    "understanding": {
                        "original_text": " ".join(word_tokens),
                        "main_topic": "language",
                        "intent": "spelling_correction"
                    }
                },
                "spelling_context_hint"
            )
        except Exception as error:
            return {
                "skipped": True,
                "reason": str(error)
            }

    # ---------- sentence correction ----------

    def fix_sentence(self, sentence):

        code_corrected, code_corrections = self.correct_code_function_calls(sentence)
        tokens = self.tokenize(code_corrected)
        token_offsets = self.token_offsets(tokens)
        protected_spans = self.protected_code_spans(code_corrected)
        word_positions = [
            index
            for index, token in enumerate(tokens)
            if self.is_word_token(token)
        ]
        word_tokens = [
            tokens[index]
            for index in word_positions
        ]

        corrections = list(code_corrections)
        fixed_tokens = list(tokens)

        for word_index, token_index in enumerate(word_positions):
            word = tokens[token_index]
            token_start, token_end = token_offsets[token_index]
            if any(token_start < end and token_end > start for start, end in protected_spans):
                corrections.append({
                    "original": word,
                    "corrected": word,
                    "changed": False,
                    "reason": "protected_code_identifier",
                    "score": 100,
                    "kind": "code_identifier",
                    "top_candidates": []
                })
                continue
            decision = self.choose_best_candidate(
                word,
                word_tokens,
                word_index
            )
            fixed_tokens[token_index] = decision["word"]
            corrections.append({
                "original": word,
                "corrected": decision["word"],
                "changed": decision["changed"],
                "reason": decision["reason"],
                "score": round(decision.get("score", 0), 2),
                "top_candidates": [
                    {
                        "word": item["candidate"],
                        "score": round(item["score"], 2),
                        "distance": item["distance"]
                    }
                    for item in decision.get("candidates", [])[:5]
                ]
            })

        return "".join(fixed_tokens), corrections

    def fix_sentence_fast(self, sentence):

        code_corrected, code_corrections = self.correct_code_function_calls(sentence)
        tokens = self.tokenize(code_corrected)
        token_offsets = self.token_offsets(tokens)
        protected_spans = self.protected_code_spans(code_corrected)
        corrections = list(code_corrections)
        fixed_tokens = list(tokens)

        for index, token in enumerate(tokens):
            if not self.is_word_token(token):
                continue

            token_start, token_end = token_offsets[index]
            if any(token_start < end and token_end > start for start, end in protected_spans):
                corrections.append({
                    "original": token,
                    "corrected": token,
                    "changed": False,
                    "reason": "fast_protected_code_identifier",
                    "score": 100,
                    "kind": "code_identifier",
                    "top_candidates": []
                })
                continue

            lowered = self.normalize(token)
            corrected = COMMON_CORRECTIONS.get(lowered, lowered)
            corrected = self.preserve_case(token, corrected)
            changed = corrected != token

            fixed_tokens[index] = corrected
            corrections.append({
                "original": token,
                "corrected": corrected,
                "changed": changed,
                "reason": "fast_known_typo" if changed else "fast_mode_kept",
                "score": 100 if changed else 95,
                "top_candidates": []
            })

        return "".join(fixed_tokens), corrections

    def process(self, sentence):

        tokens = self.tokenize(sentence)
        word_count = sum(1 for token in tokens if self.is_word_token(token))
        char_count = len(str(sentence))

        if word_count > MAX_DEEP_WORDS or char_count > MAX_DEEP_CHARS:
            corrected, corrections = self.fix_sentence_fast(sentence)
            mode = "fast_long_text"
            mode_reason = (
                f"Long or technical input: {word_count} words, {char_count} characters. "
                "Skipped expensive per-word dictionary candidate search."
            )
        else:
            corrected, corrections = self.fix_sentence(sentence)
            mode = "deep_context"
            mode_reason = "Short enough for full context-aware spelling analysis."

        changed = corrected != sentence

        changed_items = [
            item
            for item in corrections
            if item["changed"]
        ]

        confidence = 95
        if changed_items:
            confidence = round(
                sum(item["score"] for item in changed_items) / len(changed_items),
                2
            )

        return {
            "brain": "Spelling_brain",
            "original_text": sentence,
            "corrected_text": corrected,
            "changed": changed,
            "corrections": corrections,
            "corrections_count": len(corrections),
            "changed_count": len(changed_items),
            "confidence": max(0, min(confidence, 100)),
            "mode": mode,
            "mode_reason": mode_reason,
            "input_size": {
                "words": word_count,
                "characters": char_count
            },
            "skipped_deep_analysis": mode == "fast_long_text",
            "method": {
                "dictionary": "UnderstandingDk main_dictionary.json",
                "connections": "UnderstandingDk Connections_Dictionary.json",
                "grammar": "UnderstandingDk Grammar_dictionary.json",
                "scoring": "edit_distance + semantic_context + grammar_context",
                "creative_fallback": "used only when no candidate or ambiguous context"
            },
            "code_function_dictionary": CODE_TERMS_FILE.name,
            "code_function_calls_detected": sum(
                1 for item in corrections if item.get("kind") == "code_function"
            ),
            "code_function_corrections": [
                item for item in corrections
                if item.get("kind") == "code_function" and item.get("changed")
            ]
        }


brain = SpellingBrain()
