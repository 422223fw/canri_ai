"""Activate a native CANRI checkpoint only after its sealed release gate passes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
CANRI_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_REPORT = PACKAGE_ROOT / "sealed_evaluation_v3.json"
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native_v3_inference.pt"
DEFAULT_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer_v3.json"
DEFAULT_SETTINGS = CANRI_ROOT / "data" / "Local_model_settings.json"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Activate a sealed and manually approved native CANRI model."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Confirm that the generated samples received human review.",
    )
    return parser


def _load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return value


def _relative_to_canri(path: Path) -> str:
    try:
        return path.resolve().relative_to(CANRI_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise RuntimeError("Native model files must remain inside main_ai_canri.") from error


def activate(args: argparse.Namespace) -> dict:
    if not args.approve:
        raise RuntimeError("Activation requires --approve after human sample review.")
    report_path = Path(args.report)
    checkpoint = Path(args.checkpoint)
    tokenizer = Path(args.tokenizer)
    settings_path = Path(args.settings)
    report = _load_object(report_path)
    if report.get("automated_gate_passed") is not True:
        raise RuntimeError("The sealed automated quality gate has not passed.")
    if report.get("manual_review_approved") is not True:
        raise RuntimeError(
            "The sealed report is not manually approved; rerun sealed_evaluate "
            "with --manual-review-approved after reviewing its samples."
        )
    if report.get("ready_for_canri_default_backend") is not True:
        raise RuntimeError("The sealed report does not mark this checkpoint ready.")
    if not checkpoint.is_file() or not tokenizer.is_file():
        raise RuntimeError("The inference checkpoint and tokenizer must both exist.")

    settings = _load_object(settings_path)
    settings.update(
        {
            "enabled": True,
            "backend": "canri_native",
            "native_checkpoint_path": _relative_to_canri(checkpoint),
            "native_tokenizer_path": _relative_to_canri(tokenizer),
            "native_training_status_path": _relative_to_canri(report_path),
            "native_allow_experimental": False,
        }
    )
    temporary = settings_path.with_name(settings_path.name + ".tmp")
    temporary.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(settings_path)
    return {
        "activated": True,
        "checkpoint": str(checkpoint.resolve()),
        "tokenizer": str(tokenizer.resolve()),
        "report": str(report_path.resolve()),
        "settings": str(settings_path.resolve()),
    }


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = activate(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
