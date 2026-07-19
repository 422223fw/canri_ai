"""Bounded, source-aware web collection primitives used by Canri scanners."""

from __future__ import annotations

import gzip
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser


DATA_DIR = Path(__file__).parent / "data"
DEFAULT_MAX_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_MAX_RESPONSE_BYTES = 1_500_000
DEFAULT_MAX_RECORD_BYTES = 600_000
DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_HOST_DELAY_SECONDS = 2.0
USER_AGENT = "CanriKnowledgeScanner/1.0 (+local educational knowledge index)"

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+.#-]{1,48}")
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about",
    "what", "when", "where", "which", "while", "there", "their", "have",
    "has", "are", "was", "were", "will", "would", "can", "could", "should",
    "you", "your", "how", "why", "who", "its", "not", "also", "does",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file)
        return value
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def text_terms(value: Any, limit: int = 80) -> list[str]:
    terms = []
    for match in TOKEN_PATTERN.findall(str(value or "").lower()):
        term = match.strip("-_.")
        if len(term) < 2 or term in STOP_WORDS or term in terms:
            continue
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def stable_id(*parts: Any, prefix: str = "web") -> str:
    source = "\x1f".join(str(part or "").strip().lower() for part in parts)
    return f"{prefix}_{hashlib.sha256(source.encode('utf-8')).hexdigest()[:20]}"


def content_hash(*parts: Any) -> str:
    source = "\x1f".join(str(part or "") for part in parts)
    return hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()


def host_matches(hostname: str, allowed_domains: Iterable[str]) -> bool:
    hostname = str(hostname or "").lower().rstrip(".")
    for allowed in allowed_domains:
        allowed = str(allowed or "").lower().rstrip(".")
        if hostname == allowed or hostname.endswith("." + allowed):
            return True
    return False


def is_public_hostname(hostname: str) -> bool:
    hostname = str(hostname or "").strip().lower().rstrip(".")
    if not hostname or hostname in {"localhost", "localhost.localdomain"}:
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def addresses_are_public(hostname: str) -> bool:
    """Reject DNS results that could turn an allowed host into an SSRF target."""

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                str(hostname),
                443,
                type=socket.SOCK_STREAM,
            )
            if item[4]
        }
    except (OSError, UnicodeError, ValueError):
        return False
    if not addresses:
        return False
    return all(is_public_hostname(address) for address in addresses)


class VisibleTextParser(HTMLParser):
    BLOCKED = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked_depth = 0
        self._title_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.BLOCKED:
            self._blocked_depth += 1
        if tag == "title":
            self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.BLOCKED and self._blocked_depth:
            self._blocked_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        clean = re.sub(r"\s+", " ", unescape(data)).strip()
        if not clean:
            return
        if self._title_depth:
            self.title_parts.append(clean)
        if not self._blocked_depth:
            self.text_parts.append(clean)


def extract_visible_text(raw: bytes, content_type: str) -> tuple[str, str]:
    charset_match = re.search(r"charset=([\w.-]+)", content_type or "", re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    try:
        decoded = raw.decode(charset, errors="replace")
    except LookupError:
        decoded = raw.decode("utf-8", errors="replace")

    lowered_type = str(content_type or "").lower()
    if "html" in lowered_type or "xml" in lowered_type:
        parser = VisibleTextParser()
        parser.feed(decoded)
        title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()
        text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
        return title, text
    return "", re.sub(r"\s+", " ", decoded).strip()


class ScannerFetchError(RuntimeError):
    pass


@dataclass(slots=True)
class FetchResult:
    url: str
    status: int
    content: bytes
    content_type: str
    etag: str | None
    last_modified: str | None
    retrieved_utc: str
    not_modified: bool = False


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, validator) -> None:
        super().__init__()
        self.validator = validator

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        absolute = urljoin(req.full_url, newurl)
        if not self.validator(absolute):
            raise ScannerFetchError(f"Redirect blocked by scanner policy: {absolute}")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


