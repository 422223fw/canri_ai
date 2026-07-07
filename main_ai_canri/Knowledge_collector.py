"""
Knowledge_collector.py
Canri AI

Background trusted-knowledge collector.

Design:
- Uses approved English encyclopedic sources, starting with English Wikipedia.
- Stores large article data as JSON Lines, not one giant JSON array.
- Maintains a small JSON index for fast lookup by other brains.
- Runs in tiny background batches so Canri stays responsive.
- Stops growth at 1.5GB, then switches to update-check mode.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DATA_DIR = Path(__file__).parent / "data"
DB_FILE = DATA_DIR / "Knowledge_database.jsonl"
INDEX_FILE = DATA_DIR / "Knowledge_index.json"
QUEUE_FILE = DATA_DIR / "Knowledge_queue.json"
SOURCES_FILE = DATA_DIR / "Knowledge_sources.json"
STATS_FILE = DATA_DIR / "Knowledge_statistics.json"

MAX_DATABASE_BYTES = int(1.5 * 1024 * 1024 * 1024)
DEFAULT_BATCH_SIZE = 3
DEFAULT_SLEEP_SECONDS = 30
DEFAULT_UPDATE_AFTER_DAYS = 7
USER_AGENT = "CanriAIKnowledgeCollector/1.0 (local educational project)"

TRUSTED_SOURCES = {
    "wikipedia_en": {
        "name": "English Wikipedia",
        "type": "encyclopedia",
        "language": "en",
        "trust_score": 82,
        "api": "https://en.wikipedia.org/w/api.php",
        "page": "https://en.wikipedia.org/wiki/{title}",
        "allowed_domain": "en.wikipedia.org"
    }
}

SEED_TOPICS = [
    "Artificial intelligence",
    "Computer science",
    "Software engineering",
    "Python programming language",
    "Weather",
    "Meteorology",
    "Physics",
    "Chemistry",
    "Biology",
    "Mathematics",
    "Geography",
    "History",
    "Technology",
    "Computer hardware",
    "Video game",
    "Internet",
    "Data science",
    "Cybersecurity",
    "Medicine",
    "Astronomy"
]

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about",
    "what", "when", "where", "which", "while", "there", "their", "have",
    "has", "are", "was", "were", "will", "would", "can", "could", "should",
    "you", "your", "how", "why", "who", "its", "not", "also"
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_title(title: str) -> str:
    clean = re.sub(r"\s+", " ", str(title).strip().lower())
    clean = clean.replace("_", " ")
    return clean


def article_id_for(source_id: str, title: str) -> str:
    digest = hashlib.sha1(f"{source_id}:{normalize_title(title)}".encode("utf-8")).hexdigest()
    return f"knowledge_{digest[:16]}"


def text_terms(text: str, limit: int = 80) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", str(text).lower())
    clean = []
    for word in words:
        word = word.strip("-")
        if word and word not in STOP_WORDS and word not in clean:
            clean.append(word)
        if len(clean) >= limit:
            break
    return clean


def summarize_text(text: str, max_sentences: int = 5, max_chars: int = 1200) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= max_chars:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentence for sentence in sentences[:max_sentences] if sentence)
    return summary[:max_chars].rsplit(" ", 1)[0].strip() + "..."


def read_json(path: Path, default):
    if not path.exists() or path.stat().st_size == 0:
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def database_size() -> int:
    return DB_FILE.stat().st_size if DB_FILE.exists() else 0


def classify_error(error_text: str) -> str:
    lowered = str(error_text).lower()

    if "certificate_verify_failed" in lowered or "ssl" in lowered:
        return "ssl_certificate_problem"

    if "10061" in lowered or "actively refused" in lowered:
        return "network_connection_refused"

    if "timed out" in lowered or "timeout" in lowered:
        return "network_timeout"

    if "name resolution" in lowered or "no address associated" in lowered:
        return "dns_problem"

    return "unknown_error"


class KnowledgeCollector:

    def __init__(
        self,
        max_bytes: int = MAX_DATABASE_BYTES,
        batch_size: int = DEFAULT_BATCH_SIZE,
        sleep_seconds: int = DEFAULT_SLEEP_SECONDS,
        update_after_days: int = DEFAULT_UPDATE_AFTER_DAYS,
    ):
        self.max_bytes = max_bytes
        self.batch_size = batch_size
        self.sleep_seconds = sleep_seconds
        self.update_after_days = update_after_days
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.index = read_json(INDEX_FILE, {"articles": {}, "terms": {}, "metadata": {}})
        self.queue = read_json(QUEUE_FILE, {"pending": list(SEED_TOPICS), "seen_queries": []})
        self.sources = read_json(SOURCES_FILE, TRUSTED_SOURCES)
        self.stats = read_json(STATS_FILE, {})

    # ---------- HTTP ----------

    def request_json(self, url: str, params: Dict[str, str], timeout: int = 12):
        query = urlencode(params)
        request = Request(
            f"{url}?{query}",
            headers={"User-Agent": USER_AGENT}
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except URLError as error:
            message = str(error)
            if "CERTIFICATE_VERIFY_FAILED" not in message:
                raise

            context = ssl._create_unverified_context()
            with urlopen(request, timeout=timeout, context=context) as response:
                self.stats["ssl_fallback_used"] = self.stats.get(
                    "ssl_fallback_used",
                    0
                ) + 1
                self.stats["ssl_fallback_reason"] = (
                    "Python could not verify the HTTPS certificate on this machine."
                )
                return json.loads(response.read().decode("utf-8", errors="replace"))

    def search_wikipedia(self, query: str, limit: int = 5) -> List[str]:
        source = self.sources["wikipedia_en"]
        data = self.request_json(
            source["api"],
            {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": str(limit),
                "utf8": "1"
            }
        )
        return [
            item.get("title", "")
            for item in data.get("query", {}).get("search", [])
            if item.get("title")
        ]

    def fetch_wikipedia_article(self, title: str) -> Optional[Dict[str, object]]:
        source = self.sources["wikipedia_en"]
        data = self.request_json(
            source["api"],
            {
                "action": "query",
                "format": "json",
                "prop": "extracts|info",
                "explaintext": "1",
                "exsectionformat": "plain",
                "inprop": "url",
                "redirects": "1",
                "titles": title,
                "utf8": "1"
            }
        )
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        page = next(iter(pages.values()))
        if page.get("missing") is not None:
            return None

        text = str(page.get("extract", "")).strip()
        if len(text) < 400:
            return None

        canonical_title = page.get("title", title)
        page_url = page.get("fullurl") or source["page"].format(title=quote(canonical_title.replace(" ", "_")))

        return {
            "source_id": "wikipedia_en",
            "source_name": source["name"],
            "source_trust_score": source["trust_score"],
            "title": canonical_title,
            "url": page_url,
            "language": "en",
            "retrieved_utc": utc_now(),
            "source_updated_hint": page.get("touched"),
            "text": text
        }

    # ---------- storage ----------

    def read_record_at_offset(self, offset: int) -> Optional[Dict[str, object]]:
        if not DB_FILE.exists():
            return None
        try:
            with DB_FILE.open("rb") as file:
                file.seek(offset)
                line = file.readline()
            return json.loads(line.decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def append_record(self, record: Dict[str, object]) -> int:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        offset = database_size()
        with DB_FILE.open("ab") as file:
            line = json.dumps(record, ensure_ascii=False).encode("utf-8") + b"\n"
            file.write(line)
        return offset

    def merge_with_existing(self, article: Dict[str, object]) -> Dict[str, object]:
        key = normalize_title(article["title"])
        existing_meta = self.index.get("articles", {}).get(key)
        if not existing_meta:
            return article

        existing = self.read_record_at_offset(existing_meta.get("offset", 0)) or {}
        existing_sources = existing.get("sources", [])
        source_item = {
            "source_id": article["source_id"],
            "source_name": article["source_name"],
            "url": article["url"],
            "trust_score": article["source_trust_score"],
            "retrieved_utc": article["retrieved_utc"],
            "source_updated_hint": article.get("source_updated_hint")
        }

        sources = existing_sources + [
            source_item
            for source_item in [source_item]
            if source_item.get("url") not in {
                item.get("url")
                for item in existing_sources
                if isinstance(item, dict)
            }
        ]

        old_text = existing.get("text", "")
        new_text = article["text"]
        merged_text = new_text if len(new_text) >= len(old_text) else old_text

        return {
            **article,
            "article_id": existing.get("article_id", article_id_for(article["source_id"], article["title"])),
            "version": int(existing.get("version", 1)) + 1,
            "sources": sources,
            "text": merged_text,
            "merged_from_versions": [existing.get("version", 1), int(existing.get("version", 1)) + 1]
        }

    def upsert_article(self, article: Dict[str, object]) -> Optional[Dict[str, object]]:
        title = article["title"]
        key = normalize_title(title)
        merged = self.merge_with_existing(article)

        merged.setdefault("article_id", article_id_for(article["source_id"], title))
        merged.setdefault("version", 1)
        merged.setdefault("sources", [{
            "source_id": article["source_id"],
            "source_name": article["source_name"],
            "url": article["url"],
            "trust_score": article["source_trust_score"],
            "retrieved_utc": article["retrieved_utc"],
            "source_updated_hint": article.get("source_updated_hint")
        }])
        merged["summary"] = summarize_text(merged.get("text", ""))
        merged["terms"] = text_terms(f"{merged.get('title', '')} {merged.get('summary', '')} {merged.get('text', '')}")
        merged["content_bytes"] = len(str(merged.get("text", "")).encode("utf-8"))
        merged["stored_utc"] = utc_now()

        if database_size() + merged["content_bytes"] > self.max_bytes:
            return None

        offset = self.append_record(merged)
        self.index.setdefault("articles", {})[key] = {
            "article_id": merged["article_id"],
            "title": merged["title"],
            "summary": merged["summary"][:600],
            "terms": merged["terms"][:40],
            "sources": merged["sources"][:6],
            "offset": offset,
            "version": merged["version"],
            "stored_utc": merged["stored_utc"],
            "last_checked_utc": utc_now()
        }

        for term in merged["terms"][:30]:
            bucket = self.index.setdefault("terms", {}).setdefault(term, [])
            if key not in bucket:
                bucket.append(key)
                self.index["terms"][term] = bucket[-60:]

        self.index["metadata"] = {
            "database_file": DB_FILE.name,
            "database_bytes": database_size(),
            "max_database_bytes": self.max_bytes,
            "articles": len(self.index.get("articles", {})),
            "updated_utc": utc_now(),
            "format": "jsonl"
        }

        return merged

    # ---------- queue/update ----------

    def save_state(self):
        write_json(INDEX_FILE, self.index)
        write_json(QUEUE_FILE, self.queue)
        write_json(SOURCES_FILE, self.sources)
        write_json(STATS_FILE, self.stats)

    def pop_topic(self) -> Optional[str]:
        pending = self.queue.setdefault("pending", [])
        seen = set(self.queue.setdefault("seen_queries", []))

        while pending:
            topic = pending.pop(0)
            if topic not in seen:
                seen.add(topic)
                self.queue["seen_queries"] = list(seen)[-10000:]
                return topic

        return None

    def enqueue_related_titles(self, titles: Iterable[str]) -> None:
        pending = self.queue.setdefault("pending", [])
        seen = set(self.queue.setdefault("seen_queries", []))
        for title in titles:
            if title and title not in pending and title not in seen:
                pending.append(title)
        self.queue["pending"] = pending[-20000:]

    def choose_stale_article(self) -> Optional[str]:
        articles = self.index.get("articles", {})
        if not articles:
            return None

        sorted_items = sorted(
            articles.items(),
            key=lambda item: item[1].get("last_checked_utc", "")
        )
        return sorted_items[0][1].get("title") if sorted_items else None

    def run_once(self) -> Dict[str, object]:
        started = time.perf_counter()
        mode = "collect" if database_size() < self.max_bytes else "update_check"
        stored = 0
        errors = []
        topic = None

        try:
            topic = self.pop_topic() if mode == "collect" else self.choose_stale_article()
            if not topic:
                self.enqueue_related_titles(SEED_TOPICS)
                topic = self.pop_topic()

            if not topic:
                return {"mode": mode, "stored": 0, "reason": "no_topic"}

            titles = self.search_wikipedia(topic, limit=self.batch_size)
            self.enqueue_related_titles(titles)

            for title in titles[:self.batch_size]:
                if self.stop_event.is_set():
                    break
                article = self.fetch_wikipedia_article(title)
                if not article:
                    continue
                if self.upsert_article(article):
                    stored += 1
                time.sleep(0.8)

        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            errors.append(str(error))
            if topic and mode == "collect":
                pending = self.queue.setdefault("pending", [])
                seen = set(self.queue.setdefault("seen_queries", []))
                seen.discard(topic)
                self.queue["seen_queries"] = list(seen)[-10000:]
                if topic not in pending:
                    pending.insert(0, topic)

        elapsed = round(time.perf_counter() - started, 2)
        error_type = classify_error(errors[0]) if errors else None
        self.stats["last_run"] = {
            "mode": mode,
            "stored": stored,
            "errors": errors,
            "error_type": error_type,
            "network_status": "blocked_or_unavailable" if errors else "ok",
            "next_action": (
                "Check internet, firewall, VPN, or run again from a terminal with network access."
                if errors else
                "Collector is working."
            ),
            "elapsed_seconds": elapsed,
            "database_bytes": database_size(),
            "updated_utc": utc_now()
        }
        self.stats["runs"] = self.stats.get("runs", 0) + 1
        self.stats["articles"] = len(self.index.get("articles", {}))
        self.save_state()

        return self.stats["last_run"]

    def run_forever(self):
        self.save_state()
        while not self.stop_event.is_set():
            self.run_once()
            self.stop_event.wait(self.sleep_seconds)

    def start(self):
        if self.thread and self.thread.is_alive():
            return self.thread

        self.thread = threading.Thread(
            target=self.run_forever,
            name="CanriKnowledgeCollector",
            daemon=True
        )
        self.thread.start()
        return self.thread

    def stop(self):
        self.stop_event.set()


def search_knowledge(query: str, limit: int = 5) -> List[Dict[str, object]]:
    index = read_json(INDEX_FILE, {"articles": {}, "terms": {}})
    terms = text_terms(query, limit=20)
    scores = {}

    for term in terms:
        for key in index.get("terms", {}).get(term, []):
            scores[key] = scores.get(key, 0) + 3

    for key, meta in index.get("articles", {}).items():
        searchable = f"{key} {meta.get('title', '')} {meta.get('summary', '')}".lower()
        for term in terms:
            if term in searchable:
                scores[key] = scores.get(key, 0) + 1

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    results = []
    for key, score in ranked:
        meta = index.get("articles", {}).get(key, {})
        results.append({
            "title": meta.get("title"),
            "summary": meta.get("summary"),
            "sources": meta.get("sources", []),
            "score": score,
            "stored_utc": meta.get("stored_utc"),
            "version": meta.get("version")
        })

    return results


def enqueue_knowledge_topics(query: str, max_topics: int = 8) -> Dict[str, object]:
    """Add useful query terms to the collector queue without starting network work."""

    queue = read_json(QUEUE_FILE, {"pending": [], "seen_queries": []})
    pending = queue.setdefault("pending", [])
    seen = set(queue.setdefault("seen_queries", []))

    terms = text_terms(query, limit=40)
    topics = []

    clean_query = re.sub(r"\s+", " ", str(query).strip())
    if 4 <= len(clean_query) <= 90:
        topics.append(clean_query)

    topics.extend(term.title() for term in terms[:max_topics])

    added = []
    for topic in topics:
        if not topic or topic in pending or topic in seen:
            continue
        pending.append(topic)
        added.append(topic)

    queue["pending"] = pending[-20000:]
    write_json(QUEUE_FILE, queue)

    return {
        "added": added,
        "added_count": len(added),
        "pending_count": len(queue["pending"])
    }


_collector: Optional[KnowledgeCollector] = None


def start_background_collector() -> Optional[KnowledgeCollector]:
    enabled = os.environ.get("CANRI_KNOWLEDGE_BACKGROUND", "1").lower() not in {
        "0", "false", "no", "off"
    }
    if not enabled:
        return None

    global _collector
    if _collector is None:
        _collector = KnowledgeCollector()
        _collector.start()
    return _collector


if __name__ == "__main__":
    collector = KnowledgeCollector(batch_size=2, sleep_seconds=5)
    print(json.dumps(collector.run_once(), ensure_ascii=False, indent=2))
