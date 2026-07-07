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
from datetime import datetime, timezone
from pathlib import Path

try:
    from Data_context import search_data_context
except Exception:
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


class ManagerBrain:

    def __init__(self):

        self.brains = {}
        self.execution_history = []
        self.company_products = self.load_json(COMPANY_PRODUCTS_FILE, {})

        print("Manager Brain Loaded")

    def load_json(self, path, default):

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    # ---------- registration ----------

    def register_brain(self, name, brain_object):

        if not name or brain_object is None:
            return

        self.brains[name] = brain_object

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
            "source": "Knowledge_database",
            "queue_update": {}
        }

        if not query or search_knowledge is None:
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
        term_text = " ".join(terms + [raw_text])

        domains = []

        domain_rules = [
            ("code", ["code", "program", "python", "javascript", "java", "function", "api", "json"]),
            ("science", ["science", "physics", "chemistry", "biology", "article", "experiment"]),
            ("language", ["language", "translation", "translate", "grammar", "synonym", "antonym"]),
            ("geography", ["geography", "country", "city", "capital", "map", "gps", "river", "mountain"]),
            ("technology", ["technology", "hardware", "computer", "cpu", "gpu", "robot", "server"]),
            ("history", ["history", "historical", "empire", "war", "ancient"]),
            ("math", ["math", "number", "equation", "calculate", "algebra"]),
            ("security", ["security", "password", "token", "encrypt", "danger", "bomb", "suicide"]),
            ("vision", ["vision", "image", "photo", "picture", "video", "file", "attachment", "pdf", "png", "jpg", "mp4"]),
            ("voice", ["voice", "audio", "sound", "recording", "microphone", "speech", "transcribe", "wav", "mp3", "m4a"]),
            ("creative", ["creative", "creativity", "idea", "invent", "original", "brainstorm", "stuck", "fallback"]),
            ("story", ["story", "stories", "sentence", "sentences", "chapter", "character", "plot", "narrative", "leo", "tiny door"]),
            ("game", ["game", "player", "enemy", "level", "inventory"])
        ]

        for domain, keywords in domain_rules:
            if topic == domain or intent == domain or any(keyword in term_text for keyword in keywords):
                domains.append(domain)

        if intent == "code_generation":
            domains.append("code")

        if intent in ["question", "research"]:
            domains.append("research")

        explicit_story_request = (
            "story" in domains
            and any(
                marker in raw_text
                for marker in [
                    "story",
                    "stories",
                    "sentences",
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

    def build_plan(self, report, memory_report=None):

        memory_report = memory_report or {}
        domains = self.classify_request(report, memory_report)

        phases = [
            {
                "phase": "safety_and_context",
                "brains": [
                    "Emotion_brain",
                    "Security_brain"
                ]
            },
            {
                "phase": "core_reasoning",
                "brains": [
                    "Planner_brain"
                ]
            },
            {
                "phase": "domain_experts",
                "brains": []
            },
            {
                "phase": "verification",
                "brains": [
                    "Fact_Check_brain",
                    "Learning_brain"
                ]
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

        if "voice" in domains:
            experts.extend([
                "Voice_brain",
                "Vision_brain",
                "Security_brain"
            ])

        if "creative" in domains:
            experts.extend([
                "Creative_brain",
                "Planner_brain"
            ])

        if "story" in domains:
            experts.extend([
                "Creative_brain",
                "Story_brain",
                "Character_brain",
                "World_brain"
            ])

        if "game" in domains:
            experts.extend([
                "Game_brain",
                "Creative_brain",
                "Technology_brain",
                "Planner_brain"
            ])

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

    def build_context(self, original_data, report, memory_report, phase, results):

        context = {}

        if isinstance(original_data, dict):
            context.update(original_data)
        else:
            context["original_text"] = str(original_data)

        context["understanding"] = report
        context["memory"] = memory_report
        context["dictionary"] = context.get("dictionary") or self.build_dictionary_context(
            original_data,
            report,
            memory_report
        )
        context["data_context"] = context.get("data_context") or self.build_local_data_context(
            original_data,
            report,
            memory_report
        )
        context["knowledge"] = context.get("knowledge") or self.build_knowledge_context(
            original_data,
            report,
            memory_report
        )
        context["manager_context"] = {
            "phase": phase,
            "previous_results": results,
            "available_brains": sorted(self.brains.keys()),
            "dictionary": context["dictionary"],
            "data_context": context["data_context"],
            "knowledge": context["knowledge"]
        }

        return context

    def execute(self, selected_brains, data, report=None, memory_report=None, phase="single"):

        results = {}
        report = report or self.get_understanding_report(data)
        memory_report = memory_report or self.get_memory_report(data)

        for brain_name in selected_brains:

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
                results
            )

            try:
                result = brain.process(context)
                result = self.attach_creative_help_if_needed(
                    brain_name,
                    result,
                    context,
                    phase
                )
                results[brain_name] = result
                self.emit_progress(
                    data,
                    "brain_done",
                    f"Finished {brain_name}",
                    brain_name,
                    phase,
                    result
                )

            except Exception as error:
                error_result = {
                    "error": str(error),
                    "phase": phase
                }
                error_result = self.attach_creative_help_if_needed(
                    brain_name,
                    error_result,
                    context,
                    phase
                )
                results[brain_name] = error_result
                self.emit_progress(
                    data,
                    "brain_error",
                    f"{brain_name} failed",
                    brain_name,
                    phase,
                    error_result
                )

        return results

    def needs_creative_help(self, brain_name, result):

        if brain_name in [
            "Creative_brain",
            "Security_brain",
            "Response_brain",
            "Fact_Check_brain",
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

            results = self.execute(
                phase_brains,
                phase_context,
                report,
                memory_report,
                phase_name
            )

            all_results.update(results)

            phase_results.append({
                "phase": phase_name,
                "brains": phase_brains,
                "results": results
            })

            memory_result = results.get("Memory_brain")
            if isinstance(memory_result, dict) and isinstance(memory_result.get("memory"), dict):
                memory_report = memory_result["memory"]

        return all_results, phase_results

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

    # ---------- process ----------

    def process(self, data):

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

        if isinstance(data, dict):
            data = dict(data)
            data["knowledge"] = shared_knowledge
            data["dictionary"] = shared_dictionary
            data["data_context"] = shared_data_context

        phases = self.build_plan(report, memory_report)
        plan = self.flatten_plan(phases)

        results, phase_results = self.execute_phases(
            phases,
            data,
            report,
            memory_report
        )

        manager_report = {
            "brain": "Manager_brain",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "domains_detected": self.classify_request(report, memory_report),
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
            "suggested_next_brains": self.collect_suggested_next_brains(results),
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

        return manager_report


brain = ManagerBrain()
