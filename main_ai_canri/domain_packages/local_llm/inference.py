"""Inference for the native CANRI checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from .model.transformer import CanriConfig, build_model, require_torch
from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "checkpoints" / "canri_native.pt"
DEFAULT_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer.json"


@dataclass
class _LoadedRuntime:
    model: Any
    tokenizer: CanriTokenizer
    config: CanriConfig
    torch: Any
    device: str
    lexical_token_ids: tuple[int, ...]
    lexical_token_id_set: frozenset[int]
    byte_id_to_value: dict[int, int]
    utf8_continuation_ids: tuple[int, ...]
    invalid_utf8_start_ids: tuple[int, ...]
    user_marker_id: int | None
    assistant_marker_id: int | None
    end_marker_id: int | None


_RUNTIME_CACHE: dict[tuple[str, int, str, int, str], _LoadedRuntime] = {}
_RUNTIME_LOCK = RLock()


def clear_runtime_cache() -> None:
    with _RUNTIME_LOCK:
        _RUNTIME_CACHE.clear()


def _resolve_device(torch, requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA inference was requested, but CUDA is unavailable.")
    return requested


def _load_runtime(
    checkpoint_path: Path,
    tokenizer_path: Path,
    device: str,
) -> _LoadedRuntime:
    torch, _ = require_torch()
    selected_device = _resolve_device(torch, device)
    checkpoint_mtime = checkpoint_path.stat().st_mtime_ns
    tokenizer_mtime = tokenizer_path.stat().st_mtime_ns
    key = (
        str(checkpoint_path.resolve()),
        checkpoint_mtime,
        str(tokenizer_path.resolve()),
        tokenizer_mtime,
        selected_device,
    )
    with _RUNTIME_LOCK:
        cached = _RUNTIME_CACHE.get(key)
        if cached is not None:
            return cached
        tokenizer = CanriTokenizer.load(tokenizer_path)
        try:
            payload: dict[str, Any] = torch.load(
                checkpoint_path,
                map_location="cpu",
                weights_only=False,
            )
        except TypeError:
            payload = torch.load(checkpoint_path, map_location="cpu")
        config = CanriConfig(**payload["config"])
        model = build_model(config).to(selected_device)
        model.load_state_dict(payload["model_state"])
        model.eval()
        lexical_token_ids = tuple(
            index
            for index, token in enumerate(tokenizer.vocabulary)
            if len(token) > 1
            and not token.startswith("<")
            and any(character.isalnum() or character == "_" for character in token)
        )
        runtime = _LoadedRuntime(
            model=model,
            tokenizer=tokenizer,
            config=config,
            torch=torch,
            device=selected_device,
            lexical_token_ids=lexical_token_ids,
            lexical_token_id_set=frozenset(lexical_token_ids),
            byte_id_to_value={
                int(token_id): int(value)
                for value, token_id in tokenizer.byte_token_ids.items()
                if token_id is not None
            },
            utf8_continuation_ids=tuple(
                int(tokenizer.byte_token_ids[value])
                for value in range(0x80, 0xC0)
                if tokenizer.byte_token_ids.get(value) is not None
            ),
            invalid_utf8_start_ids=tuple(
                int(tokenizer.byte_token_ids[value])
                for value in (
                    *range(0x80, 0xC2),
                    0xE0,
                    0xED,
                    0xF0,
                    0xF4,
                    *range(0xF5, 0x100),
                )
                if tokenizer.byte_token_ids.get(value) is not None
            ),
            user_marker_id=tokenizer.token_to_id.get("<|user|>"),
            assistant_marker_id=tokenizer.token_to_id.get("<|assistant|>"),
            end_marker_id=tokenizer.token_to_id.get("<|end|>"),
        )
        _RUNTIME_CACHE.clear()
        _RUNTIME_CACHE[key] = runtime
        return runtime


def _fit_prompt(token_ids: list[int], context_length: int) -> list[int]:
    if len(token_ids) <= context_length:
        return token_ids
    head_size = max(8, context_length * 3 // 5)
    tail_size = context_length - head_size
    return token_ids[:head_size] + token_ids[-tail_size:]


def _blocked_ngram_tokens(generated: list[int], size: int) -> set[int]:
    ngram_size = max(0, int(size))
    if ngram_size < 2 or len(generated) < ngram_size - 1:
        return set()
    prefix = tuple(generated[-(ngram_size - 1):])
    blocked = set()
    for index in range(len(generated) - ngram_size + 1):
        if tuple(generated[index:index + ngram_size - 1]) == prefix:
            blocked.add(generated[index + ngram_size - 1])
    return blocked


def _utf8_continuations_for_start(value: int) -> int:
    if 0x00 <= value <= 0x7F:
        return 0
    if 0xC2 <= value <= 0xDF:
        return 1
    if 0xE0 <= value <= 0xEF:
        return 2
    if 0xF0 <= value <= 0xF4:
        return 3
    return -1


def _constrain_utf8_logits(runtime: _LoadedRuntime, logits, pending: int):
    if not runtime.byte_id_to_value:
        return logits
    if pending > 0:
        constrained = runtime.torch.full_like(logits, float("-inf"))
        allowed = list(runtime.utf8_continuation_ids)
        constrained[:, allowed] = logits[:, allowed]
        return constrained
    if runtime.invalid_utf8_start_ids:
        logits[:, list(runtime.invalid_utf8_start_ids)] = float("-inf")
    return logits


def generate_text(
    prompt: str,
    *,
    checkpoint: str | Path = DEFAULT_CHECKPOINT,
    tokenizer_path: str | Path = DEFAULT_TOKENIZER,
    max_new_tokens: int = 256,
    temperature: float = 0.7,
    top_k: int = 40,
    top_p: float = 0.92,
    repetition_penalty: float = 1.08,
    no_repeat_ngram_size: int = 4,
    min_new_tokens: int = 4,
    lexical_token_bias: float = 0.35,
    device: str = "auto",
    seed: int | None = None,
    instruction_format: bool = True,
) -> str:
    checkpoint_path = Path(checkpoint)
    if not checkpoint_path.is_file():
        raise RuntimeError("No native CANRI checkpoint exists. Run train.py first.")
    tokenizer_file = Path(tokenizer_path)
    if not tokenizer_file.is_file():
        raise RuntimeError("The native CANRI tokenizer does not exist.")
    runtime = _load_runtime(checkpoint_path, tokenizer_file, device)
    torch = runtime.torch
    tokenizer = runtime.tokenizer
    config = runtime.config
    selected_device = runtime.device
    model = runtime.model
    if seed is not None:
        torch.manual_seed(int(seed))
    model_prompt = str(prompt or "")
    if instruction_format and "<|assistant|>" not in model_prompt:
        model_prompt = f"<|user|>\n{model_prompt.strip()}\n<|assistant|>\n"
    token_ids = tokenizer.encode(model_prompt, add_special_tokens=False)
    if not token_ids:
        token_ids = [tokenizer.bos_id]
    token_ids = _fit_prompt(token_ids, config.context_length)
    input_ids = torch.tensor(
        [token_ids],
        dtype=torch.long,
        device=selected_device,
    )
    generated: list[int] = []
    pending_utf8 = 0
    pending_utf8_start: int | None = None
    with torch.inference_mode():
        for token_index in range(max(1, int(max_new_tokens))):
            logits, _ = model(input_ids[:, -config.context_length:])
            next_logits = logits[:, -1, :].clone()
            for token_id in set(generated[-64:]):
                if token_id not in runtime.lexical_token_id_set:
                    continue
                value = next_logits[0, token_id]
                next_logits[0, token_id] = (
                    value * max(1.0, float(repetition_penalty))
                    if value < 0
                    else value / max(1.0, float(repetition_penalty))
                )
            next_logits[:, tokenizer.pad_id] = float("-inf")
            next_logits[:, tokenizer.bos_id] = float("-inf")
            for marker_id in (runtime.user_marker_id, runtime.assistant_marker_id):
                if marker_id is not None:
                    next_logits[:, marker_id] = float("-inf")
            if runtime.lexical_token_ids and float(lexical_token_bias):
                next_logits[:, list(runtime.lexical_token_ids)] += float(lexical_token_bias)
            if token_index < max(0, int(min_new_tokens)) or pending_utf8 > 0:
                next_logits[:, tokenizer.eos_id] = float("-inf")
                if runtime.end_marker_id is not None:
                    next_logits[:, runtime.end_marker_id] = float("-inf")
            next_logits = _constrain_utf8_logits(runtime, next_logits, pending_utf8)
            for token_id in _blocked_ngram_tokens(generated, no_repeat_ngram_size):
                next_logits[:, token_id] = float("-inf")
            effective_temperature = float(temperature)
            if effective_temperature <= 0:
                next_id = torch.argmax(next_logits, dim=-1, keepdim=True)
                input_ids = torch.cat([input_ids, next_id], dim=1)
                selected_id = int(next_id.item())
                if selected_id == tokenizer.eos_id:
                    break
                generated.append(selected_id)
                byte_value = runtime.byte_id_to_value.get(selected_id)
                if byte_value is not None:
                    if pending_utf8 > 0:
                        pending_utf8 -= 1
                    else:
                        pending_utf8 = _utf8_continuations_for_start(byte_value)
                        pending_utf8_start = (
                            len(generated) - 1 if pending_utf8 > 0 else None
                        )
                    if pending_utf8 == 0:
                        pending_utf8_start = None
                continue
            next_logits = next_logits / max(effective_temperature, 0.05)
            effective_top_k = min(max(0, int(top_k)), next_logits.shape[-1])
            if effective_top_k:
                threshold = torch.topk(next_logits, effective_top_k).values[:, -1:]
                next_logits = next_logits.masked_fill(next_logits < threshold, float("-inf"))
            probabilities = torch.softmax(next_logits, dim=-1)
            nucleus = min(1.0, max(0.0, float(top_p)))
            if 0.0 < nucleus < 1.0:
                sorted_probabilities, sorted_indices = torch.sort(
                    probabilities, descending=True
                )
                cumulative = torch.cumsum(sorted_probabilities, dim=-1)
                remove = cumulative - sorted_probabilities > nucleus
                sorted_probabilities = sorted_probabilities.masked_fill(remove, 0.0)
                sorted_probabilities /= sorted_probabilities.sum(
                    dim=-1, keepdim=True
                ).clamp_min(1e-12)
                sampled = torch.multinomial(sorted_probabilities, num_samples=1)
                next_id = sorted_indices.gather(-1, sampled)
            else:
                next_id = torch.multinomial(probabilities, num_samples=1)
            input_ids = torch.cat([input_ids, next_id], dim=1)
            selected_id = int(next_id.item())
            if selected_id == tokenizer.eos_id:
                break
            generated.append(selected_id)
            byte_value = runtime.byte_id_to_value.get(selected_id)
            if byte_value is not None:
                if pending_utf8 > 0:
                    pending_utf8 -= 1
                else:
                    pending_utf8 = _utf8_continuations_for_start(byte_value)
                    pending_utf8_start = len(generated) - 1 if pending_utf8 > 0 else None
                if pending_utf8 == 0:
                    pending_utf8_start = None
    if pending_utf8 > 0 and pending_utf8_start is not None:
        generated = generated[:pending_utf8_start]
    result = tokenizer.decode(generated)
    for marker in ("<|end|>", "<|user|>", "<|assistant|>"):
        if marker in result:
            result = result.split(marker, 1)[0]
    return result.strip()
