"""Streaming access to every usable record in CANRI's local data directory.

The training path intentionally avoids building a second multi-hundred-MB
corpus or materializing every token window in RAM. JSON and JSONL files are
read in chunks, while SQLite databases are opened read-only and traversed in
batches.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from collections import deque
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterable, Iterator

from .tokenizer import CanriTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
CANRI_ROOT = PACKAGE_ROOT.parents[1]
DATA_ROOT = CANRI_ROOT / "data"
DEFAULT_CORPUS = PACKAGE_ROOT / "data" / "canri_training_corpus.txt"
DEFAULT_TOKENIZER = PACKAGE_ROOT / "data" / "canri_tokenizer.json"
DEFAULT_TRAINING_POLICY = PACKAGE_ROOT / "training_data_policy.json"
TEXT_SUFFIXES = {".json", ".jsonl", ".txt", ".md", ".csv"}
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


@dataclass(frozen=True)
class DataSource:
    path: Path
    relative_name: str
    kind: str
    size_bytes: int


@dataclass(frozen=True)
class TrainingDataPolicy:
    name: str
    include_globs: tuple[str, ...]
    exclude_globs: tuple[str, ...]
    source_path: str = ""

    def accepts(self, relative_name: str) -> bool:
        normalized = str(relative_name).replace("\\", "/").casefold()
        included = not self.include_globs or any(
            fnmatchcase(normalized, pattern.casefold())
            for pattern in self.include_globs
        )
        excluded = any(
            fnmatchcase(normalized, pattern.casefold())
            for pattern in self.exclude_globs
        )
        return included and not excluded


def load_training_data_policy(
    path: str | Path = DEFAULT_TRAINING_POLICY,
) -> TrainingDataPolicy:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Training data policy must be a JSON object.")
    include = payload.get("include_globs", [])
    exclude = payload.get("exclude_globs", [])
    if not isinstance(include, list) or not isinstance(exclude, list):
        raise ValueError("Training data policy globs must be arrays.")
    return TrainingDataPolicy(
        name=str(payload.get("name") or source.stem),
        include_globs=tuple(str(item) for item in include if str(item).strip()),
        exclude_globs=tuple(str(item) for item in exclude if str(item).strip()),
        source_path=str(source.resolve()),
    )


def iter_data_sources(
    data_root: Path = DATA_ROOT,
    *,
    policy: TrainingDataPolicy | None = None,
) -> Iterator[DataSource]:
    root = Path(data_root).resolve()
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        suffix = path.suffix.casefold()
        if suffix in TEXT_SUFFIXES:
            kind = suffix.lstrip(".") or "text"
        elif suffix in SQLITE_SUFFIXES:
            kind = "sqlite"
        else:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        relative_name = path.relative_to(root).as_posix()
        if policy is not None and not policy.accepts(relative_name):
            continue
        yield DataSource(
            path=path,
            relative_name=relative_name,
            kind=kind,
            size_bytes=size,
        )


def inventory_data_sources(
    data_root: Path = DATA_ROOT,
    *,
    policy: TrainingDataPolicy | None = None,
) -> dict:
    all_sources = list(iter_data_sources(data_root))
    sources = (
        [source for source in all_sources if policy.accepts(source.relative_name)]
        if policy is not None
        else all_sources
    )
    by_kind: dict[str, dict[str, int]] = {}
    fingerprint = hashlib.sha256()
    for source in sources:
        group = by_kind.setdefault(source.kind, {"files": 0, "bytes": 0})
        group["files"] += 1
        group["bytes"] += source.size_bytes
        fingerprint.update(
            f"{source.relative_name}\0{source.size_bytes}\0".encode("utf-8", errors="replace")
        )
    return {
        "root": str(Path(data_root).resolve()),
        "files": len(sources),
        "bytes": sum(source.size_bytes for source in sources),
        "by_kind": by_kind,
        "fingerprint": fingerprint.hexdigest(),
        "excluded_files": len(all_sources) - len(sources),
        "excluded_bytes": sum(source.size_bytes for source in all_sources)
        - sum(source.size_bytes for source in sources),
        "policy": {
            "name": policy.name,
            "source": policy.source_path,
        }
        if policy is not None
        else None,
    }


def _source_marker(source: DataSource, section: str = "") -> str:
    suffix = f":{section}" if section else ""
    return f"\n<source:{source.relative_name}{suffix}>\n"


def _iter_text_chunks(source: DataSource, chunk_chars: int) -> Iterator[str]:
    yield _source_marker(source)
    with source.path.open("r", encoding="utf-8", errors="replace") as handle:
        while True:
            chunk = handle.read(chunk_chars)
            if not chunk:
                break
            yield chunk
    yield "\n</source>\n"


def _quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _iter_sqlite_chunks(source: DataSource, chunk_chars: int) -> Iterator[str]:
    connection = sqlite3.connect(f"{source.path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            quoted = _quote_identifier(table)
            columns = [
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({quoted})")
            ]
            yield _source_marker(source, table)
            cursor = connection.execute(f"SELECT * FROM {quoted}")
            buffer: list[str] = []
            buffered_chars = 0
            while True:
                rows = cursor.fetchmany(100)
                if not rows:
                    break
                for row in rows:
                    record = dict(zip(columns, row)) if columns else {"values": list(row)}
                    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
                    buffer.append(line)
                    buffered_chars += len(line)
                    if buffered_chars >= chunk_chars:
                        yield "".join(buffer)
                        buffer.clear()
                        buffered_chars = 0
            if buffer:
                yield "".join(buffer)
            yield "\n</source>\n"
    finally:
        connection.close()


def iter_source_texts(
    source: DataSource,
    *,
    chunk_chars: int = 1_048_576,
) -> Iterator[str]:
    chunk_chars = max(4_096, int(chunk_chars))
    try:
        if source.kind == "sqlite":
            yield from _iter_sqlite_chunks(source, chunk_chars)
        else:
            yield from _iter_text_chunks(source, chunk_chars)
    except (OSError, UnicodeError, sqlite3.DatabaseError):
        return


def iter_all_data_texts(
    data_root: Path = DATA_ROOT,
    *,
    chunk_chars: int = 1_048_576,
    policy: TrainingDataPolicy | None = None,
) -> Iterator[str]:
    """Yield all readable JSON, JSONL, text, and SQLite content."""

    for source in iter_data_sources(data_root, policy=policy):
        yield from iter_source_texts(source, chunk_chars=chunk_chars)


def iter_data_texts(
    data_root: Path = DATA_ROOT,
    max_file_chars: int = 2_000_000,
    include_rules: bool = False,
    policy: TrainingDataPolicy | None = None,
) -> Iterable[str]:
    """Compatibility iterator for callers that still need bounded excerpts."""

    for source in iter_data_sources(data_root, policy=policy):
        if not include_rules and "rule" in source.relative_name.casefold():
            continue
        remaining = max(0, int(max_file_chars))
        chunks: list[str] = []
        for text in iter_source_texts(source, chunk_chars=min(remaining or 4_096, 1_048_576)):
            if remaining <= 0:
                break
            chunks.append(text[:remaining])
            remaining -= min(len(text), remaining)
        combined = "".join(chunks)
        if combined.strip():
            yield combined


def build_corpus(
    output_path: Path = DEFAULT_CORPUS,
    *,
    max_total_chars: int = 25_000_000,
    data_root: Path = DATA_ROOT,
    include_rules: bool = True,
    policy: TrainingDataPolicy | None = None,
) -> dict:
    """Build a legacy bounded corpus; streaming training does not require it."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    files = 0
    with output_path.open("w", encoding="utf-8") as output:
        for source in iter_data_sources(data_root, policy=policy):
            if not include_rules and "rule" in source.relative_name.casefold():
                continue
            source_written = False
            for text in iter_source_texts(source):
                remaining = max_total_chars - written
                if remaining <= 0:
                    break
                value = text[:remaining]
                output.write(value)
                written += len(value)
                source_written = source_written or bool(value)
            files += int(source_written)
            if written >= max_total_chars:
                break
    return {
        "output": str(output_path),
        "files_read": files,
        "characters": written,
        "max_total_characters": max_total_chars,
    }


