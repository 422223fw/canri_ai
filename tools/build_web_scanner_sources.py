"""Build deterministic source registries for Canri's bounded web scanners."""

from __future__ import annotations

import argparse
import json
import re
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "main_ai_canri" / "data"
COMPANY_PRODUCTS_FILE = DATA_DIR / "Company_products.json"

COMPANY_DOMAINS = {
    "apple": "apple.com",
    "microsoft": "microsoft.com",
    "google": "google.com",
    "openai": "openai.com",
    "amazon": "amazon.com",
    "meta": "meta.com",
    "nvidia": "nvidia.com",
    "tesla": "tesla.com",
    "samsung": "samsung.com",
    "sony": "sony.com",
    "adobe": "adobe.com",
    "intel": "intel.com",
    "amd": "amd.com",
    "ibm": "ibm.com",
    "oracle": "oracle.com",
    "salesforce": "salesforce.com",
    "spotify": "spotify.com",
    "netflix": "netflix.com",
    "cloudflare": "cloudflare.com",
    "cisco": "cisco.com",
    "dell": "dell.com",
    "hp": "hp.com",
    "lenovo": "lenovo.com",
    "asus": "asus.com",
    "valve": "steampowered.com",
    "epic games": "epicgames.com",
    "unity": "unity.com",
    "jetbrains": "jetbrains.com",
    "autodesk": "autodesk.com",
    "shopify": "shopify.com",
}

CODE_CONCEPTS = [
    "asyncio", "authentication", "authorization", "caching", "cli application",
    "concurrency", "configuration", "cryptography", "data validation", "database migration",
    "dependency injection", "error handling", "event driven architecture", "fastapi", "file processing",
    "flask", "graph algorithm", "http client", "json serialization", "logging",
    "machine learning", "message queue", "microservice", "network programming", "observability",
    "orm", "package design", "parallel processing", "performance profiling", "plugin architecture",
    "postgresql", "pytest", "rate limiting", "rest api", "retry strategy",
    "security testing", "serialization", "socket programming", "sqlite", "task scheduling",
    "testing", "threading", "type checking", "websocket", "worker pool",
    "arduino python", "raspberry pi gpio", "sensor calibration", "serial protocol", "scientific computing",
]

CODE_CONCERNS = [
    "best practices", "complete example", "design pattern", "error recovery", "production architecture",
    "security", "testing strategy", "performance", "maintainability", "documentation",
]

PYPI_PROJECTS = [
    "requests", "httpx", "aiohttp", "fastapi", "flask", "django", "starlette", "uvicorn",
    "pydantic", "sqlalchemy", "alembic", "psycopg", "asyncpg", "aiosqlite", "redis",
    "celery", "rq", "dramatiq", "pytest", "pytest-asyncio", "hypothesis", "coverage",
    "ruff", "black", "mypy", "pyright", "tox", "nox", "click", "typer", "rich",
    "textual", "jinja2", "beautifulsoup4", "lxml", "pandas", "numpy", "scipy", "sympy",
    "matplotlib", "seaborn", "plotly", "scikit-learn", "torch", "tensorflow", "keras",
    "transformers", "datasets", "pillow", "opencv-python", "imageio", "soundfile", "librosa",
    "cryptography", "argon2-cffi", "passlib", "pyjwt", "authlib", "bcrypt", "paramiko",
    "pyopenssl", "orjson", "msgpack", "pyyaml", "tomli", "python-dotenv", "attrs",
    "dataclasses-json", "marshmallow", "tenacity", "backoff", "structlog", "loguru",
    "prometheus-client", "opentelemetry-api", "sentry-sdk", "boto3", "google-cloud-storage",
    "azure-storage-blob", "kubernetes", "docker", "fabric", "invoke", "watchdog", "apscheduler",
    "schedule", "networkx", "igraph", "shapely", "geopandas", "folium", "pyserial",
    "gpiozero", "smbus2", "adafruit-blinka", "paho-mqtt", "websockets", "python-socketio",
    "grpcio", "protobuf", "email-validator", "python-multipart", "itsdangerous", "werkzeug",
]

