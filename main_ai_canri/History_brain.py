"""
History_brain.py
Canri AI
"""

import json
import re
from pathlib import Path

from Scanner_knowledge import scanner_evidence
from urllib.parse import quote_plus


DATA_DIR = Path(__file__).parent / "data"
SOURCES_FILE = DATA_DIR / "history_sources.json"
KNOWLEDGE_FILE = DATA_DIR / "history_knowledge.json"


class HistoryBrain:

    def __init__(self):

        self.sources = []
        self.knowledge = {}

        self.load_data()

        print("History Brain Loaded")

    def load_data(self):

        if SOURCES_FILE.exists():

            with open(
                SOURCES_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.sources = json.load(f)

        if KNOWLEDGE_FILE.exists():

            with open(
                KNOWLEDGE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.knowledge = json.load(f)

    def extract_text(
        self,
        data
    ):

        if isinstance(
            data,
            str
        ):

            return data

        if not isinstance(
            data,
            dict
        ):

            return str(data)

        text_parts = []

        for key in [
            "user_message",
            "original_text",
            "corrected_text",
            "question",
            "topic",
            "main_topic",
            "text"
        ]:

            value = data.get(
                key
            )

            if value:

                text_parts.append(
                    str(value)
                )

        understanding = data.get(
            "understanding",
            {}
        )

        if isinstance(
            understanding,
            dict
        ):

            value = understanding.get(
                "original_text"
            )

            if value:

                text_parts.append(
                    str(value)
                )

        return " ".join(text_parts)

    def normalize_text(
        self,
        text
    ):

        return re.sub(
            r"\s+",
            " ",
            text.lower()
        ).strip()

    def score_topic(
        self,
        text,
        topic_data
    ):

        score = 0

        for keyword in topic_data.get(
            "keywords",
            []
        ):

            keyword = keyword.lower()

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(keyword)
                + r"(?![a-z0-9])"
            )

            if re.search(
                pattern,
                text
            ):

                score += 5

        for region in topic_data.get(
            "regions",
            []
        ):

            if region.replace(
                "_",
                " "
            ) in text:

                score += 2

        return score

    def detect_topic(
        self,
        text
    ):

        scores = {}

        for topic_id, topic_data in self.knowledge.items():

            score = self.score_topic(
                text,
                topic_data
            )

            if score > 0:

                scores[topic_id] = score

        if not scores:

            return {
                "topic_id": "general_history",
                "score": 0,
                "matched_topics": {}
            }

        best_topic = max(
            scores,
            key=scores.get
        )

        return {
            "topic_id": best_topic,
            "score": scores[best_topic],
            "matched_topics": dict(
                sorted(
                    scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            )
        }

    def detect_dates(
        self,
        text
    ):

        years = re.findall(
            r"\b(?:[1-2]\d{3}|[1-9]\d{2})\b",
            text
        )

        centuries = re.findall(
            r"\b\d{1,2}(?:st|nd|rd|th)\s+century\b",
            text
        )

        return {
            "years": list(dict.fromkeys(years)),
            "centuries": list(dict.fromkeys(centuries))
        }

    def detect_question_type(
        self,
        text
    ):

        if any(
            word in text
            for word in [
                "why",
                "cause",
                "causes",
                "because"
            ]
        ):

            return "causal_explanation"

        if any(
            word in text
            for word in [
                "when",
                "timeline",
                "chronology"
            ]
        ):

            return "chronology"

        if any(
            word in text
            for word in [
                "compare",
                "difference",
                "similar"
            ]
        ):

            return "comparison"

        if any(
            word in text
            for word in [
                "who",
                "person",
                "leader",
                "king",
                "president"
            ]
        ):

            return "biographical"

        return "overview"

    def build_search_query(
        self,
        text,
        topic
    ):

        query_parts = []

        if topic and topic != "general_history":

            query_parts.append(
                topic.replace(
                    "_",
                    " "
                )
            )

        cleaned = re.sub(
            r"[^a-z0-9\s-]",
            " ",
            text.lower()
        )

        words = [
            word
            for word in cleaned.split()
            if len(word) > 2
        ]

        query_parts.extend(
            words[:8]
        )

        return " ".join(
            list(dict.fromkeys(query_parts))
        ).strip()

    def get_source_by_id(
        self,
        source_id
    ):

        for source in self.sources:

            if source.get(
                "id"
            ) == source_id:

                return source

        return None

    def choose_sources(
        self,
        topic_id,
        question_type
    ):

        selected = []

        topic_data = self.knowledge.get(
            topic_id,
            {}
        )

        source_ids = topic_data.get(
            "recommended_sources",
            []
        )

        if question_type in [
            "causal_explanation",
            "comparison",
            "overview"
        ]:

            source_ids.append(
                "jstor"
            )

        if question_type in [
            "chronology",
            "biographical"
        ]:

            source_ids.extend([
                "library_of_congress",
                "national_archives_us"
            ])

        if not source_ids:

            source_ids = [
                "world_history_encyclopedia",
                "jstor",
                "library_of_congress"
            ]

        for source_id in list(
            dict.fromkeys(source_ids)
        ):

            source = self.get_source_by_id(
                source_id
            )

            if source:

                selected.append(
                    source
                )

        selected.sort(
            key=lambda item: item.get(
                "trust_score",
                0
            ),
            reverse=True
        )

        return selected[:5]

    def build_source_links(
        self,
        sources,
        query
    ):

        links = []

        encoded_query = quote_plus(
            query
        )

        for source in sources:

            search_url = source.get(
                "search_url",
                source.get(
                    "url",
                    ""
                )
            )

            links.append(
                {
                    "name": source.get(
                        "name"
                    ),
                    "type": source.get(
                        "source_type"
                    ),
                    "trust_score": source.get(
                        "trust_score"
                    ),
                    "url": source.get(
                        "url"
                    ),
                    "search_url": search_url.replace(
                        "{query}",
                        encoded_query
                    )
                }
            )

        return links

    def build_research_plan(
        self,
        question_type
    ):

        base_steps = [
            "Identify the exact event, period, people, and place.",
            "Separate primary sources from secondary interpretations.",
            "Build a short chronology before explaining causes or meaning.",
            "Compare at least two reliable sources before answering.",
            "Mark uncertainty when sources disagree or evidence is incomplete."
        ]

        if question_type == "causal_explanation":

            base_steps.insert(
                2,
                "Separate long-term causes, short-term triggers, and consequences."
            )

        if question_type == "comparison":

            base_steps.insert(
                2,
                "Compare the cases by period, geography, institutions, and outcomes."
            )

        if question_type == "biographical":

            base_steps.insert(
                2,
                "Check dates, offices, actions, and contemporary documents."
            )

        return base_steps

    def calculate_confidence(
        self,
        topic_score,
        source_count,
        date_count
    ):

        confidence = 40

        if topic_score > 0:

            confidence += 25

        if source_count >= 3:

            confidence += 20

        if date_count > 0:

            confidence += 10

        return min(
            confidence,
            95
        )

    def process(
        self,
        data
    ):

        raw_text = self.extract_text(
            data
        )
        scanner_articles = scanner_evidence(data, limit=5)

        text = self.normalize_text(
            raw_text
        )

        detected = self.detect_topic(
            text
        )

        topic_id = detected["topic_id"]

        topic_data = self.knowledge.get(
            topic_id,
            {}
        )

        question_type = self.detect_question_type(
            text
        )

        dates = self.detect_dates(
            text
        )

        query = self.build_search_query(
            text,
            topic_id
        )

        sources = self.choose_sources(
            topic_id,
            question_type
        )

        source_links = self.build_source_links(
            sources,
            query
        )

        confidence = self.calculate_confidence(
            detected["score"],
            len(source_links),
            len(dates["years"]) + len(dates["centuries"])
        )

        return {
            "brain": "History_brain",
            "success": True,
            "original_text": raw_text,
            "history_topic": topic_id,
            "topic_label": topic_data.get(
                "label",
                "General History"
            ),
            "period": topic_data.get(
                "period",
                "unknown"
            ),
            "question_type": question_type,
            "dates_detected": dates,
            "matched_topics": detected["matched_topics"],
            "study_angles": topic_data.get(
                "study_angles",
                []
            ),
            "research_query": query,
            "recommended_sources": source_links,
            "research_plan": self.build_research_plan(
                question_type
            ),
            "source_count": len(source_links),
            "scanner_articles_found": len(scanner_articles),
            "scanner_evidence": scanner_articles,
            "verified": False,
            "reasoning_used": True,
            "confidence": confidence,
            "note": (
                "History_brain prepares historical research and trusted "
                "source links. It does not claim final verification until "
                "the selected sources are actually read and compared."
            )
        }


brain = HistoryBrain()
