"""
Manager_brain.py
Canri AI

The manager is the internal orchestrator:
- understands which brains should work on a request
- builds a phased execution plan
- passes Understanding + Memory context to every brain
- records errors, missing brains, confidence, and next steps
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from Brain_runtime import brain_runtime
from Brain_storage import load_json_resilient

try:
    from Data_context import (
        build_shared_data_context,
        context_view_for_brain,
        search_data_context
    )
except Exception:
    build_shared_data_context = None
    context_view_for_brain = None
    search_data_context = None

try:
    from Knowledge_collector import (
        enqueue_knowledge_topics,
        search_knowledge,
        text_terms
    )
except Exception:
    enqueue_knowledge_topics = None
    search_knowledge = None
    text_terms = None

try:
    from Scanner_knowledge import search_scanner_knowledge
except Exception:
    search_scanner_knowledge = None

try:
    from UnderstandingDk import (
        get_forms as dk_get_forms,
        get_meanings as dk_get_meanings,
        grammar_exists as dk_grammar_exists,
        related as dk_related,
        search_word as dk_search_word,
        suggest as dk_suggest,
        word_exists as dk_word_exists
    )
except Exception:
    dk_get_forms = None
    dk_get_meanings = None
    dk_grammar_exists = None
    dk_related = None
    dk_search_word = None
    dk_suggest = None
    dk_word_exists = None


DATA_DIR = Path(__file__).parent / "data"
COMPANY_PRODUCTS_FILE = DATA_DIR / "Company_products.json"


ALWAYS_AVAILABLE_SAFETY_BRAINS = [
    "Emotion_brain",
    "Security_brain"
]

REQUEST_TIME_BUDGET_SECONDS = None
DEFAULT_BRAIN_SOFT_TIMEOUT_SECONDS = None
MAX_QUALITY_RETRIES_PER_BRAIN = 20
MAX_COLLABORATION_PARTICIPANTS = 5
MAX_CENTRAL_DOMAINS = 4


class ManagerBrain:

    def __init__(self):

        self.brains = {}
        self.execution_history = []
        self._request_started = None
        self._request_deadline = None
        self._retry_counts = {}
        self._active_brain_stack = []
        self._runtime_events = []
        self._request_id = None
        self.registry_health = {}
        self.company_products = self.load_json(COMPANY_PRODUCTS_FILE, {})

        print("Manager Brain Loaded")

    def load_json(self, path, default):
        return load_json_resilient(path, default=default)

    # ---------- registration ----------

    def register_brain(self, name, brain_object):

        if not name or brain_object is None:
            return

        self.brains[name] = brain_object
        self.registry_health[name] = brain_runtime.validate_registration(
            name,
            brain_object
        )

    # ---------- report extraction ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "unknown",
                "intent": "unknown"
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            report = dict(understanding)
            for key in [
                "original_text",
                "corrected_text",
                "text",
                "goal",
                "prompt"
            ]:
                if not report.get(key) and data.get(key):
                    report[key] = data[key]
            return report

        if (
            "main_topic" in data
            or "intent" in data
            or "words" in data
        ):
            return data

        return {}

    def get_memory_report(self, data):

        if not isinstance(data, dict):
            return {}

        memory = data.get("memory")

        if isinstance(memory, dict):
            return memory

        return {}

    def collect_terms(self, report, memory_report):

        terms = []

        for key in ["main_topic", "intent", "language", "target_language"]:
            value = report.get(key)
            if value and value != "unknown":
                terms.append(str(value).lower())

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            terms.extend(str(topic).lower() for topic in topics)

        for task in report.get("possible_tasks", []):
            terms.append(str(task).replace("_", " ").lower())

        requested_action = report.get("requested_action", {})
        if isinstance(requested_action, dict):
            for key in ["action_word", "action_kind", "target", "intent_override"]:
                value = requested_action.get(key)
                if value:
                    terms.append(str(value).replace("_", " ").lower())

        word_type_groups = report.get("word_type_groups", {})
        if isinstance(word_type_groups, dict):
            for group_name, group_words in word_type_groups.items():
                if group_name in {"verbs", "nouns", "adjectives", "adverbs"}:
                    terms.append(str(group_name).replace("_", " ").lower())
                    terms.extend(
                        str(word).lower()
                        for word in group_words[:12]
                    )

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            word = word_data.get("word")
            if word:
                terms.append(str(word).lower())

            for connection in word_data.get("connections", [])[:8]:
                terms.append(str(connection).lower())

        meaning_frame = report.get("meaning_frame", {})
        if isinstance(meaning_frame, dict):
            for key in ["subject", "action", "object", "question_focus"]:
                value = meaning_frame.get(key)
                if value:
                    terms.append(str(value).lower())
            terms.extend(
                str(term).lower()
                for term in meaning_frame.get("content_terms", [])[:20]
            )

        semantic_frame = report.get("semantic_frame", {})
        if isinstance(semantic_frame, dict):
            for key in ["main_action", "main_target", "subject", "question_focus"]:
                value = semantic_frame.get(key)
                if value:
                    terms.append(str(value).lower())

            for list_key in ["targets", "modifiers", "relations"]:
                values = semantic_frame.get(list_key, [])
                if isinstance(values, list):
                    terms.extend(str(value).lower() for value in values[:20])

            for action in semantic_frame.get("actions", [])[:12]:
                if isinstance(action, dict) and action.get("word"):
                    terms.append(str(action["word"]).lower())

            for chunk in semantic_frame.get("phrase_chunks", [])[:15]:
                if isinstance(chunk, dict):
                    if chunk.get("text"):
                        terms.append(str(chunk["text"]).lower())
                    if chunk.get("head"):
                        terms.append(str(chunk["head"]).lower())

        for tag in report.get("advanced_word_tags", [])[:60]:
            if not isinstance(tag, dict):
                continue
            word = tag.get("word")
            if word:
                terms.append(str(word).lower())
            semantic_tag = tag.get("semantic_tag")
            if semantic_tag in {"action_command", "action", "target_or_concept", "proper_or_technical_name"}:
                terms.append(str(semantic_tag).replace("_", " ").lower())

        sentence_graph = report.get("sentence_graph", {})
        if isinstance(sentence_graph, dict):
            for edge in sentence_graph.get("edges", [])[:30]:
                if not isinstance(edge, dict):
                    continue
                for key in ["from_word", "relation", "to_word"]:
                    value = edge.get(key)
                    if value:
                        terms.append(str(value).replace("_", " ").lower())

        for keyword in memory_report.get("current_keywords", [])[:20]:
            terms.append(str(keyword).lower())

        return list(dict.fromkeys(term for term in terms if term))

    def extract_query_text(self, original_data, report, memory_report):

        parts = []

        if isinstance(original_data, str):
            parts.append(original_data)

        if isinstance(original_data, dict):
            for key in [
                "original_text",
                "corrected_text",
                "text",
                "goal",
                "prompt",
                "question"
            ]:
                if original_data.get(key):
                    parts.append(str(original_data[key]))

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:
            if report.get(key):
                parts.append(str(report[key]))

        parts.extend(self.collect_terms(report, memory_report)[:25])

        return " ".join(parts).strip()

    def build_knowledge_context(self, original_data, report, memory_report):

        query = self.extract_query_text(
            original_data,
            report,
            memory_report
        )

        context = {
            "query": query,
            "matches": [],
            "available": False,
            "source": "unified_scanner_indexes",
            "queue_update": {}
        }

        if not query or (search_scanner_knowledge is None and search_knowledge is None):
            return context

        if enqueue_knowledge_topics:
            try:
                context["queue_update"] = enqueue_knowledge_topics(
                    query,
                    max_topics=8
                )
            except Exception as error:
                context["queue_update"] = {
                    "error": str(error)
                }

        try:
            if search_scanner_knowledge is not None:
                matches = search_scanner_knowledge(query, limit=12)
            else:
                matches = search_knowledge(query, limit=6)
        except Exception as error:
            context["error"] = str(error)
            return context

        context["matches"] = matches
        context["available"] = bool(matches)
        context["match_count"] = len(matches)

        if text_terms:
            try:
                context["query_terms"] = text_terms(query, limit=30)
            except Exception:
                context["query_terms"] = []

        return context

    def build_scanner_view(self, knowledge, brain_name):
        """Provide every brain a small relevant evidence pack, never the full database."""

        factual_brains = {
            "Research_brain", "Fact_Check_brain", "Reasoning_brain", "Science_brain",
            "Geography_brain", "History_brain", "Technology_brain", "Learning_brain",
            "Quality_Control_brain", "Collaboration_brain"
        }
        preferred_collections = {
            "Code_brain": {"code", "general", "trusted_knowledge"},
            "Technology_brain": {"code", "product", "general", "trusted_knowledge"},
            "Science_brain": {"general", "trusted_knowledge", "product"},
            "Math_brain": {"general", "trusted_knowledge", "code"},
            "History_brain": {"general", "trusted_knowledge"},
            "Geography_brain": {"general", "trusted_knowledge", "product"},
            "Language_brain": {"general", "trusted_knowledge", "code", "product"},
            "Story_brain": {"general", "trusted_knowledge", "product"},
            "Emotion_brain": {"general", "trusted_knowledge"},
            "Planner_brain": {"general", "trusted_knowledge", "product", "code"},
            "Reasoning_brain": {"general", "trusted_knowledge", "product", "code"},
            "Research_brain": {"general", "trusted_knowledge", "product", "code"},
            "Fact_Check_brain": {"general", "trusted_knowledge", "product", "code"},
            "Creative_brain": {"product", "general", "code", "trusted_knowledge"},
            "Understanding_brain": {"product", "general", "code", "trusted_knowledge"},
        }
        raw_matches = []
        if isinstance(knowledge, dict):
            raw_matches = [
                item for item in knowledge.get("matches", [])
                if isinstance(item, dict)
            ]
        wanted = preferred_collections.get(brain_name)
        if wanted:
            ordered = [
                item for item in raw_matches if item.get("collection", "trusted_knowledge") in wanted
            ]
            ordered.extend(item for item in raw_matches if item not in ordered)
        else:
            ordered = raw_matches

        matches = []
        for item in ordered[:8]:
                if not isinstance(item, dict):
                    continue
                matches.append({
                    "article_id": item.get("article_id"),
                    "record_id": item.get("record_id"),
                    "collection": item.get("collection", "trusted_knowledge"),
                    "title": item.get("title"),
                    "summary": str(item.get("summary", ""))[:700],
                    "content_excerpt": str(item.get("content_excerpt", ""))[:1400],
                    "trust_score": item.get("trust_score", 0),
                    "score": item.get("score", 0),
                    "source_count": item.get("source_count", 0),
                    "sources": item.get("sources", [])[:3],
                    "url": item.get("url"),
                    "source_type": item.get("source_type"),
                    "metadata": item.get("metadata", {})
                })

        required = bool(matches) and brain_name not in {
            "Memory_brain", "Security_brain", "Response_brain"
        }
        return {
            "brain": brain_name,
            "available": bool(matches),
            "required_for_answer": required,
            "matches": matches,
            "retrieval": "indexed_jsonl_excerpt",
            "policy": (
                "Use relevant scanner evidence and preserve its sources. Separate evidence from inference."
                if brain_name in factual_brains else
                "Consider the relevant scanner excerpts before producing the specialist result; "
                "use them when they improve accuracy and ignore unrelated evidence."
            )
        }

    def build_dictionary_context(self, original_data, report, memory_report):

        query = self.extract_query_text(
            original_data,
            report,
            memory_report
        )
        words = re.findall(
            r"[A-Za-z][A-Za-z0-9\-]{1,}",
            query.lower()
        )
        terms = list(dict.fromkeys(
            words + self.collect_terms(report, memory_report)
        ))[:35]

        context = {
            "query": query,
            "entries": [],
            "suggestions": {},
            "company_matches": [],
            "product_matches": [],
            "available": False,
            "source": "UnderstandingDk + Company_products"
        }

        for term in terms:
            if not term or len(term) < 2:
                continue

            if dk_word_exists and dk_word_exists(term):
                meanings = dk_get_meanings(term) if dk_get_meanings else []
                related = dk_related(term) if dk_related else []
                forms = (
                    dk_get_forms(term)
                    if dk_grammar_exists and dk_grammar_exists(term) and dk_get_forms
                    else {}
                )
                entries = dk_search_word(term) if dk_search_word else []
                word_type = entries[0].get("type") if entries else None

                context["entries"].append({
                    "word": term,
                    "type": word_type,
                    "meanings": meanings[:3],
                    "connections": related[:10],
                    "forms": forms
                })
            elif dk_suggest:
                suggestions = dk_suggest(term, limit=4)
                if suggestions:
                    context["suggestions"][term] = suggestions

        product_data = self.company_products or {}
        companies = product_data.get("companies", {})
        products = product_data.get("products", {})
        lowered_query = query.lower()

        def name_in_query(name):
            clean = str(name).strip().lower()
            if not clean:
                return False
            pattern = r"(?<![a-z0-9])" + re.escape(clean) + r"(?![a-z0-9])"
            return re.search(pattern, lowered_query) is not None

        for company_id, company in companies.items():
            names = [
                company_id,
                company.get("name", "")
            ] + company.get("aliases", [])
            if any(name_in_query(name) for name in names):
                context["company_matches"].append({
                    "id": company_id,
                    "name": company.get("name"),
                    "field": company.get("field"),
                    "description": company.get("description"),
                    "products": company.get("products", [])[:12]
                })

        for product_id, product in products.items():
            names = [
                product_id,
                product.get("name", "")
            ] + product.get("aliases", [])
            if any(name_in_query(name) for name in names):
                context["product_matches"].append({
                    "id": product_id,
                    "name": product.get("name"),
                    "company": product.get("company"),
                    "category": product.get("category"),
                    "description": product.get("description")
                })

        context["entries"] = context["entries"][:12]
        context["company_matches"] = context["company_matches"][:8]
        context["product_matches"] = context["product_matches"][:12]
        context["available"] = bool(
            context["entries"]
            or context["company_matches"]
            or context["product_matches"]
        )
        context["entry_count"] = len(context["entries"])
        context["company_match_count"] = len(context["company_matches"])
        context["product_match_count"] = len(context["product_matches"])

        return context

    def build_local_data_context(self, original_data, report, memory_report):

        query = self.extract_query_text(
            original_data,
            report,
            memory_report
        )

        if not query or search_data_context is None:
            return {
                "available": False,
                "query": query,
                "matches": [],
                "source": "main_ai_canri/data"
            }

        try:
            if build_shared_data_context:
                context = build_shared_data_context(query, limit=12)
            else:
                context = search_data_context(query, limit=12)
        except Exception as error:
            return {
                "available": False,
                "query": query,
                "matches": [],
                "error": str(error),
                "source": "main_ai_canri/data"
            }

        context["query"] = query
        context["source"] = "main_ai_canri/data"
        return context

    def build_shared_brain_context(
        self,
        original_data,
        report,
        memory_report,
        dictionary,
        data_context,
        knowledge
    ):

        query = self.extract_query_text(
            original_data,
            report,
            memory_report
        )

        conversation = (
            memory_report.get("conversation", {})
            if isinstance(memory_report, dict)
            else {}
        )

        data_pack = (
            data_context.get("context_pack", {})
            if isinstance(data_context, dict)
            else {}
        )

        dictionary_entries = []
        if isinstance(dictionary, dict):
            for entry in dictionary.get("entries", [])[:8]:
                if not isinstance(entry, dict):
                    continue
                dictionary_entries.append({
                    "word": entry.get("word"),
                    "type": entry.get("type"),
                    "meanings": entry.get("meanings", [])[:2],
                    "connections": entry.get("connections", [])[:6],
                    "forms": entry.get("forms", {})
                })

        knowledge_matches = []
        if isinstance(knowledge, dict):
            for item in knowledge.get("matches", [])[:5]:
                if not isinstance(item, dict):
                    continue
                knowledge_matches.append({
                    "title": item.get("title"),
                    "summary": str(item.get("summary", ""))[:500],
                    "content_excerpt": str(item.get("content_excerpt", ""))[:1000],
                    "trust_score": item.get("trust_score", 0),
                    "source_count": item.get("source_count", 0),
                    "score": item.get("score"),
                    "sources": item.get("sources", [])[:2]
                })

        recommended = []
        if isinstance(data_pack, dict):
            recommended.extend(data_pack.get("recommended_brains", []))

        return {
            "query": query,
            "request": {
                "main_topic": report.get("main_topic"),
                "intent": report.get("intent"),
                "possible_tasks": report.get("possible_tasks", [])[:12],
                "requested_action": report.get("requested_action", {}),
                "semantic_frame": report.get("semantic_frame", {}),
                "meaning_frame": report.get("meaning_frame", {}),
                "request_contract": report.get("request_contract", {}),
                "global_picture": report.get("global_picture", {}),
                "detail_inventory": report.get("detail_inventory", {}),
                "requirements": report.get("requirements", [])[:80],
            },
            "conversation": {
                "session_id": conversation.get("session_id"),
                "turn_count": conversation.get("turn_count", 0),
                "summary": conversation.get("summary", ""),
                "keywords": conversation.get("keywords", [])[:20],
                "recent_turns": conversation.get("recent_turns", [])[-4:],
                "last_completed_turn": conversation.get("last_completed_turn", {}),
                "continuation_request": conversation.get("continuation_request", False),
                "topic_shift_from_previous": conversation.get("topic_shift_from_previous", False),
                "keyword_overlap_with_previous": conversation.get("keyword_overlap_with_previous", [])[:12],
                "usable_previous_code": conversation.get("usable_previous_code"),
                "session_isolation": conversation.get("session_isolation", True)
            },
            "dictionary": {
                "available": dictionary.get("available") if isinstance(dictionary, dict) else False,
                "entries": dictionary_entries,
                "company_matches": dictionary.get("company_matches", [])[:5] if isinstance(dictionary, dict) else [],
                "product_matches": dictionary.get("product_matches", [])[:8] if isinstance(dictionary, dict) else []
            },
            "local_data": {
                "available": data_context.get("available") if isinstance(data_context, dict) else False,
                "domains": data_pack.get("domains", []) if isinstance(data_pack, dict) else [],
                "key_terms": data_pack.get("key_terms", [])[:25] if isinstance(data_pack, dict) else [],
                "data_sources": data_pack.get("data_sources", [])[:6] if isinstance(data_pack, dict) else [],
                "evidence_snippets": data_pack.get("evidence_snippets", [])[:8] if isinstance(data_pack, dict) else [],
                "confidence": data_pack.get("confidence", 0) if isinstance(data_pack, dict) else 0
            },
            "knowledge": {
                "available": knowledge.get("available") if isinstance(knowledge, dict) else False,
                "matches": knowledge_matches
            },
            "recommended_brains": list(dict.fromkeys(recommended)),
            "handoff_rules": [
                "Every specialist should use Understanding + Memory + shared_context before answering.",
                "Every specialist must preserve the global goal and account for every assigned atomic requirement.",
                "Every specialist receives indexed scanner evidence and should use relevant excerpts instead of loading full databases.",
                "If a specialist cannot satisfy the request, return needs_help=True with missing parts.",
                "Quality_Control_brain must check whether the final answer matches the user request.",
                "Response_brain must show the final user-facing result, not internal planning reports."
            ]
        }

    # ---------- planning ----------

    def classify_request(self, report, memory_report):

        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()
        terms = self.collect_terms(report, memory_report)
        raw_text = " ".join(
            str(report.get(key, ""))
            for key in [
                "original_text",
                "corrected_text",
                "text",
                "goal",
                "prompt"
            ]
            if report.get(key)
        ).lower()
        domains = []
        for item in report.get("central_domains", []):
            domain = item.get("domain") if isinstance(item, dict) else item
            domain = str(domain or "").lower().strip()
            # Secondary dictionary associations are evidence, not an explicit
            # user request. Domain rules below add them only when the prompt
            # itself contains a matching term.
            if domain == topic and domain not in {"unknown", "general"}:
                domains.append(domain)

        domain_rules = [
            ("code", ["code", "program", "python", "javascript", "java", "function", "api", "json"]),
            ("science", ["science", "physics", "chemistry", "biology", "article", "experiment", "photosynthesis", "dna", "genetics", "evolution", "ecosystem", "water cycle", "volcano", "immune system", "electric current", "sound wave", "climate", "atom", "atoms"]),
            ("language", ["language", "translation", "translate", "grammar", "synonym", "antonym"]),
            ("geography", ["geography", "country", "city", "capital", "map", "gps", "river", "mountain"]),
            ("technology", [
                "technology", "hardware", "computer", "cpu", "gpu", "robot", "server",
                "microcontroller", "arduino", "raspberry pi", "sensor", "gpio", "serial",
                "embedded", "firmware", "circuit", "electronics", "iot"
            ]),
            ("history", ["history", "historical", "empire", "war", "ancient"]),
            ("math", ["math", "number", "equation", "calculate", "solve", "step by step", "algebra", "x^2", "x**2"]),
            ("security", ["security", "password", "token", "encrypt", "danger", "bomb", "suicide"]),
            ("emotion", [
                "feel", "feeling", "sad", "lonely", "anxious", "worried",
                "afraid", "angry", "upset", "frustrated", "overwhelmed",
                "emotional support", "can we talk", "listen to me", "need someone",
                "\u05e7\u05e9\u05d4 \u05dc\u05d9", "\u05d0\u05e0\u05d9 \u05de\u05e8\u05d2\u05d9\u05e9", "\u05d0\u05e0\u05d9 \u05de\u05e8\u05d2\u05d9\u05e9\u05d4", "\u05d0\u05e4\u05e9\u05e8 \u05dc\u05d3\u05d1\u05e8"
            ]),
            ("image_generation", ["generate image", "create image", "make image", "draw", "illustration", "poster", "logo", "icon", "concept art", "image prompt"]),
            ("vision", ["vision", "image", "photo", "picture", "video", "attachment", "pdf", "png", "jpg", "mp4"]),
            ("voice", ["voice", "audio", "sound", "recording", "microphone", "speech", "transcribe", "wav", "mp3", "m4a"]),
            ("creative", ["creative", "creativity", "idea", "invent", "original", "brainstorm", "stuck", "fallback"]),
            ("story", ["story", "stories", "chapter", "character", "plot", "narrative", "leo", "tiny door"]),
            ("game", ["game", "player", "enemy", "level", "inventory"])
        ]

        def keyword_is_explicit(keyword):
            keyword = str(keyword).lower().strip()
            if not keyword:
                return False
            return re.search(
                r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])",
                raw_text
            ) is not None

        for domain, keywords in domain_rules:
            if topic == domain or intent == domain or any(keyword_is_explicit(keyword) for keyword in keywords):
                domains.append(domain)

        if intent in {"code_generation", "code_analysis"}:
            domains.append("code")

        if intent == "math" or (
            re.search(r"\d|\bx\b", raw_text)
            and (
                "=" in raw_text
                or "^" in raw_text
                or "**" in raw_text
                or any(term in raw_text for term in ["solve", "calculate", "step by step"])
            )
        ):
            domains.append("math")

        if intent in ["question", "research"]:
            domains.append("research")

        if intent == "image_generation":
            domains.append("image_generation")

        explicit_story_request = (
            "story" in domains
            and any(
                marker in raw_text
                for marker in [
                    "story",
                    "stories",
                    "chapter",
                    "continue the same story",
                    "continued story"
                ]
            )
        )
        explicit_code_request = any(
            marker in raw_text
            for marker in [
                "code",
                "program",
                "python",
                "javascript",
                "java",
                "function"
            ]
        )
        explicit_game_request = any(
            marker in raw_text
            for marker in [
                "game",
                "rpg",
                "player",
                "enemy",
                "inventory",
                "level"
            ]
        )

        if explicit_story_request and not explicit_code_request and not explicit_game_request:
            domains = [
                domain
                for domain in domains
                if domain in {"story", "creative", "memory_context"}
            ]

        if memory_report.get("memory_found", 0):
            domains.append("memory_context")

        if not domains:
            domains.append("general")

        return list(dict.fromkeys(domains))

    def primary_domain(self, report, memory_report=None):

        memory_report = memory_report or {}
        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()
        raw_text = " ".join(
            str(report.get(key, ""))
            for key in [
                "original_text",
                "corrected_text",
                "text",
                "goal",
                "prompt"
            ]
            if report.get(key)
        ).lower()
        requested_action = report.get("requested_action", {})
        action_intent = ""
        if isinstance(requested_action, dict):
            action_intent = str(requested_action.get("intent_override", "")).lower()

        if intent in {"code_generation", "code_analysis"} or action_intent in {"code_generation", "code_analysis"}:
            return "code"

        if topic == "code" and any(term in raw_text for term in ["code", "program", "python", "runnable", "terminal"]):
            return "code"

        if intent == "math" or action_intent == "math" or (
            re.search(r"\d|\bx\b", raw_text)
            and (
                "=" in raw_text
                or "^" in raw_text
                or "**" in raw_text
                or any(term in raw_text for term in ["solve", "calculate", "equation", "step by step"])
            )
        ):
            return "math"

        if intent == "image_generation" or topic == "image_generation":
            return "image_generation"

        if intent == "story_creation" or topic == "story":
            return "story"

        if topic == "emotion":
            return "emotion"

        if any(
            marker in raw_text
            for marker in [
                "historically", "historical importance", "history of", "timeline of",
                "printing press", "renaissance", "silk road", "moon landing",
                "ancient egypt", "roman empire", "industrial revolution",
                "french revolution", "invention of writing", "development of the internet"
            ]
        ):
            return "history"

        if topic in {
            "science", "geography", "technology", "history", "language",
            "game", "voice", "vision", "security", "emotion", "planning"
        }:
            return topic

        if intent in {"question", "research"} and any(
            marker in raw_text
            for marker in ["reliable", "sources", "fact check", "local knowledge", "what is", "explain"]
        ):
            return "knowledge"

        return topic or "general"

    def routing_decision(self, report, memory_report=None):

        memory_report = memory_report or {}
        primary = self.primary_domain(report, memory_report)
        contract = report.get("request_contract", {})
        conversation = memory_report.get("conversation", {}) if isinstance(memory_report, dict) else {}
        continuation_contract = contract.get("continuation", {}) if isinstance(contract, dict) else {}
        continuation_requested = bool(
            (isinstance(continuation_contract, dict) and continuation_contract.get("requested"))
            or (isinstance(conversation, dict) and conversation.get("continuation_request"))
        )
        domains = self.focus_domains(
            self.classify_request(report, memory_report),
            report,
            memory_report
        )
        contract = report.get("request_contract", {})
        action = contract.get("action") if isinstance(contract, dict) else None
        intent = str(report.get("intent", "request"))
        specialist_map = {
            "code": "Code_brain",
            "math": "Math_brain",
            "story": "Story_brain",
            "image_generation": "Image_brain",
            "voice": "Voice_brain",
            "vision": "Vision_brain",
            "science": "Science_brain",
            "geography": "Geography_brain",
            "technology": "Technology_brain",
            "history": "History_brain",
            "language": "Language_brain",
            "knowledge": "Research_brain",
            "game": "Game_brain",
            "emotion": "Emotion_brain",
        }
        primary_brain = specialist_map.get(primary, "Reasoning_brain")
        supporting = []
        if primary in {"knowledge", "science", "geography", "technology", "history"}:
            supporting.extend(["Research_brain", "Fact_Check_brain"])
        if primary == "story":
            supporting.extend(["Creative_brain", "Character_brain", "World_brain"])
        if primary == "code":
            supporting.extend(["Planner_brain", "Quality_Control_brain"])
        if primary == "math":
            supporting.extend(["Reasoning_brain", "Quality_Control_brain"])
        if primary == "emotion":
            supporting.extend(["Creative_brain", "Response_brain"])

        for domain in domains:
            specialist = specialist_map.get(domain)
            if specialist and specialist != primary_brain:
                supporting.append(specialist)
        if len([domain for domain in domains if domain != "memory_context"]) > 1:
            supporting.extend(["Planner_brain", "Reasoning_brain", "Collaboration_brain"])
            if primary == "code" and any(
                domain in domains for domain in {"science", "technology", "game", "creative"}
            ):
                supporting.append("Creative_brain")

        return {
            "primary_domain": primary,
            "primary_brain": primary_brain,
            "supporting_brains": list(dict.fromkeys(supporting)),
            "domains": domains,
            "multi_domain": len([
                domain for domain in domains if domain != "memory_context"
            ]) > 1,
            "action": action,
            "intent": intent,
            "continuation": continuation_requested,
            "reason": f"intent={intent}; primary_domain={primary}; specialist={primary_brain}"
        }

    def focus_domains(self, domains, report, memory_report):

        primary = self.primary_domain(report, memory_report)
        domain_set = set(domains)

        if primary == "math":
            return [
                domain
                for domain in ["math", "security", "memory_context"]
                if domain in domain_set or domain == "math"
            ]

        if primary == "code":
            ordered = [
                "code", "science", "technology", "math", "game", "security",
                "vision", "voice", "image_generation", "creative", "research"
            ]
            focused = [domain for domain in ordered if domain in domain_set]
            if "code" not in focused:
                focused.insert(0, "code")
            core = focused[:MAX_CENTRAL_DOMAINS]
            if "memory_context" in domain_set:
                core.append("memory_context")
            return list(dict.fromkeys(core))

        if primary == "story":
            return [
                domain
                for domain in ["story", "creative", "memory_context"]
                if domain in domain_set or domain in {"story", "creative"}
            ]

        if primary == "image_generation":
            return [
                domain
                for domain in ["image_generation", "creative", "security", "memory_context"]
                if domain in domain_set or domain in {"image_generation", "creative"}
            ]

        if primary == "knowledge":
            return [
                domain
                for domain in ["research", "science", "technology", "geography", "history", "language", "general", "memory_context"]
                if domain in domain_set
            ] or ["research"]

        memory_domain = ["memory_context"] if "memory_context" in domain_set else []
        central = [domain for domain in domains if domain != "memory_context"][:MAX_CENTRAL_DOMAINS]
        return list(dict.fromkeys(central + memory_domain))

    def build_plan(self, report, memory_report=None):

        memory_report = memory_report or {}
        domains = self.classify_request(report, memory_report)
        domains = self.focus_domains(domains, report, memory_report)
        primary = self.primary_domain(report, memory_report)
        contract = report.get("request_contract", {})
        conversation = memory_report.get("conversation", {}) if isinstance(memory_report, dict) else {}
        continuation_contract = contract.get("continuation", {}) if isinstance(contract, dict) else {}
        continuation_requested = bool(
            (isinstance(continuation_contract, dict) and continuation_contract.get("requested"))
            or (isinstance(conversation, dict) and conversation.get("continuation_request"))
        )
        story_continuation = primary == "story" and continuation_requested
        central_domains = [
            domain for domain in domains
            if domain not in {"memory_context", "creative"}
        ]
        requirement_count = len(contract.get("requirements", [])) if isinstance(contract, dict) else 0
        high_detail_request = (
            primary in {"code", "planning", "knowledge", "science", "technology"}
            and requirement_count >= 6
        )
        needs_collaboration = len(central_domains) > 1 or high_detail_request
        needs_planner = (
            primary in {"code", "game", "planning"}
            or needs_collaboration
        )
        needs_fact_check = primary in {
            "knowledge", "science", "geography", "technology", "history"
        }

        phases = [
            {
                "phase": "safety_and_context",
                "brains": (
                    ([] if memory_report else ["Memory_brain"])
                    + (["Emotion_brain"] if primary in {"emotion", "story"} and not story_continuation else [])
                    + ["Security_brain"]
                )
            },
            {
                "phase": "core_reasoning",
                "brains": ["Planner_brain"] if needs_planner else []
            },
            {
                "phase": "domain_experts",
                "brains": []
            },
            {
                "phase": "neural_integration",
                "brains": ["Nervous_system_brain"]
            },
            {
                "phase": "brain_collaboration",
                "brains": ["Collaboration_brain"] if needs_collaboration else []
            },
            {
                "phase": "post_collaboration_integration",
                "brains": ["Nervous_system_brain"] if needs_collaboration else []
            },
            {
                "phase": "verification",
                "brains": (
                    (["Fact_Check_brain"] if needs_fact_check else [])
                    + ["Quality_Control_brain"]
                    + ([] if story_continuation else ["Learning_brain"])
                )
            },
            {
                "phase": "response",
                "brains": [
                    "Response_brain"
                ]
            }
        ]

        core = phases[1]["brains"]
        experts = phases[2]["brains"]

        if "research" in domains or "general" in domains:
            core.extend([
                "Research_brain",
                "Reasoning_brain"
            ])

        if "code" in domains:
            core.extend([
                "Reasoning_brain",
                "Technology_brain"
            ])
            experts.extend([
                "Code_brain"
            ])

        if "science" in domains:
            experts.extend([
                "Science_brain",
                "Research_brain",
                "Reasoning_brain"
            ])

        if "language" in domains:
            experts.extend([
                "Language_brain"
            ])

        if "geography" in domains:
            experts.extend([
                "Geography_brain",
                "Research_brain"
            ])

        if "technology" in domains:
            experts.extend([
                "Technology_brain",
                "Research_brain"
            ])

        if "history" in domains:
            experts.extend([
                "History_brain",
                "Research_brain"
            ])

        if "math" in domains:
            experts.extend([
                "Math_brain",
                "Reasoning_brain"
            ])

        if "security" in domains:
            phases[0]["brains"].append(
                "Security_brain"
            )

        if "vision" in domains:
            experts.extend([
                "Vision_brain",
                "Security_brain"
            ])

        if "image_generation" in domains:
            experts.extend([
                "Image_brain",
                "Creative_brain",
                "Security_brain"
            ])

        if "voice" in domains:
            experts.extend([
                "Voice_brain",
                "Vision_brain",
                "Security_brain"
            ])

        if "emotion" in domains:
            experts.extend([
                "Creative_brain"
            ])

        if "creative" in domains and not story_continuation:
            experts.extend([
                "Creative_brain",
                "Planner_brain"
            ])

        if "story" in domains:
            story_text = " ".join(
                str(report.get(key, ""))
                for key in ["original_text", "corrected_text", "text", "goal", "prompt"]
                if report.get(key)
            ).lower()
            if not story_continuation:
                experts.append("Creative_brain")
            if any(
                marker in story_text
                for marker in [
                    "character profile", "character sheet", "worldbuilding",
                    "world building", "novel", "chapter outline"
                ]
            ):
                experts.extend(["Character_brain", "World_brain"])
            experts.append("Story_brain")

        if "game" in domains:
            experts.extend([
                "Game_brain",
                "Creative_brain",
                "Technology_brain",
                "Planner_brain"
            ])

        if needs_collaboration:
            core.extend(["Reasoning_brain", "Planner_brain"])
            if "code" in central_domains and any(
                domain in central_domains
                for domain in {"science", "technology", "game", "creative"}
            ):
                experts.append("Creative_brain")

        for phase in phases:
            phase["brains"] = list(dict.fromkeys(phase["brains"]))

        return phases

    def flatten_plan(self, phases):

        plan = []

        for phase in phases:
            plan.extend(phase.get("brains", []))

        return list(dict.fromkeys(plan))

    # ---------- execution ----------

    def emit_progress(self, data, stage, detail=None, brain_name=None, phase=None, result=None):

        if not isinstance(data, dict):
            return

        progress_callback = data.get("_progress_callback")
        if not progress_callback:
            return

        payload = {
            "stage": stage,
            "detail": detail,
            "data": {
                "brain": brain_name,
                "phase": phase
            }
        }

        if isinstance(result, dict):
            payload["data"]["confidence"] = result.get("confidence")
            payload["data"]["error"] = result.get("error")
            payload["data"]["needs_help"] = result.get("needs_help")
            payload["data"]["needs_creative_brain"] = result.get("needs_creative_brain")

        try:
            progress_callback(payload)
        except Exception:
            pass

    def build_context(
        self,
        original_data,
        report,
        memory_report,
        phase,
        results,
        brain_name=None
    ):

        context = {}

        if isinstance(original_data, dict):
            context.update(original_data)
        else:
            context["original_text"] = str(original_data)

        combined_results = {}
        if isinstance(context.get("results"), dict):
            combined_results.update(context["results"])
        if isinstance(results, dict):
            combined_results.update(results)
        context["results"] = combined_results

        context["understanding"] = report
        request_contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
        context["execution_contract"] = {
            "global_picture": request_contract.get("global_picture", {}),
            "detail_inventory": request_contract.get("detail_inventory", {}),
            "requirements": request_contract.get("requirements", []),
            "output_constraints": request_contract.get("output_constraints", {}),
            "continuation": request_contract.get("continuation", {}),
            "enhancement_policy": request_contract.get("enhancement_policy", {}),
            "instruction": (
                "Satisfy the global goal and then verify every small detail. "
                "Do not discard a detail merely because the main topic is correct. "
                "Consider useful improvements, but never replace an explicit requirement or violate a strict output format."
            )
        }
        context["memory"] = memory_report
        context["dictionary"] = context.get("dictionary") or self.build_dictionary_context(
            original_data,
            report,
            memory_report
        )
        full_data_context = context.get("full_data_context") or context.get("data_context") or self.build_local_data_context(
            original_data,
            report,
            memory_report
        )
        context["full_data_context"] = full_data_context
        if context_view_for_brain is not None and brain_name:
            context["data_context"] = context_view_for_brain(
                full_data_context,
                brain_name
            )
        else:
            context["data_context"] = full_data_context
        context["knowledge"] = context.get("knowledge") or self.build_knowledge_context(
            original_data,
            report,
            memory_report
        )
        context["knowledge_context"] = context["knowledge"]
        context["scanner_knowledge"] = self.build_scanner_view(
            context["knowledge"],
            brain_name
        )
        context["shared_context"] = context.get("shared_context") or self.build_shared_brain_context(
            original_data,
            report,
            memory_report,
            context["dictionary"],
            context["data_context"],
            context["knowledge"]
        )
        context["manager_context"] = {
            "phase": phase,
            "target_brain": brain_name,
            "previous_results": combined_results,
            "available_brains": sorted(self.brains.keys()),
            "dictionary": context["dictionary"],
            "data_context": context["data_context"],
            "knowledge": context["knowledge"],
            "scanner_knowledge": context["scanner_knowledge"],
            "shared_context": context["shared_context"],
            "conversation": (
                memory_report.get("conversation", {})
                if isinstance(memory_report, dict)
                else {}
            ),
            "execution_contract": context["execution_contract"],
            "brain_dialogue": context.get("brain_dialogue", {}),
            "performance_budget": {
                "request_budget_seconds": REQUEST_TIME_BUDGET_SECONDS,
                "brain_soft_timeout_seconds": DEFAULT_BRAIN_SOFT_TIMEOUT_SECONDS,
                "remaining_seconds": max(
                    0,
                    round(self._request_deadline - time.perf_counter(), 3)
                ) if self._request_deadline else None
            }
        }

        context["execution_contract"]["scanner_grounding"] = {
            "required": context["scanner_knowledge"]["required_for_answer"],
            "available": context["scanner_knowledge"]["available"],
            "instruction": context["scanner_knowledge"]["policy"]
        }

        return context

    def execute_collaboration_round(
        self,
        data,
        report,
        memory_report,
        all_results,
        collaboration_result
    ):
        """Run one bounded reply round using questions prepared by Collaboration_brain."""

        if not isinstance(collaboration_result, dict):
            return {}, None

        requests = collaboration_result.get("consultation_requests", [])
        if not isinstance(requests, list) or not requests:
            return {}, None

        replies = {}
        for request in requests[:MAX_COLLABORATION_PARTICIPANTS]:
            if not isinstance(request, dict):
                continue
            target = request.get("target_brain")
            if (
                not target
                or target == "Collaboration_brain"
                or target not in self.brains
            ):
                continue
            if self._request_deadline and time.perf_counter() >= self._request_deadline:
                break

            dialogue_context = dict(data) if isinstance(data, dict) else {
                "original_text": str(data)
            }
            dialogue_context["results"] = dict(all_results)
            dialogue_context["collaboration_round"] = "response"
            dialogue_context["collaboration_request"] = request
            dialogue_context["brain_dialogue"] = {
                "round": 1,
                "question": request.get("question"),
                "peer_messages": request.get("peer_messages", []),
                "participants": collaboration_result.get("participants", []),
                "instruction": (
                    "Answer the consultation question, use relevant peer findings, and improve your "
                    "result without changing the user's goal or dropping requirements."
                )
            }

            # Existing specialist retry interfaces also receive the consultation as actionable feedback.
            dialogue_context["retry_target"] = target
            dialogue_context["retry_request"] = {
                "target_brain": target,
                "problem": "peer consultation requested",
                "instruction": request.get("question"),
                "peer_messages": request.get("peer_messages", [])
            }
            dialogue_context["retry_instructions"] = [
                request.get("question"),
                "Consider the peer messages in brain_dialogue and preserve all original requirements."
            ]

            result = self.execute(
                [target],
                dialogue_context,
                report,
                memory_report,
                "brain_consultation_reply"
            )
            replies.update(result)
            all_results.update(result)

        if not replies:
            return {}, None

        final_context = dict(data) if isinstance(data, dict) else {
            "original_text": str(data)
        }
        final_context["results"] = dict(all_results)
        final_context["collaboration_round"] = "consensus"
        final_context["routing_decision"] = self.routing_decision(report, memory_report)
        consensus = self.execute(
            ["Collaboration_brain"],
            final_context,
            report,
            memory_report,
            "brain_collaboration_consensus"
        ).get("Collaboration_brain")
        return replies, consensus

    def execute(self, selected_brains, data, report=None, memory_report=None, phase="single"):

        results = {}
        report = report or self.get_understanding_report(data)
        memory_report = memory_report or self.get_memory_report(data)

        for brain_name in selected_brains:

            if (
                self._request_deadline
                and time.perf_counter() >= self._request_deadline
                and brain_name not in {"Quality_Control_brain", "Response_brain"}
            ):
                results[brain_name] = {
                    "skipped": True,
                    "reason": "request_time_budget_exceeded",
                    "timeout": True
                }
                continue

            if brain_name in self._active_brain_stack:
                results[brain_name] = {
                    "skipped": True,
                    "reason": "brain_recursion_prevented",
                    "loop_prevented": True
                }
                continue

            if brain_name not in self.brains:
                results[brain_name] = {
                    "skipped": True,
                    "reason": "brain_not_registered"
                }
                continue

            brain = self.brains[brain_name]

            if not hasattr(brain, "process"):
                results[brain_name] = {
                    "skipped": True,
                    "reason": "brain_has_no_process_method"
                }
                continue

            self.emit_progress(
                data,
                "brain_start",
                f"Running {brain_name}",
                brain_name,
                phase
            )

            context = self.build_context(
                data,
                report,
                memory_report,
                phase,
                results,
                brain_name
            )

            try:
                self._active_brain_stack.append(brain_name)
                remaining_seconds = (
                    max(self._request_deadline - time.perf_counter(), 0.05)
                    if self._request_deadline
                    else None
                )
                timeout_seconds = brain_runtime.timeout_for(
                    brain_name,
                    remaining_seconds
                )
                execution = brain_runtime.invoke(
                    brain_name,
                    brain,
                    context,
                    phase=phase,
                    timeout_seconds=timeout_seconds,
                    request_id=self._request_id,
                    attempt=self._retry_counts.get(brain_name, 0) + 1
                )
                self._runtime_events.append(execution.telemetry)
                result = execution.result

                # Creative assistance is useful for weak drafts, not for runtime
                # failures. Applying it to an exception was a source of unrelated
                # story output in code, math, and factual requests.
                if execution.ok:
                    result = self.attach_creative_help_if_needed(
                        brain_name,
                        result,
                        context,
                        phase
                    )

                scanner_view = context.get("scanner_knowledge", {})
                result["scanner_context"] = {
                    "received": bool(scanner_view.get("available")),
                    "required": bool(scanner_view.get("required_for_answer")),
                    "considered_by_contract": bool(scanner_view.get("available")),
                    "retrieval": scanner_view.get("retrieval"),
                    "article_ids": [
                        item.get("article_id")
                        for item in scanner_view.get("matches", [])
                        if isinstance(item, dict) and item.get("article_id")
                    ],
                    "sources": list(dict.fromkeys(
                        source.get("source_id")
                        for item in scanner_view.get("matches", [])
                        if isinstance(item, dict)
                        for source in item.get("sources", [])
                        if isinstance(source, dict) and source.get("source_id")
                    ))
                }
                result["performance"] = {
                    "elapsed_seconds": execution.telemetry.get("elapsed_seconds", 0),
                    "queue_seconds": execution.telemetry.get("queue_seconds", 0),
                    "timeout_seconds": execution.telemetry.get("timeout_seconds"),
                    "slow": bool(execution.telemetry.get("slow")),
                    "status": execution.telemetry.get("status"),
                    "runtime_contract": execution.telemetry.get("contract_version")
                }
                results[brain_name] = result
                self.emit_progress(
                    data,
                    "brain_done" if execution.ok else "brain_error",
                    (
                        f"Finished {brain_name}"
                        if execution.ok
                        else f"{brain_name} could not complete its work"
                    ),
                    brain_name,
                    phase,
                    result
                )

            except Exception:
                error_result = {
                    "brain": brain_name,
                    "error": "manager_postprocessing_failed",
                    "error_code": "manager_postprocessing_failed",
                    "user_safe_error": (
                        "Canri could not validate this brain result safely."
                    ),
                    "phase": phase,
                    "recoverable": True,
                    "confidence": 0
                }
                results[brain_name] = error_result
                self.emit_progress(
                    data,
                    "brain_error",
                    f"{brain_name} result validation failed",
                    brain_name,
                    phase,
                    error_result
                )
            finally:
                if self._active_brain_stack and self._active_brain_stack[-1] == brain_name:
                    self._active_brain_stack.pop()
                elif brain_name in self._active_brain_stack:
                    self._active_brain_stack.remove(brain_name)

        return results

    def needs_creative_help(self, brain_name, result):

        if brain_name in [
            "Creative_brain",
            "Security_brain",
            "Response_brain",
            "Fact_Check_brain",
            "Quality_Control_brain",
            "Learning_brain"
        ]:
            return False

        if not isinstance(result, dict):
            return False

        if result.get("creative_help") or result.get("creative_fallback"):
            return False

        if result.get("needs_creative_brain") is True:
            return True

        if result.get("needs_help") is True:
            return True

        if result.get("error"):
            return True

        if result.get("missing"):
            return True

        suggested = result.get("suggested_next_brains", [])
        if "Creative_brain" in suggested:
            return True

        return False

    def creative_task_type(self, brain_name, result):

        if brain_name == "Code_brain":
            return "creative_code_assembly"

        if brain_name in ["Story_brain", "Character_brain", "World_brain"]:
            return "creative_story_support"

        if brain_name in ["Planner_brain", "Reasoning_brain"]:
            return "creative_problem_solving"

        if brain_name == "Game_brain":
            return "creative_game_design"

        return "creative_support"

    def attach_creative_help_if_needed(self, brain_name, result, context, phase):

        if not self.needs_creative_help(brain_name, result):
            return result

        creative = self.brains.get("Creative_brain")

        if creative is None or not hasattr(creative, "solve_brain_task"):
            result["creative_help"] = {
                "brain": "Creative_brain",
                "skipped": True,
                "reason": "creative_brain_not_registered"
            }
            return result

        task_report = dict(context)
        task_report["problem"] = self.describe_creative_need(result)
        task_report["source_result"] = result
        task_report["source_brain"] = brain_name
        task_report["phase"] = phase

        try:
            result["creative_help"] = creative.solve_brain_task(
                brain_name,
                task_report,
                self.creative_task_type(brain_name, result)
            )
        except Exception as error:
            result["creative_help"] = {
                "brain": "Creative_brain",
                "error": str(error),
                "source_brain": brain_name
            }

        return result

    def describe_creative_need(self, result):

        if not isinstance(result, dict):
            return "brain returned unusable result"

        if result.get("error"):
            return f"brain error: {result.get('error')}"

        if result.get("missing"):
            return "missing parts: " + ", ".join(str(item) for item in result.get("missing", [])[:8])

        if result.get("needs_creative_brain"):
            return "brain explicitly requested creative help"

        if result.get("needs_help"):
            return "brain reported low confidence and needs help"

        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            return f"low confidence: {confidence}"

        return "creative support requested"

    def execute_phases(self, phases, data, report, memory_report):

        all_results = {}
        phase_results = []

        if isinstance(data, dict) and isinstance(data.get("knowledge"), dict):
            shared_knowledge = data["knowledge"]
        else:
            shared_knowledge = self.build_knowledge_context(
                data,
                report,
                memory_report
            )

        if isinstance(data, dict) and isinstance(data.get("dictionary"), dict):
            shared_dictionary = data["dictionary"]
        else:
            shared_dictionary = self.build_dictionary_context(
                data,
                report,
                memory_report
            )

        if isinstance(data, dict) and isinstance(data.get("data_context"), dict):
            shared_data_context = data["data_context"]
        else:
            shared_data_context = self.build_local_data_context(
                data,
                report,
                memory_report
            )

        if isinstance(data, dict) and isinstance(data.get("shared_context"), dict):
            shared_brain_context = data["shared_context"]
        else:
            shared_brain_context = self.build_shared_brain_context(
                data,
                report,
                memory_report,
                shared_dictionary,
                shared_data_context,
                shared_knowledge
            )

        for phase_data in phases:

            phase_name = phase_data.get("phase", "unknown")
            phase_brains = phase_data.get("brains", [])
            phase_context = data

            if isinstance(data, dict):
                phase_context = dict(data)
                phase_context["results"] = all_results
                phase_context["knowledge"] = shared_knowledge
                phase_context["dictionary"] = shared_dictionary
                phase_context["data_context"] = shared_data_context
                phase_context["shared_context"] = shared_brain_context

            results = self.execute(
                phase_brains,
                phase_context,
                report,
                memory_report,
                phase_name
            )

            all_results.update(results)

            if phase_name == "brain_collaboration":
                collaboration_result = results.get("Collaboration_brain")
                collaboration_replies, consensus = self.execute_collaboration_round(
                    phase_context,
                    report,
                    memory_report,
                    all_results,
                    collaboration_result
                )
                if collaboration_replies:
                    all_results.update(collaboration_replies)
                    phase_results.append({
                        "phase": "brain_consultation_replies",
                        "brains": list(collaboration_replies),
                        "results": collaboration_replies
                    })
                if isinstance(consensus, dict):
                    all_results["Collaboration_brain"] = consensus
                    results["Collaboration_brain"] = consensus
                    phase_results.append({
                        "phase": "brain_collaboration_consensus",
                        "brains": ["Collaboration_brain"],
                        "results": {"Collaboration_brain": consensus}
                    })

            phase_results.append({
                "phase": phase_name,
                "brains": phase_brains,
                "results": results
            })

            memory_result = results.get("Memory_brain")
            if isinstance(memory_result, dict) and isinstance(memory_result.get("memory"), dict):
                memory_report = memory_result["memory"]

            quality_result = results.get("Quality_Control_brain")
            if isinstance(quality_result, dict) and quality_result.get("needs_retry"):
                retry_rounds, _ = self.resolve_quality_until_stable(
                    data,
                    report,
                    memory_report,
                    all_results,
                    quality_result,
                    shared_knowledge,
                    shared_dictionary,
                    shared_data_context,
                    phase_prefix="quality"
                )
                phase_results.extend(retry_rounds)

            if phase_name == "response" and "Quality_Control_brain" in self.brains:
                final_recheck_results = self.execute_quality_recheck(
                    data,
                    report,
                    memory_report,
                    all_results,
                    shared_knowledge,
                    shared_dictionary,
                    shared_data_context
                )

                if final_recheck_results:
                    all_results.update(final_recheck_results)
                    phase_results.append({
                        "phase": "final_quality_gate",
                        "brains": list(final_recheck_results.keys()),
                        "results": final_recheck_results
                    })

                    final_quality = final_recheck_results.get("Quality_Control_brain", {})
                    if isinstance(final_quality, dict) and final_quality.get("needs_retry"):
                        final_retry_rounds, _ = self.resolve_quality_until_stable(
                            data,
                            report,
                            memory_report,
                            all_results,
                            final_quality,
                            shared_knowledge,
                            shared_dictionary,
                            shared_data_context,
                            phase_prefix="final_quality"
                        )
                        phase_results.extend(final_retry_rounds)

                    refreshed_response = self.execute(
                        ["Response_brain"],
                        {
                            **data,
                            "results": all_results,
                            "knowledge": shared_knowledge,
                            "dictionary": shared_dictionary,
                            "data_context": shared_data_context,
                            "shared_context": shared_brain_context
                        } if isinstance(data, dict) else data,
                        report,
                        memory_report,
                        "final_response_refresh"
                    )

                    if refreshed_response:
                        all_results.update(refreshed_response)
                        phase_results.append({
                            "phase": "final_response_refresh",
                            "brains": list(refreshed_response.keys()),
                            "results": refreshed_response
                        })

        return all_results, phase_results

    def retry_brains_from_quality(self, quality_result):

        retry_brains = []

        for request in quality_result.get("retry_requests", []):
            if not isinstance(request, dict):
                continue

            brain_name = request.get("target_brain")
            if (
                brain_name
                and brain_name in self.brains
                and brain_name not in {
                    "Quality_Control_brain",
                    "Response_brain",
                    "Security_brain",
                    "Learning_brain",
                    "Nervous_system_brain"
                }
                and brain_name not in retry_brains
            ):
                retry_brains.append(brain_name)

        return retry_brains[:5]

    def build_retry_context(
        self,
        data,
        all_results,
        shared_knowledge,
        shared_dictionary,
        shared_data_context,
        quality_result,
        target_brain=None,
        retry_request=None
    ):

        if isinstance(data, dict):
            retry_context = dict(data)
        else:
            retry_context = {
                "original_text": str(data)
            }

        retry_context["results"] = all_results
        retry_context["knowledge"] = shared_knowledge
        retry_context["dictionary"] = shared_dictionary
        retry_context["data_context"] = shared_data_context
        retry_context["full_data_context"] = shared_data_context
        retry_context["quality_feedback"] = quality_result
        retry_context["nervous_system"] = all_results.get(
            "Nervous_system_brain",
            {}
        )
        retry_context["retry_target"] = target_brain
        retry_context["retry_request"] = retry_request or {}
        retry_context["quality_retry_attempt"] = (
            self._retry_counts.get(target_brain, 0)
            if target_brain
            else 0
        )
        retry_context["failed_requirements"] = list(
            (retry_request or {}).get("failed_requirements", [])
        )
        retry_context["retry_instructions"] = [
            item.get("instruction")
            for item in quality_result.get("retry_requests", [])
            if isinstance(item, dict)
            and (not target_brain or item.get("target_brain") == target_brain)
            and item.get("instruction")
        ]
        if target_brain:
            retry_context["previous_attempt"] = all_results.get(target_brain)

        return retry_context

    def execute_quality_retry(
        self,
        data,
        report,
        memory_report,
        all_results,
        quality_result,
        shared_knowledge,
        shared_dictionary,
        shared_data_context
    ):

        retry_brains = self.retry_brains_from_quality(quality_result)

        if not retry_brains:
            return {}

        retry_results = {}
        requests_by_brain = {
            item.get("target_brain"): item
            for item in quality_result.get("retry_requests", [])
            if isinstance(item, dict) and item.get("target_brain")
        }

        for brain_name in retry_brains:
            if self._retry_counts.get(brain_name, 0) >= MAX_QUALITY_RETRIES_PER_BRAIN:
                continue
            self._retry_counts[brain_name] = self._retry_counts.get(brain_name, 0) + 1
            retry_request = requests_by_brain.get(brain_name, {})
            retry_context = self.build_retry_context(
                data,
                all_results,
                shared_knowledge,
                shared_dictionary,
                shared_data_context,
                quality_result,
                brain_name,
                retry_request
            )
            self.emit_progress(
                retry_context,
                "quality_retry",
                f"Retrying {brain_name}: {retry_request.get('problem', 'quality issue')}",
                brain_name,
                "quality_retry",
                quality_result
            )
            result = self.execute(
                [brain_name],
                retry_context,
                report,
                memory_report,
                "quality_retry"
            )
            retry_results.update(result)

        return retry_results

    def execute_quality_recheck(
        self,
        data,
        report,
        memory_report,
        all_results,
        shared_knowledge,
        shared_dictionary,
        shared_data_context
    ):

        if "Quality_Control_brain" not in self.brains:
            return {}

        recheck_context = self.build_retry_context(
            data,
            all_results,
            shared_knowledge,
            shared_dictionary,
            shared_data_context,
            {
                "recheck": True
            }
        )

        return self.execute(
            ["Quality_Control_brain"],
            recheck_context,
            report,
            memory_report,
            "quality_recheck"
        )

    def resolve_quality_until_stable(
        self,
        data,
        report,
        memory_report,
        all_results,
        quality_result,
        shared_knowledge,
        shared_dictionary,
        shared_data_context,
        phase_prefix="quality"
    ):
        """Retry exactly the failing brains until quality passes or retries end."""

        rounds = []
        current_quality = quality_result if isinstance(quality_result, dict) else {}

        while current_quality.get("needs_retry"):
            retry_brains = self.retry_brains_from_quality(current_quality)
            retry_brains = [
                brain_name
                for brain_name in retry_brains
                if self._retry_counts.get(brain_name, 0) < MAX_QUALITY_RETRIES_PER_BRAIN
            ]
            if not retry_brains:
                break

            retry_results = self.execute_quality_retry(
                data,
                report,
                memory_report,
                all_results,
                current_quality,
                shared_knowledge,
                shared_dictionary,
                shared_data_context
            )
            retry_results = {
                brain_name: result
                for brain_name, result in retry_results.items()
                if isinstance(result, dict)
                and not result.get("skipped")
                and not result.get("error")
            }
            if not retry_results:
                break

            all_results.update(retry_results)
            if "Nervous_system_brain" in self.brains:
                neural_context = self.build_retry_context(
                    data,
                    all_results,
                    shared_knowledge,
                    shared_dictionary,
                    shared_data_context,
                    current_quality
                )
                neural_results = self.execute(
                    ["Nervous_system_brain"],
                    neural_context,
                    report,
                    memory_report,
                    "quality_neural_integration"
                )
                if neural_results:
                    all_results.update(neural_results)

            recheck_results = self.execute_quality_recheck(
                data,
                report,
                memory_report,
                all_results,
                shared_knowledge,
                shared_dictionary,
                shared_data_context
            )
            if not recheck_results:
                break

            all_results.update(recheck_results)
            next_quality = recheck_results.get("Quality_Control_brain", {})
            round_number = max(
                (
                    self._retry_counts.get(brain_name, 0)
                    for brain_name in retry_results
                ),
                default=1
            )
            rounds.append({
                "phase": f"{phase_prefix}_retry_{round_number}",
                "brains": list(retry_results),
                "results": retry_results,
                "quality_feedback": current_quality.get("retry_requests", []),
                "quality_recheck": next_quality
            })

            if not isinstance(next_quality, dict):
                break
            current_quality = next_quality

        return rounds, current_quality

    # ---------- scoring ----------

    def estimate_system_confidence(self, results):

        confidences = []

        for result in results.values():
            if not isinstance(result, dict):
                continue

            confidence = result.get("confidence")
            if isinstance(confidence, (int, float)):
                confidences.append(confidence)

        if not confidences:
            return 0

        return round(sum(confidences) / len(confidences), 2)

    def collect_suggested_next_brains(self, results):

        suggested = []

        for result in results.values():
            if not isinstance(result, dict):
                continue

            suggested.extend(
                result.get("suggested_next_brains", [])
            )

        return list(dict.fromkeys(suggested))

    def collect_follow_up_tasks(self, results, limit=5):

        collected = []
        seen = set()
        for result in results.values():
            if not isinstance(result, dict):
                continue
            for task in result.get("suggested_follow_up_tasks", []):
                if not isinstance(task, dict):
                    continue
                identity = str(task.get("id") or task.get("title") or "").strip().lower()
                if not identity or identity in seen:
                    continue
                seen.add(identity)
                collected.append({
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "goal": task.get("goal"),
                    "owner_brains": task.get("owner_brains", [])[:6],
                    "acceptance_checks": task.get("acceptance_checks", [])[:6],
                    "evidence_groups": task.get("evidence_groups", [])[:8],
                })
                if len(collected) >= max(1, int(limit)):
                    return collected
        return collected

    # ---------- process ----------

    def process(self, data):

        self._request_started = time.perf_counter()
        requested_deadline = (
            data.get("_request_deadline_monotonic")
            if isinstance(data, dict)
            else None
        )
        local_deadline = (
            self._request_started + REQUEST_TIME_BUDGET_SECONDS
            if isinstance(REQUEST_TIME_BUDGET_SECONDS, (int, float))
            and REQUEST_TIME_BUDGET_SECONDS > 0
            else None
        )
        if isinstance(requested_deadline, (int, float)):
            self._request_deadline = (
                min(local_deadline, float(requested_deadline))
                if local_deadline is not None
                else float(requested_deadline)
            )
        else:
            self._request_deadline = local_deadline
        self._retry_counts = {}
        self._active_brain_stack = []
        self._runtime_events = []
        self._request_id = (
            str(data.get("_request_id"))
            if isinstance(data, dict) and data.get("_request_id")
            else "request_" + uuid4().hex
        )

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        shared_knowledge = self.build_knowledge_context(
            data,
            report,
            memory_report
        )
        shared_dictionary = self.build_dictionary_context(
            data,
            report,
            memory_report
        )
        shared_data_context = self.build_local_data_context(
            data,
            report,
            memory_report
        )
        shared_brain_context = self.build_shared_brain_context(
            data,
            report,
            memory_report,
            shared_dictionary,
            shared_data_context,
            shared_knowledge
        )

        if isinstance(data, dict):
            data = dict(data)
            data["_request_id"] = self._request_id
            data["knowledge"] = shared_knowledge
            data["dictionary"] = shared_dictionary
            data["data_context"] = shared_data_context
            data["shared_context"] = shared_brain_context
            data["routing_decision"] = self.routing_decision(report, memory_report)

        phases = self.build_plan(report, memory_report)
        plan = self.flatten_plan(phases)

        results, phase_results = self.execute_phases(
            phases,
            data,
            report,
            memory_report
        )

        runtime_events = brain_runtime.events_for_request(self._request_id)
        manager_report = {
            "brain": "Manager_brain",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "primary_domain": self.primary_domain(report, memory_report),
            "routing_decision": self.routing_decision(report, memory_report),
            "domains_detected": self.classify_request(report, memory_report),
            "domains_used": self.focus_domains(
                self.classify_request(report, memory_report),
                report,
                memory_report
            ),
            "dictionary_context": {
                "available": shared_dictionary.get("available"),
                "entry_count": shared_dictionary.get("entry_count", 0),
                "company_match_count": shared_dictionary.get("company_match_count", 0),
                "product_match_count": shared_dictionary.get("product_match_count", 0),
                "entries": [
                    {
                        "word": item.get("word"),
                        "type": item.get("type"),
                        "meanings": item.get("meanings", [])[:2],
                        "connections": item.get("connections", [])[:6]
                    }
                    for item in shared_dictionary.get("entries", [])[:8]
                    if isinstance(item, dict)
                ],
                "company_matches": shared_dictionary.get("company_matches", [])[:5],
                "product_matches": shared_dictionary.get("product_matches", [])[:8]
            },
            "local_data_context": {
                "available": shared_data_context.get("available"),
                "profiled_files": shared_data_context.get("profiled_files"),
                "total_profiled_bytes": shared_data_context.get("total_profiled_bytes"),
                "domains": shared_data_context.get("domains", [])[:10],
                "query_terms": shared_data_context.get("query_terms", [])[:20],
                "matches": [
                    {
                        "file": item.get("file"),
                        "score": item.get("score"),
                        "shape": item.get("shape"),
                        "items": item.get("items"),
                        "matched_terms": item.get("matched_terms", [])[:8]
                    }
                    for item in shared_data_context.get("matches", [])[:8]
                    if isinstance(item, dict)
                ]
            },
            "knowledge_context": {
                "available": shared_knowledge.get("available"),
                "match_count": shared_knowledge.get("match_count", 0),
                "queue_update": shared_knowledge.get("queue_update", {}),
                "query_terms": shared_knowledge.get("query_terms", [])[:20],
                "matches": [
                    {
                        "title": item.get("title"),
                        "score": item.get("score"),
                        "sources": item.get("sources", [])[:2]
                    }
                    for item in shared_knowledge.get("matches", [])[:5]
                    if isinstance(item, dict)
                ]
            },
            "conversation_context": (
                memory_report.get("conversation", {})
                if isinstance(memory_report, dict)
                else {}
            ),
            "shared_context": shared_brain_context,
            "quality_control": (
                {
                    "passed": results.get("Quality_Control_brain", {}).get("passed"),
                    "quality_score": results.get("Quality_Control_brain", {}).get("quality_score"),
                    "needs_retry": results.get("Quality_Control_brain", {}).get("needs_retry"),
                    "issues": results.get("Quality_Control_brain", {}).get("issues", [])[:8]
                }
                if isinstance(results.get("Quality_Control_brain"), dict)
                else {}
            ),
            "brains_used": plan,
            "phases": [
                {
                    "phase": phase["phase"],
                    "brains": phase["brains"]
                }
                for phase in phases
            ],
            "results": results,
            "phase_results": phase_results,
            "system_confidence": self.estimate_system_confidence(results),
            "performance": {
                "elapsed_seconds": round(time.perf_counter() - self._request_started, 4),
                "budget_seconds": REQUEST_TIME_BUDGET_SECONDS,
                "within_budget": (
                    self._request_deadline is None
                    or time.perf_counter() <= self._request_deadline
                ),
                "retry_counts": dict(self._retry_counts),
                "loop_prevention": True,
                "runtime": brain_runtime.summarize_events(runtime_events)
            },
            "runtime": {
                "contract_version": brain_runtime.CONTRACT_VERSION,
                "request_id": self._request_id,
                "summary": brain_runtime.summarize_events(runtime_events),
                "events": runtime_events,
                "registry": dict(self.registry_health),
                "all_registered_brains_valid": bool(self.registry_health) and all(
                    item.get("valid")
                    for item in self.registry_health.values()
                    if isinstance(item, dict)
                )
            },
            "suggested_next_brains": self.collect_suggested_next_brains(results),
            "suggested_follow_up_tasks": self.collect_follow_up_tasks(results),
            "visible_work_summary": {
                "central_domains": self.focus_domains(
                    self.classify_request(report, memory_report),
                    report,
                    memory_report
                ),
                "domain_experts_used": [
                    name
                    for name in plan
                    if name not in {
                        "Memory_brain", "Emotion_brain", "Security_brain",
                        "Manager_brain", "Quality_Control_brain", "Response_brain",
                        "Learning_brain", "Collaboration_brain",
                        "Nervous_system_brain"
                    }
                ],
                "collaboration_used": "Collaboration_brain" in plan,
                "quality_retry_count": sum(self._retry_counts.values()),
                "scanner_collections_available": sorted({
                    str(item.get("collection", "trusted_knowledge"))
                    for item in shared_knowledge.get("matches", [])
                    if isinstance(item, dict)
                }),
            },
            "missing_or_skipped": {
                name: result
                for name, result in results.items()
                if isinstance(result, dict)
                and (
                    result.get("skipped")
                    or result.get("error")
                )
            },
            "rules": [
                "Use Understanding_brain and Memory_brain context as the base.",
                "Run safety/context brains before domain experts.",
                "Route each topic to the strongest registered expert brain.",
                "Keep skipped or failing brains visible instead of hiding them.",
                "Return a phased plan so Canri can explain how it worked."
            ]
        }

        self.execution_history.append({
            "created_utc": manager_report["created_utc"],
            "domains": manager_report["domains_detected"],
            "brains_used": plan,
            "system_confidence": manager_report["system_confidence"]
        })

        self.execution_history = self.execution_history[-200:]

        brain_runtime.flush_statistics()

        return manager_report


brain = ManagerBrain()
