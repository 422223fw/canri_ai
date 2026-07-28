"""
Geography_brain.py
Canri AI

תפקיד:
מוח מומחה לגיאוגרפיה: מדינות, ערים, אזורים, מפות, GPS,
קואורדינטות, אקלים, גבולות, נהרות, הרים, ימים ומקומות בעולם.

הוא עובד לפי כלל Canri:
מקבל דוח Understanding_brain, מחפש ידע מקומי, ואם צריך מידע
עדכני או מיקום מדויק הוא מפעיל/מכין fallback ל-Research_brain.
"""

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_runtime import invoke_brain_safely
from Brain_storage import atomic_write_json
from domain_packages.understanding.context import stop_terms as understanding_stop_terms

from Scanner_knowledge import scanner_evidence


DATA_DIR = Path(__file__).parent / "data"
PLACES_PATH = DATA_DIR / "Geography_places.json"
CONCEPTS_PATH = DATA_DIR / "Geography_concepts.json"
REGIONS_PATH = DATA_DIR / "Geography_regions.json"
STATISTICS_PATH = DATA_DIR / "Geography_statistics.json"
INDEX_PATH = DATA_DIR / "Geography_index.json"
RELATIONS_PATH = DATA_DIR / "Geography_relations.json"
QUERY_PATTERNS_PATH = DATA_DIR / "Geography_query_patterns.json"
CREATIVE_PROFILES_PATH = DATA_DIR / "Geography_creative_profiles.json"

LOCAL_CONFIDENCE_THRESHOLD = 55
MAX_LOCAL_RESULTS = 6

