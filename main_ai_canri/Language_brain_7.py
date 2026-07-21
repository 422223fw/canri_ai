"""
Language_brain_7.py
Canri AI

Language Analysis Engine.
Detects language, direction, style, sentence role tags and a semantic frame.
"""

import re


class LanguageAnalysisEngine:

    def __init__(self):
        print("Language Analysis Engine Loaded")
        self.command_verbs = {
            "write", "create", "build", "make", "translate", "explain",
            "analyze", "analyse", "fix", "improve", "solve", "continue",
            "summarize", "summarise", "tell", "give", "show", "compare",
            "check", "generate", "plan", "design",
        }
        self.determiners = {"a", "an", "the", "this", "that", "these", "those"}
        self.prepositions = {"to", "for", "with", "from", "in", "on", "about", "into", "under", "over", "of"}

    def normalize_text(self, text):
        return str(text).strip()

    def count_hebrew_chars(self, text):
        return len(re.findall(r"[\u0590-\u05FF]", str(text)))

    def count_english_chars(self, text):
        return len(re.findall(r"[A-Za-z]", str(text)))

    def count_digits(self, text):
        return len(re.findall(r"\d", str(text)))

    def count_symbols(self, text):
        return len(re.findall(r"[^\w\s\u0590-\u05FFA-Za-z]", str(text)))

    def extract_words(self, text):
        return re.findall(r"[A-Za-z\u0590-\u05FF]+", str(text))

    def tokenize(self, text):
        return re.findall(r"\w+|[^\w\s]", str(text), flags=re.UNICODE)

    def get_languages_data(self, language_data):
        return language_data.get("languages", {})

    def get_models_data(self, language_data):
        return language_data.get("models", {})

    def get_rules_data(self, language_data):
        return language_data.get("rules", {})

    def get_examples_data(self, language_data):
        return language_data.get("examples", [])

    def get_precision_data(self, language_data):
        data = language_data.get("precision_patterns", {})
        return data if isinstance(data, dict) else {}

    def request_action_map(self, language_data):
        actions = self.get_precision_data(language_data).get("request_actions", [])
        return {
            str(item.get("word", "")).lower(): item
            for item in actions
            if isinstance(item, dict) and item.get("word")
        }

    def detect_language_by_chars(self, text):
        hebrew_count = self.count_hebrew_chars(text)
        english_count = self.count_english_chars(text)

        if hebrew_count == 0 and english_count == 0:
            language = "unknown"
            confidence = 0
            reason = "no alphabetic characters"
        elif hebrew_count > 0 and english_count > 0:
            language = "mixed"
            confidence = 60
            reason = "hebrew and english characters found"
        elif hebrew_count > english_count:
            language = "he"
            confidence = 75
            reason = "more hebrew characters"
        else:
            language = "en"
            confidence = 75
            reason = "more english characters"

        return {
            "detected_language": language,
            "method": "character_detection",
            "reason": reason,
            "hebrew_chars": hebrew_count,
            "english_chars": english_count,
            "confidence": confidence,
        }

    def detect_language_from_report(self, report):
        if not isinstance(report, dict):
            return None

        for key in ["language", "detected_language", "source_language"]:
            value = report.get(key)
            if value:
                return value

        nested = report.get("understanding")
        if isinstance(nested, dict):
            for key in ["language", "detected_language", "source_language"]:
                value = nested.get(key)
                if value:
                    return value

        return None

    def detect_language_from_models(self, text, language_data):
        models = self.get_models_data(language_data)
        text_lower = str(text).lower()
        scores = {}

        if not isinstance(models, dict):
            return None

        for language_code, model in models.items():
            if not isinstance(model, dict):
                continue

            score = 0
            for char in model.get("alphabet", []):
                if char and char in text:
                    score += 1

            for word in model.get("common_words", []):
                if str(word).lower() in text_lower.split():
                    score += 5

            if score > 0:
                scores[language_code] = score

        if not scores:
            return None

        return max(scores, key=scores.get)

    def detect_language(self, text, report, language_data):
        from_report = self.detect_language_from_report(report)
        if from_report:
            return {
                "detected_language": from_report,
                "method": "understanding_report",
                "confidence": 90,
            }

        from_models = self.detect_language_from_models(text, language_data)
        if from_models:
            return {
                "detected_language": from_models,
                "method": "language_models",
                "confidence": 85,
            }

        return self.detect_language_by_chars(text)

    def detect_direction(self, language_code, language_data):
        models = self.get_models_data(language_data)
        model = models.get(language_code, {}) if isinstance(models, dict) else {}
        direction = model.get("direction") if isinstance(model, dict) else None

        if direction:
            return direction

        if language_code == "he":
            return "rtl"

        if language_code == "mixed":
            return "mixed"

        return "ltr"

    def detect_alphabet(self, text):
        alphabets = []

        if self.count_hebrew_chars(text):
            alphabets.append("hebrew")
        if self.count_english_chars(text):
            alphabets.append("latin")
        if self.count_digits(text):
            alphabets.append("numbers")
        if self.count_symbols(text):
            alphabets.append("symbols")

        return alphabets or ["unknown"]

    def get_language_model(self, language_code, language_data):
        models = self.get_models_data(language_data)
        return models.get(language_code, {}) if isinstance(models, dict) else {}

    def get_language_name(self, language_code, language_data):
        languages = self.get_languages_data(language_data)

        if isinstance(languages, dict):
            data = languages.get(language_code)
            if isinstance(data, dict):
                return data.get("name", language_code)
            if isinstance(data, str):
                return data

        if isinstance(languages, list):
            for item in languages:
                if isinstance(item, dict) and item.get("code") == language_code:
                    return item.get("name", language_code)

        return language_code

    def detect_formality(self, text):
        text_lower = str(text).lower()
        formal_markers = ["please", "therefore", "however", "would you", "could you", "thank you"]
        informal_markers = ["yo", "bro", "lol", "haha", "חח", "אחי", "סבבה"]
        formal_score = sum(1 for marker in formal_markers if marker in text_lower)
        informal_score = sum(1 for marker in informal_markers if marker in text_lower)

        if formal_score > informal_score:
            style = "formal"
        elif informal_score > formal_score:
            style = "informal"
        else:
            style = "neutral"

        return {
            "style": style,
            "formal_score": formal_score,
            "informal_score": informal_score,
        }

    def detect_text_type(self, text):
        text_str = str(text).strip()

        if not text_str:
            return "empty"
        if text_str.endswith("?"):
            return "question"
        if text_str.endswith("!"):
            return "exclamation"
        if len(text_str.split()) <= 3:
            return "short_phrase"

        return "statement"

    def find_matching_rules(self, text, language_code, language_data):
        rules = self.get_rules_data(language_data)
        results = []

        if not isinstance(rules, dict):
            return results

        all_rules = []
        for key in ["general", language_code]:
            value = rules.get(key, [])
            if isinstance(value, list):
                all_rules.extend(value)

        text_lower = str(text).lower()

        for rule in all_rules:
            if isinstance(rule, dict):
                trigger = rule.get("trigger")
                if trigger and str(trigger).lower() in text_lower:
                    results.append(rule)
            elif isinstance(rule, str) and rule.lower() in text_lower:
                results.append({"rule": rule})

        return results

    def find_related_examples(self, text, language_code, language_data):
        examples = self.get_examples_data(language_data)
        text_words = {word.lower() for word in self.extract_words(text)}
        results = []

        if not isinstance(examples, list):
            return results

        for example in examples:
            if not isinstance(example, dict):
                continue

            example_language = example.get("language")
            if example_language and example_language != language_code:
                continue

            combined = f"{example.get('source', '')} {example.get('target', '')}"
            combined_words = {word.lower() for word in self.extract_words(combined)}
            overlap = text_words.intersection(combined_words)

            if overlap:
                results.append({
                    "example": example,
                    "matched_words": list(overlap),
                    "score": len(overlap),
                })

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:5]

    def extract_report_tags(self, report):
        if not isinstance(report, dict):
            return []

        tags = report.get("advanced_word_tags")
        if isinstance(tags, list):
            return tags

        nested = report.get("understanding")
        if isinstance(nested, dict):
            tags = nested.get("advanced_word_tags")
            if isinstance(tags, list):
                return tags

        return []

    def tag_sentence_roles(self, text, report, language_data=None):
        report_tags = self.extract_report_tags(report)
        if report_tags:
            normalized = []
            for item in report_tags:
                if isinstance(item, dict):
                    normalized.append({
                        "word": item.get("word", ""),
                        "role": item.get("role") or item.get("type") or "unknown",
                        "source": "understanding_report",
                    })
            return normalized

        tags = []
        action_map = self.request_action_map(language_data or {})

        for index, token in enumerate(self.tokenize(text)):
            lower = token.lower()

            if not re.search(r"\w", token, flags=re.UNICODE):
                role = "punctuation"
            elif lower in self.command_verbs or lower in action_map:
                role = "action"
            elif lower in self.determiners:
                role = "determiner"
            elif lower in self.prepositions:
                role = "relation"
            elif re.search(r"\d", token):
                role = "number"
            elif token[:1].isupper() and index > 0:
                role = "name_or_term"
            else:
                role = "content_word"

            tag = {
                "word": token,
                "role": role,
                "source": "language_analysis",
            }
            if lower in action_map:
                tag["action_domain"] = action_map[lower].get("domain")
                tag["action_role"] = action_map[lower].get("role")
            tags.append(tag)

        return tags

    def extract_code_fragments(self, text):
        source = str(text)
        patterns = [
            r"```[\s\S]*?```",
            r"`[^`\n]+`",
            r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*\([^\n()]*\)",
            r"\b[A-Za-z_]\w*\.(?:py|json|jsonl|txt|csv|md|yaml|yml|toml)\b",
            r"(?:^|\s)--?[A-Za-z][\w-]*",
        ]
        values = []
        for pattern in patterns:
            values.extend(match.strip() for match in re.findall(pattern, source))
        return list(dict.fromkeys(value for value in values if value))[:30]

    def extract_quantities(self, text, language_data):
        source = str(text)
        lower = source.lower()
        quantity_words = self.get_precision_data(language_data).get("quantity_words", {})
        word_values = {}
        if isinstance(quantity_words, dict):
            for values in quantity_words.values():
                if isinstance(values, dict):
                    word_values.update({str(key).lower(): value for key, value in values.items()})

        quantities = []
        pattern = re.compile(
            r"\b(?P<value>\d+|[A-Za-z\u0590-\u05FF]+)\s+"
            r"(?P<target>[A-Za-z\u0590-\u05FF][A-Za-z\u0590-\u05FF_-]*(?:\s+[A-Za-z\u0590-\u05FF][A-Za-z\u0590-\u05FF_-]*){0,2})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(source):
            raw_value = match.group("value")
            value = int(raw_value) if raw_value.isdigit() else word_values.get(raw_value.lower())
            if value is None:
                continue
            target_parts = match.group("target").strip().split()
            target = []
            for part in target_parts:
                part_lower = part.lower()
                if target and (
                    part_lower in {"and", "or", "with", "each", "then", "but"}
                    or (re.match(r"[\u0590-\u05FF]", part) and part.startswith("\u05d5"))
                ):
                    break
                target.append(part)
            prefix = lower[max(0, match.start() - 20):match.start()]
            mode = "exact"
            if any(marker in prefix for marker in ["at least", "minimum", "no fewer"]):
                mode = "minimum"
            elif any(marker in prefix for marker in ["at most", "maximum", "no more"]):
                mode = "maximum"
            quantities.append({
                "value": value,
                "raw_value": raw_value,
                "target": " ".join(target),
                "mode": mode,
            })
        return quantities[:30]

    def extract_marker_groups(self, text, mapping):
        lower = str(text).lower()
        results = []
        iterable = mapping.items() if isinstance(mapping, dict) else []
        for group, markers in iterable:
            found = [marker for marker in markers if str(marker).lower() in lower]
            if found:
                results.append({"type": group, "markers": found})
        return results

    def extract_continuation(self, text, language_data):
        groups = self.get_precision_data(language_data).get("continuation_markers", {})
        markers = []
        for values in groups.values() if isinstance(groups, dict) else []:
            markers.extend(values if isinstance(values, list) else [])
        lower = str(text).lower()
        matched = [marker for marker in markers if str(marker).lower() in lower]
        return {
            "is_continuation": bool(matched),
            "markers": list(dict.fromkeys(matched)),
            "must_preserve_previous_result": bool(matched),
        }

    def extract_output_constraints(self, text, language_data):
        mapping = self.get_precision_data(language_data).get("output_markers", {})
        return self.extract_marker_groups(text, mapping)

    def build_semantic_frame(self, tags, text, language_data=None):
        actions = []
        targets = []
        relations = []
        numbers = []

        for tag in tags:
            word = tag.get("word", "")
            role = tag.get("role", "")

            if role in ["action", "verb"]:
                actions.append(word)
            elif role in ["target", "content_word", "name_or_term", "technical_name", "noun", "concept"]:
                targets.append(word)
            elif role in ["relation", "preposition"]:
                relations.append(word)
            elif role == "number":
                numbers.append(word)

        lower = str(text).lower()
        requested_output = "answer"

        if "code" in lower or "program" in lower:
            requested_output = "code"
        elif "story" in lower:
            requested_output = "story"
        elif "translate" in lower:
            requested_output = "translation"
        elif "step by step" in lower or "solve" in lower:
            requested_output = "solution"

        language_data = language_data or {}
        precision = self.get_precision_data(language_data)
        quantified_constraints = self.extract_quantities(text, language_data)
        explicit_constraints = self.extract_marker_groups(
            text,
            precision.get("constraint_markers", {}),
        )
        continuation = self.extract_continuation(text, language_data)
        output_constraints = self.extract_output_constraints(text, language_data)
        code_fragments = self.extract_code_fragments(text)

        return {
            "actions": list(dict.fromkeys(actions)),
            "targets": list(dict.fromkeys(targets))[:30],
            "relations": list(dict.fromkeys(relations)),
            "numbers": numbers,
            "requested_output": requested_output,
            "is_action_request": bool(actions),
            "quantified_constraints": quantified_constraints,
            "explicit_constraints": explicit_constraints,
            "continuation": continuation,
            "output_constraints": output_constraints,
            "code_fragments": code_fragments,
            "detail_count": (
                len(quantified_constraints)
                + len(explicit_constraints)
                + len(output_constraints)
                + len(code_fragments)
            ),
        }

    def build_context_links(self, tags):
        useful = [
            tag for tag in tags
            if tag.get("role") not in ["punctuation", "determiner"]
        ]
        links = []

        for left, right in zip(useful, useful[1:]):
            links.append({
                "from": left.get("word"),
                "to": right.get("word"),
                "relation": "sentence_neighbor",
            })

        return links[:40]

    def calculate_complexity(self, text, tags):
        word_count = len([tag for tag in tags if tag.get("role") != "punctuation"])
        clauses = len(re.findall(r"[,;:]|\band\b|\bbut\b|\bbecause\b", str(text).lower()))

        if word_count <= 5:
            level = "simple"
        elif word_count <= 18 and clauses <= 2:
            level = "medium"
        else:
            level = "complex"

        return {
            "word_count": word_count,
            "clause_markers": clauses,
            "level": level,
        }

    def calculate_confidence(self, language_result, alphabet, model, rules, examples, semantic_frame):
        confidence = language_result.get("confidence", 0)

        if alphabet and alphabet != ["unknown"]:
            confidence += 5
        if model:
            confidence += 10
        if rules:
            confidence += 5
        if examples:
            confidence += 5
        if semantic_frame.get("actions") or semantic_frame.get("targets"):
            confidence += 5

        return min(confidence, 100)

    def analyze(self, text, report, language_data):
        text = self.normalize_text(text)
        language_result = self.detect_language(text, report, language_data)
        language_code = language_result.get("detected_language", "unknown")
        direction = self.detect_direction(language_code, language_data)
        alphabet = self.detect_alphabet(text)
        model = self.get_language_model(language_code, language_data)
        language_name = self.get_language_name(language_code, language_data)
        formality = self.detect_formality(text)
        text_type = self.detect_text_type(text)
        rules = self.find_matching_rules(text, language_code, language_data)
        examples = self.find_related_examples(text, language_code, language_data)
        word_tags = self.tag_sentence_roles(text, report, language_data)
        semantic_frame = self.build_semantic_frame(word_tags, text, language_data)
        context_links = self.build_context_links(word_tags)
        complexity = self.calculate_complexity(text, word_tags)
        confidence = self.calculate_confidence(
            language_result,
            alphabet,
            model,
            rules,
            examples,
            semantic_frame,
        )

        return {
            "engine": "LanguageAnalysisEngine",
            "input_text": text,
            "detected_language": language_code,
            "language_name": language_name,
            "detection": language_result,
            "writing_direction": direction,
            "alphabet": alphabet,
            "language_model": model,
            "formality": formality,
            "text_type": text_type,
            "matched_rules": rules,
            "related_examples": examples,
            "word_tags": word_tags,
            "semantic_frame": semantic_frame,
            "context_links": context_links,
            "complexity": complexity,
            "scanner_evidence_count": len(language_data.get("scanner_evidence", [])),
            "confidence": confidence,
        }


engine = LanguageAnalysisEngine()
