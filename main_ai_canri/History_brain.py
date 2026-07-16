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
EVENTS_FILE = DATA_DIR / "History_events.json"
FIGURES_FILE = DATA_DIR / "History_figures.json"
TIMELINES_FILE = DATA_DIR / "History_timelines.json"
INDEX_FILE = DATA_DIR / "History_index.json"


class HistoryBrain:

    def __init__(self):

        self.sources = []
        self.knowledge = {}
        self.events = {}
        self.figures = {}
        self.timelines = {}
        self.history_index = {"terms": {}, "years": {}, "eras": {}, "regions": {}}

        self.load_data()

        print("History Brain Loaded")

    def load_data(self):

        self.sources = self.load_json(SOURCES_FILE, [])
        self.knowledge = self.load_json(KNOWLEDGE_FILE, {})
        self.events = self.load_json(EVENTS_FILE, {})
        self.figures = self.load_json(FIGURES_FILE, {})
        self.timelines = self.load_json(TIMELINES_FILE, {})
        self.history_index = self.load_json(
            INDEX_FILE,
            {"terms": {}, "years": {}, "eras": {}, "regions": {}}
        )

    def load_json(self, path, default):

        if not path.exists() or path.stat().st_size == 0:
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return default

    def query_terms(self, text):

        ignored = {
            "about", "after", "and", "before", "compare", "did", "explain", "for", "give", "history",
            "historical", "please", "tell", "that", "their", "what",
            "when", "where", "which", "with", "why", "were", "from", "the", "was"
        }
        return list(dict.fromkeys(
            word
            for word in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
            if word not in ignored
        ))[:40]

    def search_local_history(self, text, dates, limit=8):

        terms = self.query_terms(text)
        candidates = {}
        term_index = self.history_index.get("terms", {})

        for term in terms:
            for event_id in term_index.get(term, []):
                candidates[event_id] = candidates.get(event_id, 0) + 6

        for year in dates.get("years", []):
            for event_id in self.history_index.get("years", {}).get(year, []):
                candidates[event_id] = candidates.get(event_id, 0) + 18

        normalized = self.normalize_text(text)
        for event_id, event in self.events.items():
            title = str(event.get("title", "")).lower()
            if title and title in normalized:
                candidates[event_id] = candidates.get(event_id, 0) + 30
            for alias in event.get("aliases", []):
                alias = str(alias).lower().strip()
                if alias and alias in normalized:
                    candidates[event_id] = candidates.get(event_id, 0) + 35
            matched = sum(1 for term in terms if term in title)
            if matched >= 2:
                candidates[event_id] = candidates.get(event_id, 0) + matched * 5

        ranked = []
        for event_id, score in candidates.items():
            event = self.events.get(event_id)
            if not event:
                continue
            ranked.append({**event, "match_score": score})
        ranked.sort(key=lambda item: (-item["match_score"], item.get("start_year", 0)))

        figure_matches = []
        for figure in self.figures.values():
            searchable = f"{figure.get('name', '')} {figure.get('region', '')} {figure.get('summary', '')}".lower()
            score = sum(5 for term in terms if term in searchable)
            if score:
                figure_matches.append({**figure, "match_score": score})
        figure_matches.sort(key=lambda item: item["match_score"], reverse=True)

        return {
            "terms": terms,
            "events": ranked[:limit],
            "figures": figure_matches[:4],
        }

    def build_timeline(self, matches, limit=8):

        return [
            {
                "year": event.get("display_year", event.get("start_year")),
                "title": event.get("title"),
                "summary": event.get("summary"),
            }
            for event in sorted(
                matches.get("events", []),
                key=lambda item: item.get("start_year", 0)
            )[:limit]
        ]

    def build_local_answer(self, question_type, matches):

        events = matches.get("events", [])
        figures = matches.get("figures", [])
        if not events and not figures:
            return ""

        if question_type == "comparison" and len(events) >= 2:
            first, second = events[:2]
            return (
                f"{first['title']} ({first.get('display_year')}) occurred in {first.get('region')}. "
                f"{first.get('summary')}\n\n"
                f"{second['title']} ({second.get('display_year')}) occurred in {second.get('region')}. "
                f"{second.get('summary')}\n\n"
                "The main comparison is their period, region, causes, institutions, and consequences; "
                "the local evidence is a concise summary and should be checked against the listed sources for a formal claim."
            )

        if question_type == "biographical" and figures:
            figure = figures[0]
            death = figure.get("death_year")
            life = f"{figure.get('birth_year')} to {death}" if death else f"born {figure.get('birth_year')}"
            return f"{figure.get('name')} ({life}) was associated with {figure.get('region')}. {figure.get('summary')}"

        event = events[0]
        if question_type == "historical_significance":
            consequence_text = ", ".join(event.get("consequences", [])[:4])
            significance = (
                f"Its long-term importance includes {consequence_text}."
                if consequence_text
                else (
                    "It was historically important because it changed institutions, knowledge, exchange, "
                    "or later developments beyond its original setting."
                )
            )
            return " ".join([
                f"{event.get('title')} is associated with {event.get('display_year')} and {event.get('region')}.",
                str(event.get("summary", "")),
                significance,
            ])

        lines = [
            f"{event.get('title')} ({event.get('display_year')})",
            str(event.get("summary", "")),
        ]
        if question_type == "causal_explanation":
            if event.get("causes"):
                lines.append("Main causes: " + ", ".join(event["causes"]) + ".")
            if event.get("consequences"):
                lines.append("Major consequences: " + ", ".join(event["consequences"]) + ".")
        elif question_type == "chronology":
            timeline = self.build_timeline(matches)
            if len(timeline) > 1:
                lines.append("Timeline: " + "; ".join(f"{item['year']} - {item['title']}" for item in timeline) + ".")
        return "\n".join(line for line in lines if line)

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
            phrase in text
            for phrase in ["historically important", "historical importance", "significance", "why was"]
        ):

            return "historical_significance"

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

        source_ids = list(topic_data.get(
            "recommended_sources",
            []
        ))

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

        local_matches = self.search_local_history(text, dates)

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

        local_answer = self.build_local_answer(question_type, local_matches)
        if local_matches["events"] or local_matches["figures"]:
            best_match_score = max(
                [item.get("match_score", 0) for item in local_matches["events"] + local_matches["figures"]],
                default=0
            )
            confidence = min(96, max(confidence + 12, 82 if best_match_score >= 10 else 70))

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
            "local_matches": local_matches,
            "timeline": self.build_timeline(local_matches),
            "answer": local_answer,
            "final_output": local_answer or (
                "I do not have a sufficiently close local historical record for this request yet. "
                "Use the research query and trusted sources below to verify it."
            ),
            "verified": bool(local_matches["events"] or local_matches["figures"]),
            "verification_status": (
                "curated_local_summary_needs_source_confirmation"
                if local_answer else "research_required"
            ),
            "reasoning_used": True,
            "confidence": confidence,
            "note": (
                "History_brain prepares historical research and trusted "
                "source links. It does not claim final verification until "
                "the selected sources are actually read and compared."
            )
        }


brain = HistoryBrain()