class GeographyBrain:

    def __init__(self):

        self.places = self._load_json(
            PLACES_PATH,
            {}
        )

        self.concepts = self._load_json(
            CONCEPTS_PATH,
            {}
        )

        self.regions = self._load_json(
            REGIONS_PATH,
            {}
        )

        self.statistics = self._load_json(
            STATISTICS_PATH,
            {}
        )

        self.index = self._load_json(INDEX_PATH, {})
        self.relations = self._load_json(RELATIONS_PATH, {})
        self.query_patterns = self._load_json(QUERY_PATTERNS_PATH, {})
        self.creative_profiles = self._load_json(CREATIVE_PROFILES_PATH, {})
        self.search_index = self._prepare_search_index()
        self.alias_index = self._prepare_alias_index()

        print("Geography Brain Loaded")

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

    def _prepare_search_index(self):

        terms = self.index.get("terms", {}) if isinstance(self.index, dict) else {}
        if terms:
            return {
                str(term).lower(): list(dict.fromkeys(refs))
                for term, refs in terms.items()
                if isinstance(refs, list)
            }

        generated = {}
        collections = {
            "place": self.places,
            "concept": self.concepts,
            "region": self.regions,
        }
        for record_type, records in collections.items():
            for name, record in records.items():
                values = [name]
                for key in ["aliases", "keywords", "nearby"]:
                    value = record.get(key, [])
                    values.extend(value if isinstance(value, list) else [value])
                values.extend(
                    record.get(key, "")
                    for key in ["type", "country", "continent", "region", "capital"]
                )
                reference = f"{record_type}:{name}"
                for value in values:
                    for token in self._tokenize(value):
                        generated.setdefault(token, []).append(reference)
        return {term: list(dict.fromkeys(refs)) for term, refs in generated.items()}

    def _prepare_alias_index(self):

        exact = self.index.get("exact", {}) if isinstance(self.index, dict) else {}
        aliases = {
            str(alias).lower(): list(dict.fromkeys(refs))
            for alias, refs in exact.items()
            if isinstance(refs, list)
        }
        if aliases:
            return aliases

        for prefix, records in [
            ("place", self.places),
            ("concept", self.concepts),
            ("region", self.regions),
        ]:
            for name, record in records.items():
                reference = f"{prefix}:{name}"
                for alias in [name] + record.get("aliases", []):
                    aliases.setdefault(str(alias).lower(), []).append(reference)
        return aliases

    def _tokenize(self, value):

        return list(dict.fromkeys(re.findall(
            r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9'\-\u0590-\u05FF]{1,}",
            str(value).lower()
        )))

    def _phrase_in_text(self, phrase, text):

        return re.search(
            rf"(?<![\w]){re.escape(str(phrase).lower())}(?![\w])",
            str(text).lower()
        ) is not None

    def _candidate_references(self, terms, text=""):

        references = []
        exact_references = []
        lowered = str(text).lower()
        for alias, refs in sorted(
            self.alias_index.items(),
            key=lambda item: len(item[0]),
            reverse=True
        ):
            if len(alias) > 2 and self._phrase_in_text(alias, lowered):
                exact_references.extend(refs)

        if exact_references:
            return list(dict.fromkeys(exact_references))[:80]

        query_tokens = []
        for term in terms:
            query_tokens.extend(self._tokenize(term))
            if term in self.search_index:
                references.extend(self.search_index[term])
        for token in query_tokens:
            references.extend(self.search_index.get(token, []))

        return list(dict.fromkeys(references))

    # ---------- Understanding report ----------

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
                "user_message",
                "original_text",
                "corrected_text",
                "question",
                "query",
                "text",
                "location",
                "place"
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
        ).strip()

    def collect_terms(
        self,
        report,
        text
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
                and len(word) > 1
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

        tokens = re.findall(
            r"[a-zA-Z\u0590-\u05FF][a-zA-Z\u0590-\u05FF'\-\.]{1,}",
            text
        )

        terms.extend(
            tokens
        )

        clean_terms = []
        blocked = understanding_stop_terms(report)

        for term in terms:

            term = re.sub(
                r"\s+",
                " ",
                term
            ).strip().lower()

            if (
                term
                and term not in blocked
                and term not in clean_terms
            ):

                clean_terms.append(
                    term
                )

        # Prefer exact indexed names and aliases for phrases such as "new york city".
        lowered = text.lower()

        for name in sorted(self.alias_index, key=len, reverse=True):

            if len(name) > 2 and self._phrase_in_text(name, lowered) and name not in clean_terms:
                clean_terms.insert(
                    0,
                    name
                )

        return clean_terms

    # ---------- intent/type detection ----------

    def detect_geography_intent(
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

        lowered = text.lower()

        best_pattern = None
        best_score = 0
        pattern_values = (
            self.query_patterns.values()
            if isinstance(self.query_patterns, dict)
            else self.query_patterns
        )
        for pattern in pattern_values:
            if not isinstance(pattern, dict):
                continue
            score = sum(
                1
                for marker in pattern.get("markers", [])
                if str(marker).lower() in lowered
            )
            if score > best_score:
                best_pattern = pattern
                best_score = score

        if best_pattern and best_score:
            return best_pattern.get("intent", "geography_explanation")

        if any(
            word in lowered
            for word in [
                "where is",
                "איפה",
                "location",
                "gps",
                "coordinates"
            ]
        ):

            return "location_lookup"

        if any(
            word in lowered
            for word in [
                "capital",
                "עיר בירה"
            ]
        ):

            return "capital_lookup"

        if any(
            word in lowered
            for word in [
                "weather",
                "forecast",
                "מזג אוויר"
            ]
        ):

            return "weather_lookup"

        if any(
            word in lowered
            for word in [
                "population",
                "אוכלוסייה",
                "people live"
            ]
        ):

            return "population_lookup"

        if any(
            word in lowered
            for word in [
                "map",
                "route",
                "distance",
                "מפה",
                "מרחק",
                "מסלול"
            ]
        ):

            return "map_or_distance"

        if intent:
            return intent

        return "geography_explanation"

    def detect_geo_type(
        self,
        local_matches,
        terms
    ):

        if local_matches:
            data = local_matches[0].get(
                "data",
                {}
            )
            if data.get(
                "type"
            ):
                return data.get(
                    "type"
                )

        for concept in [
            "country",
            "city",
            "river",
            "mountain",
            "desert",
            "ocean",
            "sea",
            "region",
            "gps",
            "climate"
        ]:

            if concept in terms:
                return concept

        return "place_or_region"

    # ---------- search ----------

    def _score_text(
        self,
        text,
        terms,
        weight
    ):

        lowered = text.lower()
        matches = []

        for term in terms:

            if term and term in lowered:
                matches.append(
                    term
                )

        return len(
            matches
        ) * weight, sorted(
            set(matches)
        )

    def search_places(
        self,
        terms,
        text=""
    ):

        results = []
        candidate_references = self._candidate_references(terms, text)
        candidate_names = [
            reference.split(":", 1)[1]
            for reference in candidate_references
            if reference.startswith("place:")
        ]
        records = (
            ((name, self.places[name]) for name in candidate_names if name in self.places)
            if candidate_references
            else self.places.items()
        )

        for name, data in records:

            searchable = " ".join([
                name,
                data.get(
                    "type",
                    ""
                ),
                data.get(
                    "country",
                    ""
                ),
                data.get(
                    "continent",
                    ""
                ),
                data.get(
                    "region",
                    ""
                ),
                data.get(
                    "capital",
                    ""
                ),
                data.get(
                    "summary",
                    ""
                ),
                " ".join(
                    data.get(
                        "key_facts",
                        []
                    )
                ),
                " ".join(
                    data.get(
                        "nearby",
                        []
                    )
                ),
                " ".join(
                    data.get(
                        "keywords",
                        []
                    )
                ),
                " ".join(data.get("aliases", [])),
                " ".join(data.get("languages", [])),
                " ".join(data.get("landforms", []))
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                3
            )

            if name in terms:
                score += 12
                matches.append(
                    name
                )

            if self._phrase_in_text(name, text):
                score += 20
                matches.append(
                    name
                )

            if score:
                results.append({
                    "type": "place",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": data
                })

        return results

    def search_concepts(
        self,
        terms,
        text=""
    ):

        results = []
        candidate_references = self._candidate_references(terms, text)
        candidate_names = [
            reference.split(":", 1)[1]
            for reference in candidate_references
            if reference.startswith("concept:")
        ]
        records = (
            ((name, self.concepts[name]) for name in candidate_names if name in self.concepts)
            if candidate_references
            else self.concepts.items()
        )

        for name, data in records:

            searchable = " ".join([
                name,
                data.get(
                    "definition",
                    ""
                ),
                " ".join(
                    data.get(
                        "keywords",
                        []
                    )
                ),
                " ".join(data.get("aliases", [])),
                " ".join(data.get("examples", []))
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                2
            )

            if name in terms:
                score += 8
                matches.append(
                    name
                )

            if score:
                results.append({
                    "type": "concept",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": data
                })

        return results

    def search_regions(
        self,
        terms,
        text=""
    ):

        results = []
        candidate_references = self._candidate_references(terms, text)
        candidate_names = [
            reference.split(":", 1)[1]
            for reference in candidate_references
            if reference.startswith("region:")
        ]
        records = (
            ((name, self.regions[name]) for name in candidate_names if name in self.regions)
            if candidate_references
            else self.regions.items()
        )

        for name, data in records:

            searchable = " ".join([
                name,
                data.get(
                    "continent",
                    ""
                ),
                data.get(
                    "description",
                    ""
                ),
                " ".join(
                    data.get(
                        "keywords",
                        []
                    )
                ),
                " ".join(data.get("countries", [])),
                " ".join(data.get("major_places", []))
            ])

            score, matches = self._score_text(
                searchable,
                terms,
                2
            )

            if name in terms:
                score += 10
                matches.append(
                    name
                )

            if score:
                results.append({
                    "type": "region",
                    "name": name,
                    "score": score,
                    "matches": sorted(
                        set(matches)
                    ),
                    "data": data
                })

        return results

    def search_local_knowledge(
        self,
        terms,
        text=""
    ):

        results = (
            self.search_places(
                terms,
                text
            )
            +
            self.search_concepts(
                terms,
                text
            )
            +
            self.search_regions(
                terms,
                text
            )
        )

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:MAX_LOCAL_RESULTS]

    # ---------- output ----------

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

        return round(
            min(
                (top_score * 7) + (coverage * 0.5),
                100
            ),
            2
        )

    def build_facts(
        self,
        local_matches
    ):

        facts = []

        for match in local_matches[:3]:

            data = match.get(
                "data",
                {}
            )

            if data.get(
                "summary"
            ):
                facts.append(
                    data["summary"]
                )

            facts.extend(
                data.get(
                    "key_facts",
                    []
                )[:3]
            )

            if data.get(
                "definition"
            ):
                facts.append(
                    data["definition"]
                )

            if data.get(
                "description"
            ):
                facts.append(
                    data["description"]
                )

        return list(
            dict.fromkeys(
                facts
            )
        )[:10]

    def related_places(self, place_name, limit=12):

        if not place_name:
            return []
        relation_data = self.relations.get(place_name, {})
        if isinstance(relation_data, list):
            return relation_data[:limit]
        if not isinstance(relation_data, dict):
            return []

        related = []
        for relation_type, targets in relation_data.items():
            if not isinstance(targets, list):
                continue
            for target in targets:
                if isinstance(target, dict):
                    value = dict(target)
                    value.setdefault("relation", relation_type)
                else:
                    value = {"name": str(target), "relation": relation_type}
                related.append(value)
        return related[:limit]

    def hierarchy_for_match(self, match):

        data = match.get("data", {}) if match else {}
        values = []
        for level in ["continent", "region", "country", "administrative_area"]:
            if data.get(level):
                values.append({"level": level, "name": data[level]})
        if match and match.get("name"):
            values.append({"level": data.get("type", match.get("type")), "name": match["name"]})
        return values

    def haversine_distance_km(self, left, right):

        try:
            lat1 = math.radians(float(left["lat"]))
            lon1 = math.radians(float(left["lon"]))
            lat2 = math.radians(float(right["lat"]))
            lon2 = math.radians(float(right["lon"]))
        except (KeyError, TypeError, ValueError):
            return None

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        return round(6371.0088 * 2 * math.asin(min(1, math.sqrt(value))), 2)

    def build_structured_answer(self, intent, local_matches):

        if not local_matches:
            return {}
        top_match = local_matches[0]
        top_data = top_match.get("data", {})
        if top_match.get("type") == "concept":
            return {
                "concept": top_match.get("name"),
                "category": top_data.get("category"),
                "definition": top_data.get("definition"),
                "examples": top_data.get("examples", []),
                "related_concepts": top_data.get("related_concepts", [])[:8],
                "direct_answer": top_data.get("definition")
            }
        if top_match.get("type") == "region":
            return {
                "region": top_match.get("name"),
                "continent": top_data.get("continent"),
                "description": top_data.get("description"),
                "countries": top_data.get("countries", [])[:30],
                "major_places": top_data.get("major_places", [])[:20],
                "direct_answer": top_data.get("description")
            }

        place_matches = [item for item in local_matches if item.get("type") == "place"]
        if not place_matches:
            return {}
        primary = place_matches[0]
        data = primary.get("data", {})
        answer = {
            "place": primary.get("name"),
            "type": data.get("type"),
            "summary": data.get("summary"),
            "hierarchy": self.hierarchy_for_match(primary),
            "coordinates": data.get("coordinates"),
            "capital": data.get("capital"),
            "country": data.get("country"),
        }
        if intent == "capital_lookup" and data.get("capital"):
            answer["direct_answer"] = f"The capital of {primary['name'].title()} is {data['capital']}."
        elif intent == "location_lookup":
            location = ", ".join(
                str(data[key])
                for key in ["region", "country", "continent"]
                if data.get(key)
            )
            answer["direct_answer"] = f"{primary['name'].title()} is located in {location}." if location else data.get("summary")

        if len(place_matches) >= 2:
            distance = self.haversine_distance_km(
                place_matches[0].get("data", {}).get("coordinates", {}),
                place_matches[1].get("data", {}).get("coordinates", {})
            )
            if distance is not None:
                answer["straight_line_distance"] = {
                    "from": place_matches[0]["name"],
                    "to": place_matches[1]["name"],
                    "kilometers": distance,
                    "note": "Approximate great-circle distance, not a travel route."
                }
        return answer

    def detect_needs(
        self,
        intent,
        local_matches,
        confidence,
        terms
    ):

        needs_map_or_gps = intent in [
            "location_lookup",
            "map_or_distance",
            "distance_lookup",
            "route_lookup"
        ] or any(
            term in terms
            for term in [
                "gps",
                "coordinates",
                "map",
                "route",
                "distance"
            ]
        )

        needs_current_data = intent in [
            "weather_lookup",
            "population_lookup",
            "border_lookup",
            "route_lookup"
        ] or any(
            term in terms
            for term in [
                "weather",
                "forecast",
                "population",
                "current",
                "today",
                "latest",
                "border"
            ]
        )

        concept_needs_live = any(
            match["type"] == "concept"
            and match["data"].get(
                "needs_live_lookup"
            )
            for match in local_matches
        )

        needs_research = (
            confidence < LOCAL_CONFIDENCE_THRESHOLD
            or needs_current_data
            or concept_needs_live
        )

        return {
            "needs_map_or_gps": needs_map_or_gps,
            "needs_current_data": needs_current_data,
            "needs_research": needs_research
        }

    def build_research_payload(
        self,
        report,
        text,
        terms,
        intent
    ):

        query = " ".join(
            list(
                dict.fromkeys(
                    ["geography", intent] + terms[:10] + [text]
                )
            )
        )

        payload = dict(
            report
        )

        payload.update({
            "original_text": text,
            "main_topic": "geography",
            "intent": intent,
            "query": query,
            "geography_terms": terms
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
                phase="geography_research_fallback",
                request_id=payload.get("_request_id") if isinstance(payload, dict) else None
            )

        except Exception:

            return {
                "brain": "Research_brain",
                "error": "research_fallback_unavailable",
                "user_safe_error": "Geography research support is currently unavailable.",
                "verified": False,
                "confidence": 0
            }

    def update_statistics(
        self,
        confidence,
        place
    ):

        stats = self.statistics.get(
            "Geography_brain",
            {}
        )

        stats["uses"] = stats.get(
            "uses",
            0
        ) + 1

        stats["last_confidence"] = confidence
        stats["last_place"] = place
        stats["last_used_utc"] = datetime.now(
            timezone.utc
        ).isoformat()
        stats["places"] = len(self.places)
        stats["concepts"] = len(self.concepts)
        stats["regions"] = len(self.regions)
        stats["relations"] = len(self.relations)
        stats["creative_profiles"] = len(self.creative_profiles)
        stats["indexed_terms"] = len(self.search_index)

        self.statistics["Geography_brain"] = stats

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

        terms = self.collect_terms(
            report,
            text
        )

        local_matches = self.search_local_knowledge(
            terms,
            text
        )
        scanner_articles = scanner_evidence(data, limit=5)

        intent = self.detect_geography_intent(
            report,
            terms,
            text
        )

        geo_type = self.detect_geo_type(
            local_matches,
            terms
        )

        confidence = self.calculate_confidence(
            local_matches,
            terms
        )

        needs = self.detect_needs(
            intent,
            local_matches,
            confidence,
            terms
        )

        research_result = None

        if needs["needs_research"]:

            research_payload = self.build_research_payload(
                report,
                text,
                terms,
                intent
            )

            research_result = self.run_research_fallback(
                research_payload
            )

        place_detected = None

        if local_matches:
            place_detected = local_matches[0]["name"]

        structured_answer = self.build_structured_answer(intent, local_matches)
        related = self.related_places(place_detected)

        self.update_statistics(
            confidence,
            place_detected
        )

        return {
            "brain": "Geography_brain",
            "used_understanding_report": bool(report),
            "intent": intent,
            "geography_type": geo_type,
            "place_detected": place_detected,
            "terms_used": terms,
            "confidence": confidence,
            "local_knowledge_found": len(local_matches),
            "facts": self.build_facts(local_matches) + [
                {
                    "text": item.get("text"),
                    "title": item.get("title"),
                    "trust_score": item.get("trust_score"),
                    "sources": item.get("sources", [])
                }
                for item in scanner_articles
                if item.get("text")
            ],
            "scanner_articles_found": len(scanner_articles),
            "scanner_evidence": scanner_articles,
            "structured_answer": structured_answer,
            "related_places": related,
            "index_used": bool(self.search_index),
            "indexed_terms": len(self.search_index),
            "candidate_records": len(self._candidate_references(terms, text)),
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
            "needs_map_or_gps": needs["needs_map_or_gps"],
            "needs_current_data": needs["needs_current_data"],
            "needs_research": needs["needs_research"],
            "suggested_next_brains": [
                brain_name
                for brain_name, enabled in [
                    ("Research_brain", needs["needs_research"]),
                    ("Fact_Check_brain", True),
                    ("Response_brain", True)
                ]
                if enabled
            ],
            "research_fallback": research_result,
            "data_files_used": [
                "Geography_places.json",
                "Geography_concepts.json",
                "Geography_regions.json",
                "Geography_index.json",
                "Geography_relations.json",
                "Geography_query_patterns.json",
                "Geography_creative_profiles.json",
                "Geography_statistics.json"
            ],
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Search local geography knowledge first.",
                "Use Research_brain for current population, weather, borders, GPS, or unknown places.",
                "Do not treat approximate coordinates as live GPS.",
                "Prefer official map/data sources for precise or current answers."
            ]
        }


brain = GeographyBrain()
