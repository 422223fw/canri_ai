"""Focused release checks for the Canri 1.0 shared brain runtime."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "main_ai_canri"
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from Brain_runtime import BrainRuntime  # noqa: E402
from Brain_storage import atomic_write_json, load_json_resilient  # noqa: E402
from Manager_brain import ManagerBrain  # noqa: E402


class RuntimeChecks:
    def __init__(self):
        self.results = []

    def check(self, name, condition, detail=None):
        passed = bool(condition)
        self.results.append({"name": name, "passed": passed, "detail": detail})
        print(("PASS " if passed else "FAIL ") + name)

    def finish(self):
        failed = [item for item in self.results if not item["passed"]]
        summary = {
            "total": len(self.results),
            "passed": len(self.results) - len(failed),
            "failed": len(failed),
            "failures": failed,
        }
        print(json.dumps(summary, indent=2))
        if failed:
            raise SystemExit(1)


class GoodBrain:
    def process(self, data):
        control = data.get("_runtime_control", {}) if isinstance(data, dict) else {}
        return {
            "brain": "Good_brain",
            "answer": "ready",
            "received_request_id": data.get("_request_id"),
            "received_runtime_contract": control.get("contract_version"),
        }


class SlowBrain:
    def process(self, data):
        time.sleep(0.15)
        return {"brain": "Slow_brain", "answer": "late"}


class BrokenBrain:
    def process(self, data):
        raise RuntimeError("private diagnostic must not reach the user")


class EmptyBrain:
    def process(self, data):
        return None


class TextBrain:
    def process(self, data):
        return "plain result"


def run_runtime_checks(checks, runtime):
    valid = runtime.validate_registration("Good_brain", GoodBrain())
    invalid = runtime.validate_registration("Missing_brain", object())
    checks.check("runtime_valid_registration", valid["valid"] is True, valid)
    checks.check("runtime_invalid_registration", invalid["valid"] is False, invalid)

    good = runtime.invoke(
        "Good_brain",
        GoodBrain(),
        {"_request_id": "runtime_request"},
        phase="release_test",
        timeout_seconds=1.0,
    )
    checks.check("runtime_success_status", good.ok, good.telemetry)
    checks.check("runtime_result_contract", good.result.get("brain") == "Good_brain", good.result)
    checks.check(
        "runtime_request_id_propagation",
        good.result.get("received_request_id") == "runtime_request",
        good.result,
    )
    checks.check(
        "runtime_control_propagation",
        good.result.get("received_runtime_contract") == "1.0",
        good.result,
    )

    text = runtime.invoke("Text_brain", TextBrain(), {}, timeout_seconds=1.0)
    checks.check(
        "runtime_text_normalization",
        text.result.get("display_text") == "plain result" and text.result.get("normalized_result") is True,
        text.result,
    )

    empty = runtime.invoke("Empty_brain", EmptyBrain(), {}, timeout_seconds=1.0)
    checks.check(
        "runtime_empty_result_rejected",
        empty.telemetry.get("status") == "invalid_result" and empty.result.get("error") == "empty_brain_result",
        empty.result,
    )

    broken = runtime.invoke("Broken_brain", BrokenBrain(), {}, timeout_seconds=1.0)
    serialized_broken = json.dumps({"result": broken.result, "telemetry": broken.telemetry})
    checks.check("runtime_exception_captured", broken.telemetry.get("status") == "error", broken.telemetry)
    checks.check(
        "runtime_exception_details_are_private",
        "private diagnostic" not in serialized_broken,
        serialized_broken,
    )
    checks.check(
        "runtime_exception_fingerprint_available",
        bool(broken.telemetry.get("exception_fingerprint")),
        broken.telemetry,
    )

    started = time.perf_counter()
    slow = runtime.invoke("Slow_brain", SlowBrain(), {}, timeout_seconds=0.03)
    wall_time = time.perf_counter() - started
    checks.check("runtime_timeout_status", slow.result.get("timeout") is True, slow.result)
    checks.check("runtime_timeout_is_bounded", wall_time < 0.12, wall_time)

    events = runtime.events_for_request("runtime_request")
    checks.check("runtime_request_event_history", len(events) == 1, events)
    summary = runtime.summarize_events(events)
    checks.check(
        "runtime_request_summary",
        summary.get("calls") == 1 and summary.get("statuses", {}).get("success") == 1,
        summary,
    )

    health = runtime.health_snapshot()
    checks.check("runtime_health_totals", health.get("totals", {}).get("calls", 0) >= 5, health.get("totals"))
    checks.check("runtime_health_per_brain", "Good_brain" in health.get("brains", {}), health.get("brains"))
    checks.check("runtime_statistics_flush", runtime.flush_statistics() is True)
    saved = json.loads(runtime.statistics_path.read_text(encoding="utf-8"))
    checks.check("runtime_statistics_valid_json", saved.get("runtime_contract") == "1.0", saved)


def run_storage_checks(checks):
    storage_dir = PROJECT_ROOT / "tmp" / "runtime_checks"
    storage_dir.mkdir(parents=True, exist_ok=True)
    atomic_path = storage_dir / "atomic_storage.json"
    transient_path = storage_dir / "transient_storage.json"

    checks.check("storage_initial_atomic_write", atomic_write_json(atomic_path, {"version": 0}))
    observed = []

    def writer():
        for version in range(1, 41):
            atomic_write_json(atomic_path, {"version": version, "items": list(range(version % 7))})

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    while thread.is_alive():
        value = load_json_resilient(atomic_path, default={"invalid": True}, retries=2, delay=0.001)
        observed.append(value)
    thread.join(timeout=1.0)
    observed.append(load_json_resilient(atomic_path, default={"invalid": True}))
    checks.check(
        "storage_concurrent_reads_remain_valid",
        bool(observed) and all(isinstance(item, dict) and "version" in item for item in observed),
        observed[-3:],
    )

    transient_path.write_text("{", encoding="utf-8")

    def repair_transient_file():
        time.sleep(0.03)
        atomic_write_json(transient_path, {"recovered": True})

    repair = threading.Thread(target=repair_transient_file, daemon=True)
    repair.start()
    recovered = load_json_resilient(transient_path, default={}, retries=5, delay=0.02)
    repair.join(timeout=1.0)
    checks.check("storage_transient_invalid_json_recovers", recovered.get("recovered") is True, recovered)


def run_manager_checks(checks):
    manager = ManagerBrain()
    manager.register_brain("Good_brain", GoodBrain())
    manager._request_started = time.perf_counter()
    manager._request_deadline = manager._request_started + 2.0
    manager._request_id = "manager_runtime_request"
    data = {
        "_request_id": manager._request_id,
        "original_text": "test",
        "dictionary": {"available": False},
        "data_context": {"available": False},
        "full_data_context": {"available": False},
        "knowledge": {"available": False, "matches": []},
        "shared_context": {"available": False},
    }
    report = {"original_text": "test", "main_topic": "general", "intent": "request"}
    result = manager.execute(["Good_brain"], data, report, {}, "runtime_release_test")
    brain_result = result.get("Good_brain", {})
    checks.check("manager_uses_runtime_contract", brain_result.get("performance", {}).get("runtime_contract") == "1.0", brain_result)
    checks.check("manager_registry_health", manager.registry_health.get("Good_brain", {}).get("valid") is True, manager.registry_health)


def run_application_registry_checks(checks):
    import main as canri_main

    canri_main.register_all_brains()
    expected = {
        "Spelling_brain", "Understanding_brain", "Memory_brain", "Research_brain",
        "Reasoning_brain", "Response_brain", "Creative_brain", "Code_brain",
        "Math_brain", "Science_brain", "Language_brain", "History_brain",
        "Geography_brain", "Technology_brain", "Game_brain", "Story_brain",
        "Character_brain", "World_brain", "Image_brain", "Vision_brain",
        "Voice_brain", "Learning_brain", "Fact_Check_brain",
        "Quality_Control_brain", "Collaboration_brain", "Planner_brain",
        "Emotion_brain", "Security_brain",
    }
    registered = set(canri_main.manager_brain.brains)
    missing = sorted(expected - registered)
    checks.check("application_registers_all_brains", not missing, missing)
    checks.check("application_registers_vision", "Vision_brain" in registered, sorted(registered))
    checks.check("application_registers_voice", "Voice_brain" in registered, sorted(registered))
    invalid = {
        name: item
        for name, item in canri_main.manager_brain.registry_health.items()
        if not item.get("valid")
    }
    checks.check("application_all_registrations_valid", not invalid, invalid)


def main():
    checks = RuntimeChecks()
    statistics_path = PROJECT_ROOT / "tmp" / "runtime_checks" / "statistics.json"
    statistics_path.parent.mkdir(parents=True, exist_ok=True)
    if statistics_path.exists():
        statistics_path.unlink()
    runtime = BrainRuntime(statistics_path=statistics_path)
    run_runtime_checks(checks, runtime)
    run_storage_checks(checks)
    run_manager_checks(checks)
    run_application_registry_checks(checks)
    checks.finish()


if __name__ == "__main__":
    main()
