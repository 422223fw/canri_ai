"""Crash-safe JSON persistence shared by Canri brains."""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4


_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _path_lock(path: Path) -> threading.RLock:
    key = str(path.resolve()).casefold()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def load_json_resilient(path: Any, default: Any, retries: int = 4, delay: float = 0.04) -> Any:
    """Read JSON while tolerating a short replacement window from another process."""

    path = Path(path)
    attempts = max(int(retries), 1)
    for attempt in range(attempts):
        try:
            with _path_lock(path):
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            if attempt + 1 < attempts:
                time.sleep(max(float(delay), 0.0) * (attempt + 1))
    return copy.deepcopy(default)


def atomic_write_json(
    path: Any,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
) -> bool:
    """Write a complete JSON document and replace the destination atomically."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _path_lock(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    payload = json.dumps(
        data,
        ensure_ascii=ensure_ascii,
        indent=indent,
        sort_keys=sort_keys,
    ) + "\n"

    with lock:
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as file:
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())

            for attempt in range(5):
                try:
                    os.replace(temporary, path)
                    return True
                except OSError:
                    if attempt == 4:
                        raise
                    time.sleep(0.03 * (attempt + 1))
        except OSError:
            return False
        finally:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
    return False