PYTHON_MODULES = [
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii", "bisect", "builtins",
    "bz2", "calendar", "cmath", "cmd", "code", "codecs", "collections", "colorsys", "compileall",
    "concurrent.futures", "configparser", "contextlib", "contextvars", "copy", "csv", "ctypes",
    "dataclasses", "datetime", "decimal", "difflib", "dis", "doctest", "email", "enum", "errno",
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools",
    "gc", "getopt", "getpass", "gettext", "glob", "graphlib", "gzip", "hashlib", "heapq", "hmac",
    "html", "http", "imaplib", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "logging", "lzma", "mailbox", "math", "mimetypes", "multiprocessing", "netrc", "numbers",
    "operator", "os", "pathlib", "pdb", "pickle", "pickletools", "pkgutil", "platform", "plistlib",
    "pprint", "profile", "pstats", "queue", "random", "re", "readline", "reprlib", "resource",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtplib",
    "socket", "socketserver", "sqlite3", "ssl", "statistics", "string", "stringprep", "struct",
    "subprocess", "sys", "sysconfig", "tarfile", "tempfile", "textwrap", "threading", "time",
    "timeit", "tkinter", "token", "tokenize", "tomllib", "trace", "traceback", "tracemalloc",
    "types", "typing", "unicodedata", "unittest", "urllib", "uuid", "venv", "warnings", "wave",
    "weakref", "webbrowser", "xml", "xml.etree.elementtree", "xmlrpc", "zipfile", "zipimport", "zlib",
]

PYTHON_DOC_PATHS = [
    "tutorial/index.html", "tutorial/introduction.html", "tutorial/controlflow.html",
    "tutorial/datastructures.html", "tutorial/modules.html", "tutorial/inputoutput.html",
    "tutorial/errors.html", "tutorial/classes.html", "tutorial/stdlib.html",
    "tutorial/stdlib2.html", "tutorial/venv.html", "tutorial/floatingpoint.html",
    "reference/index.html", "reference/lexical_analysis.html", "reference/datamodel.html",
    "reference/executionmodel.html", "reference/import.html", "reference/expressions.html",
    "reference/simple_stmts.html", "reference/compound_stmts.html", "reference/toplevel_components.html",
    "reference/grammar.html", "howto/argparse.html", "howto/descriptor.html",
    "howto/enum.html", "howto/functional.html", "howto/ipaddress.html", "howto/logging.html",
    "howto/logging-cookbook.html", "howto/regex.html", "howto/sockets.html",
    "howto/sorting.html", "howto/unicode.html", "howto/urllib2.html",
    "howto/instrumentation.html", "howto/isolating-extensions.html", "howto/curses.html",
    "howto/clinic.html", "howto/annotations.html", "howto/a-conceptual-overview-of-asyncio.html",
    "using/index.html", "using/cmdline.html", "using/windows.html", "using/mac.html",
    "using/unix.html", "using/configure.html", "using/editors.html", "using/android.html",
    "faq/index.html", "faq/general.html", "faq/programming.html", "faq/design.html",
    "faq/library.html", "faq/windows.html", "extending/index.html", "extending/extending.html",
    "extending/building.html", "extending/embedding.html", "c-api/index.html",
    "c-api/intro.html", "c-api/stable.html", "c-api/structures.html", "c-api/exceptions.html",
    "c-api/memory.html", "c-api/init.html", "c-api/veryhigh.html", "c-api/refcounting.html",
    "dis.html", "whatsnew/index.html", "glossary.html",
]