class SafeHttpClient:
    """HTTPS-only client with allowlists, robots checks, response caps, and host pacing."""

    def __init__(
        self,
        allowed_domains: Iterable[str],
        *,
        user_agent: str = USER_AGENT,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        host_delay_seconds: float = DEFAULT_HOST_DELAY_SECONDS,
    ) -> None:
        self.allowed_domains = tuple(sorted({
            str(domain).lower().strip().rstrip(".")
            for domain in allowed_domains
            if str(domain).strip()
        }))
        self.user_agent = user_agent
        self.timeout_seconds = max(2, min(int(timeout_seconds), 30))
        self.max_response_bytes = max(4096, int(max_response_bytes))
        self.host_delay_seconds = max(0.2, float(host_delay_seconds))
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, tuple[float, RobotFileParser | None, bool]] = {}
        self._dns_cache: dict[str, tuple[float, bool]] = {}
        self._lock = threading.RLock()
        self._opener = build_opener(
            _SafeRedirectHandler(self.is_allowed_network_url)
        )

    def is_allowed_url(self, url: str) -> bool:
        try:
            parsed = urlparse(str(url))
        except ValueError:
            return False
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.port not in {None, 443}:
            return False
        return is_public_hostname(parsed.hostname) and host_matches(
            parsed.hostname,
            self.allowed_domains,
        )

    def is_allowed_network_url(self, url: str) -> bool:
        if not self.is_allowed_url(url):
            return False
        hostname = urlparse(str(url)).hostname or ""
        now = time.time()
        with self._lock:
            cached = self._dns_cache.get(hostname)
        if cached and now - cached[0] < 15 * 60:
            return cached[1]
        allowed = addresses_are_public(hostname)
        with self._lock:
            self._dns_cache[hostname] = (now, allowed)
        return allowed

    def _pace(self, hostname: str) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request.get(hostname, 0.0)
            delay = self.host_delay_seconds - elapsed
        if delay > 0:
            time.sleep(delay)
        with self._lock:
            self._last_request[hostname] = time.monotonic()

    def _request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        if not self.is_allowed_network_url(url):
            raise ScannerFetchError(f"URL blocked by scanner allowlist: {url}")
        hostname = urlparse(url).hostname or ""
        self._pace(hostname)
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/html, text/plain, application/xml;q=0.9",
            "Accept-Encoding": "gzip",
        }
        request_headers.update(headers or {})
        request = Request(url, headers=request_headers, method="GET")
        try:
            response = self._opener.open(request, timeout=self.timeout_seconds)
            final_url = response.geturl()
            if not self.is_allowed_network_url(final_url):
                raise ScannerFetchError(f"Final URL blocked by scanner policy: {final_url}")
            raw = response.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raise ScannerFetchError(
                    f"Response exceeded {self.max_response_bytes} bytes: {url}"
                )
            if str(response.headers.get("Content-Encoding", "")).lower() == "gzip":
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
                    raw = compressed.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ScannerFetchError("Decompressed response exceeded scanner limit")
            return FetchResult(
                url=final_url,
                status=int(getattr(response, "status", 200)),
                content=raw,
                content_type=str(response.headers.get("Content-Type", "")),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                retrieved_utc=utc_now(),
            )
        except HTTPError as error:
            if error.code == 304:
                return FetchResult(
                    url=url,
                    status=304,
                    content=b"",
                    content_type="",
                    etag=error.headers.get("ETag") if error.headers else None,
                    last_modified=(
                        error.headers.get("Last-Modified") if error.headers else None
                    ),
                    retrieved_utc=utc_now(),
                    not_modified=True,
                )
            raise ScannerFetchError(f"HTTP {error.code} for {url}") from error
        except (
            URLError,
            TimeoutError,
            OSError,
            ValueError,
            EOFError,
            gzip.BadGzipFile,
        ) as error:
            raise ScannerFetchError(f"Network error for {url}: {error}") from error

    def robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        now = time.time()
        with self._lock:
            cached = self._robots.get(root)
        if cached and now - cached[0] < 24 * 60 * 60:
            parser, allowed_on_error = cached[1], cached[2]
            return parser.can_fetch(self.user_agent, url) if parser else allowed_on_error

        parser = RobotFileParser()
        robots_url = root + "/robots.txt"
        allowed_on_error = False
        try:
            result = self._request(robots_url)
            parser.set_url(robots_url)
            parser.parse(result.content.decode("utf-8", errors="replace").splitlines())
        except ScannerFetchError as error:
            message = str(error)
            if any(f"HTTP {status}" in message for status in (400, 404, 410)):
                parser = None
                allowed_on_error = True
            else:
                parser = None
                allowed_on_error = False
        with self._lock:
            self._robots[root] = (now, parser, allowed_on_error)
        return parser.can_fetch(self.user_agent, url) if parser else allowed_on_error

    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        headers: dict[str, str] | None = None,
        respect_robots: bool = True,
    ) -> FetchResult:
        if respect_robots and not self.robots_allowed(url):
            raise ScannerFetchError(f"robots.txt does not allow this scanner URL: {url}")
        conditional = dict(headers or {})
        if etag:
            conditional["If-None-Match"] = etag
        if last_modified:
            conditional["If-Modified-Since"] = last_modified
        return self._request(url, conditional)


