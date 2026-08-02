"""A small causal Transformer initialized and trained by CANRI itself.

PyTorch is intentionally imported lazily. Dataset and tokenizer preparation
remain usable on machines that do not yet have a training runtime installed.
"""

from __future__ import annotations

import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_DLL_DIRECTORY_HANDLES: list[Any] = []
_REQUIRED_MSVC_FILES = ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")


@dataclass
class CanriConfig:
    vocab_size: int
    context_length: int = 256
    embedding_size: int = 256
    layers: int = 6
    heads: int = 8
    dropout: float = 0.1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _version_key(path: Path) -> tuple[int, ...]:
    values = [int(item) for item in re.findall(r"\d+", path.name)]
    return tuple(values) if values else (0,)


def _is_x64_pe(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            handle.seek(0x3C)
            pe_offset = struct.unpack("<I", handle.read(4))[0]
            handle.seek(pe_offset + 4)
            return struct.unpack("<H", handle.read(2))[0] == 0x8664
    except (OSError, struct.error):
        return False


def prepare_windows_runtime() -> str | None:
    """Add a compatible Microsoft app-local C++ runtime when Windows is old.

    Python's current runtime can be newer than the system-wide MSVC runtime.
    On affected Windows installations PyTorch then fails while loading c10.dll.
    We first honor an explicit local directory and otherwise inspect Microsoft
    Edge's signed app-local runtime directories. No system files are modified.
    """

    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return None
    candidates: list[Path] = []
    configured = os.environ.get("CANRI_MSVC_RUNTIME", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    roots = (
        program_files_x86 / "Microsoft" / "EdgeCore",
        program_files_x86 / "Microsoft" / "Edge" / "Application",
        program_files_x86 / "Microsoft" / "EdgeWebView" / "Application",
    )
    for root in roots:
        if root.is_dir():
            candidates.extend(path for path in root.iterdir() if path.is_dir())
    valid = [
        path
        for path in candidates
        if all((path / name).is_file() for name in _REQUIRED_MSVC_FILES)
        and _is_x64_pe(path / "msvcp140.dll")
    ]
    if not valid:
        return None
    selected = max(valid, key=_version_key)
    handle = os.add_dll_directory(str(selected))
    _DLL_DIRECTORY_HANDLES.append(handle)
    return str(selected)


def require_torch():
    runtime_path = prepare_windows_runtime()
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError(
            "Training CANRI from scratch requires PyTorch. "
            "Install a matching CPU or CUDA build, then run train.py again."
        ) from error
    except OSError as error:
        runtime_note = f" Runtime directory tried: {runtime_path}." if runtime_path else ""
        raise RuntimeError(
            "PyTorch is installed but its native libraries could not be loaded. "
            "Install the latest Microsoft Visual C++ x64 Redistributable."
            + runtime_note
        ) from error
    return torch, nn


def build_model(config: CanriConfig):
    torch, nn = require_torch()

    class CausalTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.config = config
            self.token_embedding = nn.Embedding(config.vocab_size, config.embedding_size)
            self.position_embedding = nn.Embedding(config.context_length, config.embedding_size)
            layer = nn.TransformerEncoderLayer(
                d_model=config.embedding_size,
                nhead=config.heads,
                dim_feedforward=config.embedding_size * 4,
                dropout=config.dropout,
                activation="gelu",
                batch_first=True,
                norm_first=True,
            )
            self.blocks = nn.TransformerEncoder(
                layer,
                num_layers=config.layers,
                enable_nested_tensor=False,
            )
            self.norm = nn.LayerNorm(config.embedding_size)
            self.output = nn.Linear(config.embedding_size, config.vocab_size, bias=False)
            self.output.weight = self.token_embedding.weight
            self.register_buffer(
                "causal_mask",
                torch.triu(
                    torch.ones(config.context_length, config.context_length, dtype=torch.bool),
                    diagonal=1,
                ),
                persistent=False,
            )
            self.apply(self._initialize_weights)

        @staticmethod
        def _initialize_weights(module):
            if isinstance(module, (nn.Linear, nn.Embedding)):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if isinstance(module, nn.Linear) and module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

        def forward(self, input_ids, targets=None):
            sequence_length = input_ids.shape[1]
            if sequence_length > config.context_length:
                raise ValueError("Input is longer than the configured context length.")
            positions = torch.arange(sequence_length, device=input_ids.device)
            hidden = self.token_embedding(input_ids) + self.position_embedding(positions)
            mask = self.causal_mask[:sequence_length, :sequence_length]
            hidden = self.blocks(hidden, mask=mask)
            logits = self.output(self.norm(hidden))
            loss = None
            if targets is not None:
                loss = nn.functional.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    targets.reshape(-1),
                    ignore_index=-100,
                )
            return logits, loss

    return CausalTransformer()
