"""Bounded scanner for GitHub metadata, code forums, PyPI, and Python docs."""

from __future__ import annotations

import html
import json
import os
import re
import time
from urllib.parse import urlencode

from Code_artifact_catalog import (
    CodeArtifactCatalog,
    extract_python_documentation_callables,
)
from Web_scanner_core import (
    DATA_DIR,
    BaseWebScanner,
    ScannerFetchError,
    extract_visible_text,
    scanner_background_enabled,
    stable_id,
    utc_now,
)


SOURCE_FILE = DATA_DIR / "Code_scan_sources.json"


def clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


class CodeKnowledgeScanner(BaseWebScanner):
    def __init__(self) -> None:
        super().__init__("code", SOURCE_FILE, sleep_seconds=300)
        self._stack_backoff_until = 0.0
        self.artifact_catalog = CodeArtifactCatalog()
        self.artifact_catalog.seed_local_standard_library()

    def _json(self, url: str, *, headers=None, state=None):
        state = state or {}
        result = self.client.fetch(
            url,
            headers=headers,
            etag=state.get("etag"),
            last_modified=state.get("last_modified"),
            respect_robots=False,
        )
        if result.not_modified:
            return result, None
        try:
            return result, json.loads(result.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
            raise ScannerFetchError(f"Invalid JSON response from {url}: {error}") from error

    def _github_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token_name = str(self.config.get("github_token_environment", "GITHUB_TOKEN"))
        token = os.environ.get(token_name)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _github_records(self, target: dict) -> list[dict]:
        query = str(target.get("query", "")).strip()
        url = "https://api.github.com/search/repositories?" + urlencode({
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5,
        })
        result, payload = self._json(url, headers=self._github_headers())
        records = []
        for item in (payload or {}).get("items", [])[:5]:
            if not isinstance(item, dict):
                continue
            full_name = str(item.get("full_name") or item.get("name") or "repository")
            description = str(item.get("description") or "").strip()
            topics = [str(value) for value in item.get("topics", [])[:20]]
            license_data = item.get("license") if isinstance(item.get("license"), dict) else {}
            repository_url = str(item.get("html_url") or "")
            text = " ".join(filter(None, [
                description,
                f"Primary language: {item.get('language')}." if item.get("language") else "",
                f"Topics: {', '.join(topics)}." if topics else "",
                f"License: {license_data.get('spdx_id')}." if license_data.get("spdx_id") else "",
            ]))
            records.append({
                "record_id": stable_id("github", full_name, prefix="code"),
                "title": full_name,
                "summary": description[:1600],
                "text": text,
                "url": repository_url,
                "source_id": "github_api",
                "source_name": "GitHub public repository metadata",
                "source_type": "code_repository_metadata",
                "trust_score": 78,
                "retrieved_utc": result.retrieved_utc,
                "terms": [query, item.get("language", ""), *topics],
                "metadata": {
                    "query": query,
                    "full_name": full_name,
                    "default_branch": item.get("default_branch"),
                    "language": item.get("language"),
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "open_issues": item.get("open_issues_count", 0),
                    "archived": item.get("archived", False),
                    "updated_at": item.get("updated_at"),
                    "license": license_data.get("spdx_id"),
                    "api_scope": "metadata_only_no_repository_mirroring",
                },
                "sources": [{
                    "source_id": "github_api",
                    "source_name": "GitHub REST API",
                    "url": repository_url,
                    "trust_score": 78,
                    "retrieved_utc": result.retrieved_utc,
                }],
            })
        return records

    def _pypi_records(self, target: dict) -> list[dict]:
        project = str(target.get("project", "")).strip()
        record_id = stable_id("pypi", project, prefix="code")
        state = self.store.state(record_id)
        result, payload = self._json(str(target["url"]), state=state)
        if payload is None:
            self.store.mark_checked(
                record_id,
                etag=result.etag,
                last_modified=result.last_modified,
            )
            return []
        info = payload.get("info", {}) if isinstance(payload, dict) else {}
        description = clean_html_text(info.get("description", ""))[:35_000]
        summary = str(info.get("summary") or "").strip()
        project_urls = info.get("project_urls") if isinstance(info.get("project_urls"), dict) else {}
        raw_keywords = info.get("keywords") or ""
        if isinstance(raw_keywords, str):
            keyword_terms = raw_keywords.replace(",", " ").split()
        elif isinstance(raw_keywords, list):
            keyword_terms = [str(value) for value in raw_keywords]
        else:
            keyword_terms = []
        requires_dist = [
            str(item) for item in (info.get("requires_dist") or [])[:100]
        ]
        vulnerabilities = payload.get("vulnerabilities", []) if isinstance(payload, dict) else []
        return [{
            "record_id": record_id,
            "title": str(info.get("name") or project),
            "summary": summary[:2000],
            "text": " ".join(filter(None, [
                summary,
                description,
                f"Version: {info.get('version')}.",
                f"Requires Python: {info.get('requires_python')}." if info.get("requires_python") else "",
                f"Dependencies: {'; '.join(requires_dist)}." if requires_dist else "",
            ])),
            "url": str(info.get("package_url") or target["url"]),
            "source_id": "pypi_json_api",
            "source_name": "Python Package Index",
            "source_type": "official_package_metadata",
            "trust_score": 88,
            "etag": result.etag,
            "last_modified": result.last_modified,
            "retrieved_utc": result.retrieved_utc,
            "terms": [project, *keyword_terms, *requires_dist[:20]],
            "metadata": {
                "project": project,
                "version": info.get("version"),
                "requires_python": info.get("requires_python"),
                "requires_dist": requires_dist,
                "license": info.get("license_expression") or info.get("license"),
                "project_urls": project_urls,
                "known_vulnerabilities": vulnerabilities[:20],
                "metadata_notice": "Package metadata is publisher-provided and must be validated before use.",
            },
            "sources": [{
                "source_id": "pypi_json_api",
                "source_name": "PyPI JSON API",
                "url": str(info.get("package_url") or target["url"]),
                "trust_score": 88,
                "retrieved_utc": result.retrieved_utc,
            }],
        }]

    def _stack_overflow_records(self, target: dict) -> list[dict]:
        remaining = self._stack_backoff_until - time.monotonic()
        if remaining > 0:
            time.sleep(min(remaining, 120.0))
        query = str(target.get("query", "")).strip()
        url = "https://api.stackexchange.com/2.3/search/advanced?" + urlencode({
            "site": "stackoverflow",
            "q": query,
            "pagesize": 5,
            "order": "desc",
            "sort": "relevance",
        })
        result, payload = self._json(url)
        backoff = int((payload or {}).get("backoff") or 0)
        if backoff > 0:
            self._stack_backoff_until = max(
                self._stack_backoff_until,
                time.monotonic() + min(backoff, 120),
            )
        records = []
        for item in (payload or {}).get("items", [])[:5]:
            if not isinstance(item, dict):
                continue
            question_id = item.get("question_id")
            title = clean_html_text(item.get("title", ""))
            tags = [str(tag) for tag in item.get("tags", [])[:20]]
            question_url = str(item.get("link") or "")
            summary = (
                f"Stack Overflow question with score {item.get('score', 0)}, "
                f"{item.get('answer_count', 0)} answers, and tags {', '.join(tags)}."
            )
            records.append({
                "record_id": stable_id("stackoverflow", question_id, prefix="code"),
                "title": title or f"Stack Overflow question {question_id}",
                "summary": summary,
                "text": f"{title}. {summary}",
                "url": question_url,
                "source_id": "stackexchange_api",
                "source_name": "Stack Overflow via Stack Exchange API",
                "source_type": "code_forum_metadata",
                "trust_score": 68,
                "retrieved_utc": result.retrieved_utc,
                "terms": [query, *tags],
                "metadata": {
                    "query": query,
                    "question_id": question_id,
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                    "accepted_answer_id": item.get("accepted_answer_id"),
                    "last_activity_date": item.get("last_activity_date"),
                    "backoff_seconds": (payload or {}).get("backoff"),
                    "evidence_notice": "Forum content is community-authored and requires verification.",
                },
                "sources": [{
                    "source_id": "stackexchange_api",
                    "source_name": "Stack Exchange API",
                    "url": question_url,
                    "trust_score": 68,
                    "retrieved_utc": result.retrieved_utc,
                }],
            })
        return records

    def _python_docs_records(self, target: dict) -> list[dict]:
        record_id = stable_id("python_docs", target.get("url"), prefix="code")
        state = self.store.state(record_id)
        result = self.client.fetch(
            str(target["url"]),
            etag=state.get("etag"),
            last_modified=state.get("last_modified"),
            respect_robots=True,
        )
        if result.not_modified:
            self.store.mark_checked(
                record_id,
                etag=result.etag,
                last_modified=result.last_modified,
            )
            return []
        title, text = extract_visible_text(result.content, result.content_type)
        if not text:
            raise ScannerFetchError(f"Python documentation page had no text: {target['url']}")
        module = str(target.get("module") or title or "Python documentation")
        version_match = re.search(
            r"Python\s+(\d+\.\d+(?:\.\d+)?)",
            f"{title} {text[:500]}",
            flags=re.IGNORECASE,
        )
        callables = extract_python_documentation_callables(
            result.content,
            library=module,
            source_url=result.url,
            retrieved_utc=result.retrieved_utc,
            library_version=version_match.group(1) if version_match else None,
        )
        catalog_update = self.artifact_catalog.upsert_many(callables)
        return [{
            "record_id": record_id,
            "title": title or f"Python documentation: {module}",
            "summary": text[:1600],
            "text": text[:60_000],
            "url": result.url,
            "source_id": "python_docs",
            "source_name": "Official Python documentation",
            "source_type": "official_language_documentation",
            "trust_score": 96,
            "etag": result.etag,
            "last_modified": result.last_modified,
            "retrieved_utc": result.retrieved_utc,
            "terms": [module, "python", "documentation"],
            "metadata": {
                "module_or_section": module,
                "library_callables_discovered": len(callables),
                "library_catalog_update": catalog_update,
                "artifact_policy": (
                    "Only structured API signatures and generated call templates are indexed; "
                    "arbitrary executable page examples are not copied."
                ),
            },
            "sources": [{
                "source_id": "python_docs",
                "source_name": "Python documentation",
                "url": result.url,
                "trust_score": 96,
                "retrieved_utc": result.retrieved_utc,
            }],
        }]

    def run_once(self, max_targets: int | None = None) -> dict:
        result = super().run_once(max_targets=max_targets)
        result["artifact_catalog"] = self.artifact_catalog.summary()
        return result

    def process_target(self, target: dict) -> list[dict]:
        adapter = str(target.get("adapter", ""))
        if adapter == "github_repositories":
            return self._github_records(target)
        if adapter == "pypi_project":
            return self._pypi_records(target)
        if adapter == "stack_overflow":
            return self._stack_overflow_records(target)
        if adapter == "python_docs":
            return self._python_docs_records(target)
        raise ValueError(f"Unknown code scanner adapter: {adapter}")


_scanner: CodeKnowledgeScanner | None = None


def get_code_knowledge_scanner() -> CodeKnowledgeScanner:
    global _scanner
    if _scanner is None:
        _scanner = CodeKnowledgeScanner()
    return _scanner


def start_background_code_scanner() -> CodeKnowledgeScanner | None:
    if not scanner_background_enabled() or not SOURCE_FILE.exists():
        return None
    scanner = get_code_knowledge_scanner()
    scanner.start()
    return scanner


if __name__ == "__main__":
    print(json.dumps(get_code_knowledge_scanner().run_once(), ensure_ascii=False, indent=2))
