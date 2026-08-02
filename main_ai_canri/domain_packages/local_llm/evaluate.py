"""Evaluate a native CANRI checkpoint on held-out instruction examples."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from itertools import islice
from pathlib import Path

from .dataset import DATA_ROOT, DEFAULT_TOKENIZER
from .inference import DEFAULT_CHECKPOINT
from .instruction_dataset import (
    INSTRUCTION_SPLIT_VERSION,
    iter_instruction_training_windows,
)
from .model.transformer import CanriConfig, build_model, require_torch
from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_STATUS = PACKAGE_ROOT / "training_status.json"


def _load_checkpoint(torch, path: Path) -> dict:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate CANRI's native checkpoint.")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--skip-examples", type=int, default=0)
    parser.add_argument("--examples", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--max-examples-per-source", type=int, default=6_000)
    parser.add_argument("--maximum-validation-loss", type=float, default=1.5)
    parser.add_argument("--minimum-training-steps", type=int, default=20_000)
    parser.add_argument("--manual-review-approved", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_STATUS)
    return parser


def evaluate(args: argparse.Namespace) -> dict:
    torch, _ = require_torch()
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.is_file():
        raise RuntimeError(f"Checkpoint does not exist: {checkpoint_path}")
    tokenizer = CanriTokenizer.load(args.tokenizer)
    payload = _load_checkpoint(torch, checkpoint_path)
    config = CanriConfig(**payload["config"])
    model = build_model(config)
    model.load_state_dict(payload["model_state"])
    model.eval()

    windows = list(islice(
        iter_instruction_training_windows(
            tokenizer,
            data_root=Path(args.data_root),
            context_length=config.context_length,
            split="validation",
            validation_fraction=float(args.validation_fraction),
            shuffle_buffer=0,
            max_examples_per_source=max(0, int(args.max_examples_per_source)),
        ),
        max(0, int(args.skip_examples)),
        max(0, int(args.skip_examples)) + max(1, int(args.examples)),
    ))
    batch_size = max(1, int(args.batch_size))
    weighted_loss = 0.0
    evaluated_tokens = 0
    evaluated = 0
    windows_by_source = defaultdict(list)
    source_totals = defaultdict(
        lambda: {"weighted_loss": 0.0, "tokens": 0, "examples": 0}
    )
    for window in windows:
        windows_by_source[window.source].append(window)
    with torch.inference_mode():
        for source, source_windows in windows_by_source.items():
            for offset in range(0, len(source_windows), batch_size):
                pending = source_windows[offset:offset + batch_size]
                useful_width = max(
                    max(
                        (
                            index + 1
                            for index, token in enumerate(item.target_ids)
                            if token != -100
                        ),
                        default=1,
                    )
                    for item in pending
                )
                batch_input = torch.tensor(
                    [item.token_ids[:useful_width] for item in pending],
                    dtype=torch.long,
                )
                batch_target = torch.tensor(
                    [item.target_ids[:useful_width] for item in pending],
                    dtype=torch.long,
                )
                _, loss = model(batch_input, batch_target)
                target_tokens = int((batch_target != -100).sum().item())
                batch_weighted_loss = float(loss.detach()) * target_tokens
                weighted_loss += batch_weighted_loss
                evaluated_tokens += target_tokens
                evaluated += len(pending)
                source_totals[source]["weighted_loss"] += batch_weighted_loss
                source_totals[source]["tokens"] += target_tokens
                source_totals[source]["examples"] += len(pending)

    if not evaluated_tokens:
        raise RuntimeError("No held-out instruction examples were available.")
    validation_loss = weighted_loss / evaluated_tokens
    source_metrics = []
    for source, totals in source_totals.items():
        source_loss = totals["weighted_loss"] / max(1, totals["tokens"])
        source_metrics.append(
            {
                "source": source,
                "examples": totals["examples"],
                "assistant_tokens": totals["tokens"],
                "loss": round(source_loss, 6),
                "perplexity": round(math.exp(min(source_loss, 20.0)), 4),
            }
        )
    source_metrics.sort(key=lambda item: (-item["loss"], item["source"]))
    global_steps = int(payload.get("step", 0))
    lineage = payload.get("lineage", {})
    lineage = lineage if isinstance(lineage, dict) else {}
    split_enforced_since_step = int(
        lineage.get("instruction_split_enforced_since_step", global_steps)
    )
    clean_holdout_lineage = split_enforced_since_step == 0
    maximum_loss = float(args.maximum_validation_loss)
    minimum_steps = max(1, int(args.minimum_training_steps))
    automated_gate = (
        validation_loss <= maximum_loss
        and global_steps >= minimum_steps
        and clean_holdout_lineage
    )
    manual_review_approved = bool(args.manual_review_approved)
    ready = automated_gate and manual_review_approved
    result = {
        "schema_version": 2,
        "status": "ready" if ready else "experimental_not_ready",
        "ready_for_canri_default_backend": ready,
        "automated_gate_passed": automated_gate,
        "manual_review_approved": manual_review_approved,
        "checkpoint": str(checkpoint_path),
        "checkpoint_bytes": checkpoint_path.stat().st_size,
        "global_steps": global_steps,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "tokenizer_mode": tokenizer.mode,
        "vocabulary_size": len(tokenizer),
        "held_out_examples": evaluated,
        "held_out_assistant_tokens": evaluated_tokens,
        "held_out_skip": max(0, int(args.skip_examples)),
        "evaluation_protocol": "assistant_only_deterministic_holdout_v2",
        "instruction_split_version": INSTRUCTION_SPLIT_VERSION,
        "instruction_split_enforced_since_step": split_enforced_since_step,
        "clean_holdout_lineage": clean_holdout_lineage,
        "validation_fraction": float(args.validation_fraction),
        "validation_loss": round(validation_loss, 6),
        "perplexity": round(math.exp(min(validation_loss, 20.0)), 4),
        "held_out_source_metrics": source_metrics,
        "readiness_gate": {
            "maximum_validation_loss": maximum_loss,
            "minimum_training_steps": minimum_steps,
            "manual_generation_review_required": True,
            "clean_holdout_lineage_required": True,
        },
        "training_data": payload.get("training_data", {}),
        "lineage": lineage,
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
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
