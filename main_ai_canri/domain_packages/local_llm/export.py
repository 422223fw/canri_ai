"""Export a compact inference-only CANRI native checkpoint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .model.transformer import require_torch


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = PACKAGE_ROOT / "checkpoints" / "canri_native_v2.pt"
DEFAULT_OUTPUT = PACKAGE_ROOT / "checkpoints" / "canri_native_v2_inference.pt"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export CANRI weights without optimizer state."
    )
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def _load_checkpoint(torch, path: Path) -> dict:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def export_checkpoint(source: Path, output: Path) -> dict:
    torch, _ = require_torch()
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise RuntimeError(f"Checkpoint does not exist: {source}")
    payload = _load_checkpoint(torch, source)
    required = {"config", "model_state"}
    missing = sorted(required - payload.keys())
    if missing:
        raise RuntimeError(f"Checkpoint is missing required fields: {missing}")
    compact = {
        "schema_version": 3,
        "model_type": payload.get(
            "model_type", "canri_native_causal_transformer"
        ),
        "artifact_type": "inference_only",
        "exported_utc": datetime.now(timezone.utc).isoformat(),
        "config": payload["config"],
        "model_state": payload["model_state"],
        "step": int(payload.get("step", 0)),
        "last_loss": payload.get("last_loss"),
        "tokenizer": payload.get("tokenizer"),
        "training_data": payload.get("training_data", {}),
        "training_policy": payload.get("training_policy", {}),
        "lineage": payload.get("lineage", {}),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    torch.save(compact, temporary)
    temporary.replace(output)
    return {
        "source": str(source),
        "source_bytes": source.stat().st_size,
        "output": str(output),
        "output_bytes": output.stat().st_size,
        "global_steps": compact["step"],
        "optimizer_state_included": False,
        "weight_transfer_preserved": "weight_transfer" in compact["lineage"],
    }


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = export_checkpoint(args.checkpoint, args.output)
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
