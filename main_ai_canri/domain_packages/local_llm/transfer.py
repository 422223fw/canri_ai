"""Expand CANRI's native model while preserving compatible learned weights."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import (
    DATA_ROOT,
    DEFAULT_TRAINING_POLICY,
    inventory_data_sources,
    iter_all_data_texts,
    load_training_data_policy,
)
from .model.transformer import CanriConfig, build_model, require_torch
from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native.pt"
DEFAULT_SOURCE_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer.json"
DEFAULT_TARGET_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native_v2.pt"
DEFAULT_TARGET_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer_v2.json"
DEFAULT_TARGET_STATUS = PACKAGE_ROOT / "training_status_v2.json"
DEFAULT_TRANSFER_REPORT = PACKAGE_ROOT / "weight_transfer_report_v2.json"
DEFAULT_QUALITY_CORPUS = PACKAGE_ROOT / "quality_corpus"
_LAYER_PATTERN = re.compile(r"^blocks\.layers\.(\d+)\.(.+)$")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transfer CANRI native weights into an expanded architecture."
    )
    parser.add_argument("--source-checkpoint", type=Path, default=DEFAULT_SOURCE_CHECKPOINT)
    parser.add_argument("--source-tokenizer", type=Path, default=DEFAULT_SOURCE_TOKENIZER)
    parser.add_argument("--target-checkpoint", type=Path, default=DEFAULT_TARGET_CHECKPOINT)
    parser.add_argument("--target-tokenizer", type=Path, default=DEFAULT_TARGET_TOKENIZER)
    parser.add_argument("--target-status", type=Path, default=DEFAULT_TARGET_STATUS)
    parser.add_argument("--report", type=Path, default=DEFAULT_TRANSFER_REPORT)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--data-policy", type=Path, default=DEFAULT_TRAINING_POLICY)
    parser.add_argument("--vocab-size", type=int, default=8_448)
    parser.add_argument("--context-length", type=int, default=256)
    parser.add_argument("--embedding-size", type=int, default=224)
    parser.add_argument("--layers", type=int, default=5)
    parser.add_argument("--heads", type=int, default=7)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument(
        "--tokenizer-strategy",
        choices=("preserve", "byte_v3"),
        default="preserve",
    )
    parser.add_argument(
        "--tokenizer-quality-corpus",
        type=Path,
        default=DEFAULT_QUALITY_CORPUS,
    )
    parser.add_argument("--tokenizer-quality-repeats", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    return parser


def _load_checkpoint(torch, path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def _source_key_for_target(key: str, source_layers: int) -> tuple[str, bool]:
    match = _LAYER_PATTERN.match(key)
    if not match:
        return key, False
    target_layer = int(match.group(1))
    if target_layer < source_layers:
        return key, False
    source_key = f"blocks.layers.{source_layers - 1}.{match.group(2)}"
    return source_key, True


def _copy_overlap(target, source) -> int:
    if target.ndim != source.ndim:
        return 0
    if target.ndim == 0:
        target.copy_(source)
        return 1
    slices = tuple(slice(0, min(left, right)) for left, right in zip(target.shape, source.shape))
    target[slices].copy_(source[slices])
    copied = 1
    for item in slices:
        copied *= int(item.stop)
    return copied


def _copy_attention_projection(target, source, *, bias: bool) -> int:
    old_width = source.shape[0] // 3
    new_width = target.shape[0] // 3
    copied = 0
    for projection in range(3):
        source_part = source[projection * old_width:(projection + 1) * old_width]
        target_part = target[projection * new_width:(projection + 1) * new_width]
        copied += _copy_overlap(target_part, source_part)
    return copied


def _copy_token_rows(
    target,
    source,
    *,
    source_tokenizer: CanriTokenizer,
    target_tokenizer: CanriTokenizer,
) -> tuple[int, int]:
    if target.ndim != 2 or source.ndim != 2:
        return 0, 0
    copied = 0
    matched = 0
    width = min(int(target.shape[1]), int(source.shape[1]))
    for target_index, token in enumerate(target_tokenizer.vocabulary):
        source_index = source_tokenizer.token_to_id.get(token)
        if source_index is None or source_index >= int(source.shape[0]):
            continue
        target[target_index, :width].copy_(source[source_index, :width])
        copied += width
        matched += 1
    return copied, matched


def _iter_quality_corpus_texts(root: Path, repeats: int):
    paths = sorted(Path(root).glob("*.jsonl"))
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(record, dict):
                    continue
                text = "\n".join(
                    part
                    for part in (
                        str(record.get("user") or "").strip(),
                        str(record.get("assistant") or "").strip(),
                    )
                    if part
                )
                if not text:
                    continue
                for _ in range(max(1, int(repeats))):
                    yield text


def transfer_state_dict(
    target_state: dict[str, Any],
    source_state: dict[str, Any],
    *,
    source_layers: int,
    source_tokenizer: CanriTokenizer | None = None,
    target_tokenizer: CanriTokenizer | None = None,
) -> dict[str, Any]:
    transferred_elements = 0
    exact_tensors = 0
    partial_tensors = 0
    cloned_layer_tensors = 0
    matched_token_rows = 0
    missing_tensors = []
    for target_key, target_tensor in target_state.items():
        source_key, cloned_layer = _source_key_for_target(target_key, source_layers)
        source_tensor = source_state.get(source_key)
        if source_tensor is None:
            missing_tensors.append(target_key)
            continue
        if (
            target_key in {"token_embedding.weight", "output.weight"}
            and source_tokenizer is not None
            and target_tokenizer is not None
        ):
            copied, matched = _copy_token_rows(
                target_tensor,
                source_tensor,
                source_tokenizer=source_tokenizer,
                target_tokenizer=target_tokenizer,
            )
            matched_token_rows = max(matched_token_rows, matched)
        elif target_key.endswith("self_attn.in_proj_weight"):
            copied = _copy_attention_projection(target_tensor, source_tensor, bias=False)
        elif target_key.endswith("self_attn.in_proj_bias"):
            copied = _copy_attention_projection(target_tensor, source_tensor, bias=True)
        else:
            copied = _copy_overlap(target_tensor, source_tensor)
        transferred_elements += copied
        if tuple(target_tensor.shape) == tuple(source_tensor.shape):
            exact_tensors += 1
        else:
            partial_tensors += 1
        cloned_layer_tensors += int(cloned_layer)
    return {
        "transferred_state_elements": transferred_elements,
        "exact_tensors": exact_tensors,
        "partial_tensors": partial_tensors,
        "cloned_layer_tensors": cloned_layer_tensors,
        "matched_token_rows": matched_token_rows,
        "missing_tensors": missing_tensors,
    }


def transfer(args: argparse.Namespace) -> dict[str, Any]:
    torch, _ = require_torch()
    source_checkpoint = Path(args.source_checkpoint)
    source_tokenizer_path = Path(args.source_tokenizer)
    target_checkpoint = Path(args.target_checkpoint)
    target_tokenizer_path = Path(args.target_tokenizer)
    if not source_checkpoint.is_file() or not source_tokenizer_path.is_file():
        raise RuntimeError("The source checkpoint and tokenizer must both exist.")
    if not args.force and (target_checkpoint.exists() or target_tokenizer_path.exists()):
        raise RuntimeError("The v2 target already exists. Use --force only for an intentional rebuild.")

    payload = _load_checkpoint(torch, source_checkpoint)
    source_config = CanriConfig(**payload["config"])
    source_tokenizer = CanriTokenizer.load(source_tokenizer_path)
    policy = load_training_data_policy(Path(args.data_policy))
    inventory = inventory_data_sources(Path(args.data_root), policy=policy)
    tokenizer_strategy = str(args.tokenizer_strategy)
    if tokenizer_strategy == "byte_v3":
        quality_texts = _iter_quality_corpus_texts(
            Path(args.tokenizer_quality_corpus),
            max(1, int(args.tokenizer_quality_repeats)),
        )
        expanded_tokenizer = CanriTokenizer.from_byte_fallback_texts(
            quality_texts,
            max_vocab_size=max(512, int(args.vocab_size)),
        )
    else:
        expanded_tokenizer = CanriTokenizer.expanded_from_texts(
            source_tokenizer,
            iter_all_data_texts(Path(args.data_root), policy=policy),
            max_vocab_size=max(len(source_tokenizer), int(args.vocab_size)),
        )
    expanded_tokenizer.save(
        target_tokenizer_path,
        metadata={
            "weight_transfer_source": str(source_tokenizer_path.resolve()),
            "data_fingerprint": inventory["fingerprint"],
            "training_data_policy": policy.name,
            "tokenizer_strategy": tokenizer_strategy,
        },
    )

    target_config = CanriConfig(
        vocab_size=len(expanded_tokenizer),
        context_length=max(source_config.context_length, int(args.context_length)),
        embedding_size=max(source_config.embedding_size, int(args.embedding_size)),
        layers=max(source_config.layers, int(args.layers)),
        heads=max(1, int(args.heads)),
        dropout=min(0.5, max(0.0, float(args.dropout))),
    )
    if target_config.embedding_size % target_config.heads:
        raise RuntimeError("The target embedding size must be divisible by target heads.")
    old_head_size = source_config.embedding_size // source_config.heads
    new_head_size = target_config.embedding_size // target_config.heads
    if old_head_size != new_head_size:
        raise RuntimeError(
            "Weight transfer requires the same attention head size; "
            f"source={old_head_size}, target={new_head_size}."
        )

    torch.manual_seed(int(args.seed))
    target_model = build_model(target_config)
    target_state = target_model.state_dict()
    transfer_details = transfer_state_dict(
        target_state,
        payload["model_state"],
        source_layers=source_config.layers,
        source_tokenizer=source_tokenizer,
        target_tokenizer=expanded_tokenizer,
    )
    target_model.load_state_dict(target_state)
    optimizer = torch.optim.AdamW(target_model.parameters(), lr=3e-4, weight_decay=0.1)
    target_parameters = sum(parameter.numel() for parameter in target_model.parameters())
    source_parameters = int(
        payload.get("parameters")
        or sum(parameter.numel() for parameter in build_model(source_config).parameters())
    )
    created_utc = datetime.now(timezone.utc).isoformat()
    lineage = {
        "trained_from_random_initialization": True,
        "downloaded_base_model": False,
        "seed": int(args.seed),
        "weight_transfer": {
            "source_checkpoint": str(source_checkpoint.resolve()),
            "source_global_steps": int(payload.get("step", 0)),
            "source_parameters": source_parameters,
            "target_parameters": target_parameters,
            "source_config": source_config.to_dict(),
            "target_config": target_config.to_dict(),
            "tokenizer_strategy": tokenizer_strategy,
            **transfer_details,
        },
        "instruction_split_version": "sha256_v1",
        "instruction_split_enforced_since_step": -1,
    }
    checkpoint_payload = {
        "schema_version": 3,
        "model_type": "canri_native_causal_transformer",
        "config": target_config.to_dict(),
        "model_state": target_model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "step": 0,
        "epoch": 0,
        "last_loss": None,
        "tokenizer": str(target_tokenizer_path.resolve()),
        "training_data": inventory,
        "training_policy": {"phase": "weight_transfer"},
        "training_runs": [],
        "lineage": lineage,
    }
    target_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_checkpoint.with_name(target_checkpoint.name + ".tmp")
    torch.save(checkpoint_payload, temporary)
    temporary.replace(target_checkpoint)

    report = {
        "schema_version": 1,
        "created_utc": created_utc,
        "source_checkpoint": str(source_checkpoint.resolve()),
        "target_checkpoint": str(target_checkpoint.resolve()),
        "target_tokenizer": str(target_tokenizer_path.resolve()),
        "checkpoint_bytes": target_checkpoint.stat().st_size,
        "source_parameters": source_parameters,
        "target_parameters": target_parameters,
        "parameter_growth": target_parameters - source_parameters,
        "source_vocabulary_size": len(source_tokenizer),
        "target_vocabulary_size": len(expanded_tokenizer),
        "tokenizer_strategy": tokenizer_strategy,
        "data_inventory": inventory,
        "lineage": lineage,
    }
    _atomic_json(Path(args.report), report)
    _atomic_json(
        Path(args.target_status),
        {
            "schema_version": 2,
            "status": "weight_transferred_training_required",
            "ready_for_canri_default_backend": False,
            "checkpoint": str(target_checkpoint.resolve()),
            "checkpoint_bytes": target_checkpoint.stat().st_size,
            "global_steps": 0,
            "parameters": target_parameters,
            "vocabulary_size": len(expanded_tokenizer),
            "validation_loss": None,
            "manual_review_approved": False,
            "lineage": lineage,
        },
    )
    return report


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = transfer(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
