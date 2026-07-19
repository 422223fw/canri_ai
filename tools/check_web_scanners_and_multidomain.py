"""Offline checks for Canri multi-domain routing and bounded web scanners."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANRI_ROOT = PROJECT_ROOT / "main_ai_canri"
DATA_DIR = CANRI_ROOT / "data"
RUNTIME_DIR = PROJECT_ROOT / "tmp" / "scanner_checks"

os.environ["CANRI_WEB_SCANNERS_BACKGROUND"] = "0"
sys.path.insert(0, str(CANRI_ROOT))

from Code_brain import CodeBrain  # noqa: E402
from Collaboration_brain import CollaborationBrain  # noqa: E402
from Creative_brain import CreativeBrain  # noqa: E402
from Manager_brain import ManagerBrain  # noqa: E402
from Understanding_brain import UnderstandingBrain  # noqa: E402
from Web_scanner_core import IndexedJsonlStore, SafeHttpClient  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(name: str) -> dict:
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        value = json.load(file)
    check(isinstance(value, dict), f"{name} must contain a JSON object")
    return value


def test_source_catalogs() -> None:
    product = load_json("Product_scan_sources.json")
    code = load_json("Code_scan_sources.json")
    general = load_json("General_scan_sources.json")

    check(len(product.get("targets", [])) == 100, "Product scanner must start with 100 products")
    check(len(code.get("targets", [])) >= 1000, "Code scanner needs at least 1000 curated targets")
    check(len(general.get("targets", [])) >= 1000, "General scanner needs at least 1000 curated targets")
    check(code.get("max_database_bytes") == 2 * 1024**3, "Code scanner quota must be 2 GiB")
    check(general.get("max_database_bytes") == 2 * 1024**3, "General scanner quota must be 2 GiB")

    allowed_product_hosts = set(product.get("allowed_domains", []))
    for target in product["targets"]:
        parsed = urlparse(str(target.get("official_url", "")))
        check(parsed.scheme == "https", "Product source URLs must use HTTPS")
        check(
            parsed.hostname in allowed_product_hosts,
            f"Product source is outside the official allowlist: {parsed.hostname}",
        )

    code_adapters = {item.get("adapter") for item in code["targets"]}
    check(
        {"github_repositories", "stack_overflow", "pypi_project", "python_docs"}
        .issubset(code_adapters),
        "Code catalog is missing a required source adapter",
    )
    general_adapters = {item.get("adapter") for item in general["targets"]}
    check(
        {"wikipedia", "crossref", "pubmed"}.issubset(general_adapters),
        "General catalog is missing a required source adapter",
    )


def test_safe_url_policy() -> None:
    client = SafeHttpClient(["example.com"], host_delay_seconds=0.2)
    check(client.is_allowed_url("https://example.com/docs"), "Allowed HTTPS URL was rejected")
    check(not client.is_allowed_url("http://example.com/docs"), "HTTP URL must be rejected")
    check(not client.is_allowed_url("https://localhost/test"), "localhost must be rejected")
    check(not client.is_allowed_url("https://127.0.0.1/test"), "loopback IP must be rejected")
    check(not client.is_allowed_url("https://evil.example.net/test"), "Unlisted domain must be rejected")
    check(not client.is_allowed_url("https://user:pass@example.com/test"), "Credentialed URL must be rejected")


def test_indexed_jsonl_store() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    suffix = str(os.getpid())
    store = IndexedJsonlStore(
        "code",
        RUNTIME_DIR / f"database_{suffix}.jsonl",
        RUNTIME_DIR / f"index_{suffix}.sqlite3",
        max_database_bytes=2_000_000,
    )
    base = {
        "record_id": "code_test_record",
        "title": "Python Arduino gravity sensor",
        "summary": "A calibrated hardware measurement example.",
        "text": "Python reads an Arduino gravity sensor and validates SI units.",
        "url": "https://example.com/gravity",
        "source_id": "offline_test",
        "source_type": "official_documentation",
        "trust_score": 90,
    }
    first = store.upsert(base)
    second = store.upsert(base)
    changed = dict(base, text=base["text"] + " Updated calibration guidance.")
    third = store.upsert(changed)
    matches = store.search("Arduino gravity calibration", limit=3)

    check(first.get("status") == "inserted", "First scanner record was not inserted")
    check(second.get("status") == "unchanged", "Unchanged scanner record was duplicated")
    check(third.get("status") == "updated" and third.get("version") == 2, "Changed record was not versioned")
    check(matches and matches[0].get("record_id") == "code_test_record", "Indexed retrieval missed the record")
    check("Updated calibration" in store.get("code_test_record").get("text", ""), "Latest record version was not returned")


def multi_domain_prompt() -> str:
    return (
        "Build a professional multi-file Python system for an Arduino sensor that "
        "measures gravity, explains the physics, calibrates hardware readings, "
        "collects data asynchronously, and includes behavior tests."
    )


def test_multi_domain_routing_and_collaboration() -> None:
    prompt = multi_domain_prompt()
    understanding = UnderstandingBrain().process({"original_text": prompt})
    central = understanding.get("central_domains", [])
    check("code" in central, "Understanding missed the code domain")
    check("science" in central, "Understanding missed the science domain")
    check("technology" in central, "Understanding missed the technology domain")

    manager = ManagerBrain()
    routing = manager.routing_decision(understanding, {})
    check(routing.get("multi_domain") is True, "Manager did not mark the request as multi-domain")
    check(
        {"code", "science", "technology"}.issubset(set(routing.get("domains", []))),
        "Manager dropped a central domain",
    )
    check("Science_brain" in routing.get("supporting_brains", []), "Science brain was not routed")
    check("Technology_brain" in routing.get("supporting_brains", []), "Technology brain was not routed")
    check("Creative_brain" in routing.get("supporting_brains", []), "Creative brain was not routed")

    fake_results = {
        name: {"brain": name, "answer": f"{name} contribution"}
        for name in [
            "Code_brain", "Science_brain", "Technology_brain",
            "Planner_brain", "Reasoning_brain",
        ]
    }
    collaboration = CollaborationBrain().process({
        "original_text": prompt,
        "understanding": understanding,
        "routing_decision": routing,
        "results": fake_results,
        "collaboration_round": "planning",
    })
    check(len(collaboration.get("domains", [])) >= 3, "Collaboration did not retain all domains")
    check(len(collaboration.get("participants", [])) >= 3, "Too few specialists joined collaboration")
    check(collaboration.get("consultation_requests"), "No peer consultation was created")


def test_hardware_science_project() -> None:
    prompt = multi_domain_prompt()
    understanding = {
        "intent": "code_generation",
        "main_topic": "code",
        "central_domains": ["code", "science", "technology"],
        "original_text": prompt,
    }
    result = CodeBrain().process({
        "original_text": prompt,
        "understanding": understanding,
        "routing_decision": {
            "domains": ["code", "science", "technology"],
            "multi_domain": True,
        },
    })
    files = result.get("project_files", {})
    required = {
        "pyproject.toml",
        "app/hardware.py",
        "app/science.py",
        "app/controller.py",
        "app/main.py",
        "tests/test_hardware_science.py",
    }
    check(required.issubset(files), "Hardware/science project is missing required files")
    check(result.get("project_review", {}).get("ready") is True, "Generated hardware project failed self-review")
    check("pyserial>=3.5" in files["pyproject.toml"], "Hardware dependency is missing")
    for path, content in files.items():
        if path.endswith(".py"):
            ast.parse(content, filename=path)

    root = RUNTIME_DIR / f"hardware_project_{os.getpid()}"
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    scenario = (
        "import asyncio\n"
        "from app.controller import collect_measurements\n"
        "from app.hardware import SimulatedSensor\n"
        "from app.science import summarize_measurements\n"
        "readings=asyncio.run(collect_measurements(SimulatedSensor([9.8,9.9]),2,0))\n"
        "summary=summarize_measurements(readings)\n"
        "assert summary.count == 2 and summary.minimum == 9.8\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPYCACHEPREFIX"] = str(RUNTIME_DIR / "pycache")
    completed = subprocess.run(
        [sys.executable, "-c", scenario],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    check(completed.returncode == 0, f"Generated hardware project failed: {completed.stderr}")


def test_controlled_cross_domain_follow_ups() -> None:
    creative = CreativeBrain()
    tasks = creative.build_follow_up_tasks(
        multi_domain_prompt(),
        ["code", "science", "technology"],
        {"title": "Calibrated sensor architecture"},
        {
            "Python docs": {"source_group": "scanner_code"},
            "Physics source": {"source_group": "scanner_general"},
        },
    )
    check(len(tasks) >= 2, "Creative brain did not produce useful cross-domain follow-ups")
    check(
        {"Code_brain", "Science_brain", "Technology_brain"}.issubset(
            set(tasks[0].get("owner_brains", []))
        ),
        "Cross-domain follow-up dropped a specialist",
    )
    check(
        all(task.get("acceptance_checks") for task in tasks),
        "Follow-up tasks must be verifiable rather than vague ideas",
    )


def main() -> None:
    tests = [
        test_source_catalogs,
        test_safe_url_policy,
        test_indexed_jsonl_store,
        test_multi_domain_routing_and_collaboration,
        test_hardware_science_project,
        test_controlled_cross_domain_follow_ups,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} offline scanner and multi-domain checks")


if __name__ == "__main__":
    main()
