"""
Technology_brain.py
Canri AI

תפקיד:
מוח מומחה לטכנולוגיה, תוכנה, חומרה, רשתות, AI, רובוטיקה,
סייבר, מערכות, API, דאטה וארכיטקטורה טכנולוגית.

הוא עובד לפי הכלל של Canri:
הוא לא מנחש מהטקסט הגולמי בלבד. הוא קורא את הדוח של
Understanding_brain, משתמש ב-main_topic / intent / possible_tasks /
words / connections, מחפש ידע מקומי, ואם אין מספיק ידע מפעיל
Research_brain כדי לקבל מקורות אמינים.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_runtime import invoke_brain_safely
from Brain_storage import atomic_write_json
from domain_packages.understanding.context import stop_terms as understanding_stop_terms

from Scanner_knowledge import scanner_evidence


DATA_DIR = Path(__file__).parent / "data"
TERMS_PATH = DATA_DIR / "Technology_terms.json"
HARDWARE_PATH = DATA_DIR / "Hardware_dictionary.json"
STACKS_PATH = DATA_DIR / "Tech_stack_templates.json"
STATISTICS_PATH = DATA_DIR / "Technology_statistics.json"

LOCAL_CONFIDENCE_THRESHOLD = 55
MAX_LOCAL_RESULTS = 6

class TechnologyBrain:

    def __init__(self):

        self.terms = self._load_json(
            TERMS_PATH,
            {}
        )

        self.hardware = self._load_json(
            HARDWARE_PATH,
            {}
        )

        self.stack_templates = self._load_json(
            STACKS_PATH,
            {}
        )

        self.statistics = self._load_json(
            STATISTICS_PATH,
            {}
        )

        print("Technology Brain Loaded")

    # ---------- loading ----------

    def _load_json(
        self,
        path,
        default
    ):

        if not path.exists():
            return default

        try:

            with path.open(
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(
                    file
                )

        except (OSError, json.JSONDecodeError):
            return default

    def _save_statistics(self):

        atomic_write_json(STATISTICS_PATH, self.statistics)

    # ---------- understanding report ----------

    def get_understanding_report(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return {}

        understanding = data.get(
            "understanding",
            {}
        )

        if isinstance(
            understanding,
            dict
        ) and (
            "words" in understanding
            or "main_topic" in understanding
            or "intent" in understanding
        ):

            return understanding

        if (
            "words" in data
            or "main_topic" in data
            or "intent" in data
        ):

            return data

        return {}

    def extract_text(
        self,
        data,
        report
    ):

        parts = []

        if isinstance(
            data,
            str
        ):

            parts.append(
                data
            )

        if isinstance(
            data,
            dict
        ):

            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "query",
                "text"
            ]:

                value = data.get(
                    key
                )

                if value:
                    parts.append(
                        str(value)
                    )

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value:
                parts.append(
                    str(value)
                )

        return " ".join(
            parts
        )

    def collect_terms_from_report(
        self,
        report,
        fallback_text
    ):

        terms = []

        for key in [
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value and value != "unknown":
                terms.append(
                    str(value)
                )

        topics = report.get(
            "topics",
            {}
        )

        if isinstance(
            topics,
            dict
        ):

            for topic in topics:
                terms.append(
                    str(topic)
                )

        for task in report.get(
            "possible_tasks",
            []
        ):

            terms.append(
                str(task).replace(
                    "_",
                    " "
                )
            )

        for word_data in report.get(
            "words",
            []
        ):

            if not isinstance(
                word_data,
                dict
            ):

                continue

            word = str(
                word_data.get(
                    "word",
                    ""
                )
            ).strip()

            if (
                word
                and len(word) > 2
                and word_data.get(
                    "exists",
                    True
                )
                and not word_data.get("is_stop_word")
            ):

                terms.append(
                    word
                )

            for connection in word_data.get(
                "connections",
                []
            )[:8]:

                terms.append(
                    str(connection)
                )

        for token in re.findall(
            r"[a-zA-Z][a-zA-Z0-9_\-\+\.]{1,}",
            fallback_text
        ):

            terms.append(
                token
            )

        clean_terms = []
        blocked = understanding_stop_terms(report)

        for term in terms:

            term = re.sub(
                r"[^a-zA-Z0-9_\-\+\.\s]",
                " ",
                term
            )

            term = re.sub(
                r"\s+",
                " ",
                term
            ).strip().lower()

            if (
                term
                and len(term) > 1
                and term not in blocked
                and term not in clean_terms
            ):

                clean_terms.append(
                    term
                )

        return clean_terms

    # ---------- detection ----------

    def detect_intent(
        self,
        report,
        terms,
        text
    ):

        intent = str(
            report.get(
                "intent",
                ""
            )
        ).lower()

        if intent and intent not in {"unknown", "request"}:
            return intent

        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        requested_action = report.get("requested_action", {})
        requested_action = requested_action if isinstance(requested_action, dict) else {}
        for value in (
            requested_action.get("intent_override"),
            contract.get("intent"),
            contract.get("action"),
        ):
            value = str(value or "").strip().casefold()
            if value and value not in {"unknown", "request"}:
                return value

        return "analysis"

    def detect_domain(
        self,
        report,
        local_matches
    ):
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        candidates = []
        for item in [
            *report.get("central_domains", []),
            *contract.get("central_domains", []),
        ]:
            candidates.append(item.get("domain") if isinstance(item, dict) else item)
        candidates.extend([report.get("main_topic"), contract.get("topic")])
        for candidate in candidates:
            candidate = str(candidate or "").strip().casefold()
            if candidate not in {"", "unknown", "request", "technology"}:
                return candidate

        if local_matches:
            top = local_matches[0]
            data = top.get("data", {}) if isinstance(top, dict) else {}
            if isinstance(data, dict):
                for field in ("domain", "category", "type", "field"):
                    value = str(data.get(field) or "").strip().casefold()
                    if value:
                        return value
            match_type = str(top.get("type") or "").strip().casefold()
            if match_type:
                return match_type.removesuffix("_component").removesuffix("_term")
        return "technology"

    # ---------- local search ----------

    def _score_text(
        self,
        text,
        terms,
        weight
    ):

        lowered = text.lower()

        matches = [
            term
            for term in terms
            if term and term in lowered
        ]

        return len(
            matches
        ) * weight, matches

    def search_terms(
        self,
        terms
    ):

        results = []

        for name, item in self.terms.items():

            searchable = " ".join([
                name,
                item.get(
                    "domain",
                    ""
                ),
                item.get(
                    "definition",
                    ""
                ),
                " ".join(
                    item.get(
                        "related",
                        []
                    )
                ),
                " ".join(
                    item.get(
                        "use_cases",
                        []
                    )
                )
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                3
            )

            if name in terms:
                score += 8
                matches.append(
                    name
                )

            if score:

                results.append({
                    "type": "technology_term",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": item
                })

        return results

    def search_hardware(
        self,
        terms
    ):

        results = []

        for name, item in self.hardware.items():

            searchable = " ".join([
                name,
                item.get(
                    "category",
                    ""
                ),
                item.get(
                    "role",
                    ""
                ),
                " ".join(
                    item.get(
                        "important_specs",
                        []
                    )
                ),
                " ".join(
                    item.get(
                        "compatibility_checks",
                        []
                    )
                )
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                4
            )

            if name in terms:
                score += 10
                matches.append(
                    name
                )

            if score:

                results.append({
                    "type": "hardware_component",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": item
                })

        return results

    def search_stacks(
        self,
        terms
    ):

        results = []

        for name, item in self.stack_templates.items():

            searchable = " ".join([
                name,
                item.get(
                    "goal",
                    ""
                ),
                " ".join(
                    item.get(
                        "recommended_stack",
                        []
                    )
                ),
                " ".join(
                    item.get(
                        "components",
                        []
                    )
                ),
                " ".join(
                    item.get(
                        "risks",
                        []
                    )
                )
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                2
            )

            if score:

                results.append({
                    "type": "stack_template",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": item
                })

        return results

    def search_local_knowledge(
        self,
        terms
    ):

        results = (
            self.search_terms(
                terms
            )
            +
            self.search_hardware(
                terms
            )
            +
            self.search_stacks(
                terms
            )
        )

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:MAX_LOCAL_RESULTS]

    # ---------- output building ----------

    def calculate_confidence(
        self,
        local_matches,
        terms
    ):

        if not local_matches:
            return 0

        top_score = local_matches[0]["score"]
        matched_terms = set()

        for match in local_matches[:3]:
            matched_terms.update(
                match.get(
                    "matches",
                    []
                )
            )

        coverage = 0

        if terms:
            coverage = (
                len(matched_terms)
                /
                max(
                    len(terms[:12]),
                    1
                )
            ) * 100

        confidence = min(
            (top_score * 8) + (coverage * 0.5),
            100
        )

        return round(
            confidence,
            2
        )

    def collect_recommendations(
        self,
        local_matches
    ):

        components = []
        risks = []
        stack = []
        next_brains = []

        for match in local_matches:

            data = match.get(
                "data",
                {}
            )

            components.extend(
                data.get(
                    "related",
                    []
                )
            )

            components.extend(
                data.get(
                    "components",
                    []
                )
            )

            components.extend(
                data.get(
                    "important_specs",
                    []
                )
            )

            risks.extend(
                data.get(
                    "risks",
                    []
                )
            )

            risks.extend(
                data.get(
                    "common_bottlenecks",
                    []
                )
            )

            stack.extend(
                data.get(
                    "recommended_stack",
                    []
                )
            )

            next_brains.extend(
                data.get(
                    "next_brains",
                    []
                )
            )

        return {
            "recommended_components": list(
                dict.fromkeys(
                    components
                )
            )[:12],
            "recommended_stack": list(
                dict.fromkeys(
                    stack
                )
            )[:12],
            "risks": list(
                dict.fromkeys(
                    risks
                )
            )[:10],
            "suggested_next_brains": list(
                dict.fromkeys(
                    next_brains
                )
            )[:8]
        }

    def build_answer(
        self,
        domain,
        local_matches,
        recommendations,
        research_result=None
    ):

        parts = []

        if local_matches:
            top = local_matches[0]
            item = top.get("data", {})
            name = str(top.get("name") or domain).replace("_", " ")
            definition = (
                item.get("definition")
                or item.get("role")
                or item.get("goal")
                or item.get("description")
            )
            if definition:
                parts.append(f"{name.title()}: {str(definition).strip()}")

        components = recommendations.get("recommended_components", [])
        stack = recommendations.get("recommended_stack", [])
        risks = recommendations.get("risks", [])
        if components:
            parts.append(
                "Important components or checks: "
                + ", ".join(map(str, components[:6]))
                + "."
            )
        if stack:
            parts.append(
                "Suitable stack: " + ", ".join(map(str, stack[:6])) + "."
            )
        if risks:
            parts.append(
                "Main risks or limits: " + ", ".join(map(str, risks[:5])) + "."
            )

        if not parts and isinstance(research_result, dict):
            for key in ["answer", "summary", "final_output"]:
                value = research_result.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
                    break

        if not parts:
            parts.append(
                f"The request concerns {domain.replace('_', ' ')}. "
                "More verified technical context is required before a specific recommendation."
            )

        return "\n\n".join(parts)

    def source_citations(self, scanner_articles, research_result=None):

        citations = []
        for article in scanner_articles[:6]:
            sources = article.get("sources", [])
            citations.extend(source for source in sources if isinstance(source, dict))
            if not sources and article.get("url"):
                citations.append({
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "trust_score": article.get("trust_score", 0)
                })

        if isinstance(research_result, dict):
            for key in ["source_citations", "strongest_sources", "fetched_sources"]:
                citations.extend(
                    item for item in research_result.get(key, [])
                    if isinstance(item, dict)
                )

        unique = []
        seen = set()
        for item in citations:
            identity = (
                item.get("url")
                or item.get("source_id")
                or item.get("title")
                or item.get("source_name")
            )
            if not identity or identity in seen:
                continue
            seen.add(identity)
            unique.append(item)

        return unique[:8]

    def detect_needs(
        self,
        local_matches,
        intent,
        domain,
        confidence
    ):

        needs_code = False
        needs_security = False

        for match in local_matches:

            data = match.get(
                "data",
                {}
            )

            if data.get(
                "needs_code"
            ):
                needs_code = True

            if data.get(
                "needs_security"
            ):
                needs_security = True

        if intent in [
            "code_generation",
            "architecture_planning"
        ]:
            needs_code = True

        if domain in [
            "security",
            "robotics"
        ]:
            needs_security = True

        return {
            "needs_code": needs_code,
            "needs_security": needs_security,
            "needs_research": confidence < LOCAL_CONFIDENCE_THRESHOLD,
            "needs_planner": intent in [
                "architecture_planning",
                "project_planning",
                "code_generation"
            ],
            "needs_hardware_check": domain in [
                "hardware",
                "robotics",
                "electronics"
            ]
        }

    def build_research_payload(
        self,
        report,
        text,
        terms,
        domain,
        intent
    ):

        query = " ".join(
            list(
                dict.fromkeys(
                    [domain, intent] + terms[:10] + [text]
                )
            )
        )

        payload = dict(
            report
        )

        payload.update({
            "original_text": text,
            "main_topic": "technology",
            "intent": intent,
            "query": query,
            "technology_domain": domain,
            "technology_terms": terms
        })

        return payload

    def run_research_fallback(
        self,
        payload
    ):

        try:

            from Research_brain import ResearchBrain

            research_brain = ResearchBrain()

            return invoke_brain_safely(
                "Research_brain",
                research_brain,
                payload,
                phase="technology_research_fallback",
                request_id=payload.get("_request_id") if isinstance(payload, dict) else None
            )

        except Exception:

            return {
                "brain": "Research_brain",
                "error": "research_fallback_unavailable",
                "user_safe_error": "Technology research support is currently unavailable.",
                "verified": False,
                "confidence": 0
            }

    def update_statistics(
        self,
        confidence,
        domain,
        intent
    ):

        stats = self.statistics.get(
            "Technology_brain",
            {}
        )

        stats["uses"] = stats.get(
            "uses",
            0
        ) + 1

        stats["last_confidence"] = confidence
        stats["last_domain"] = domain
        stats["last_intent"] = intent
        stats["last_used_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

        self.statistics["Technology_brain"] = stats

        self._save_statistics()

    # ---------- process ----------

    def process(
        self,
        data
    ):

        report = self.get_understanding_report(
            data
        )

        text = self.extract_text(
            data,
            report
        )

        terms = self.collect_terms_from_report(
            report,
            text
        )

        local_matches = self.search_local_knowledge(
            terms
        )

        domain = self.detect_domain(
            report,
            local_matches
        )

        intent = self.detect_intent(
            report,
            terms,
            text
        )
        scanner_articles = scanner_evidence(data, limit=5)

        confidence = self.calculate_confidence(
            local_matches,
            terms
        )

        if scanner_articles:
            scanner_trust = max(
                float(item.get("trust_score", 0) or 0)
                for item in scanner_articles
            )
            confidence = max(
                confidence,
                min(95, round(scanner_trust, 2))
            )

        recommendations = self.collect_recommendations(
            local_matches
        )

        needs = self.detect_needs(
            local_matches,
            intent,
            domain,
            confidence
        )

        research_result = None

        if needs["needs_research"]:

            research_payload = self.build_research_payload(
                report,
                text,
                terms,
                domain,
                intent
            )

            research_result = self.run_research_fallback(
                research_payload
            )

        answer = self.build_answer(
            domain,
            local_matches,
            recommendations,
            research_result
        )

        source_citations = self.source_citations(
            scanner_articles,
            research_result
        )

        self.update_statistics(
            confidence,
            domain,
            intent
        )

        return {
            "brain": "Technology_brain",
            "answer": answer,
            "summary": answer,
            "used_understanding_report": bool(report),
            "technology_domain": domain,
            "intent": intent,
            "terms_used": terms,
            "confidence": confidence,
            "local_knowledge_found": len(local_matches),
            "scanner_articles_found": len(scanner_articles),
            "scanner_evidence": scanner_articles,
            "source_citations": source_citations,
            "local_matches": [
                {
                    "type": match["type"],
                    "name": match["name"],
                    "score": match["score"],
                    "matches": match["matches"],
                    "data": match["data"]
                }
                for match in local_matches
            ],
            "recommended_components": recommendations["recommended_components"],
            "recommended_stack": recommendations["recommended_stack"],
            "risks": recommendations["risks"],
            "suggested_next_brains": list(
                dict.fromkeys(
                    recommendations["suggested_next_brains"]
                    +
                    [
                        brain_name
                        for brain_name, enabled in [
                            ("Code_brain", needs["needs_code"]),
                            ("Security_brain", needs["needs_security"]),
                            ("Research_brain", needs["needs_research"]),
                            ("Planner_brain", needs["needs_planner"])
                        ]
                        if enabled
                    ]
                )
            ),
            "needs_code": needs["needs_code"],
            "needs_security": needs["needs_security"],
            "needs_research": needs["needs_research"],
            "needs_planner": needs["needs_planner"],
            "needs_hardware_check": needs["needs_hardware_check"],
            "research_fallback": research_result,
            "self_review": {
                "ready": bool(answer) and bool(
                    local_matches or scanner_articles or research_result
                ),
                "domain_aligned": domain != "technology" or bool(terms),
                "evidence_available": bool(source_citations or local_matches)
            },
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Search local technology and hardware knowledge first.",
                "If local confidence is low, call Research_brain for trusted sources.",
                "Do not write code directly; route implementation work to Code_brain.",
                "Route unsafe or security-sensitive topics to Security_brain.",
                "For hardware, check compatibility, power, heat, and physical constraints."
            ]
        }


brain = TechnologyBrain()
