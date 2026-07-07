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
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
PLACES_PATH = DATA_DIR / "Geography_places.json"
CONCEPTS_PATH = DATA_DIR / "Geography_concepts.json"
REGIONS_PATH = DATA_DIR / "Geography_regions.json"
STATISTICS_PATH = DATA_DIR / "Geography_statistics.json"

LOCAL_CONFIDENCE_THRESHOLD = 55
MAX_LOCAL_RESULTS = 6

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "what", "where",
    "how", "why", "is", "are", "was", "were", "does", "did",
    "about", "from", "into", "של", "את", "על", "מה", "איפה",
    "איך", "למה", "זה", "אני", "רוצה"
}


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

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with STATISTICS_PATH.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.statistics,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.write(
                "\n"
            )

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

        for term in terms:

            term = re.sub(
                r"\s+",
                " ",
                term
            ).strip().lower()

            if (
                term
                and term not in STOP_WORDS
                and term not in clean_terms
            ):

                clean_terms.append(
                    term
                )

        # Add phrase matches from local database for names like "new york city".
        lowered = text.lower()

        for name in list(
            self.places.keys()
        ) + list(
            self.regions.keys()
        ):

            if name in lowered and name not in clean_terms:
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

        for name, data in self.places.items():

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
                )
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

            if name in text.lower():
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
        terms
    ):

        results = []

        for name, data in self.concepts.items():

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
                )
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
        terms
    ):

        results = []

        for name, data in self.regions.items():

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
                )
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
                terms
            )
            +
            self.search_regions(
                terms
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

    def detect_needs(
        self,
        intent,
        local_matches,
        confidence,
        terms
    ):

        needs_map_or_gps = intent in [
            "location_lookup",
            "map_or_distance"
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
            "population_lookup"
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

            return research_brain.process(
                payload
            )

        except Exception as error:

            return {
                "brain": "Research_brain",
                "error": str(error),
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
            "facts": self.build_facts(
                local_matches
            ),
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
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Search local geography knowledge first.",
                "Use Research_brain for current population, weather, borders, GPS, or unknown places.",
                "Do not treat approximate coordinates as live GPS.",
                "Prefer official map/data sources for precise or current answers."
            ]
        }


brain = GeographyBrain()
