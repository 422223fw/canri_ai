"""Validate active Canri source and data files without importing the application."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    PROJECT_ROOT / "main_ai_canri",
    PROJECT_ROOT / "tools",
    PROJECT_ROOT / "Canri_Tests",
)
SKIPPED_PARTS = {
    ".git",
    ".git_broken_backup",
    "__pycache__",
    "_runtime",
    "tmp",
}
FULL_JSONL_LIMIT_BYTES = 64 * 1024 * 1024
JSON_RETRIES = 5


def is_active_path(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    return not any(part in SKIPPED_PARTS for part in relative.parts)


def active_files(pattern: str) -> list[Path]:
    files: set[Path] = set()
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        files.update(path for path in root.rglob(pattern) if is_active_path(path))
    return sorted(files)


def validate_python(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8-sig")
        compile(source, str(path), "exec")
    except (OSError, SyntaxError, UnicodeError) as error:
        return f"{path.relative_to(PROJECT_ROOT)}: {error}"
    return None


def validate_json(path: Path) -> str | None:
    error: Exception | None = None
    for attempt in range(JSON_RETRIES):
        try:
            with path.open("r", encoding="utf-8-sig") as stream:
                json.load(stream)
            return None
        except (OSError, UnicodeError, json.JSONDecodeError) as caught:
            error = caught
            if attempt + 1 < JSON_RETRIES:
                time.sleep(0.08 * (attempt + 1))
    return f"{path.relative_to(PROJECT_ROOT)}: {error}"


def iter_complete_jsonl_lines(path: Path, full: bool):
    size = path.stat().st_size
    if full or size <= FULL_JSONL_LIMIT_BYTES:
        with path.open("r", encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, start=1):
                if line.strip():
                    yield line_number, line
        return

    sample_count = 100
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line_number > sample_count:
                break
            if line.strip():
                yield line_number, line

    block_size = min(size, 4 * 1024 * 1024)
    with path.open("rb") as stream:
        stream.seek(max(0, size - block_size))
        chunk = stream.read().decode("utf-8", errors="strict")
    lines = chunk.splitlines()
    if size > block_size and lines:
        lines = lines[1:]
    for offset, line in enumerate(lines[-sample_count:], start=1):
        if line.strip():
            yield -offset, line


def validate_jsonl(path: Path, full: bool) -> tuple[str | None, str]:
    mode = "full" if full or path.stat().st_size <= FULL_JSONL_LIMIT_BYTES else "sampled"
    try:
        for line_number, line in iter_complete_jsonl_lines(path, full):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                return (
                    f"{path.relative_to(PROJECT_ROOT)} line {line_number}: {error}",
                    mode,
                )
            if not isinstance(value, (dict, list)):
                return (
                    f"{path.relative_to(PROJECT_ROOT)} line {line_number}: "
                    "record is not an object or array",
                    mode,
                )
    except (OSError, UnicodeError) as error:
        return f"{path.relative_to(PROJECT_ROOT)}: {error}", mode
    return None, mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-jsonl",
        action="store_true",
        help="Validate every record in JSONL files larger than 64 MiB.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures: list[str] = []

    python_files = active_files("*.py")
    json_files = active_files("*.json")
    jsonl_files = active_files("*.jsonl")

    for path in python_files:
        error = validate_python(path)
        if error:
            failures.append(error)

    for path in json_files:
        error = validate_json(path)
        if error:
            failures.append(error)

    jsonl_modes = {"full": 0, "sampled": 0}
    for path in jsonl_files:
        error, mode = validate_jsonl(path, args.full_jsonl)
        jsonl_modes[mode] += 1
        if error:
            failures.append(error)

    summary = {
        "python_files": len(python_files),
        "json_files": len(json_files),
        "jsonl_files": len(jsonl_files),
        "jsonl_full": jsonl_modes["full"],
        "jsonl_sampled": jsonl_modes["sampled"],
        "failures": failures,
        "passed": not failures,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