GENERAL_SUBJECTS = {
    "physics": ["gravity", "energy", "light", "sound", "electricity", "magnetism", "atoms", "motion", "relativity", "thermodynamics"],
    "biology": ["cells", "genetics", "evolution", "ecosystems", "photosynthesis", "immunity", "microbiology", "neuroscience", "botany", "zoology"],
    "chemistry": ["chemical bonds", "elements", "molecules", "reactions", "acids and bases", "organic chemistry", "materials", "electrochemistry", "polymers", "biochemistry"],
    "earth": ["climate", "weather", "oceans", "volcanoes", "earthquakes", "geology", "atmosphere", "water cycle", "glaciers", "soil"],
    "space": ["solar system", "stars", "galaxies", "black holes", "cosmology", "spaceflight", "exoplanets", "astronomy", "moon", "mars"],
    "history": ["ancient egypt", "roman empire", "silk road", "renaissance", "industrial revolution", "printing press", "maritime exploration", "agriculture history", "cities history", "science history"],
    "geography": ["rivers", "mountains", "deserts", "islands", "countries", "cities", "population", "migration", "natural resources", "maps"],
    "health": ["nutrition", "sleep", "exercise", "public health", "vaccination", "heart health", "mental health", "infectious disease", "medical imaging", "epidemiology"],
    "society": ["education", "economics", "demography", "law", "languages", "art", "music", "literature", "architecture", "transportation"],
    "environment": ["biodiversity", "conservation", "renewable energy", "pollution", "forests", "wetlands", "sustainability", "agriculture", "fresh water", "wildlife"],
}

GENERAL_ASPECTS = [
    "basic explanation", "history", "current research", "key concepts", "real world examples",
    "measurement methods", "common misconceptions", "causes and effects", "important discoveries", "open questions",
]


