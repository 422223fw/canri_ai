"""Generate a deterministic review set for CANRI's native language model."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .dataset import DATA_ROOT, DEFAULT_TOKENIZER
from .inference import DEFAULT_CHECKPOINT, generate_text


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_BENCHMARK = DATA_ROOT / "Local_llm_generation_benchmark.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "generation_review.json"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate native CANRI answers for human quality review."
    )
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    return [dict(item) for item in cases if isinstance(item, dict)]


def _automatic_checks(output: str, case: dict) -> dict:
    value = str(output or "").strip()
    lowered = value.casefold()
    words = re.findall(r"\w+", lowered, flags=re.UNICODE)
    repeated_ratio = 0.0
    if words:
        repeated_ratio = 1.0 - len(set(words)) / len(words)
    required = [
        str(item).casefold()
        for item in case.get("required_any", [])
        if str(item).strip()
    ]
    required_all = [
        str(item).casefold()
        for item in case.get("required_all", [])
        if str(item).strip()
    ]
    forbidden = [
        str(item).casefold()
        for item in case.get("forbidden", [])
        if str(item).strip()
    ]
    required_ok = not required or any(item in lowered for item in required)
    required_all_ok = all(item in lowered for item in required_all)
    forbidden_ok = not any(item in lowered for item in forbidden)
    length_ok = 1 <= len(value) <= int(case.get("maximum_characters", 2_000))
    repetition_ok = repeated_ratio <= float(case.get("maximum_repeated_ratio", 0.55))
    replacement_ok = "?" not in value or value.count("?") <= 2
    checks = {
        "nonempty_and_bounded": length_ok,
        "required_signal_present": required_ok,
        "all_mandatory_signals_present": required_all_ok,
        "forbidden_signal_absent": forbidden_ok,
        "repetition_bounded": repetition_ok,
        "unknown_token_artifacts_bounded": replacement_ok,
    }
    weights = {
        "nonempty_and_bounded": 2,
        "required_signal_present": 4,
        "all_mandatory_signals_present": 4,
        "forbidden_signal_absent": 1,
        "repetition_bounded": 1,
        "unknown_token_artifacts_bounded": 1,
    }
    passed_weight = sum(weights[name] for name, passed in checks.items() if passed)
    score = round(100 * passed_weight / sum(weights.values()), 2) if value else 0.0
    return {
        "checks": checks,
        "score": score,
        "word_count": len(words),
        "repeated_word_ratio": round(repeated_ratio, 4),
    }


def review(args: argparse.Namespace) -> dict:
    cases = _load_cases(Path(args.benchmark))
    if not cases:
        raise RuntimeError("The generation benchmark contains no cases.")
    results = []
    for index, case in enumerate(cases):
        prompt = str(case.get("prompt") or "").strip()
        if not prompt:
            continue
        output = generate_text(
            prompt,
            checkpoint=args.checkpoint,
            tokenizer_path=args.tokenizer,
            max_new_tokens=max(1, int(args.max_new_tokens)),
            temperature=float(args.temperature),
            seed=int(args.seed) + index,
        )
        results.append(
            {
                "id": str(case.get("id") or f"case_{index + 1}"),
                "category": str(case.get("category") or "general"),
                "prompt": prompt,
                "output": output,
                **_automatic_checks(output, case),
            }
        )
    average = sum(item["score"] for item in results) / max(1, len(results))
    semantic_checks_passed = all(
        item["checks"]["required_signal_present"]
        and item["checks"]["all_mandatory_signals_present"]
        for item in results
    )
    payload = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(Path(args.checkpoint)),
        "benchmark": str(Path(args.benchmark)),
        "cases": len(results),
        "automatic_average_score": round(average, 2),
        "automatic_gate_passed": bool(results) and average >= 85 and semantic_checks_passed,
        "manual_review_required": True,
        "manual_review_approved": False,
        "results": results,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(destination)
    return payload


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = review(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
