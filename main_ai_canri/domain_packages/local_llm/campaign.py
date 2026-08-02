"""Resumable long-running training campaign for CANRI's native v2 model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model.transformer import require_torch


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native_v2.pt"
DEFAULT_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer_v2.json"
DEFAULT_STATUS = PACKAGE_ROOT / "training_campaign_v2.json"
DEFAULT_EVENTS = PACKAGE_ROOT / "training_campaign_v2.jsonl"
DEFAULT_PROCESS_LOG = PACKAGE_ROOT / "training_campaign_v2.log"
DEFAULT_LOCK = PACKAGE_ROOT / "training_campaign_v2.lock"
DEFAULT_STOP = PACKAGE_ROOT / "training_campaign_v2.stop"
DEFAULT_STANDARD_EVALUATION = PACKAGE_ROOT / "training_status_v2.json"
DEFAULT_SEALED_EVALUATION = PACKAGE_ROOT / "sealed_evaluation_v2.json"
DEFAULT_INFERENCE = PACKAGE_ROOT / "checkpoints" / "canri_native_v2_inference.pt"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a resumable train/evaluate/export campaign."
    )
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--minimum-target-steps", type=int, default=20_000)
    parser.add_argument("--hard-limit-steps", type=int, default=40_000)
    parser.add_argument("--cycle-steps", type=int, default=250)
    parser.add_argument("--evaluation-every", type=int, default=1_000)
    parser.add_argument("--maximum-cycles", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=6e-5)
    parser.add_argument("--minimum-learning-rate", type=float, default=1e-5)
    parser.add_argument("--save-every", type=int, default=100)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--curated-repeats", type=int, default=12)
    parser.add_argument("--max-examples-per-source", type=int, default=10_000)
    parser.add_argument("--focus-until-steps", type=int, default=0)
    parser.add_argument(
        "--focus-source",
        action="append",
        default=[],
        help="Use an exact instruction source during the initial focused phase.",
    )
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--process-log", type=Path, default=DEFAULT_PROCESS_LOG)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--stop-file", type=Path, default=DEFAULT_STOP)
    parser.add_argument(
        "--standard-evaluation-output",
        type=Path,
        default=DEFAULT_STANDARD_EVALUATION,
    )
    parser.add_argument(
        "--sealed-evaluation-output",
        type=Path,
        default=DEFAULT_SEALED_EVALUATION,
    )
    parser.add_argument(
        "--inference-output",
        type=Path,
        default=DEFAULT_INFERENCE,
    )
    parser.add_argument("--skip-corpus-build", action="store_true")
    parser.add_argument("--skip-standard-evaluation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def _append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _claim_lock(path: Path) -> None:
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        existing_pid = int(existing.get("pid", 0) or 0)
        if existing_pid != os.getpid() and _pid_is_running(existing_pid):
            raise RuntimeError(
                f"A training campaign is already running with PID {existing_pid}."
            )
        path.unlink(missing_ok=True)
    _atomic_json(path, {"pid": os.getpid(), "started_utc": _utc_now()})


def _checkpoint_metadata(path: Path) -> dict:
    torch, _ = require_torch()
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        payload = torch.load(path, map_location="cpu")
    config = payload.get("config", {})
    model_state = payload.get("model_state", {})
    storages: set[int] = set()
    parameters = 0
    for value in model_state.values():
        if not hasattr(value, "numel"):
            continue
        storage = int(value.untyped_storage().data_ptr())
        if storage in storages:
            continue
        storages.add(storage)
        parameters += int(value.numel())
    return {
        "global_steps": int(payload.get("step", 0)),
        "last_loss": payload.get("last_loss"),
        "parameters": parameters,
        "config": config if isinstance(config, dict) else {},
        "checkpoint_bytes": path.stat().st_size,
    }


def _run_command(
    command: list[str],
    *,
    process_log: Path,
    events: Path,
    event_name: str,
    dry_run: bool,
) -> subprocess.CompletedProcess[str] | None:
    started = time.monotonic()
    _append_jsonl(
        events,
        {
            "utc": _utc_now(),
            "event": f"{event_name}_started",
            "command": command,
        },
    )
    if dry_run:
        return None
    environment = os.environ.copy()
    environment.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        command,
        cwd=PACKAGE_ROOT.parents[2],
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        shell=False,
    )
    process_log.parent.mkdir(parents=True, exist_ok=True)
    with process_log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"\n[{_utc_now()}] {event_name}: {' '.join(command)}\n")
        if completed.stdout:
            handle.write(completed.stdout)
        if completed.stderr:
            handle.write("\n[stderr]\n")
            handle.write(completed.stderr)
        handle.write(f"\n[returncode={completed.returncode}]\n")
    event = {
        "utc": _utc_now(),
        "event": f"{event_name}_finished",
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }
    _append_jsonl(events, event)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "Unknown command failure")[-2_000:]
        raise RuntimeError(f"{event_name} failed: {tail.strip()}")
    return completed


def _module_command(module: str, *arguments: Any) -> list[str]:
    return [sys.executable, "-m", module, *(str(value) for value in arguments)]


def _training_command(
    args: argparse.Namespace,
    run_steps: int,
    current_step: int,
) -> list[str]:
    command = _module_command(
        "main_ai_canri.domain_packages.local_llm.train",
        "--checkpoint",
        Path(args.checkpoint).resolve(),
        "--tokenizer",
        Path(args.tokenizer).resolve(),
        "--objective",
        "instruction",
        "--resume",
        "--max-steps",
        max(1, int(run_steps)),
        "--epochs",
        1,
        "--batch-size",
        max(1, int(args.batch_size)),
        "--gradient-accumulation",
        1,
        "--learning-rate",
        float(args.learning_rate),
        "--min-learning-rate",
        float(args.minimum_learning_rate),
        "--warmup-steps",
        50,
        "--lr-decay-steps",
        max(20_000, int(args.hard_limit_steps)),
        "--instruction-validation-fraction",
        0.05,
        "--instruction-shuffle-buffer",
        4096,
        "--instruction-max-per-source",
        max(1, int(args.max_examples_per_source)),
        "--instruction-curated-repeats",
        max(1, int(args.curated_repeats)),
        "--save-every",
        max(1, int(args.save_every)),
        "--log-every",
        max(1, int(args.log_every)),
        "--cpu-threads",
        max(1, int(args.cpu_threads)),
    )
    if int(current_step) < max(0, int(args.focus_until_steps)):
        for source in args.focus_source or []:
            if str(source).strip():
                command.extend(("--instruction-include-source", str(source).strip()))
    return command


def _run_evaluations(args: argparse.Namespace) -> dict:
    if not args.skip_standard_evaluation:
        _run_command(
            _module_command(
                "main_ai_canri.domain_packages.local_llm.evaluate",
                "--checkpoint",
                Path(args.checkpoint).resolve(),
                "--tokenizer",
                Path(args.tokenizer).resolve(),
                "--examples",
                512,
                "--batch-size",
                8,
                "--max-examples-per-source",
                max(1, int(args.max_examples_per_source)),
                "--output",
                Path(args.standard_evaluation_output).resolve(),
            ),
            process_log=Path(args.process_log),
            events=Path(args.events),
            event_name="standard_evaluation",
            dry_run=bool(args.dry_run),
        )
    _run_command(
        _module_command(
            "main_ai_canri.domain_packages.local_llm.sealed_evaluate",
            "--checkpoint",
            Path(args.checkpoint).resolve(),
            "--tokenizer",
            Path(args.tokenizer).resolve(),
            "--output",
            Path(args.sealed_evaluation_output).resolve(),
            "--max-new-tokens",
            160,
        ),
        process_log=Path(args.process_log),
        events=Path(args.events),
        event_name="sealed_evaluation",
        dry_run=bool(args.dry_run),
    )
    _run_command(
        _module_command(
            "main_ai_canri.domain_packages.local_llm.export",
            "--checkpoint",
            Path(args.checkpoint).resolve(),
            "--output",
            Path(args.inference_output).resolve(),
        ),
        process_log=Path(args.process_log),
        events=Path(args.events),
        event_name="inference_export",
        dry_run=bool(args.dry_run),
    )
    if args.dry_run:
        return {}
    return json.loads(
        Path(args.sealed_evaluation_output).read_text(encoding="utf-8")
    )


def run_campaign(args: argparse.Namespace) -> dict:
    checkpoint = Path(args.checkpoint).resolve()
    tokenizer = Path(args.tokenizer).resolve()
    if not checkpoint.is_file() or not tokenizer.is_file():
        raise RuntimeError("The checkpoint and tokenizer must exist before continuing.")
    minimum_target = max(1, int(args.minimum_target_steps))
    hard_limit = max(minimum_target, int(args.hard_limit_steps))
    cycle_size = max(1, int(args.cycle_steps))
    evaluation_every = max(1, int(args.evaluation_every))
    events = Path(args.events)
    process_log = Path(args.process_log)
    status_path = Path(args.status)
    stop_file = Path(args.stop_file)
    lock_path = Path(args.lock)
    _claim_lock(lock_path)
    started_utc = _utc_now()
    started = time.monotonic()
    cycles = 0
    last_evaluated_step = 0
    sealed: dict = {}
    try:
        metadata = _checkpoint_metadata(checkpoint)
        sealed_output = Path(args.sealed_evaluation_output)
        if sealed_output.is_file():
            try:
                existing = json.loads(
                    sealed_output.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                existing = {}
            existing_checkpoint = str(existing.get("checkpoint") or "").strip()
            try:
                same_checkpoint = (
                    bool(existing_checkpoint)
                    and Path(existing_checkpoint).resolve() == checkpoint
                )
            except OSError:
                same_checkpoint = False
            if same_checkpoint:
                sealed = existing
                last_evaluated_step = int(existing.get("global_steps", 0))
        if not args.skip_corpus_build:
            _run_command(
                _module_command(
                    "main_ai_canri.domain_packages.local_llm.build_quality_corpus"
                ),
                process_log=process_log,
                events=events,
                event_name="quality_corpus_build",
                dry_run=bool(args.dry_run),
            )

        while True:
            current_step = int(metadata["global_steps"])
            automated_gate = bool(sealed.get("automated_gate_passed"))
            if current_step >= minimum_target and automated_gate:
                reason = "automated_quality_gate_passed"
                state = "awaiting_manual_review"
                break
            if current_step >= hard_limit:
                reason = "hard_step_limit_reached"
                state = "quality_gate_not_met"
                break
            if stop_file.is_file():
                reason = "stop_file_requested"
                state = "stopped_resumable"
                stop_file.unlink(missing_ok=True)
                break
            if int(args.maximum_cycles) and cycles >= int(args.maximum_cycles):
                reason = "maximum_cycles_reached"
                state = "paused_resumable"
                break

            next_evaluation = (
                (current_step // evaluation_every) + 1
            ) * evaluation_every
            run_steps = min(
                cycle_size,
                hard_limit - current_step,
                max(1, next_evaluation - current_step),
            )
            status = {
                "schema_version": 1,
                "state": "training",
                "pid": os.getpid(),
                "started_utc": started_utc,
                "updated_utc": _utc_now(),
                "minimum_target_steps": minimum_target,
                "hard_limit_steps": hard_limit,
                "cycle": cycles + 1,
                "cycle_steps": run_steps,
                **metadata,
                "last_evaluated_step": last_evaluated_step,
                "stop_file": str(stop_file.resolve()),
            }
            _atomic_json(status_path, status)
            _run_command(
                _training_command(args, run_steps, current_step),
                process_log=process_log,
                events=events,
                event_name="training_cycle",
                dry_run=bool(args.dry_run),
            )
            cycles += 1
            if args.dry_run:
                reason = "dry_run_complete"
                state = "dry_run_complete"
                break
            metadata = _checkpoint_metadata(checkpoint)
            current_step = int(metadata["global_steps"])
            should_evaluate = (
                current_step >= next_evaluation
                or current_step >= minimum_target
                or current_step >= hard_limit
            )
            if should_evaluate and current_step > last_evaluated_step:
                sealed = _run_evaluations(args)
                last_evaluated_step = current_step

        result = {
            "schema_version": 1,
            "state": state,
            "reason": reason,
            "pid": os.getpid(),
            "started_utc": started_utc,
            "finished_utc": _utc_now(),
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "cycles_this_run": cycles,
            "minimum_target_steps": minimum_target,
            "hard_limit_steps": hard_limit,
            **metadata,
            "last_evaluated_step": last_evaluated_step,
            "automated_quality_gate_passed": bool(
                sealed.get("automated_gate_passed")
            ),
            "sealed_validation_loss": (
                sealed.get("reference_metrics", {}).get("loss")
                if isinstance(sealed.get("reference_metrics"), dict)
                else None
            ),
            "sealed_generation_metrics": sealed.get("generation_metrics", {}),
            "events": str(events.resolve()),
            "process_log": str(process_log.resolve()),
        }
        _atomic_json(status_path, result)
        _append_jsonl(events, {"utc": _utc_now(), "event": "campaign_stopped", **result})
        return result
    except Exception as error:
        failure = {
            "schema_version": 1,
            "state": "failed_resumable",
            "pid": os.getpid(),
            "started_utc": started_utc,
            "failed_utc": _utc_now(),
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "cycles_this_run": cycles,
            "error": f"{type(error).__name__}: {error}",
        }
        _atomic_json(status_path, failure)
        _append_jsonl(events, {"utc": _utc_now(), "event": "campaign_failed", **failure})
        raise
    finally:
        lock_path.unlink(missing_ok=True)


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = run_campaign(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
