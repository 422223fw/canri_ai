"""Curated general-knowledge scanner using encyclopedic and scholarly APIs."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from Web_scanner_core import (
    DATA_DIR,
    BaseWebScanner,
    ScannerFetchError,
    scanner_background_enabled,
    stable_id,
)


SOURCE_FILE = DATA_DIR / "General_scan_sources.json"
EXCLUDED_CODE_MARKERS = {
    "github", "source code", "programming library", "python package",
    "javascript framework", "software repository", "code snippet",
}


def clean_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


class GeneralWebScanner(BaseWebScanner):
    def __init__(self) -> None:
        super().__init__("general", SOURCE_FILE, sleep_seconds=420)

    def _json(self, url: str):
        result = self.client.fetch(url, respect_robots=False)
        try:
            payload = json.loads(result.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
            raise ScannerFetchError(f"Invalid JSON response from {url}: {error}") from error
        return result, payload

    def _allowed_general_record(self, title: str, text: str) -> bool:
        sample = f"{title} {text[:1200]}".lower()
        return not any(marker in sample for marker in EXCLUDED_CODE_MARKERS)

    def _wikipedia_records(self, target: dict) -> list[dict]:
        query = str(target.get("query", "")).strip()
        url = "https://en.wikipedia.org/w/api.php?" + urlencode({
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 0,
            "gsrlimit": 5,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "inprop": "url",
            "format": "json",
            "formatversion": 2,
        })
        result, payload = self._json(url)
        records = []
        pages = (payload.get("query") or {}).get("pages", []) if isinstance(payload, dict) else []
        for page in pages[:5]:
            if not isinstance(page, dict) or page.get("missing"):
                continue
            title = str(page.get("title") or "Wikipedia article")
            extract = clean_markup(page.get("extract", ""))
            if not extract or not self._allowed_general_record(title, extract):
                continue
            page_url = str(page.get("fullurl") or "")
            records.append({
                "record_id": stable_id("wikipedia", page.get("pageid") or title, prefix="general"),
                "title": title,
                "summary": extract[:2000],
                "text": extract[:55_000],
                "url": page_url,
                "source_id": "wikipedia_en_general",
                "source_name": "English Wikipedia",
                "source_type": "encyclopedia",
                "trust_score": 82,
                "retrieved_utc": result.retrieved_utc,
                "terms": [query, target.get("category", "")],
                "metadata": {
                    "query": query,
                    "category": target.get("category"),
                    "page_id": page.get("pageid"),
                    "content_scope": "introductory_extract",
                },
                "sources": [{
                    "source_id": "wikipedia_en_general",
                    "source_name": "English Wikipedia",
                    "url": page_url,
                    "trust_score": 82,
                    "retrieved_utc": result.retrieved_utc,
                }],
            })
        return records

    def _crossref_records(self, target: dict) -> list[dict]:
        query = str(target.get("query", "")).strip()
        url = "https://api.crossref.org/works?" + urlencode({
            "query": query,
            "rows": 5,
            "select": "DOI,title,abstract,author,published,URL,type,subject,publisher",
        })
        result, payload = self._json(url)
        items = ((payload.get("message") or {}).get("items", [])) if isinstance(payload, dict) else []
        records = []
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            titles = item.get("title") or []
            title = clean_markup(titles[0] if titles else "Scholarly work")
            abstract = clean_markup(item.get("abstract", ""))
            subjects = [str(value) for value in item.get("subject", [])[:20]]
            authors = []
            for author in item.get("author", [])[:12]:
                if isinstance(author, dict):
                    name = " ".join(filter(None, [author.get("given"), author.get("family")]))
                    if name:
                        authors.append(name)
            summary = abstract or (
                f"Scholarly metadata for {title}. Publisher: {item.get('publisher') or 'unknown'}."
            )
            if not self._allowed_general_record(title, summary):
                continue
            doi = str(item.get("DOI") or "")
            source_url = str(item.get("URL") or (f"https://doi.org/{doi}" if doi else ""))
            records.append({
                "record_id": stable_id("crossref", doi or title, prefix="general"),
                "title": title,
                "summary": summary[:2200],
                "text": " ".join(filter(None, [summary, f"Authors: {', '.join(authors)}.", f"Subjects: {', '.join(subjects)}."])),
                "url": source_url,
                "source_id": "crossref_general",
                "source_name": "Crossref",
                "source_type": "scholarly_metadata",
                "trust_score": 88,
                "retrieved_utc": result.retrieved_utc,
                "terms": [query, target.get("category", ""), *subjects],
                "metadata": {
                    "query": query,
                    "category": target.get("category"),
                    "doi": doi,
                    "authors": authors,
                    "publisher": item.get("publisher"),
                    "publication_type": item.get("type"),
                    "published": item.get("published"),
                    "abstract_available": bool(abstract),
                },
                "sources": [{
                    "source_id": "crossref_general",
                    "source_name": "Crossref",
                    "url": source_url,
                    "trust_score": 88,
                    "retrieved_utc": result.retrieved_utc,
                }],
            })
        return records

    def _pubmed_records(self, target: dict) -> list[dict]:
        query = str(target.get("query", "")).strip()
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": 5,
            "retmode": "json",
            "tool": "canri_knowledge_scanner",
        })
        search_result, search_payload = self._json(search_url)
        identifiers = ((search_payload.get("esearchresult") or {}).get("idlist", []))
        if not identifiers:
            return []
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urlencode({
            "db": "pubmed",
            "id": ",".join(str(value) for value in identifiers[:5]),
            "retmode": "xml",
            "tool": "canri_knowledge_scanner",
        })
        fetch_result = self.client.fetch(fetch_url, respect_robots=False)
        try:
            root = ET.fromstring(fetch_result.content)
        except ET.ParseError as error:
            raise ScannerFetchError(f"Invalid PubMed XML: {error}") from error

        records = []
        for article in root.findall(".//PubmedArticle")[:5]:
            pmid = "".join(article.findtext(".//PMID", default="")).strip()
            title = clean_markup("".join(article.find(".//ArticleTitle").itertext())) if article.find(".//ArticleTitle") is not None else "PubMed article"
            abstract_parts = [
                clean_markup("".join(node.itertext()))
                for node in article.findall(".//Abstract/AbstractText")
            ]
            abstract = " ".join(part for part in abstract_parts if part)
            journal = article.findtext(".//Journal/Title", default="")
            doi = ""
            for node in article.findall(".//ArticleId"):
                if str(node.attrib.get("IdType", "")).lower() == "doi" and node.text:
                    doi = node.text.strip()
                    break
            summary = abstract or f"PubMed citation for {title} in {journal}."
            if not self._allowed_general_record(title, summary):
                continue
            page_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            records.append({
                "record_id": stable_id("pubmed", pmid or doi or title, prefix="general"),
                "title": title,
                "summary": summary[:2200],
                "text": summary[:65_000],
                "url": page_url,
                "source_id": "pubmed_general",
                "source_name": "PubMed / NCBI",
                "source_type": "biomedical_literature",
                "trust_score": 94,
                "retrieved_utc": fetch_result.retrieved_utc,
                "terms": [query, target.get("category", ""), journal],
                "metadata": {
                    "query": query,
                    "category": target.get("category"),
                    "pmid": pmid,
                    "doi": doi,
                    "journal": journal,
                    "abstract_available": bool(abstract),
                    "search_retrieved_utc": search_result.retrieved_utc,
                },
                "sources": [{
                    "source_id": "pubmed_general",
                    "source_name": "PubMed / NCBI",
                    "url": page_url,
                    "trust_score": 94,
                    "retrieved_utc": fetch_result.retrieved_utc,
                }],
            })
        return records

    def process_target(self, target: dict) -> list[dict]:
        adapter = str(target.get("adapter", ""))
        if adapter == "wikipedia":
            return self._wikipedia_records(target)
        if adapter == "crossref":
            return self._crossref_records(target)
        if adapter == "pubmed":
            return self._pubmed_records(target)
        raise ValueError(f"Unknown general scanner adapter: {adapter}")


_scanner: GeneralWebScanner | None = None


def get_general_web_scanner() -> GeneralWebScanner:
    global _scanner
    if _scanner is None:
        _scanner = GeneralWebScanner()
    return _scanner


def start_background_general_scanner() -> GeneralWebScanner | None:
    if not scanner_background_enabled() or not SOURCE_FILE.exists():
        return None
    scanner = get_general_web_scanner()
    scanner.start()
    return scanner


if __name__ == "__main__":
    print(json.dumps(get_general_web_scanner().run_once(), ensure_ascii=False, indent=2))