class IndexedJsonlStore:
    """Append-only JSONL content with a SQLite term index and byte-offset retrieval."""

    def __init__(
        self,
        collection: str,
        database_path: Path,
        index_path: Path,
        *,
        max_database_bytes: int = DEFAULT_MAX_DATABASE_BYTES,
        max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES,
    ) -> None:
        self.collection = str(collection)
        self.database_path = Path(database_path)
        self.index_path = Path(index_path)
        self.max_database_bytes = max(1_000_000, int(max_database_bytes))
        self.max_record_bytes = max(16_000, int(max_record_bytes))
        self._lock = threading.RLock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_index()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.index_path), timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize_index(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS records (
                    record_id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    source_id TEXT,
                    source_type TEXT,
                    summary TEXT,
                    content_hash TEXT NOT NULL,
                    etag TEXT,
                    last_modified TEXT,
                    version INTEGER NOT NULL,
                    byte_offset INTEGER NOT NULL,
                    byte_length INTEGER NOT NULL,
                    trust_score REAL NOT NULL DEFAULT 0,
                    stored_utc TEXT NOT NULL,
                    last_checked_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS terms (
                    term TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    weight INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (term, record_id),
                    FOREIGN KEY (record_id) REFERENCES records(record_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term);
                CREATE INDEX IF NOT EXISTS idx_records_collection ON records(collection);
                CREATE INDEX IF NOT EXISTS idx_records_source ON records(source_id);
                """
            )

    def database_bytes(self) -> int:
        try:
            return self.database_path.stat().st_size
        except OSError:
            return 0

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM records").fetchone()
        return int(row["count"] if row else 0)

    def state(self, record_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM records WHERE record_id = ?",
                (str(record_id),),
            ).fetchone()
        return dict(row) if row else {}

    def _read_at(self, offset: int, length: int) -> dict[str, Any]:
        try:
            with self.database_path.open("rb") as file:
                file.seek(int(offset))
                raw = file.read(int(length))
            return json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def get(self, record_id: str) -> dict[str, Any]:
        state = self.state(record_id)
        if not state:
            return {}
        return self._read_at(state["byte_offset"], state["byte_length"])

    def _fit_record(self, record: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        fitted = dict(record)
        fitted["text"] = str(fitted.get("text", ""))
        while True:
            raw = (
                json.dumps(fitted, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            if len(raw) <= self.max_record_bytes:
                return fitted, raw
            text = fitted.get("text", "")
            if len(text) < 2000:
                raise ValueError("Record metadata exceeds the configured record size")
            fitted["text"] = text[: max(1200, int(len(text) * 0.72))]
            fitted["truncated"] = True

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        normalized = dict(record)
        normalized["collection"] = self.collection
        normalized["record_id"] = str(
            normalized.get("record_id")
            or stable_id(
                normalized.get("source_id"),
                normalized.get("url"),
                normalized.get("title"),
                prefix=self.collection,
            )
        )
        normalized["title"] = str(normalized.get("title") or "Untitled").strip()[:500]
        normalized["summary"] = str(normalized.get("summary") or "").strip()[:4000]
        normalized["text"] = str(normalized.get("text") or "").strip()
        normalized["url"] = str(normalized.get("url") or "")[:2000]
        normalized["source_id"] = str(normalized.get("source_id") or "unknown")[:120]
        normalized["source_type"] = str(normalized.get("source_type") or "web")[:120]
        normalized["trust_score"] = float(normalized.get("trust_score") or 0)
        normalized["retrieved_utc"] = str(normalized.get("retrieved_utc") or now)
        normalized["last_checked_utc"] = now
        digest = str(normalized.get("content_hash") or content_hash(
            normalized["title"], normalized["summary"], normalized["text"]
        ))
        normalized["content_hash"] = digest

        with self._lock:
            previous = self.state(normalized["record_id"])
            if previous and previous.get("content_hash") == digest:
                with self._connect() as connection:
                    connection.execute(
                        """
                        UPDATE records
                        SET last_checked_utc = ?, etag = COALESCE(?, etag),
                            last_modified = COALESCE(?, last_modified)
                        WHERE record_id = ?
                        """,
                        (
                            now,
                            normalized.get("etag"),
                            normalized.get("last_modified"),
                            normalized["record_id"],
                        ),
                    )
                return {"status": "unchanged", "record_id": normalized["record_id"]}

            normalized["version"] = int(previous.get("version", 0)) + 1
            normalized["stored_utc"] = now
            fitted, raw = self._fit_record(normalized)
            if self.database_bytes() + len(raw) > self.max_database_bytes:
                self.compact()
            if self.database_bytes() + len(raw) > self.max_database_bytes:
                return {
                    "status": "quota_reached",
                    "record_id": normalized["record_id"],
                    "database_bytes": self.database_bytes(),
                }

            with self.database_path.open("ab") as file:
                offset = file.tell()
                file.write(raw)

            weighted_terms: dict[str, int] = {}
            for term in text_terms(fitted["title"], limit=35):
                weighted_terms[term] = max(weighted_terms.get(term, 0), 6)
            for term in text_terms(fitted["summary"], limit=60):
                weighted_terms[term] = max(weighted_terms.get(term, 0), 3)
            for term in text_terms(fitted.get("text", ""), limit=180):
                weighted_terms[term] = max(weighted_terms.get(term, 0), 1)
            for term in fitted.get("terms", [])[:100]:
                clean = text_terms(term, limit=2)
                if clean:
                    weighted_terms[clean[0]] = max(weighted_terms.get(clean[0], 0), 4)

            metadata = fitted.get("metadata", {})
            metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
            with self._connect() as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute(
                    """
                    INSERT OR REPLACE INTO records (
                        record_id, collection, title, url, source_id, source_type,
                        summary, content_hash, etag, last_modified, version,
                        byte_offset, byte_length, trust_score, stored_utc,
                        last_checked_utc, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fitted["record_id"], self.collection, fitted["title"],
                        fitted["url"], fitted["source_id"], fitted["source_type"],
                        fitted["summary"], digest, fitted.get("etag"),
                        fitted.get("last_modified"), fitted["version"], offset,
                        len(raw), fitted["trust_score"], now, now, metadata_json,
                    ),
                )
                connection.execute(
                    "DELETE FROM terms WHERE record_id = ?",
                    (fitted["record_id"],),
                )
                connection.executemany(
                    "INSERT OR REPLACE INTO terms (term, record_id, weight) VALUES (?, ?, ?)",
                    [
                        (term, fitted["record_id"], weight)
                        for term, weight in weighted_terms.items()
                    ],
                )
            return {
                "status": "updated" if previous else "inserted",
                "record_id": fitted["record_id"],
                "version": fitted["version"],
                "database_bytes": self.database_bytes(),
            }

    def mark_checked(
        self,
        record_id: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE records
                SET last_checked_utc = ?, etag = COALESCE(?, etag),
                    last_modified = COALESCE(?, last_modified)
                WHERE record_id = ?
                """,
                (utc_now(), etag, last_modified, str(record_id)),
            )

    def search(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = text_terms(query, limit=30)
        if not terms or not self.index_path.exists():
            return []
        placeholders = ",".join("?" for _ in terms)
        sql = f"""
            SELECT r.*, SUM(t.weight) AS search_score,
                   COUNT(DISTINCT t.term) AS matched_terms
            FROM terms t
            JOIN records r ON r.record_id = t.record_id
            WHERE t.term IN ({placeholders}) AND r.collection = ?
            GROUP BY r.record_id
            ORDER BY search_score DESC, matched_terms DESC, r.stored_utc DESC
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(
                sql,
                (*terms, self.collection, max(1, int(limit)) * 4),
            ).fetchall()

        lowered_query = re.sub(r"\s+", " ", str(query).lower()).strip()
        results = []
        for row in rows:
            state = dict(row)
            record = self._read_at(state["byte_offset"], state["byte_length"])
            if not record:
                continue
            score = float(state.get("search_score") or 0)
            title = str(record.get("title", "")).lower()
            if lowered_query and lowered_query in title:
                score += 30
            sources = record.get("sources")
            if not isinstance(sources, list):
                sources = [{
                    "source_id": record.get("source_id"),
                    "source_name": record.get("source_name") or record.get("source_id"),
                    "url": record.get("url"),
                    "trust_score": record.get("trust_score", 0),
                    "retrieved_utc": record.get("retrieved_utc"),
                }]
            results.append({
                "article_id": record.get("record_id"),
                "record_id": record.get("record_id"),
                "collection": self.collection,
                "title": record.get("title"),
                "summary": record.get("summary"),
                "content_excerpt": str(record.get("text", ""))[:2400],
                "url": record.get("url"),
                "source_id": record.get("source_id"),
                "source_type": record.get("source_type"),
                "sources": sources[:6],
                "source_count": len(sources),
                "trust_score": float(record.get("trust_score") or 0),
                "score": round(score, 2),
                "version": record.get("version"),
                "stored_utc": record.get("stored_utc"),
                "last_checked_utc": record.get("last_checked_utc"),
                "metadata": record.get("metadata", {}),
            })
        results.sort(
            key=lambda item: (item.get("score", 0), item.get("trust_score", 0)),
            reverse=True,
        )
        return results[:max(1, int(limit))]

    def compact(self) -> dict[str, Any]:
        """Rewrite only latest indexed versions so update checks can continue at quota."""
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT record_id, byte_offset, byte_length FROM records ORDER BY record_id"
                ).fetchall()
            if not rows or not self.database_path.exists():
                return {"status": "empty", "database_bytes": self.database_bytes()}

            temporary = self.database_path.with_suffix(self.database_path.suffix + ".compact")
            offsets: dict[str, tuple[int, int]] = {}
            try:
                with temporary.open("wb") as output:
                    for row in rows:
                        record = self._read_at(row["byte_offset"], row["byte_length"])
                        if not record:
                            raise OSError(f"Could not read indexed record {row['record_id']}")
                        raw = (
                            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                        ).encode("utf-8")
                        offset = output.tell()
                        output.write(raw)
                        offsets[row["record_id"]] = (offset, len(raw))
                temporary.replace(self.database_path)
                with self._connect() as connection:
                    connection.executemany(
                        "UPDATE records SET byte_offset = ?, byte_length = ? WHERE record_id = ?",
                        [
                            (offset, length, record_id)
                            for record_id, (offset, length) in offsets.items()
                        ],
                    )
            except OSError:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                return {"status": "failed", "database_bytes": self.database_bytes()}
            return {
                "status": "compacted",
                "records": len(offsets),
                "database_bytes": self.database_bytes(),
            }


class BaseWebScanner:
    """Persistent rotating target queue with one bounded background worker."""

    def __init__(
        self,
        scanner_id: str,
        source_file: Path,
        *,
        sleep_seconds: int = 300,
    ) -> None:
        self.scanner_id = scanner_id
        self.source_file = Path(source_file)
        self.config = load_json(self.source_file, {})
        self.collection = str(self.config.get("collection") or scanner_id)
        self.sleep_seconds = max(30, int(self.config.get("sleep_seconds", sleep_seconds)))
        self.queue_file = DATA_DIR / f"{scanner_id}_scan_queue.json"
        self.statistics_file = DATA_DIR / f"{scanner_id}_scan_statistics.json"
        self.database_file = DATA_DIR / f"{scanner_id}_scan_database.jsonl"
        self.index_file = DATA_DIR / f"{scanner_id}_scan_index.sqlite3"
        self.targets = {
            str(item.get("target_id")): item
            for item in self.config.get("targets", [])
            if isinstance(item, dict) and item.get("target_id")
        }
        allowed_domains = self.config.get("allowed_domains", [])
        self.client = SafeHttpClient(
            allowed_domains,
            user_agent=str(self.config.get("user_agent") or USER_AGENT),
            timeout_seconds=int(self.config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            max_response_bytes=int(
                self.config.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES)
            ),
            host_delay_seconds=float(
                self.config.get("host_delay_seconds", DEFAULT_HOST_DELAY_SECONDS)
            ),
        )
        self.store = IndexedJsonlStore(
            self.collection,
            self.database_file,
            self.index_file,
            max_database_bytes=int(
                self.config.get("max_database_bytes", DEFAULT_MAX_DATABASE_BYTES)
            ),
            max_record_bytes=int(
                self.config.get("max_record_bytes", DEFAULT_MAX_RECORD_BYTES)
            ),
        )
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def _queue(self) -> dict[str, Any]:
        queue = load_json(self.queue_file, {})
        pending = [
            target_id for target_id in queue.get("pending", [])
            if target_id in self.targets
        ]
        if not pending:
            pending = list(self.targets)
        queue["pending"] = list(dict.fromkeys(pending))
        queue.setdefault("target_state", {})
        queue["scanner_id"] = self.scanner_id
        queue["updated_utc"] = utc_now()
        return queue

    def process_target(self, target: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def run_once(self, max_targets: int | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        limit = max(1, min(
            int(max_targets or self.config.get("batch_size", 1)),
            int(self.config.get("max_batch_size", 3)),
        ))
        stored = 0
        unchanged = 0
        errors = []
        processed = []
        with self._lock:
            queue = self._queue()
            pending = queue["pending"]
            for _ in range(limit):
                if self.stop_event.is_set() or not pending:
                    break
                target_id = pending.pop(0)
                target = self.targets.get(target_id)
                if not target:
                    continue
                target_result = {"checked_utc": utc_now()}
                try:
                    records = self.process_target(target)
                    statuses = []
                    for record in records[: int(self.config.get("max_records_per_target", 8))]:
                        result = self.store.upsert(record)
                        statuses.append(result)
                        if result.get("status") in {"inserted", "updated"}:
                            stored += 1
                        elif result.get("status") == "unchanged":
                            unchanged += 1
                    target_result["statuses"] = statuses
                    target_result["status"] = "ok"
                except Exception as error:
                    message = str(error)[:1000]
                    errors.append({"target_id": target_id, "error": message})
                    target_result.update({"status": "error", "error": message})
                pending.append(target_id)
                queue["target_state"][target_id] = target_result
                processed.append(target_id)
            queue["pending"] = pending
            queue["updated_utc"] = utc_now()
            atomic_write_json(self.queue_file, queue)

        stats = load_json(self.statistics_file, {})
        stats.update({
            "scanner_id": self.scanner_id,
            "collection": self.collection,
            "runs": int(stats.get("runs", 0)) + 1,
            "targets_configured": len(self.targets),
            "records_indexed": self.store.count(),
            "database_bytes": self.store.database_bytes(),
            "max_database_bytes": self.store.max_database_bytes,
            "last_run": {
                "processed_targets": processed,
                "stored_or_updated": stored,
                "unchanged": unchanged,
                "errors": errors,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "completed_utc": utc_now(),
            },
            "updated_utc": utc_now(),
        })
        atomic_write_json(self.statistics_file, stats)
        return stats["last_run"]

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            self.run_once()
            self.stop_event.wait(self.sleep_seconds)

    def start(self) -> threading.Thread:
        if self.thread and self.thread.is_alive():
            return self.thread
        self.thread = threading.Thread(
            target=self.run_forever,
            name=f"Canri{self.scanner_id.title()}Scanner",
            daemon=True,
        )
        self.thread.start()
        return self.thread

    def stop(self) -> None:
        self.stop_event.set()


def scanner_background_enabled() -> bool:
    return os.environ.get("CANRI_WEB_SCANNERS_BACKGROUND", "1").lower() not in {
        "0", "false", "no", "off"
    }