def _windows_from_chunks(
    chunks: Iterable[str],
    tokenizer: CanriTokenizer,
    context_length: int,
    stride: int,
) -> Iterator[list[int]]:
    buffer: list[int] = []
    for text in chunks:
        buffer.extend(tokenizer.encode(text, add_special_tokens=False))
        cursor = 0
        while len(buffer) - cursor >= context_length + 1:
            yield buffer[cursor:cursor + context_length + 1]
            cursor += stride
        if cursor:
            buffer = buffer[cursor:]


def iter_full_token_windows(
    tokenizer: CanriTokenizer,
    *,
    data_root: Path = DATA_ROOT,
    context_length: int = 256,
    stride: int | None = None,
    shuffle_sources: bool = True,
    seed: int = 42,
    policy: TrainingDataPolicy | None = None,
) -> Iterator[list[int]]:
    """Stream every token window without retaining the dataset in memory."""

    context_length = max(32, int(context_length))
    stride = max(1, int(stride or context_length))
    sources = list(iter_data_sources(data_root, policy=policy))
    if shuffle_sources:
        random.Random(seed).shuffle(sources)
    for source in sources:
        yield from _windows_from_chunks(
            iter_source_texts(source),
            tokenizer,
            context_length,
            stride,
        )


def _iter_balanced_source_samples(
    source: DataSource,
    *,
    samples: int,
    sample_bytes: int,
) -> Iterator[str]:
    if source.kind == "sqlite":
        buffered = ""
        for chunk in iter_source_texts(source, chunk_chars=sample_bytes):
            buffered += chunk
            while len(buffered) >= sample_bytes:
                yield buffered[:sample_bytes]
                buffered = buffered[sample_bytes:]
                samples -= 1
                if samples <= 0:
                    return
        if buffered and samples > 0:
            yield buffered
        return

    sample_bytes = max(4_096, int(sample_bytes))
    maximum_offset = max(0, source.size_bytes - sample_bytes)
    offsets = [0] if samples <= 1 else [
        int(maximum_offset * index / (samples - 1))
        for index in range(samples)
    ]
    with source.path.open("rb") as handle:
        for index, offset in enumerate(offsets, start=1):
            handle.seek(offset)
            raw = handle.read(sample_bytes)
            if raw:
                yield _source_marker(source, f"sample-{index}") + raw.decode(
                    "utf-8", errors="replace"
                )


