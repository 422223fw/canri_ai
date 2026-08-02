"""Dependency-free hybrid tokenizer for CANRI's native language model.

The tokenizer keeps every frequent Unicode character as a fallback and also
learns common words and identifiers from CANRI's data. This is materially more
efficient than the original character-only tokenizer while preserving Hebrew,
English, punctuation, JSON, and source code without an external model.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


SPECIAL_TOKENS = ("<pad>", "<unk>", "<bos>", "<eos>")
INSTRUCTION_TOKENS = ("<|user|>", "<|assistant|>", "<|end|>")
COMMON_WHITESPACE_TOKENS = (" ", "\n", "\t", "\r\n")
TOKEN_PATTERN = re.compile(
    r"<\|(?:user|assistant|end)\|>|\s+|\w+|[^\w\s]",
    re.UNICODE,
)
BYTE_TOKEN_PATTERN = re.compile(r"^<0x([0-9A-F]{2})>$")
CHARACTER_MODE = "character_v1"
HYBRID_MODE = "hybrid_word_character_v2"
BYTE_HYBRID_MODE = "hybrid_word_byte_v3"


def _byte_token(value: int) -> str:
    return f"<0x{int(value):02X}>"


class CanriTokenizer:
    def __init__(
        self,
        vocabulary: list[str] | None = None,
        *,
        mode: str = CHARACTER_MODE,
        metadata: dict | None = None,
    ) -> None:
        vocabulary = vocabulary or list(SPECIAL_TOKENS)
        self.vocabulary = list(dict.fromkeys(str(item) for item in vocabulary))
        for token in SPECIAL_TOKENS:
            if token not in self.vocabulary:
                self.vocabulary.insert(0, token)
        self.token_to_id = {token: index for index, token in enumerate(self.vocabulary)}
        self.pad_id = self.token_to_id["<pad>"]
        self.unk_id = self.token_to_id["<unk>"]
        self.bos_id = self.token_to_id["<bos>"]
        self.eos_id = self.token_to_id["<eos>"]
        self.mode = (
            mode
            if mode in {CHARACTER_MODE, HYBRID_MODE, BYTE_HYBRID_MODE}
            else CHARACTER_MODE
        )
        self.metadata = dict(metadata or {})
        self.byte_token_ids = {
            value: self.token_to_id.get(_byte_token(value)) for value in range(256)
        }

    @classmethod
    def from_text(cls, text: str, max_vocab_size: int = 4096) -> "CanriTokenizer":
        return cls.from_texts([str(text or "")], max_vocab_size=max_vocab_size)

    @classmethod
    def from_texts(
        cls,
        texts: Iterable[str],
        max_vocab_size: int = 4096,
    ) -> "CanriTokenizer":
        character_counts: Counter[str] = Counter()
        lexical_counts: Counter[str] = Counter()
        max_vocab_size = max(256, int(max_vocab_size))
        max_candidates = max(50_000, max_vocab_size * 16)
        tokens_since_prune = 0
        for text in texts:
            value = str(text or "")
            character_counts.update(value)
            for match in TOKEN_PATTERN.finditer(value):
                token = match.group(0)
                if 1 < len(token) <= 64 and not token.isspace():
                    lexical_counts[token] += 1
                tokens_since_prune += 1
            if tokens_since_prune >= 500_000:
                tokens_since_prune = 0
                if len(lexical_counts) > max_candidates:
                    lexical_counts = Counter(
                        dict(lexical_counts.most_common(max_candidates // 2))
                    )

        capacity = max_vocab_size - len(SPECIAL_TOKENS)
        characters = [item for item, _ in character_counts.most_common(capacity)]
        remaining = max(0, capacity - len(characters))
        lexical = [
            item
            for item, _ in lexical_counts.most_common(max_candidates)
            if item not in character_counts
        ][:remaining]
        return cls(
            list(SPECIAL_TOKENS) + characters + lexical,
            mode=HYBRID_MODE,
            metadata={
                "unique_characters": len(character_counts),
                "lexical_candidates": len(lexical_counts),
            },
        )

    @classmethod
    def expanded_from_texts(
        cls,
        base: "CanriTokenizer",
        texts: Iterable[str],
        *,
        max_vocab_size: int,
    ) -> "CanriTokenizer":
        """Preserve every existing token id and append useful new tokens.

        Stable token ids are required for transferring embedding rows from an
        older checkpoint. Rebuilding and re-sorting the vocabulary would attach
        learned vectors to unrelated words.
        """

        target_size = max(len(base), int(max_vocab_size))
        if target_size == len(base):
            return cls(
                list(base.vocabulary),
                mode=base.mode,
                metadata={**base.metadata, "expanded_from_size": len(base)},
            )
        candidates = cls.from_texts(
            texts,
            max_vocab_size=max(target_size * 2, target_size + 1024),
        )
        vocabulary = list(base.vocabulary)
        known = set(vocabulary)
        for token in candidates.vocabulary:
            if token in known:
                continue
            vocabulary.append(token)
            known.add(token)
            if len(vocabulary) >= target_size:
                break
        return cls(
            vocabulary,
            mode=HYBRID_MODE,
            metadata={
                **base.metadata,
                "expanded_from_size": len(base),
                "requested_vocab_size": target_size,
                "candidate_unique_characters": candidates.metadata.get(
                    "unique_characters", 0
                ),
                "candidate_lexical_tokens": candidates.metadata.get(
                    "lexical_candidates", 0
                ),
            },
        )

    @classmethod
    def from_byte_fallback_texts(
        cls,
        texts: Iterable[str],
        *,
        max_vocab_size: int = 8192,
    ) -> "CanriTokenizer":
        """Build a compact lexical vocabulary with lossless UTF-8 fallback.

        The previous hybrid tokenizer reserved one vocabulary row for every
        observed Unicode character. Large web corpora contain thousands of
        rare symbols, leaving too few rows for useful words and identifiers.
        This version reserves 256 byte tokens instead, so arbitrary English,
        Hebrew, source code, and punctuation remain lossless while most of the
        vocabulary can represent frequent lexical units.
        """

        fixed = [
            *SPECIAL_TOKENS,
            *INSTRUCTION_TOKENS,
            *COMMON_WHITESPACE_TOKENS,
            *(_byte_token(value) for value in range(256)),
        ]
        minimum_size = len(dict.fromkeys(fixed)) + 64
        max_vocab_size = max(minimum_size, int(max_vocab_size))
        lexical_counts: Counter[str] = Counter()
        max_candidates = max(50_000, max_vocab_size * 16)
        tokens_since_prune = 0
        observed_bytes = 0
        for text in texts:
            value = str(text or "")
            observed_bytes += len(value.encode("utf-8", errors="replace"))
            for match in TOKEN_PATTERN.finditer(value):
                token = match.group(0)
                if (
                    1 < len(token) <= 96
                    and not token.isspace()
                    and token not in INSTRUCTION_TOKENS
                ):
                    lexical_counts[token] += 1
                tokens_since_prune += 1
            if tokens_since_prune >= 500_000:
                tokens_since_prune = 0
                if len(lexical_counts) > max_candidates:
                    lexical_counts = Counter(
                        dict(lexical_counts.most_common(max_candidates // 2))
                    )

        vocabulary = list(dict.fromkeys(fixed))
        known = set(vocabulary)
        for token, _ in lexical_counts.most_common(max_candidates):
            if token in known:
                continue
            vocabulary.append(token)
            known.add(token)
            if len(vocabulary) >= max_vocab_size:
                break
        return cls(
            vocabulary,
            mode=BYTE_HYBRID_MODE,
            metadata={
                "byte_fallback": True,
                "byte_tokens": 256,
                "lexical_candidates": len(lexical_counts),
                "lexical_tokens": max(0, len(vocabulary) - len(dict.fromkeys(fixed))),
                "observed_utf8_bytes": observed_bytes,
            },
        )

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        value = str(text or "")
        if self.mode == CHARACTER_MODE:
            values = [self.token_to_id.get(character, self.unk_id) for character in value]
        else:
            values = []
            for match in TOKEN_PATTERN.finditer(value):
                token = match.group(0)
                token_id = self.token_to_id.get(token)
                if token_id is not None:
                    values.append(token_id)
                elif self.mode == BYTE_HYBRID_MODE:
                    for byte in token.encode("utf-8", errors="replace"):
                        byte_id = self.byte_token_ids.get(byte)
                        values.append(byte_id if byte_id is not None else self.unk_id)
                else:
                    values.extend(
                        self.token_to_id.get(character, self.unk_id)
                        for character in token
                    )
        if add_special_tokens:
            return [self.bos_id, *values, self.eos_id]
        return values

    def decode(self, token_ids: Iterable[int], skip_special_tokens: bool = True) -> str:
        special = set(SPECIAL_TOKENS)
        output: list[str] = []
        buffered_bytes = bytearray()

        def flush_bytes() -> None:
            if not buffered_bytes:
                return
            output.append(buffered_bytes.decode("utf-8", errors="replace"))
            buffered_bytes.clear()

        for token_id in token_ids:
            index = int(token_id)
            if index < 0 or index >= len(self.vocabulary):
                token = "<unk>"
            else:
                token = self.vocabulary[index]
            if skip_special_tokens and token in special:
                continue
            if self.mode == BYTE_HYBRID_MODE:
                match = BYTE_TOKEN_PATTERN.match(token)
                if match:
                    buffered_bytes.append(int(match.group(1), 16))
                    continue
                flush_bytes()
            output.append("?" if token == "<unk>" else token)
        flush_bytes()
        return "".join(output)

    def save(self, path: str | Path, metadata: dict | None = None) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        combined_metadata = {**self.metadata, **dict(metadata or {})}
        destination.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "mode": self.mode,
                    "vocabulary": self.vocabulary,
                    "metadata": combined_metadata,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "CanriTokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("vocabulary"), list):
            raise ValueError("Invalid CANRI tokenizer file.")
        return cls(
            payload["vocabulary"],
            mode=str(payload.get("mode") or CHARACTER_MODE),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )

    def __len__(self) -> int:
        return len(self.vocabulary)
