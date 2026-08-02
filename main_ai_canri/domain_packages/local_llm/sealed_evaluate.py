"""Evaluate CANRI's native model against a physically sealed holdout set.

Unlike the lightweight review script, this evaluator measures assistant-only
loss, deterministic generation, request signals, Python syntax, and safe pure
function behavior. The holdout file is outside every training source.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .inference import clear_runtime_cache, generate_text
from .instruction_dataset import (
    IGNORE_INDEX,
    InstructionExample,
    build_instruction_training_windows,
)
from .model.transformer import CanriConfig, build_model, require_torch
from .review import _automatic_checks
from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native_v2.pt"
DEFAULT_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer_v2.json"
DEFAULT_HOLDOUT = PACKAGE_ROOT / "evaluation" / "sealed_holdout_v2.json"
DEFAULT_CORPUS_MANIFEST = PACKAGE_ROOT / "quality_corpus" / "manifest.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "sealed_evaluation_v2.json"

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "str": str,
    "sum": sum,
    "zip": zip,
}
DISALLOWED_AST = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Attribute,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CANRI's sealed post-transfer evaluation."
    )
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument(
        "--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--maximum-validation-loss", type=float, default=1.5)
    parser.add_argument("--minimum-training-steps", type=int, default=20_000)
    parser.add_argument("--minimum-generation-score", type=float, default=85.0)
    parser.add_argument("--minimum-semantic-pass-rate", type=float, default=0.90)
    parser.add_argument("--manual-review-approved", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _load_checkpoint(torch, path: Path) -> dict:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def _resolve_device(torch, requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA evaluation was requested, but CUDA is unavailable.")
    return requested


def _extract_python(output: str) -> str:
    text = str(output or "").strip()
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.I | re.S)
    if match:
        return match.group(1).strip()
    return text


def _safe_tree(code: str, required_function: str) -> tuple[ast.Module | None, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return None, f"syntax_error: {error.msg} at line {error.lineno}"
    for statement in tree.body:
        if not isinstance(statement, (ast.FunctionDef, ast.Expr)):
            return None, "Only function definitions and docstrings are executable."
        if isinstance(statement, ast.Expr) and not isinstance(
            statement.value, ast.Constant
        ):
            return None, "Top-level expressions are not executable."
    function_names = {
        item.name for item in tree.body if isinstance(item, ast.FunctionDef)
    }
    if required_function not in function_names:
        return None, f"Missing required function: {required_function}"
    allowed_calls = set(SAFE_BUILTINS) | function_names
    for node in ast.walk(tree):
        if isinstance(node, DISALLOWED_AST):
            return None, f"Disallowed Python construct: {type(node).__name__}"
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return None, f"Disallowed identifier: {node.id}"
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in allowed_calls:
                return None, "Only approved pure function calls are executable."
    return tree, "ok"


def _values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
    return actual == expected


def validate_python_behavior(output: str, specification: dict) -> dict:
    """Execute only a tightly restricted, loop-free pure function benchmark."""

    code = _extract_python(output)
    required_function = str(specification.get("required_function") or "").strip()
    if not required_function:
        return {"passed": False, "syntax_ok": False, "error": "No function specified."}
    tree, reason = _safe_tree(code, required_function)
    if tree is None:
        return {"passed": False, "syntax_ok": not reason.startswith("syntax_error"), "error": reason}
    namespace: dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(compile(tree, "<sealed-generated-code>", "exec"), namespace, namespace)
        function = namespace[required_function]
    except Exception as error:  # The AST gate runs before this restricted execution.
        return {
            "passed": False,
            "syntax_ok": True,
            "error": f"definition_error: {type(error).__name__}: {error}",
        }
    calls = []
    passed = True
    for case in specification.get("calls", []):
        args = list(case.get("args", []))
        expected = case.get("expected")
        try:
            actual = function(*args)
            case_passed = _values_equal(actual, expected)
            error = ""
        except Exception as exception:
            actual = None
            case_passed = False
            error = f"{type(exception).__name__}: {exception}"
        passed = passed and case_passed
        calls.append(
            {
                "args": args,
                "expected": expected,
                "actual": actual,
                "passed": case_passed,
                "error": error,
            }
        )
    return {
        "passed": passed and bool(calls),
        "syntax_ok": True,
        "error": "" if passed else "One or more behavior checks failed.",
        "calls": calls,
    }


def _syntax_check(output: str) -> dict:
    code = _extract_python(output)
    try:
        ast.parse(code)
    except SyntaxError as error:
        return {
            "passed": False,
            "error": f"{error.msg} at line {error.lineno}",
        }
    return {"passed": True, "error": ""}


def _corpus_integrity(manifest_path: Path, holdout_path: Path) -> dict:
    manifest = _load_json(manifest_path)
    holdout_sha256 = hashlib.sha256(holdout_path.read_bytes()).hexdigest()
    checks = {
        "holdout_hash_matches_manifest": (
            manifest.get("sealed_holdout_sha256") == holdout_sha256
        ),
        "zero_exact_prompt_overlap": (
            int(manifest.get("exact_holdout_prompts_in_training", -1)) == 0
        ),
        "old_chat_answers_excluded": manifest.get("old_chat_answers_used") is False,
        "model_generated_answers_excluded": (
            manifest.get("model_generated_answers_used") is False
        ),
        "training_manifest_declared": manifest.get("training_only") is True,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "manifest": str(manifest_path),
        "holdout_sha256": holdout_sha256,
        "training_examples": int(manifest.get("examples", 0)),
    }


def _reference_loss(model, tokenizer, config, torch, cases: list[dict], batch_size: int) -> dict:
    windows = []
    case_categories: dict[str, str] = {}
    for case in cases:
        case_id = str(case.get("id") or "unknown")
        category = str(case.get("category") or "general")
        case_categories[case_id] = category
        example = InstructionExample(
            user=str(case.get("prompt") or ""),
            assistant=str(case.get("reference_answer") or ""),
            source=case_id,
            quality=100.0,
        )
        windows.extend(
            build_instruction_training_windows(
                tokenizer,
                example,
                context_length=config.context_length,
                max_windows_per_example=8,
            )
        )
    totals = defaultdict(lambda: {"weighted_loss": 0.0, "tokens": 0, "windows": 0})
    weighted_loss = 0.0
    tokens = 0
    size = max(1, int(batch_size))
    with torch.inference_mode():
        for offset in range(0, len(windows), size):
            pending = windows[offset:offset + size]
            useful_width = max(
                max(
                    (index + 1 for index, token in enumerate(item.target_ids) if token != IGNORE_INDEX),
                    default=1,
                )
                for item in pending
            )
            inputs = torch.tensor(
                [item.token_ids[:useful_width] for item in pending],
                dtype=torch.long,
                device=next(model.parameters()).device,
            )
            targets = torch.tensor(
                [item.target_ids[:useful_width] for item in pending],
                dtype=torch.long,
                device=inputs.device,
            )
            logits, _ = model(inputs)
            token_losses = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.shape[-1]),
                targets.reshape(-1),
                ignore_index=IGNORE_INDEX,
                reduction="none",
            ).reshape(targets.shape)
            active = targets != IGNORE_INDEX
            count = int(active.sum().item())
            value = float(token_losses[active].sum().detach())
            weighted_loss += value
            tokens += count
            for row, item in enumerate(pending):
                row_active = active[row]
                row_tokens = int(row_active.sum().item())
                totals[item.source]["weighted_loss"] += float(
                    token_losses[row][row_active].sum().detach()
                )
                totals[item.source]["tokens"] += row_tokens
                totals[item.source]["windows"] += 1
    if not tokens:
        raise RuntimeError("The sealed holdout produced no assistant tokens.")
    case_losses = []
    category_accumulator = defaultdict(lambda: {"weighted_loss": 0.0, "tokens": 0})
    for case_id, total in totals.items():
        value = total["weighted_loss"] / max(1, total["tokens"])
        category = case_categories[case_id]
        category_accumulator[category]["weighted_loss"] += total["weighted_loss"]
        category_accumulator[category]["tokens"] += total["tokens"]
        case_losses.append(
            {
                "id": case_id,
                "category": category,
                "loss": round(value, 6),
                "assistant_tokens": total["tokens"],
            }
        )
    category_losses = [
        {
            "category": category,
            "loss": round(total["weighted_loss"] / max(1, total["tokens"]), 6),
            "assistant_tokens": total["tokens"],
        }
        for category, total in category_accumulator.items()
    ]
    case_losses.sort(key=lambda item: (-item["loss"], item["id"]))
    category_losses.sort(key=lambda item: (-item["loss"], item["category"]))
    loss = weighted_loss / tokens
    return {
        "loss": round(loss, 6),
        "perplexity": round(math.exp(min(loss, 20.0)), 4),
        "assistant_tokens": tokens,
        "windows": len(windows),
        "case_metrics": case_losses,
        "category_metrics": category_losses,
    }


def evaluate(args: argparse.Namespace) -> dict:
    torch, _ = require_torch()
    checkpoint = Path(args.checkpoint)
    tokenizer_path = Path(args.tokenizer)
    holdout_path = Path(args.holdout)
    if not checkpoint.is_file() or not tokenizer_path.is_file() or not holdout_path.is_file():
        raise RuntimeError("Checkpoint, tokenizer, and sealed holdout must all exist.")
    holdout = _load_json(holdout_path)
    cases = [dict(item) for item in holdout.get("cases", []) if isinstance(item, dict)]
    if not cases:
        raise RuntimeError("The sealed holdout contains no cases.")

    payload = _load_checkpoint(torch, checkpoint)
    tokenizer = CanriTokenizer.load(tokenizer_path)
    config = CanriConfig(**payload["config"])
    device = _resolve_device(torch, str(args.device))
    model = build_model(config).to(device)
    model.load_state_dict(payload["model_state"])
    model.eval()
    reference = _reference_loss(
        model, tokenizer, config, torch, cases, int(args.batch_size)
    )

    clear_runtime_cache()
    results = []
    for index, case in enumerate(cases):
        output = generate_text(
            str(case.get("prompt") or ""),
            checkpoint=checkpoint,
            tokenizer_path=tokenizer_path,
            max_new_tokens=max(1, int(args.max_new_tokens)),
            temperature=0.0,
            lexical_token_bias=0.0,
            seed=10_000 + index,
            device=device,
        )
        automatic = _automatic_checks(output, case)
        semantic_passed = all(
            automatic["checks"][name]
            for name in (
                "nonempty_and_bounded",
                "required_signal_present",
                "all_mandatory_signals_present",
                "forbidden_signal_absent",
            )
        )
        code_result = None
        if isinstance(case.get("python"), dict):
            code_result = validate_python_behavior(output, case["python"])
        elif str(case.get("category") or "").casefold() == "code":
            code_result = _syntax_check(output)
        results.append(
            {
                "id": str(case.get("id") or f"case_{index + 1}"),
                "category": str(case.get("category") or "general"),
                "prompt": str(case.get("prompt") or ""),
                "output": output,
                "semantic_passed": semantic_passed,
                "code_validation": code_result,
                **automatic,
            }
        )

    average_score = sum(item["score"] for item in results) / len(results)
    semantic_pass_rate = sum(item["semantic_passed"] for item in results) / len(results)
    code_results = [item["code_validation"] for item in results if item["code_validation"]]
    code_pass_rate = (
        sum(bool(item.get("passed")) for item in code_results) / len(code_results)
        if code_results
        else 1.0
    )
    integrity = _corpus_integrity(Path(args.corpus_manifest), holdout_path)
    global_steps = int(payload.get("step", 0))
    thresholds = {
        "maximum_validation_loss": float(args.maximum_validation_loss),
        "minimum_training_steps": max(1, int(args.minimum_training_steps)),
        "minimum_generation_score": float(args.minimum_generation_score),
        "minimum_semantic_pass_rate": float(args.minimum_semantic_pass_rate),
        "required_code_pass_rate": 1.0,
    }
    automated_checks = {
        "sealed_corpus_integrity": integrity["passed"],
        "validation_loss": reference["loss"] <= thresholds["maximum_validation_loss"],
        "training_steps": global_steps >= thresholds["minimum_training_steps"],
        "generation_score": average_score >= thresholds["minimum_generation_score"],
        "semantic_pass_rate": semantic_pass_rate >= thresholds["minimum_semantic_pass_rate"],
        "code_pass_rate": code_pass_rate >= thresholds["required_code_pass_rate"],
    }
    automated_gate = all(automated_checks.values())
    manual_approved = bool(args.manual_review_approved)
    ready = automated_gate and manual_approved
    result = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready" if ready else "experimental_not_ready",
        "ready_for_canri_default_backend": ready,
        "automated_gate_passed": automated_gate,
        "manual_review_approved": manual_approved,
        "checkpoint": str(checkpoint),
        "checkpoint_bytes": checkpoint.stat().st_size,
        "global_steps": global_steps,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "tokenizer": str(tokenizer_path),
        "tokenizer_mode": tokenizer.mode,
        "vocabulary_size": len(tokenizer),
        "holdout": str(holdout_path),
        "holdout_cases": len(results),
        "sealed_corpus_integrity": integrity,
        "reference_metrics": reference,
        "generation_metrics": {
            "average_score": round(average_score, 2),
            "semantic_pass_rate": round(semantic_pass_rate, 4),
            "code_pass_rate": round(code_pass_rate, 4),
            "code_cases": len(code_results),
        },
        "readiness_thresholds": thresholds,
        "automated_checks": automated_checks,
        "manual_review_required": True,
        "results": results,
        "lineage": payload.get("lineage", {}),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return result


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = evaluate(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    summary = {
        key: result[key]
        for key in (
            "status",
            "automated_gate_passed",
            "manual_review_approved",
            "global_steps",
            "parameters",
            "holdout_cases",
            "reference_metrics",
            "generation_metrics",
            "automated_checks",
        )
    }
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
