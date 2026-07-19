"""Official-site product scanner for Canri's initial 100-product catalog."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from Web_scanner_core import (
    DATA_DIR,
    BaseWebScanner,
    ScannerFetchError,
    extract_visible_text,
    scanner_background_enabled,
    text_terms,
    utc_now,
)


SOURCE_FILE = DATA_DIR / "Product_scan_sources.json"


class ProductScanner(BaseWebScanner):
    def __init__(self) -> None:
        super().__init__("product", SOURCE_FILE, sleep_seconds=900)
        self._sitemap_cache: dict[str, list[str]] = {}

    def _sitemap_urls(self, target: dict) -> list[str]:
        domain = str(target.get("official_domain", "")).lower()
        if domain in self._sitemap_cache:
            return self._sitemap_cache[domain]

        locations = []
        for sitemap_url in target.get("sitemap_urls", [])[:2]:
            try:
                result = self.client.fetch(sitemap_url, respect_robots=False)
                root = ET.fromstring(result.content)
            except (ScannerFetchError, ET.ParseError, ValueError):
                continue
            locations.extend(
                str(element.text).strip()
                for element in root.iter()
                if element.tag.lower().endswith("loc") and element.text
            )

        same_domain = []
        for url in locations:
            hostname = (urlparse(url).hostname or "").lower()
            if hostname == domain or hostname.endswith("." + domain):
                same_domain.append(url)
            if len(same_domain) >= 20_000:
                break
        self._sitemap_cache[domain] = same_domain
        return same_domain

    def _discover_product_url(self, target: dict) -> str:
        candidates = self._sitemap_urls(target)
        if not candidates:
            return str(target.get("official_url", ""))
        phrases = target.get("discovery_terms", []) or [target.get("product", "")]
        token_sets = [
            set(text_terms(phrase, limit=8))
            for phrase in phrases
            if str(phrase).strip()
        ]
        ranked = []
        for url in candidates:
            url_terms = set(text_terms(url.replace("/", " "), limit=40))
            score = max((len(tokens.intersection(url_terms)) for tokens in token_sets), default=0)
            if score:
                ranked.append((score, -len(url), url))
        if not ranked:
            return str(target.get("official_url", ""))
        ranked.sort(reverse=True)
        return ranked[0][2]

    def process_target(self, target: dict) -> list[dict]:
        record_id = str(target["target_id"])
        product = str(target.get("product") or "Unknown product")
        company = str(target.get("company") or "Unknown company")
        local_description = str(target.get("local_description") or "").strip()
        source_url = str(target.get("official_url") or "")
        official_title = ""
        official_excerpt = ""
        web_status = "local_catalog_only"
        web_error = None
        etag = None
        last_modified = None

        state = self.store.state(record_id)
        try:
            source_url = self._discover_product_url(target)
            result = self.client.fetch(
                source_url,
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
            official_title, visible_text = extract_visible_text(
                result.content,
                result.content_type,
            )
            product_terms = set(text_terms(product, limit=8))
            page_terms = set(text_terms(f"{official_title} {visible_text}", limit=800))
            if product_terms and product_terms.intersection(page_terms):
                official_excerpt = visible_text[:40_000]
                web_status = "official_page_enriched"
            else:
                web_status = "official_page_not_product_specific"
            source_url = result.url
            etag = result.etag
            last_modified = result.last_modified
        except ScannerFetchError as error:
            web_error = str(error)

        text_parts = [
            f"{product} is a product associated with {company}.",
            local_description,
        ]
        if official_excerpt:
            text_parts.append(official_excerpt)
        summary = local_description or f"{product}, a product from {company}."
        if official_title and official_excerpt:
            summary = f"{summary} Official page title: {official_title}."[:2000]

        return [{
            "record_id": record_id,
            "title": product,
            "summary": summary,
            "text": " ".join(part for part in text_parts if part),
            "url": source_url,
            "source_id": f"official_product:{target.get('company_id')}",
            "source_name": f"{company} official website",
            "source_type": "official_product_site",
            "trust_score": 90 if official_excerpt else 72,
            "etag": etag,
            "last_modified": last_modified,
            "retrieved_utc": utc_now(),
            "terms": [
                product,
                company,
                str(target.get("category", "")),
                *target.get("aliases", []),
            ],
            "metadata": {
                "company_id": target.get("company_id"),
                "company": company,
                "product": product,
                "category": target.get("category"),
                "official_domain": target.get("official_domain"),
                "web_status": web_status,
                "web_error": web_error,
                "change_detection": "etag_last_modified_and_content_hash",
            },
            "sources": [{
                "source_id": f"official_product:{target.get('company_id')}",
                "source_name": f"{company} official website",
                "url": source_url,
                "trust_score": 90 if official_excerpt else 72,
                "retrieved_utc": utc_now(),
            }],
        }]


_scanner: ProductScanner | None = None


def get_product_scanner() -> ProductScanner:
    global _scanner
    if _scanner is None:
        _scanner = ProductScanner()
    return _scanner


def start_background_product_scanner() -> ProductScanner | None:
    if not scanner_background_enabled() or not SOURCE_FILE.exists():
        return None
    scanner = get_product_scanner()
    scanner.start()
    return scanner


if __name__ == "__main__":
    import json

    print(json.dumps(get_product_scanner().run_once(), ensure_ascii=False, indent=2))