def iter_balanced_token_windows(
    tokenizer: CanriTokenizer,
    *,
    data_root: Path = DATA_ROOT,
    context_length: int = 256,
    samples_per_source: int = 4,
    shuffle_sources: bool = True,
    seed: int = 42,
    policy: TrainingDataPolicy | None = None,
) -> Iterator[list[int]]:
    """Yield stratified windows across every data file for short training runs."""

    context_length = max(32, int(context_length))
    samples_per_source = max(1, int(samples_per_source))
    sources = list(iter_data_sources(data_root, policy=policy))
    if shuffle_sources:
        random.Random(seed).shuffle(sources)
    sample_bytes = max(8_192, context_length * 12)
    sample_streams = deque(
        (
            source,
            iter(
                _iter_balanced_source_samples(
                    source,
                    samples=samples_per_source,
                    sample_bytes=sample_bytes,
                )
            ),
        )
        for source in sources
    )
    while sample_streams:
        source, stream = sample_streams.popleft()
        try:
            sample = next(stream)
        except StopIteration:
            continue
        sample_streams.append((source, stream))
        token_ids = tokenizer.encode(sample, add_special_tokens=False)
        if len(token_ids) >= context_length + 1:
            yield token_ids[:context_length + 1]


def iter_training_windows(
    tokenizer: CanriTokenizer,
    *,
    data_root: Path = DATA_ROOT,
    context_length: int = 256,
    mode: str = "balanced",
    samples_per_source: int = 4,
    seed: int = 42,
    policy: TrainingDataPolicy | None = None,
) -> Iterator[list[int]]:
    if mode == "full":
        yield from iter_full_token_windows(
            tokenizer,
            data_root=data_root,
            context_length=context_length,
            seed=seed,
            policy=policy,
        )
        return
    if mode != "balanced":
        raise ValueError("Training mode must be 'balanced' or 'full'.")
    yield from iter_balanced_token_windows(
        tokenizer,
        data_root=data_root,
        context_length=context_length,
        samples_per_source=samples_per_source,
        seed=seed,
        policy=policy,
    )
