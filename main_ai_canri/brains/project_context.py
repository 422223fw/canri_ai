"""Bounded multi-file project understanding for Canri Agent mode."""

from __future__ import annotations

import ast
import hashlib
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from Agent_settings import load_agent_profiles, normalize_agent_settings


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


class ProjectContextBrain:
    """Indexes a project and returns only the files relevant to this request."""

    def __init__(self) -> None:
        self.profiles = load_agent_profiles()
        self._cache: dict[str, dict[str, Any]] = {}
        print("Project Context Brain Loaded")

    def _workspace(self, settings: dict[str, Any]) -> Path | None:
        raw = str(settings.get("workspace_path", "")).strip()
        if not raw:
            return None
        try:
            root = Path(raw).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        return root if root.is_dir() else None

    def _query_text(self, data: dict[str, Any]) -> str:
        report = data.get("understanding", {})
        values = [data.get("original_text", ""), data.get("corrected_text", "")]
        if isinstance(report, dict):
            values.extend(
                report.get(key, "")
                for key in ("original_text", "corrected_text", "goal", "prompt", "main_topic")
            )
            frame = report.get("meaning_frame", {})
            if isinstance(frame, dict):
                values.extend(frame.get(key, "") for key in ("subject", "action", "object"))
        return " ".join(str(value) for value in values if value)

    @staticmethod
    def _query_terms(text: str) -> list[str]:
        ignored = {
            "the", "and", "for", "with", "from", "that", "this", "into", "your",
            "project", "agent", "canri", "please", "make", "create", "write", "code",
        }
        terms = [token.lower() for token in TOKEN_RE.findall(text)]
        return list(dict.fromkeys(term for term in terms if term not in ignored))[:80]

    def _iter_files(self, root: Path, settings: dict[str, Any]) -> Iterable[Path]:
        ignored = set(self.profiles.get("ignored_directories", []))
        extensions = set(self.profiles.get("text_extensions", []))
        maximum = int(settings.get("max_files_per_scan", 600))
        yielded = 0
        for directory, directory_names, file_names in os.walk(
            root,
            topdown=True,
            onerror=lambda _error: None,
            followlinks=False,
        ):
            directory_names[:] = [name for name in directory_names if name not in ignored]
            for file_name in file_names:
                if yielded >= maximum:
                    return
                path = Path(directory) / file_name
                if path.is_symlink():
                    continue
                if path.suffix.lower() not in extensions and path.name not in {
                    "Dockerfile", "Makefile", "requirements.txt", "package.json"
                }:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size > int(settings.get("max_single_file_bytes", 262144)):
                    continue
                yielded += 1
                yield path

    @staticmethod
    def _python_structure(text: str) -> tuple[list[str], list[str]]:
        symbols: list[str] = []
        imports: list[str] = []
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            return symbols, imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return symbols[:100], imports[:100]

    @staticmethod
    def _generic_structure(text: str) -> tuple[list[str], list[str]]:
        symbols = re.findall(
            r"(?:class|function|def|interface|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
        )
        imports = re.findall(
            r"(?:from|import|require\s*\()\s*['\"]?([A-Za-z0-9_./@-]+)",
            text,
        )
        return list(dict.fromkeys(symbols))[:100], list(dict.fromkeys(imports))[:100]

    def _metadata(self, root: Path, path: Path, text: str) -> dict[str, Any]:
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".py":
            symbols, imports = self._python_structure(text)
        else:
            symbols, imports = self._generic_structure(text)
        terms = Counter(token.lower() for token in TOKEN_RE.findall(text[:120000]))
        return {
            "path": relative,
            "extension": path.suffix.lower(),
            "bytes": len(text.encode("utf-8", errors="ignore")),
            "modified_ns": path.stat().st_mtime_ns,
            "symbols": symbols,
            "imports": imports,
            "top_terms": [term for term, _ in terms.most_common(80)],
            "digest": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16],
        }

    def _build_index(self, root: Path, settings: dict[str, Any]) -> dict[str, Any]:
        cache_key = str(root).casefold()
        fingerprint_parts: list[tuple[str, int, int]] = []
        candidates = list(self._iter_files(root, settings))
        for path in candidates:
            try:
                stat = path.stat()
                fingerprint_parts.append((path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns))
            except OSError:
                continue
        fingerprint = hashlib.sha256(repr(fingerprint_parts).encode("utf-8")).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and cached.get("fingerprint") == fingerprint:
            return cached

        files: list[dict[str, Any]] = []
        text_cache: dict[str, str] = {}
        total_bytes = 0
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                metadata = self._metadata(root, path, text)
            except OSError:
                continue
            files.append(metadata)
            text_cache[metadata["path"]] = text
            total_bytes += metadata["bytes"]

        index = {
            "root": str(root),
            "fingerprint": fingerprint,
            "files": files,
            "text_cache": text_cache,
            "file_count": len(files),
            "indexed_bytes": total_bytes,
        }
        self._cache[cache_key] = index
        return index

    @staticmethod
    def _score_file(item: dict[str, Any], terms: list[str]) -> tuple[int, list[str]]:
        path = str(item.get("path", "")).lower()
        symbols = " ".join(item.get("symbols", [])).lower()
        imports = " ".join(item.get("imports", [])).lower()
        content_terms = set(item.get("top_terms", []))
        matched: list[str] = []
        score = 0
        for term in terms:
            term_score = 0
            if term in path:
                term_score += 8
            if term in symbols:
                term_score += 6
            if term in imports:
                term_score += 4
            if term in content_terms:
                term_score += 2
            if term_score:
                matched.append(term)
                score += term_score
        name = Path(path).name.lower()
        if name in {"readme.md", "pyproject.toml", "package.json", "requirements.txt"}:
            score += 2
        return score, matched

    @staticmethod
    def _cross_file_links(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_stem: dict[str, list[str]] = defaultdict(list)
        for item in files:
            path = str(item.get("path", ""))
            by_stem[Path(path).stem.lower()].append(path)

        links: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in files:
            source = str(item.get("path", ""))
            for imported in item.get("imports", []):
                stem = str(imported).replace("\\", "/").split("/")[-1].split(".")[-1].lower()
                for target in by_stem.get(stem, []):
                    if target == source:
                        continue
                    key = (source, target, "imports")
                    if key not in seen:
                        links.append({"from": source, "to": target, "kind": "imports", "term": imported})
                        seen.add(key)
        return links[:200]

    def process(self, data: Any) -> dict[str, Any]:
        payload = data if isinstance(data, dict) else {"original_text": str(data)}
        settings = normalize_agent_settings(payload.get("agent_settings", {}))
        mode = settings.get("mode", "off")
        if mode == "off":
            return {
                "brain": "Project_context_brain",
                "skipped": True,
                "reason": "agent_mode_off",
                "confidence": 100,
                "user_visible": False,
            }

        root = self._workspace(settings)
        if root is None:
            return {
                "brain": "Project_context_brain",
                "error": "agent_workspace_unavailable",
                "needs_workspace": True,
                "confidence": 0,
                "user_visible": False,
            }

        index = self._build_index(root, settings)
        terms = self._query_terms(self._query_text(payload))
        ranked: list[tuple[int, dict[str, Any], list[str]]] = []
        for item in index["files"]:
            score, matched = self._score_file(item, terms)
            ranked.append((score, item, matched))
        ranked.sort(key=lambda row: (row[0], -len(row[1].get("path", ""))), reverse=True)

        maximum = int(settings.get("max_selected_files", 12))
        selected_rows = [row for row in ranked if row[0] > 0][:maximum]
        if not selected_rows:
            selected_rows = ranked[: min(maximum, 6)]

        selected_files: dict[str, str] = {}
        selected_metadata: list[dict[str, Any]] = []
        remaining = int(settings.get("max_total_context_bytes", 2097152))
        for score, item, matched in selected_rows:
            path = item["path"]
            text = index["text_cache"].get(path, "")
            encoded_size = len(text.encode("utf-8", errors="ignore"))
            if encoded_size > remaining:
                continue
            remaining -= encoded_size
            selected_files[path] = text
            selected_metadata.append({**item, "score": score, "matched_terms": matched})

        result = {
            "brain": "Project_context_brain",
            "workspace": str(root),
            "mode": mode,
            "project_summary": {
                "file_count": index["file_count"],
                "indexed_bytes": index["indexed_bytes"],
                "selected_file_count": len(selected_files),
                "query_terms": terms,
                "extensions": dict(Counter(item["extension"] or "no_extension" for item in index["files"])),
            },
            "selected_files": selected_files,
            "relevant_files": selected_metadata,
            "cross_file_links": self._cross_file_links(index["files"]),
            "index_fingerprint": index["fingerprint"],
            "context_is_bounded": True,
            "confidence": 92 if selected_files else 55,
            "user_visible": False,
        }
        return result


brain = ProjectContextBrain()
