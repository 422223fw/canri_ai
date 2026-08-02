"""Train CANRI's native causal Transformer from random initialization.

The default path reads CANRI's data directory directly. It does not download a
base model and does not create a second copy of the dataset.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .dataset import (
    DATA_ROOT,
    DEFAULT_CORPUS,
    DEFAULT_TRAINING_POLICY,
    DEFAULT_TOKENIZER,
    build_corpus,
    inventory_data_sources,
    iter_all_data_texts,
    iter_training_windows,
    load_training_data_policy,
)
from .instruction_dataset import (
    IGNORE_INDEX,
    INSTRUCTION_SPLIT_VERSION,
    InstructionTrainingWindow,
    iter_instruction_training_windows,
)
from .model.transformer import CanriConfig, build_model, require_torch
from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native.pt"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train CANRI from random weights.")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--data-policy", type=Path, default=DEFAULT_TRAINING_POLICY)
    parser.add_argument("--include-all-data", action="store_true")
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument("--build-corpus", action="store_true")
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZER)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--rebuild-tokenizer", action="store_true")
    parser.add_argument("--max-vocab-size", type=int, default=8192)
    parser.add_argument("--context-length", type=int, default=256)
    parser.add_argument("--embedding-size", type=int, default=256)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--sampling-mode", choices=("balanced", "full"), default="balanced")
    parser.add_argument("--samples-per-source", type=int, default=4)
    parser.add_argument(
        "--objective",
        choices=("language_model", "instruction"),
        default="language_model",
    )
    parser.add_argument("--instruction-min-quality", type=float, default=75.0)
    parser.add_argument("--instruction-max-examples", type=int, default=0)
    parser.add_argument("--instruction-validation-fraction", type=float, default=0.05)
    parser.add_argument("--instruction-shuffle-buffer", type=int, default=2048)
    parser.add_argument("--instruction-max-per-source", type=int, default=6_000)
    parser.add_argument("--instruction-curated-repeats", type=int, default=4)
    parser.add_argument("--instruction-focus-status", type=Path)
    parser.add_argument("--instruction-focus-min-loss", type=float, default=0.0)
    parser.add_argument(
        "--instruction-include-source",
        action="append",
        default=[],
        help="Restrict instruction training to an exact source name; repeatable.",
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--cpu-threads", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--save-every", type=int, default=100)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--warmup-steps", type=int, default=200)
    parser.add_argument("--lr-decay-steps", type=int, default=20_000)
    parser.add_argument("--min-learning-rate", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _iter_corpus_texts(path: Path, chunk_chars: int = 1_048_576) -> Iterator[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        while True:
            chunk = handle.read(chunk_chars)
            if not chunk:
                break
            yield chunk


def _iter_corpus_windows(
    path: Path,
    tokenizer: CanriTokenizer,
    context_length: int,
) -> Iterator[list[int]]:
    buffer: list[int] = []
    for text in _iter_corpus_texts(path):
        buffer.extend(tokenizer.encode(text, add_special_tokens=False))
        cursor = 0
        while len(buffer) - cursor >= context_length + 1:
            yield buffer[cursor:cursor + context_length + 1]
            cursor += context_length
        if cursor:
            buffer = buffer[cursor:]


def _batched(values: Iterable, batch_size: int) -> Iterator[list]:
    batch: list = []
    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _scheduled_learning_rate(
    *,
    base_learning_rate: float,
    minimum_learning_rate: float,
    step: int,
    warmup_steps: int,
    decay_steps: int,
) -> float:
    base = max(1e-8, float(base_learning_rate))
    minimum = min(base, max(0.0, float(minimum_learning_rate)))
    current_step = max(1, int(step))
    warmup = max(0, int(warmup_steps))
    decay = max(warmup + 1, int(decay_steps))
    if warmup and current_step <= warmup:
        return base * current_step / warmup
    progress = min(1.0, max(0.0, (current_step - warmup) / (decay - warmup)))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return minimum + (base - minimum) * cosine


def _prepare_batch(torch, batch: list, *, device: str, objective: str):
    if objective == "instruction":
        if not all(isinstance(item, InstructionTrainingWindow) for item in batch):
            raise RuntimeError("Instruction training received an invalid batch.")
        useful_width = max(
            (
                max(
                    (
                        index + 1
                        for index, token in enumerate(item.target_ids)
                        if token != IGNORE_INDEX
                    ),
                    default=1,
                )
                for item in batch
            ),
            default=1,
        )
        batch_input = torch.tensor(
            [item.token_ids[:useful_width] for item in batch],
            dtype=torch.long,
            device=device,
        )
        batch_target = torch.tensor(
            [item.target_ids[:useful_width] for item in batch],
            dtype=torch.long,
            device=device,
        )
        return batch_input, batch_target
    batch_input = torch.tensor(
        [sequence[:-1] for sequence in batch],
        dtype=torch.long,
        device=device,
    )
    batch_target = torch.tensor(
        [
            [token if token != 0 else IGNORE_INDEX for token in sequence[1:]]
            for sequence in batch
        ],
        dtype=torch.long,
        device=device,
    )
    return batch_input, batch_target


def _load_torch_checkpoint(torch, path: Path) -> dict:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def _resolve_device(torch, requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but PyTorch cannot access a CUDA device.")
    return requested


def _move_optimizer_state(torch, optimizer, device: str) -> None:
    for state in optimizer.state.values():
        for key, value in state.items():
            if torch.is_tensor(value):
                state[key] = value.to(device)


def _save_checkpoint(
    torch,
    *,
    path: Path,
    model,
    optimizer,
    config: CanriConfig,
    step: int,
    epoch: int,
    last_loss: float | None,
    tokenizer_path: Path,
    data_info: dict,
    seed: int,
    training_policy: dict,
    training_runs: list[dict],
    split_enforced_since_step: int,
    base_lineage: dict | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    lineage = dict(base_lineage or {})
    lineage.update(
        {
            "trained_from_random_initialization": True,
            "downloaded_base_model": False,
            "seed": seed,
            "instruction_split_version": INSTRUCTION_SPLIT_VERSION,
            "instruction_split_enforced_since_step": int(
                split_enforced_since_step
            ),
        }
    )
    torch.save(
        {
            "schema_version": 2,
            "model_type": "canri_native_causal_transformer",
            "config": config.to_dict(),
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "step": step,
            "epoch": epoch,
            "last_loss": last_loss,
            "tokenizer": str(tokenizer_path),
            "training_data": data_info,
            "training_policy": training_policy,
            "training_runs": training_runs[-50:],
            "lineage": lineage,
        },
        temporary,
    )
    temporary.replace(path)


def _prepare_tokenizer(
    args: argparse.Namespace,
    *,
    corpus_path: Path | None,
    inventory: dict,
    policy,
) -> CanriTokenizer:
    tokenizer_path = Path(args.tokenizer)
    if tokenizer_path.exists() and not args.rebuild_tokenizer:
        return CanriTokenizer.load(tokenizer_path)
    texts = (
        _iter_corpus_texts(corpus_path)
        if corpus_path is not None
        else iter_all_data_texts(Path(args.data_root), policy=policy)
    )
    tokenizer = CanriTokenizer.from_texts(
        texts,
        max_vocab_size=max(256, int(args.max_vocab_size)),
    )
    tokenizer.save(
        tokenizer_path,
        metadata={
            "built_from": str(corpus_path) if corpus_path else inventory.get("root"),
            "data_fingerprint": inventory.get("fingerprint"),
            "data_files": inventory.get("files", 0),
            "data_bytes": inventory.get("bytes", 0),
        },
    )
    return tokenizer


def _load_instruction_focus_sources(args: argparse.Namespace) -> set[str] | None:
    explicit = {
        str(source).strip()
        for source in (args.instruction_include_source or [])
        if str(source).strip()
    }
    status_path = args.instruction_focus_status
    if status_path is None:
        return explicit or None
    payload = json.loads(Path(status_path).read_text(encoding="utf-8"))
    metrics = payload.get("held_out_source_metrics", [])
    if not isinstance(metrics, list):
        raise RuntimeError("Instruction focus status has no source metrics.")
    minimum_loss = max(0.0, float(args.instruction_focus_min_loss))
    sources = {
        str(item.get("source"))
        for item in metrics
        if isinstance(item, dict)
        and item.get("source")
        and float(item.get("loss", 0.0)) >= minimum_loss
    }
    sources.update(explicit)
    if not sources:
        raise RuntimeError(
            "Instruction focus status selected no sources at the requested loss threshold."
        )
    return sources


def train(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    data_root = Path(args.data_root).resolve()
    policy = (
        None
        if args.include_all_data
        else load_training_data_policy(Path(args.data_policy))
    )
    corpus_path = Path(args.corpus).resolve() if args.corpus else None
    if args.build_corpus:
        corpus_path = corpus_path or DEFAULT_CORPUS
        build_corpus(
            corpus_path,
            data_root=data_root,
            include_rules=True,
            policy=policy,
        )
    if corpus_path is not None and not corpus_path.is_file():
        raise RuntimeError(f"Training corpus does not exist: {corpus_path}")

    inventory = inventory_data_sources(data_root, policy=policy)
    if corpus_path is None and not inventory["files"]:
        raise RuntimeError(f"No supported training files were found under {data_root}.")

    torch, _ = require_torch()
    if int(args.cpu_threads) > 0:
        torch.set_num_threads(int(args.cpu_threads))
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = _resolve_device(torch, args.device)

    tokenizer = _prepare_tokenizer(
        args,
        corpus_path=corpus_path,
        inventory=inventory,
        policy=policy,
    )
    checkpoint = Path(args.checkpoint)
    resume_payload = None
    if args.resume:
        if not checkpoint.is_file():
            raise RuntimeError(f"Cannot resume; checkpoint does not exist: {checkpoint}")
        resume_payload = _load_torch_checkpoint(torch, checkpoint)
        config = CanriConfig(**resume_payload["config"])
        if config.vocab_size != len(tokenizer):
            raise RuntimeError(
                "Checkpoint and tokenizer vocabularies differ; use the checkpoint's tokenizer "
                "or start a new checkpoint."
            )
    else:
        config = CanriConfig(
            vocab_size=len(tokenizer),
            context_length=max(32, int(args.context_length)),
            embedding_size=max(32, int(args.embedding_size)),
            layers=max(1, int(args.layers)),
            heads=max(1, int(args.heads)),
            dropout=min(0.5, max(0.0, float(args.dropout))),
        )
    if config.embedding_size % config.heads:
        raise RuntimeError("embedding-size must be divisible by heads.")

    model = build_model(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(args.learning_rate),
        weight_decay=max(0.0, float(args.weight_decay)),
    )
    global_step = 0
    starting_epoch = 0
    previous_runs: list[dict] = []
    split_enforced_since_step = 0
    lineage_metadata: dict = {}
    if resume_payload:
        model.load_state_dict(resume_payload["model_state"])
        if isinstance(resume_payload.get("optimizer_state"), dict):
            optimizer.load_state_dict(resume_payload["optimizer_state"])
            _move_optimizer_state(torch, optimizer, device)
        for parameter_group in optimizer.param_groups:
            parameter_group["lr"] = float(args.learning_rate)
            parameter_group["weight_decay"] = max(0.0, float(args.weight_decay))
        global_step = int(resume_payload.get("step", 0))
        starting_epoch = int(resume_payload.get("epoch", 0))
        previous_runs = [
            dict(item)
            for item in resume_payload.get("training_runs", [])
            if isinstance(item, dict)
        ][-49:]
        lineage = resume_payload.get("lineage", {})
        lineage = lineage if isinstance(lineage, dict) else {}
        lineage_metadata = dict(lineage)
        recorded_split_step = lineage.get("instruction_split_enforced_since_step")
        if recorded_split_step is not None:
            split_enforced_since_step = int(recorded_split_step)
        else:
            prior_starting_steps = [
                int(item.get("starting_step", global_step))
                for item in previous_runs
                if item.get("objective") == "instruction"
            ]
            split_enforced_since_step = min(prior_starting_steps, default=global_step)

    batch_size = max(1, int(args.batch_size))
    accumulation = max(1, int(args.gradient_accumulation))
    max_steps = max(0, int(args.max_steps))
    run_steps = 0
    sequences_seen = 0
    last_loss: float | None = None
    last_gradient_norm: float | None = None
    current_learning_rate = float(args.learning_rate)
    skipped_nonfinite_batches = 0
    run_started_utc = datetime.now(timezone.utc).isoformat()
    training_policy = {
        "objective": args.objective,
        "assistant_only_instruction_loss": args.objective == "instruction",
        "instruction_split_version": INSTRUCTION_SPLIT_VERSION,
        "instruction_validation_fraction": float(args.instruction_validation_fraction),
        "instruction_shuffle_buffer": int(args.instruction_shuffle_buffer),
        "instruction_max_per_source": int(args.instruction_max_per_source),
        "instruction_curated_repeats": int(args.instruction_curated_repeats),
        "warmup_steps": int(args.warmup_steps),
        "lr_decay_steps": int(args.lr_decay_steps),
        "minimum_learning_rate": float(args.min_learning_rate),
    }
    instruction_focus_sources = (
        _load_instruction_focus_sources(args)
        if args.objective == "instruction"
        else None
    )
    training_policy["instruction_focus_sources"] = sorted(
        instruction_focus_sources or []
    )
    training_policy["instruction_focus_min_loss"] = float(
        args.instruction_focus_min_loss
    )
    model.train()
    optimizer.zero_grad(set_to_none=True)
    stop_requested = False
    completed_epoch = starting_epoch

    for epoch_offset in range(max(1, int(args.epochs))):
        epoch = starting_epoch + epoch_offset + 1
        completed_epoch = epoch
        windows = (
            iter_instruction_training_windows(
                tokenizer,
                data_root=data_root,
                context_length=config.context_length,
                minimum_quality=float(args.instruction_min_quality),
                max_examples=max(0, int(args.instruction_max_examples)),
                split="train",
                validation_fraction=float(args.instruction_validation_fraction),
                shuffle_buffer=max(0, int(args.instruction_shuffle_buffer)),
                seed=int(args.seed) + epoch,
                max_examples_per_source=max(0, int(args.instruction_max_per_source)),
                curated_repeats=max(1, int(args.instruction_curated_repeats)),
                include_sources=instruction_focus_sources,
            )
            if args.objective == "instruction"
            else _iter_corpus_windows(corpus_path, tokenizer, config.context_length)
            if corpus_path is not None
            else iter_training_windows(
                tokenizer,
                data_root=data_root,
                context_length=config.context_length,
                mode=args.sampling_mode,
                samples_per_source=max(1, int(args.samples_per_source)),
                seed=int(args.seed) + epoch,
                policy=policy,
            )
        )
        pending_batches = 0
        for batch in _batched(windows, batch_size):
            batch_input, batch_target = _prepare_batch(
                torch,
                batch,
                device=device,
                objective=args.objective,
            )
            _, loss = model(batch_input, batch_target)
            if not bool(torch.isfinite(loss).item()):
                skipped_nonfinite_batches += 1
                optimizer.zero_grad(set_to_none=True)
                pending_batches = 0
                continue
            (loss / accumulation).backward()
            pending_batches += 1
            sequences_seen += len(batch)
            last_loss = float(loss.detach().cpu())
            if pending_batches < accumulation:
                continue

            current_learning_rate = _scheduled_learning_rate(
                base_learning_rate=float(args.learning_rate),
                minimum_learning_rate=float(args.min_learning_rate),
                step=global_step + 1,
                warmup_steps=int(args.warmup_steps),
                decay_steps=int(args.lr_decay_steps),
            )
            for parameter_group in optimizer.param_groups:
                parameter_group["lr"] = current_learning_rate
            gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            last_gradient_norm = float(gradient_norm.detach().cpu())
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            pending_batches = 0
            global_step += 1
            run_steps += 1
            if args.log_every and run_steps % max(1, int(args.log_every)) == 0:
                print(
                    json.dumps(
                        {
                            "event": "training_progress",
                            "step": global_step,
                            "run_step": run_steps,
                            "loss": last_loss,
                            "learning_rate": current_learning_rate,
                            "gradient_norm": last_gradient_norm,
                            "sequences": sequences_seen,
                            "device": device,
                        },
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                    flush=True,
                )
            if args.save_every and global_step % max(1, int(args.save_every)) == 0:
                _save_checkpoint(
                    torch,
                    path=checkpoint,
                    model=model,
                    optimizer=optimizer,
                    config=config,
                    step=global_step,
                    epoch=epoch,
                    last_loss=last_loss,
                    tokenizer_path=Path(args.tokenizer),
                    data_info={
                        **inventory,
                        "objective": args.objective,
                        "sampling_mode": args.sampling_mode,
                        "instruction_split_version": INSTRUCTION_SPLIT_VERSION,
                        "corpus": str(corpus_path) if corpus_path else None,
                    },
                    seed=int(args.seed),
                    training_policy=training_policy,
                        training_runs=previous_runs,
                        split_enforced_since_step=split_enforced_since_step,
                        base_lineage=lineage_metadata,
                )
            if max_steps and run_steps >= max_steps:
                stop_requested = True
                break

        if pending_batches and not stop_requested:
            current_learning_rate = _scheduled_learning_rate(
                base_learning_rate=float(args.learning_rate),
                minimum_learning_rate=float(args.min_learning_rate),
                step=global_step + 1,
                warmup_steps=int(args.warmup_steps),
                decay_steps=int(args.lr_decay_steps),
            )
            for parameter_group in optimizer.param_groups:
                parameter_group["lr"] = current_learning_rate
            gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            last_gradient_norm = float(gradient_norm.detach().cpu())
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            global_step += 1
            run_steps += 1
        if stop_requested:
            break

    if run_steps <= 0:
        raise RuntimeError("No training sequences were produced from the selected data.")

    data_info = {
        **inventory,
        "objective": args.objective,
        "sampling_mode": args.sampling_mode,
        "samples_per_source": int(args.samples_per_source),
        "instruction_split_version": INSTRUCTION_SPLIT_VERSION,
        "corpus": str(corpus_path) if corpus_path else None,
    }
    elapsed_seconds = round(time.monotonic() - started, 2)
    current_run = {
        "started_utc": run_started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "objective": args.objective,
        "starting_step": global_step - run_steps,
        "ending_step": global_step,
        "run_steps": run_steps,
        "sequences_seen": sequences_seen,
        "last_loss": last_loss,
        "last_gradient_norm": last_gradient_norm,
        "ending_learning_rate": current_learning_rate,
        "skipped_nonfinite_batches": skipped_nonfinite_batches,
        "elapsed_seconds": elapsed_seconds,
    }
    training_runs = [*previous_runs, current_run]
    _save_checkpoint(
        torch,
        path=checkpoint,
        model=model,
        optimizer=optimizer,
        config=config,
        step=global_step,
        epoch=completed_epoch,
        last_loss=last_loss,
        tokenizer_path=Path(args.tokenizer),
        data_info=data_info,
        seed=int(args.seed),
        training_policy=training_policy,
        training_runs=training_runs,
        split_enforced_since_step=split_enforced_since_step,
        base_lineage=lineage_metadata,
    )
    return {
        "checkpoint": str(checkpoint),
        "checkpoint_bytes": checkpoint.stat().st_size,
        "tokenizer": str(args.tokenizer),
        "vocabulary_size": len(tokenizer),
        "tokenizer_mode": tokenizer.mode,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "device": device,
        "resumed": bool(resume_payload),
        "global_steps": global_step,
        "run_steps": run_steps,
        "sequences_seen": sequences_seen,
        "last_loss": last_loss,
        "last_gradient_norm": last_gradient_norm,
        "ending_learning_rate": current_learning_rate,
        "skipped_nonfinite_batches": skipped_nonfinite_batches,
        "elapsed_seconds": elapsed_seconds,
        "trained_from_random_initialization": True,
        "downloaded_base_model": False,
        "data": data_info,
        "config": config.to_dict(),
    }


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = train(args)
    except (RuntimeError, OSError, ValueError, sqlite3.DatabaseError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
