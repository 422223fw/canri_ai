"""
Research_brain.py
Canri AI
"""

import json
import re
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

try:
    from Knowledge_collector import search_knowledge
except Exception:
    search_knowledge = None


DATA_DIR = Path(__file__).parent / "data"
SOURCES_FILE = DATA_DIR / "research_sources.json"


class ResearchBrain:

    def __init__(self):

        self.sources = []

        self.load_sources()

        print("Research Brain Loaded")

    def load_sources(self):

        if SOURCES_FILE.exists():

            with open(
                SOURCES_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.sources = json.load(f)

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
            "query",
            "text",
            "main_topic",
            "topic"
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

        return " ".join(text_parts).strip()

    def normalize_query(
        self,
        text
    ):

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text[:300]

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

    def collect_terms_from_understanding(
        self,
        report
    ):

        terms = []

        main_topic = report.get(
            "main_topic",
            ""
        )

        if main_topic and main_topic != "unknown":

            terms.append(
                str(main_topic)
            )

        for topic in report.get(
            "topics",
            {}
        ):

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
            ):

                terms.append(
                    word
                )

            for connection in word_data.get(
                "connections",
                []
            )[:5]:

                terms.append(
                    str(connection)
                )

        clean_terms = []

        for term in terms:

            term = re.sub(
                r"[^a-zA-Z0-9_\-\s]",
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
                and len(term) > 2
                and term not in clean_terms
            ):

                clean_terms.append(
                    term
                )

        return clean_terms

    def build_query_from_understanding(
        self,
        report,
        fallback_text
    ):

        if not report:

            return self.normalize_query(
                fallback_text
            )

        original_text = report.get(
            "original_text",
            fallback_text
        )

        terms = self.collect_terms_from_understanding(
            report
        )

        query_parts = []

        main_topic = report.get(
            "main_topic",
            ""
        )

        intent = report.get(
            "intent",
            ""
        )

        if main_topic and main_topic != "unknown":

            query_parts.append(
                str(main_topic)
            )

        if intent:

            query_parts.append(
                str(intent)
            )

        query_parts.extend(
            terms[:10]
        )

        if original_text:

            query_parts.append(
                str(original_text)
            )

        query = " ".join(
            query_parts
        )

        query = re.sub(
            r"\s+",
            " ",
            query
        ).strip()

        return self.normalize_query(
            query
        )

    def detect_category_from_understanding(
        self,
        report
    ):

        if not report:

            return None

        main_topic = str(
            report.get(
                "main_topic",
                ""
            )
        ).lower()

        topic_map = {
            "history": "history",
            "geography": "maps",
            "map": "maps",
            "gps": "maps",
            "health": "health",
            "medicine": "health",
            "biology": "science",
            "physics": "science",
            "chemistry": "science",
            "science": "science",
            "technology": "technology",
            "code": "technology",
            "programming": "technology",
            "security": "technology",
            "data": "data",
            "statistics": "data",
            "news": "news"
        }

        if main_topic in topic_map:

            return topic_map[main_topic]

        topics = report.get(
            "topics",
            {}
        )

        if isinstance(
            topics,
            dict
        ):

            for topic in topics:

                topic = str(
                    topic
                ).lower()

                if topic in topic_map:

                    return topic_map[topic]

        return None

    def detect_category(
        self,
        text
    ):

        lowered = text.lower()

        category_keywords = {
            "maps": [
                "gps",
                "location",
                "map",
                "where is",
                "coordinates",
                "geography"
            ],
            "health": [
                "health",
                "disease",
                "medicine",
                "medical",
                "virus",
                "symptom",
                "vaccine"
            ],
            "history": [
                "history",
                "war",
                "ancient",
                "empire",
                "revolution",
                "archive",
                "primary source"
            ],
            "science": [
                "science",
                "space",
                "climate",
                "weather",
                "earthquake",
                "biology",
                "physics",
                "chemistry"
            ],
            "technology": [
                "python",
                "code",
                "programming",
                "security",
                "standard",
                "software",
                "api"
            ],
            "data": [
                "population",
                "statistics",
                "country data",
                "economy",
                "gdp",
                "world bank",
                "un data"
            ],
            "news": [
                "today",
                "latest",
                "current",
                "news",
                "recent"
            ]
        }

        scores = {}

        for category, keywords in category_keywords.items():

            score = 0

            for keyword in keywords:

                if keyword in lowered:

                    score += 1

            if score:

                scores[category] = score

        if not scores:

            return "general"

        return max(
            scores,
            key=scores.get
        )

    def get_source_domain_score(
        self,
        source,
        category
    ):

        score = source.get(
            "trust_score",
            50
        )

        if source.get(
            "category"
        ) == category:

            score += 5

        if source.get(
            "source_type",
            ""
        ).startswith(
            "official"
        ):

            score += 3

        return min(
            score,
            100
        )

    def choose_sources(
        self,
        category
    ):

        selected = []

        for source in self.sources:

            if category == "general":

                if source.get(
                    "category"
                ) in [
                    "academic",
                    "data",
                    "science",
                    "history"
                ]:

                    selected.append(
                        source
                    )

            elif source.get(
                "category"
            ) == category:

                selected.append(
                    source
                )

        if not selected:

            selected = [
                source
                for source in self.sources
                if source.get(
                    "trust_score",
                    0
                ) >= 94
            ]

        selected.sort(
            key=lambda source: self.get_source_domain_score(
                source,
                category
            ),
            reverse=True
        )

        return selected[:5]

    def domain_allowed(
        self,
        url
    ):

        domain = urlparse(
            url
        ).netloc.lower()

        if domain.startswith(
            "www."
        ):

            domain = domain[4:]

        for source in self.sources:

            for allowed in source.get(
                "domains",
                []
            ):

                if (
                    domain == allowed
                    or domain.endswith(
                        "." + allowed
                    )
                ):

                    return source

        return None

    def build_research_links(
        self,
        sources,
        query,
        category
    ):

        encoded = quote_plus(
            query
        )

        links = []

        for source in sources:

            search_url = source.get(
                "search_url",
                source.get(
                    "base_url",
                    ""
                )
            ).replace(
                "{query}",
                encoded
            )

            links.append(
                {
                    "source_id": source.get(
                        "id"
                    ),
                    "name": source.get(
                        "name"
                    ),
                    "category": source.get(
                        "category"
                    ),
                    "source_type": source.get(
                        "source_type"
                    ),
                    "trust_score": source.get(
                        "trust_score"
                    ),
                    "reliability_score": self.get_source_domain_score(
                        source,
                        category
                    ),
                    "base_url": source.get(
                        "base_url"
                    ),
                    "search_url": search_url,
                    "strengths": source.get(
                        "strengths",
                        []
                    )
                }
            )

        return links

    def clean_html(
        self,
        html
    ):

        html = re.sub(
            r"(?is)<script.*?</script>",
            " ",
            html
        )

        html = re.sub(
            r"(?is)<style.*?</style>",
            " ",
            html
        )

        text = re.sub(
            r"(?s)<[^>]+>",
            " ",
            html
        )

        text = unescape(
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text

    def fetch_trusted_url(
        self,
        url
    ):

        source = self.domain_allowed(
            url
        )

        if not source:

            return {
                "success": False,
                "error": "URL is not from an approved research source",
                "source": None,
                "text": ""
            }

        try:

            request = Request(
                url,
                headers={
                    "User-Agent": "CanriAIResearchBrain/1.0"
                }
            )

            with urlopen(
                request,
                timeout=8
            ) as response:

                raw = response.read(
                    500000
                )

            html = raw.decode(
                "utf-8",
                errors="ignore"
            )

            return {
                "success": True,
                "error": None,
                "source": source,
                "text": self.clean_html(
                    html
                )
            }

        except URLError as error:

            return {
                "success": False,
                "error": str(error),
                "source": source,
                "text": ""
            }

    def summarize_text(
        self,
        text
    ):

        if not text:

            return ""

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        clean_sentences = [
            sentence.strip()
            for sentence in sentences
            if 40 <= len(sentence.strip()) <= 280
        ]

        return " ".join(
            clean_sentences[:3]
        )

    def extract_direct_url(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return None

        for key in [
            "url",
            "source_url",
            "page_url"
        ]:

            value = data.get(
                key
            )

            if value:

                return str(value)

        return None

    def process(
        self,
        data
    ):

        text = self.extract_text(
            data
        )

        understanding_report = self.get_understanding_report(
            data
        )

        understanding_terms = self.collect_terms_from_understanding(
            understanding_report
        )

        query = self.build_query_from_understanding(
            understanding_report,
            text
        )

        category = (
            self.detect_category_from_understanding(
                understanding_report
            )
            or
            self.detect_category(
                query
            )
        )

        direct_url = self.extract_direct_url(
            data
        )

        facts = []
        warnings = []
        fetched_sources = []
        local_knowledge = []

        if search_knowledge:

            try:

                local_knowledge = search_knowledge(
                    query,
                    limit=5
                )

            except Exception as error:

                warnings.append(
                    f"Local knowledge search failed: {error}"
                )

        for item in local_knowledge[:3]:

            summary = item.get(
                "summary"
            )

            if summary:

                facts.append(
                    summary
                )

        if direct_url:

            fetched = self.fetch_trusted_url(
                direct_url
            )

            if fetched["success"]:

                source = fetched["source"]
                summary = self.summarize_text(
                    fetched["text"]
                )

                if summary:

                    facts.append(
                        summary
                    )

                fetched_sources.append(
                    {
                        "name": source.get(
                            "name"
                        ),
                        "url": direct_url,
                        "trust_score": source.get(
                            "trust_score"
                        ),
                        "source_type": source.get(
                            "source_type"
                        )
                    }
                )

            else:

                warnings.append(
                    fetched["error"]
                )

        sources = self.choose_sources(
            category
        )

        research_links = self.build_research_links(
            sources,
            query,
            category
        )

        if not facts:

            warnings.append(
                "No verified facts returned yet. Use the approved source links and verify before answering."
            )

        source_count = len(
            fetched_sources
        ) or len(
            research_links
        )

        verified = (
            len(facts) > 0
            and (
                len(fetched_sources) > 0
                or len(local_knowledge) > 0
            )
        )

        confidence = 0

        if verified and fetched_sources:

            confidence = min(
                max(
                    source.get(
                        "trust_score",
                        0
                    )
                    for source in fetched_sources
                ),
                100
            )

        elif local_knowledge:

            source_scores = []

            for item in local_knowledge:

                for source in item.get(
                    "sources",
                    []
                ):

                    source_scores.append(
                        source.get(
                            "trust_score",
                            70
                        )
                    )

            confidence = min(
                max(source_scores or [72]),
                86
            )

        elif research_links:

            confidence = min(
                max(
                    link.get(
                        "reliability_score",
                        0
                    )
                    for link in research_links
                ),
                85
            )

        return {
            "brain": "Research_brain",
            "query": query,
            "category": category,
            "used_understanding_report": bool(
                understanding_report
            ),
            "understanding_main_topic": understanding_report.get(
                "main_topic"
            ) if understanding_report else None,
            "understanding_intent": understanding_report.get(
                "intent"
            ) if understanding_report else None,
            "understanding_terms_used": understanding_terms,
            "verified": verified,
            "confidence": confidence,
            "source_count": source_count,
            "facts": facts,
            "local_knowledge": local_knowledge,
            "fetched_sources": fetched_sources,
            "approved_research_links": research_links,
            "warnings": list(
                dict.fromkeys(
                    warnings
                )
            ),
            "rules": [
                "Use only approved sources.",
                "Search the local trusted knowledge database before using internet links.",
                "Reject random websites.",
                "Give every source a reliability score.",
                "Do not present internet information as verified unless source content was fetched and checked.",
                "Prefer official, academic, archive, and standards sources.",
                "Wikipedia is allowed only as background and topic navigation; confirm important claims with stronger sources."
            ]
        }


brain = ResearchBrain()
