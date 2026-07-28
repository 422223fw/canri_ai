"""Shared execution boundary for every Canri brain.

The runtime keeps domain brains simple while enforcing the operational rules
needed by a stable application: bounded execution, normalized results, safe
errors, per-request telemetry, registry validation, and persistent health
metrics. It deliberately stores diagnostics separately from user-facing brain
results so internal failures cannot leak into an answer.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional
from uuid import uuid4

from Brain_storage import atomic_write_json, load_json_resilient


DATA_DIR = Path(__file__).parent / "data"
DEFAULT_STATISTICS_FILE = DATA_DIR / "Brain_runtime_statistics.json"


def _configured_watchdog_seconds() -> Optional[float]:
    """Return an optional emergency watchdog; normal thinking is unlimited."""

    raw_value = os.environ.get("CANRI_BRAIN_WATCHDOG_SECONDS", "").strip()
    if not raw_value:
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


EMERGENCY_BRAIN_WATCHDOG_SECONDS = _configured_watchdog_seconds()


DEFAULT_PROFILES = {
    "default": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Spelling_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Understanding_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Memory_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Manager_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Security_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Planner_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Reasoning_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Code_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Creative_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Image_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Movie_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Project_context_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Local_LLM_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Agent_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Vision_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Voice_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": False},
    "Fact_Check_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Quality_Control_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
    "Response_brain": {"timeout_seconds": EMERGENCY_BRAIN_WATCHDOG_SECONDS, "critical": True},
}


@dataclass(frozen=True)
class BrainExecution:
    """A brain result plus diagnostics that stay outside the result payload."""

    result: Dict[str, Any]
    telemetry: Dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.telemetry.get("status") == "success"


class BrainRuntime:
    CONTRACT_VERSION = "1.0"
    MAX_EVENT_HISTORY = 2000

    def __init__(
        self,
        statistics_path: Optional[Path] = None,
        profiles: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ):
        self.statistics_path = Path(statistics_path or DEFAULT_STATISTICS_FILE)
        self.profiles = {
            name: dict(profile)
            for name, profile in (profiles or DEFAULT_PROFILES).items()
        }
        self._lock = threading.RLock()
        self._active_calls: Dict[str, Dict[str, Any]] = {}
        self._events = []
        self._dirty = False
        self._statistics = self._load_statistics()

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_statistics(self) -> Dict[str, Any]:
        default = {
            "schema_version": 1,
            "runtime_contract": self.CONTRACT_VERSION,
            "updated_utc": None,
            "totals": {
                "calls": 0,
                "success": 0,
                "errors": 0,
                "timeouts": 0,
                "invalid_results": 0,
                "busy": 0,
            },
            "brains": {},
        }
        loaded = load_json_resilient(self.statistics_path, default=default)
        if not isinstance(loaded, dict):
            return default
        loaded.setdefault("schema_version", 1)
        loaded["runtime_contract"] = self.CONTRACT_VERSION
        loaded.setdefault("totals", default["totals"])
        loaded.setdefault("brains", {})
        return loaded

    def profile_for(self, brain_name: str) -> Dict[str, Any]:
        profile = dict(self.profiles.get("default", {}))
        profile.update(self.profiles.get(str(brain_name), {}))
        return profile

    def timeout_for(
        self,
        brain_name: str,
        remaining_seconds: Optional[float] = None,
    ) -> Optional[float]:
        configured_value = self.profile_for(brain_name).get(
            "timeout_seconds",
            EMERGENCY_BRAIN_WATCHDOG_SECONDS,
        )
        if configured_value is None:
            configured = EMERGENCY_BRAIN_WATCHDOG_SECONDS
        else:
            configured = max(float(configured_value), 0.05)
            if EMERGENCY_BRAIN_WATCHDOG_SECONDS is not None:
                configured = min(configured, EMERGENCY_BRAIN_WATCHDOG_SECONDS)
        if remaining_seconds is None:
            return configured
        if configured is None:
            return max(float(remaining_seconds), 0.05)
        return min(configured, max(float(remaining_seconds), 0.05))

    def validate_registration(self, brain_name: str, brain_object: Any) -> Dict[str, Any]:
        process = getattr(brain_object, "process", None)
        result = {
            "brain": str(brain_name),
            "registered": brain_object is not None,
            "has_process": callable(process),
            "contract_version": self.CONTRACT_VERSION,
            "profile": self.profile_for(brain_name),
            "valid": False,
            "reason": None,
        }
        if brain_object is None:
            result["reason"] = "brain_object_missing"
            return result
        if not callable(process):
            result["reason"] = "process_method_missing"
            return result
        try:
            parameters = list(inspect.signature(process).parameters.values())
        except (TypeError, ValueError):
            parameters = []
        accepts_input = any(
            parameter.kind in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            }
            for parameter in parameters
        )
        result["accepts_input"] = accepts_input
        result["valid"] = accepts_input
        if not accepts_input:
            result["reason"] = "process_does_not_accept_input"
        return result

    def _request_id(self, payload: Any, request_id: Optional[str]) -> str:
        if request_id:
            return str(request_id)
        if isinstance(payload, Mapping):
            for key in ("_request_id", "request_id"):
                value = payload.get(key)
                if value:
                    return str(value)
        return "request_" + uuid4().hex

    def _prepare_payload(
        self,
        payload: Any,
        request_id: str,
        brain_name: str,
        phase: str,
        deadline: Optional[float],
        cancel_event: threading.Event,
    ) -> Any:
        if not isinstance(payload, dict):
            return payload
        prepared = dict(payload)
        prepared.setdefault("_request_id", request_id)
        scanner_evidence = []
        scanner_view = prepared.get("scanner_knowledge", {})
        if isinstance(scanner_view, Mapping):
            scanner_evidence.extend(scanner_view.get("matches", []))
        data_context = prepared.get("data_context", {})
        if isinstance(data_context, Mapping):
            scanner_evidence.extend(data_context.get("scanner_matches", []))

        compact_evidence = []
        seen_evidence = set()
        for item in scanner_evidence:
            if not isinstance(item, Mapping):
                continue
            identity = (
                item.get("article_id")
                or item.get("record_id")
                or item.get("url")
                or item.get("title")
                or str(item)[:160]
            )
            if identity in seen_evidence:
                continue
            seen_evidence.add(identity)
            compact_evidence.append(dict(item))
            if len(compact_evidence) >= 12:
                break

        prepared["_knowledge_context"] = {
            "available": bool(compact_evidence),
            "indexed_evidence": compact_evidence,
            "usage_contract": [
                "Consider every relevant excerpt before producing the domain result.",
                "Ignore excerpts that do not support the current request.",
                "Do not turn unverified scanner text into a certain factual claim.",
                "Preserve source and trust metadata for fact checking.",
            ],
            "retrieval_mode": "lazy_indexed_relevant_excerpts",
        }
        prepared["_runtime_control"] = {
            "contract_version": self.CONTRACT_VERSION,
            "brain": brain_name,
            "phase": phase,
            "deadline_monotonic": deadline,
            "cancel_event": cancel_event,
        }
        return prepared

    @staticmethod
    def cancellation_requested(payload: Any) -> bool:
        if not isinstance(payload, Mapping):
            return False
        control = payload.get("_runtime_control", {})
        if not isinstance(control, Mapping):
            return False
        event = control.get("cancel_event")
        if isinstance(event, threading.Event) and event.is_set():
            return True
        deadline = control.get("deadline_monotonic")
        return isinstance(deadline, (int, float)) and time.perf_counter() >= deadline

    @staticmethod
    def _safe_failure(
        brain_name: str,
        code: str,
        phase: str,
        message: str,
        *,
        timeout: bool = False,
        skipped: bool = False,
    ) -> Dict[str, Any]:
        return {
            "brain": brain_name,
            "error": code,
            "error_code": code,
            "user_safe_error": message,
            "phase": phase,
            "timeout": bool(timeout),
            "skipped": bool(skipped),
            "recoverable": True,
            "confidence": 0,
        }

    def _normalize_result(
        self,
        brain_name: str,
        raw_result: Any,
        phase: str,
    ) -> tuple[Dict[str, Any], str, list[str]]:
        warnings = []
        if raw_result is None:
            return (
                self._safe_failure(
                    brain_name,
                    "empty_brain_result",
                    phase,
                    "The selected brain returned no result.",
                ),
                "invalid_result",
                ["result_was_none"],
            )
        if isinstance(raw_result, Mapping):
            result = dict(raw_result)
            if not result:
                return (
                    self._safe_failure(
                        brain_name,
                        "empty_brain_result",
                        phase,
                        "The selected brain returned an empty result.",
                    ),
                    "invalid_result",
                    ["result_mapping_was_empty"],
                )
        elif isinstance(raw_result, str) and raw_result.strip():
            result = {
                "brain": brain_name,
                "answer": raw_result.strip(),
                "display_text": raw_result.strip(),
                "normalized_result": True,
            }
            warnings.append("string_result_normalized")
        else:
            result = {
                "brain": brain_name,
                "data": raw_result,
                "normalized_result": True,
            }
            warnings.append("non_mapping_result_normalized")

        declared_brain = result.get("brain")
        if declared_brain and str(declared_brain) != brain_name:
            warnings.append("declared_brain_does_not_match_registration")
            result.setdefault("reported_brain", declared_brain)
        result["brain"] = brain_name

        if result.get("timeout"):
            status = "timeout"
        elif result.get("skipped"):
            status = "skipped"
        elif result.get("error"):
            status = "reported_error"
        else:
            status = "success"
        return result, status, warnings

    @staticmethod
    def _exception_fingerprint(error: BaseException) -> str:
        value = f"{type(error).__name__}:{error}".encode("utf-8", errors="replace")
        return hashlib.sha256(value).hexdigest()[:16]

    def invoke(
        self,
        brain_name: str,
        processor: Any,
        payload: Any,
        *,
        phase: str = "single",
        timeout_seconds: Optional[float] = None,
        request_id: Optional[str] = None,
        attempt: int = 1,
    ) -> BrainExecution:
        brain_name = str(brain_name or "Unknown_brain")
        request_id = self._request_id(payload, request_id)
        profile = self.profile_for(brain_name)
        timeout_seconds = self.timeout_for(
            brain_name,
            timeout_seconds if timeout_seconds is not None else None,
        )
        call_started = time.perf_counter()
        started_utc = self.utc_now()
        deadline = (
            call_started + timeout_seconds
            if timeout_seconds is not None
            else None
        )
        callable_process: Optional[Callable[[Any], Any]]
        if callable(processor) and not hasattr(processor, "process"):
            callable_process = processor
        else:
            callable_process = getattr(processor, "process", None)

        if not callable(callable_process):
            result = self._safe_failure(
                brain_name,
                "brain_process_unavailable",
                phase,
                "The selected capability is not available.",
                skipped=True,
            )
            telemetry = self._telemetry(
                brain_name,
                request_id,
                phase,
                "invalid_registration",
                started_utc,
                call_started,
                timeout_seconds,
                0.0,
                attempt,
                ["process_method_missing"],
                profile,
            )
            self._record(telemetry)
            return BrainExecution(result, telemetry)

        queue_started = time.perf_counter()
        while True:
            with self._lock:
                active = self._active_calls.get(brain_name)
                if not active:
                    break
                active_done = active["done"]
            if deadline is None:
                active_done.wait(0.1)
                continue
            remaining = deadline - time.perf_counter()
            if remaining <= 0 or not active_done.wait(min(remaining, 0.1)):
                if remaining > 0:
                    continue
                result = self._safe_failure(
                    brain_name,
                    "brain_busy_timeout",
                    phase,
                    "The selected brain is still handling another request.",
                    timeout=True,
                    skipped=True,
                )
                telemetry = self._telemetry(
                    brain_name,
                    request_id,
                    phase,
                    "busy",
                    started_utc,
                    call_started,
                    timeout_seconds,
                    time.perf_counter() - queue_started,
                    attempt,
                    ["serialized_brain_queue_timeout"],
                    profile,
                )
                self._record(telemetry)
                return BrainExecution(result, telemetry)

        queue_seconds = time.perf_counter() - queue_started
        remaining = (
            deadline - time.perf_counter()
            if deadline is not None
            else None
        )
        if remaining is not None and remaining <= 0:
            result = self._safe_failure(
                brain_name,
                "brain_queue_timeout",
                phase,
                "The request time budget was exhausted before this brain started.",
                timeout=True,
                skipped=True,
            )
            telemetry = self._telemetry(
                brain_name,
                request_id,
                phase,
                "timeout",
                started_utc,
                call_started,
                timeout_seconds,
                queue_seconds,
                attempt,
                ["request_budget_exhausted_in_queue"],
                profile,
            )
            self._record(telemetry)
            return BrainExecution(result, telemetry)

        done = threading.Event()
        cancel_event = threading.Event()
        token = uuid4().hex
        box: Dict[str, Any] = {}
        prepared_payload = self._prepare_payload(
            payload,
            request_id,
            brain_name,
            phase,
            deadline,
            cancel_event,
        )

        def run_processor() -> None:
            try:
                box["result"] = callable_process(prepared_payload)
            except Exception as error:  # The runtime is the exception boundary.
                box["exception"] = error
            finally:
                done.set()
                with self._lock:
                    current = self._active_calls.get(brain_name)
                    if current and current.get("token") == token:
                        self._active_calls.pop(brain_name, None)

        with self._lock:
            self._active_calls[brain_name] = {
                "token": token,
                "request_id": request_id,
                "done": done,
                "started_utc": started_utc,
            }

        worker = threading.Thread(
            target=run_processor,
            name=f"canri-{brain_name}-{token[:8]}",
            daemon=True,
        )
        worker.start()
        completed = done.wait(
            None
            if deadline is None
            else max(deadline - time.perf_counter(), 0.0)
        )

        if not completed:
            cancel_event.set()
            result = self._safe_failure(
                brain_name,
                "brain_timeout",
                phase,
                "The selected brain exceeded its execution time budget.",
                timeout=True,
                skipped=True,
            )
            telemetry = self._telemetry(
                brain_name,
                request_id,
                phase,
                "timeout",
                started_utc,
                call_started,
                timeout_seconds,
                queue_seconds,
                attempt,
                ["cooperative_cancellation_requested"],
                profile,
            )
            self._record(telemetry)
            return BrainExecution(result, telemetry)

        if "exception" in box:
            error = box["exception"]
            result = self._safe_failure(
                brain_name,
                "brain_execution_failed",
                phase,
                "The selected brain could not complete this part of the request.",
            )
            telemetry = self._telemetry(
                brain_name,
                request_id,
                phase,
                "error",
                started_utc,
                call_started,
                timeout_seconds,
                queue_seconds,
                attempt,
                ["exception_captured"],
                profile,
                exception_type=type(error).__name__,
                exception_fingerprint=self._exception_fingerprint(error),
            )
            self._record(telemetry)
            return BrainExecution(result, telemetry)

        result, status, warnings = self._normalize_result(
            brain_name,
            box.get("result"),
            phase,
        )
        telemetry = self._telemetry(
            brain_name,
            request_id,
            phase,
            status,
            started_utc,
            call_started,
            timeout_seconds,
            queue_seconds,
            attempt,
            warnings,
            profile,
        )
        self._record(telemetry)
        return BrainExecution(result, telemetry)

    def _telemetry(
        self,
        brain_name: str,
        request_id: str,
        phase: str,
        status: str,
        started_utc: str,
        call_started: float,
        timeout_seconds: Optional[float],
        queue_seconds: float,
        attempt: int,
        warnings: list[str],
        profile: Mapping[str, Any],
        **extra: Any,
    ) -> Dict[str, Any]:
        elapsed = max(time.perf_counter() - call_started, 0.0)
        telemetry = {
            "contract_version": self.CONTRACT_VERSION,
            "request_id": request_id,
            "brain": brain_name,
            "phase": str(phase),
            "status": status,
            "started_utc": started_utc,
            "finished_utc": self.utc_now(),
            "elapsed_seconds": round(elapsed, 4),
            "queue_seconds": round(max(queue_seconds, 0.0), 4),
            "timeout_seconds": (
                round(timeout_seconds, 4)
                if timeout_seconds is not None
                else None
            ),
            "slow": (
                elapsed > timeout_seconds * 0.8
                if timeout_seconds is not None
                else False
            ),
            "critical": bool(profile.get("critical")),
            "attempt": max(int(attempt), 1),
            "warnings": list(warnings),
        }
        telemetry.update(extra)
        return telemetry

    def _record(self, telemetry: Mapping[str, Any]) -> None:
        event = dict(telemetry)
        status = str(event.get("status", "error"))
        brain_name = str(event.get("brain", "Unknown_brain"))
        elapsed = float(event.get("elapsed_seconds", 0.0) or 0.0)
        with self._lock:
            self._events.append(event)
            self._events = self._events[-self.MAX_EVENT_HISTORY :]
            totals = self._statistics.setdefault("totals", {})
            totals["calls"] = int(totals.get("calls", 0)) + 1
            status_bucket = {
                "success": "success",
                "timeout": "timeouts",
                "invalid_result": "invalid_results",
                "invalid_registration": "invalid_results",
                "busy": "busy",
            }.get(status, "errors")
            totals[status_bucket] = int(totals.get(status_bucket, 0)) + 1

            brains = self._statistics.setdefault("brains", {})
            brain_stats = brains.setdefault(brain_name, {})
            previous_calls = int(brain_stats.get("calls", 0))
            total_seconds = float(brain_stats.get("total_seconds", 0.0)) + elapsed
            brain_stats.update({
                "calls": previous_calls + 1,
                "success": int(brain_stats.get("success", 0)) + (status == "success"),
                "errors": int(brain_stats.get("errors", 0)) + (
                    status not in {"success", "timeout", "busy", "invalid_result", "invalid_registration", "skipped"}
                ),
                "timeouts": int(brain_stats.get("timeouts", 0)) + (status == "timeout"),
                "invalid_results": int(brain_stats.get("invalid_results", 0)) + (
                    status in {"invalid_result", "invalid_registration"}
                ),
                "busy": int(brain_stats.get("busy", 0)) + (status == "busy"),
                "slow_calls": int(brain_stats.get("slow_calls", 0)) + bool(event.get("slow")),
                "total_seconds": round(total_seconds, 4),
                "average_seconds": round(total_seconds / (previous_calls + 1), 4),
                "maximum_seconds": round(max(float(brain_stats.get("maximum_seconds", 0.0)), elapsed), 4),
                "last_status": status,
                "last_finished_utc": event.get("finished_utc"),
            })
            self._statistics["updated_utc"] = event.get("finished_utc")
            self._dirty = True

    def events_for_request(self, request_id: str, limit: int = 200) -> list[Dict[str, Any]]:
        with self._lock:
            matches = [
                dict(event)
                for event in self._events
                if event.get("request_id") == request_id
            ]
        return matches[-max(int(limit), 1) :]

    @staticmethod
    def summarize_events(events: list[Mapping[str, Any]]) -> Dict[str, Any]:
        statuses: Dict[str, int] = {}
        for event in events:
            status = str(event.get("status", "unknown"))
            statuses[status] = statuses.get(status, 0) + 1
        elapsed = sum(float(event.get("elapsed_seconds", 0.0) or 0.0) for event in events)
        return {
            "calls": len(events),
            "statuses": statuses,
            "brain_time_seconds": round(elapsed, 4),
            "failed_brains": [
                event.get("brain")
                for event in events
                if event.get("status") not in {"success", "skipped"}
            ],
            "slow_brains": [
                event.get("brain")
                for event in events
                if event.get("slow")
            ],
        }

    def health_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._statistics, ensure_ascii=True))

    def flush_statistics(self) -> bool:
        with self._lock:
            if not self._dirty:
                return False
            payload = json.loads(json.dumps(self._statistics, ensure_ascii=True))
            self._dirty = False
        if atomic_write_json(
            self.statistics_path,
            payload,
            sort_keys=True,
        ):
            return True
        with self._lock:
            self._dirty = True
        return False


brain_runtime = BrainRuntime()


def invoke_brain_safely(
    brain_name: str,
    brain_or_callable: Any,
    payload: Any,
    *,
    phase: str = "nested",
    timeout_seconds: Optional[float] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience API for specialist-to-specialist fallback calls."""

    execution = brain_runtime.invoke(
        brain_name,
        brain_or_callable,
        payload,
        phase=phase,
        timeout_seconds=timeout_seconds,
        request_id=request_id,
    )
    return execution.result