def write_json(path: Path, value: dict, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --force")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def build_product_sources() -> dict:
    catalog = json.loads(COMPANY_PRODUCTS_FILE.read_text(encoding="utf-8"))
    detailed = catalog.get("products", {})
    targets = []
    seen = set()
    for company_id, company in catalog.get("companies", {}).items():
        domain = COMPANY_DOMAINS.get(company_id)
        if not domain:
            continue
        for product_name in company.get("products", []):
            key = product_name.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            detail = detailed.get(key, {})
            targets.append({
                "target_id": f"product:{slug(company_id)}:{slug(product_name)}",
                "company_id": company_id,
                "company": company.get("name", company_id.title()),
                "product": detail.get("name", product_name),
                "category": detail.get("category", company.get("field", "product")),
                "local_description": detail.get("description", company.get("description", "")),
                "aliases": detail.get("aliases", []),
                "official_domain": domain,
                "official_url": f"https://{domain}/",
                "sitemap_urls": [f"https://{domain}/sitemap.xml"],
                "discovery_terms": [product_name] + detail.get("aliases", []),
            })
            if len(targets) == 100:
                break
        if len(targets) == 100:
            break
    if len(targets) != 100:
        raise RuntimeError(f"Expected 100 product targets, built {len(targets)}")
    return {
        "schema_version": 1,
        "scanner_id": "product",
        "collection": "product",
        "description": "One hundred products enriched only from their companies' official domains.",
        "targets_expected": 100,
        "targets": targets,
        "allowed_domains": sorted({item["official_domain"] for item in targets}),
        "max_database_bytes": 536_870_912,
        "max_response_bytes": 2_000_000,
        "max_record_bytes": 500_000,
        "host_delay_seconds": 3.0,
        "timeout_seconds": 12,
        "batch_size": 1,
        "max_batch_size": 2,
        "max_records_per_target": 2,
        "sleep_seconds": 900,
        "update_strategy": "conditional_get_plus_content_hash",
        "policy": [
            "Only official company domains are allowed.",
            "Honor robots.txt and use sitemaps only for same-domain product discovery.",
            "Store short searchable excerpts and source metadata, not complete site mirrors.",
        ],
    }


def build_code_sources() -> dict:
    combinations = [f"{concept} {concern}" for concept, concern in product(CODE_CONCEPTS, CODE_CONCERNS)]
    github_queries = combinations[:350]
    stack_queries = list(reversed(combinations))[:350]
    targets = []
    for index, query in enumerate(github_queries):
        targets.append({
            "target_id": f"code:github:{index:04d}",
            "adapter": "github_repositories",
            "query": query,
        })
    for index, query in enumerate(stack_queries):
        targets.append({
            "target_id": f"code:stackoverflow:{index:04d}",
            "adapter": "stack_overflow",
            "query": query,
        })
    for name in PYPI_PROJECTS[:100]:
        targets.append({
            "target_id": f"code:pypi:{slug(name)}",
            "adapter": "pypi_project",
            "project": name,
            "url": f"https://pypi.org/pypi/{name}/json",
        })
    documentation_targets = [
        (module, f"https://docs.python.org/3/library/{module}.html")
        for module in dict.fromkeys(PYTHON_MODULES)
    ]
    documentation_targets.extend(
        (path.rsplit("/", 1)[-1].replace(".html", ""), f"https://docs.python.org/3/{path}")
        for path in PYTHON_DOC_PATHS
    )
    if len(documentation_targets) < 200:
        raise RuntimeError("Python documentation registry must contain at least 200 real pages")
    for index, (module, url) in enumerate(documentation_targets[:200]):
        targets.append({
            "target_id": f"code:python-docs:{index:04d}",
            "adapter": "python_docs",
            "module": module,
            "url": url,
        })
    if len(targets) != 1000:
        raise RuntimeError(f"Expected 1000 code targets, built {len(targets)}")
    return {
        "schema_version": 1,
        "scanner_id": "code",
        "collection": "code",
        "description": "One thousand bounded API/documentation targets for software knowledge.",
        "targets_expected": 1000,
        "targets": targets,
        "allowed_domains": [
            "api.github.com", "pypi.org", "api.stackexchange.com", "docs.python.org"
        ],
        "max_database_bytes": 2_147_483_648,
        "max_response_bytes": 1_500_000,
        "max_record_bytes": 600_000,
        "host_delay_seconds": 2.0,
        "timeout_seconds": 12,
        "batch_size": 1,
        "max_batch_size": 2,
        "max_records_per_target": 5,
        "sleep_seconds": 300,
        "github_token_environment": "GITHUB_TOKEN",
        "update_strategy": "conditional_get_plus_api_updated_at_plus_content_hash",
        "policy": [
            "Use public official APIs for GitHub, PyPI, and Stack Exchange.",
            "Keep repository/package/forum metadata and bounded excerpts; do not mirror entire repositories.",
            "Honor API quotas, Retry-After/backoff instructions, ETag, and Last-Modified.",
            "Prefer official Python documentation and package metadata over anonymous snippets.",
        ],
    }


def build_general_sources() -> dict:
    targets = []
    index = 0
    for category, subjects in GENERAL_SUBJECTS.items():
        for subject in subjects:
            for aspect in GENERAL_ASPECTS:
                query = f"{subject} {aspect}"
                if category in {"health", "biology"} and index % 3 == 0:
                    adapter = "pubmed"
                elif index % 2:
                    adapter = "crossref"
                else:
                    adapter = "wikipedia"
                targets.append({
                    "target_id": f"general:{index:04d}",
                    "adapter": adapter,
                    "category": category,
                    "query": query,
                    "exclude_domains": ["code", "company", "product"],
                })
                index += 1
    if len(targets) != 1000:
        raise RuntimeError(f"Expected 1000 general targets, built {len(targets)}")
    return {
        "schema_version": 1,
        "scanner_id": "general",
        "collection": "general",
        "description": "One thousand curated general-knowledge discovery targets; no random blind crawling.",
        "targets_expected": 1000,
        "targets": targets,
        "allowed_domains": [
            "en.wikipedia.org", "api.crossref.org", "eutils.ncbi.nlm.nih.gov"
        ],
        "max_database_bytes": 2_147_483_648,
        "max_response_bytes": 2_000_000,
        "max_record_bytes": 700_000,
        "host_delay_seconds": 2.0,
        "timeout_seconds": 12,
        "batch_size": 1,
        "max_batch_size": 2,
        "max_records_per_target": 6,
        "sleep_seconds": 420,
        "update_strategy": "conditional_get_plus_source_timestamp_plus_content_hash",
        "policy": [
            "Use curated encyclopedic and scholarly sources instead of random domains.",
            "Exclude software-code and company-product discovery from this collection.",
            "Preserve source URL, trust score, retrieval time, and version for every record.",
            "Store bounded excerpts and metadata, not full copyrighted site mirrors.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        DATA_DIR / "Product_scan_sources.json": build_product_sources(),
        DATA_DIR / "Code_scan_sources.json": build_code_sources(),
        DATA_DIR / "General_scan_sources.json": build_general_sources(),
    }
    for path, value in outputs.items():
        write_json(path, value, args.force)
        print(f"{path.name}: {len(value['targets'])} targets")


if __name__ == "__main__":
    main()
