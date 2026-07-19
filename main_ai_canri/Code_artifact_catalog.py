"""Indexed library API and usage-template catalogs for Canri's code system."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import re
import sys
import threading
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote


DATA_DIR = Path(__file__).parent / "data"
LIBRARY_FUNCTIONS_FILE = DATA_DIR / "Library_functions.json"
LIBRARY_TEMPLATES_FILE = DATA_DIR / "Code_library_templates.json"

TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_+.#-]{1,63}")
CALLABLE_TYPES = {"function", "method", "classmethod", "staticmethod"}

SAFE_STANDARD_LIBRARY_MODULES = (
    "asyncio",
    "base64",
    "bisect",
    "calendar",
    "contextlib",
    "csv",
    "dataclasses",
    "datetime",
    "functools",
    "hashlib",
    "heapq",
    "hmac",
    "itertools",
    "json",
    "math",
    "operator",
    "os",
    "pathlib",
    "random",
    "re",
    "secrets",
    "shutil",
    "sqlite3",
    "statistics",
    "tempfile",
    "textwrap",
    "time",
    "urllib.parse",
    "uuid",
)

SAFE_STANDARD_LIBRARY_CLASSES = {
    "collections": ("Counter", "deque"),
    "concurrent.futures": ("Executor", "Future", "ThreadPoolExecutor"),
    "datetime": ("date", "datetime", "time", "timedelta"),
    "pathlib": ("Path", "PurePath"),
    "sqlite3": ("Connection", "Cursor", "Row"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: Any, prefix: str) -> str:
    source = "\x1f".join(str(part or "").strip().lower() for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def text_terms(value: Any, limit: int = 80) -> list[str]:
    terms = []
    for token in TOKEN_PATTERN.findall(str(value or "").lower()):
        token = token.strip("-_.")
        if len(token) < 2 or token in terms:
            continue
        terms.append(token)
        if len(terms) >= limit:
            break
    return terms


def _first_doc_line(value: Any, limit: int = 1200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    match = re.search(r"(?<=[.!?])\s", text)
    return text[: min(match.start() + 1 if match else len(text), limit)]


def _normalize_documentation_signature(value: Any) -> str:
    signature = str(value or "").replace("¶", "")
    signature = re.sub(r"\s*\.\s*", ".", signature)
    signature = re.sub(r"\s*\(\s*", "(", signature)
    signature = re.sub(r"\s*\)\s*", ")", signature)
    signature = re.sub(r"\s*,\s*", ", ", signature)
    signature = re.sub(r"\s*=\s*", "=", signature)
    signature = re.sub(r"\*\s+\*", "**", signature)
    signature = re.sub(r"\*\*\s+", "**", signature)
    signature = re.sub(r"(?<!\*)\*\s+(?=[A-Za-z_])", "*", signature)
    return re.sub(r"\s+", " ", signature).strip()


def _safe_signature(callable_object: Any, display_name: str) -> str:
    try:
        signature = f"{display_name}{inspect.signature(callable_object)}"
        return re.sub(r" at 0x[0-9A-Fa-f]+(?=>)", "", signature)
    except (TypeError, ValueError):
        return f"{display_name}(...)"


def _content_fingerprint(value: dict[str, Any], ignored: Iterable[str] = ()) -> str:
    ignored = set(ignored) | {"updated_utc", "last_seen_utc", "retrieved_utc"}

    def filtered_value(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                key: filtered_value(child)
                for key, child in item.items()
                if key not in ignored
            }
        if isinstance(item, list):
            return [filtered_value(child) for child in item]
        return item

    filtered = filtered_value(value)
    payload = json.dumps(filtered, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _template_arguments(signature: str, callable_type: str) -> str:
    """Turn a documentation signature into a conservative call argument list."""

    if "(" not in signature or ")" not in signature:
        return ""
    body = signature[signature.find("(") + 1:signature.rfind(")")]
    parts = []
    current = []
    depth = 0
    for character in body:
        if character in "([{":
            depth += 1
        elif character in ")]}" and depth > 0:
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if current:
        parts.append("".join(current).strip())

    arguments = []
    for part in parts:
        part = part.strip().strip("[]")
        if not part or part in {"/", "*", "self", "cls"} or "=" in part:
            continue
        prefix = ""
        if part.startswith("**") or part.startswith("*"):
            continue
        name = part.split(":", 1)[0].strip()
        name = re.sub(r"[^A-Za-z0-9_]", "", name)
        if not name or name in {"self", "cls"}:
            continue
        arguments.append(f"{prefix}{name}")
    if callable_type in {"method", "classmethod", "staticmethod"}:
        arguments = [item for item in arguments if item not in {"self", "cls"}]
    return ", ".join(arguments)


def _risk_profile(library: str, function_name: str) -> tuple[str, list[str]]:
    destructive = {
        "remove", "removedirs", "rename", "renames", "replace", "rmdir",
        "rmtree", "unlink", "truncate",
    }
    process_control = {
        "abort", "execl", "execle", "execlp", "execlpe", "execv", "execve",
        "execvp", "execvpe", "kill", "killpg", "popen", "spawnl", "spawnle",
        "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "startfile", "system",
    }
    topics = []
    if function_name in destructive and library in {"os", "pathlib", "shutil"}:
        topics.append("destructive_filesystem_operation")
    if function_name in process_control and library == "os":
        topics.append("process_or_shell_control")
    return ("security_review" if topics else "standard", topics)


class _SphinxCallableParser(HTMLParser):
    """Extract callable definitions from Sphinx ``py function/method`` blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.dl_stack: list[dict[str, Any] | None] = []
        self.callables: list[dict[str, str]] = []

    def _current(self) -> dict[str, Any] | None:
        if not self.dl_stack:
            return None
        return self.dl_stack[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "dl":
            classes = set(attributes.get("class", "").split())
            callable_type = next(
                (kind for kind in CALLABLE_TYPES if kind in classes),
                None,
            )
            frame = None
            if "py" in classes and callable_type:
                frame = {
                    "callable_type": callable_type,
                    "qualified_name": "",
                    "signature_parts": [],
                    "description_parts": [],
                    "phase": "waiting",
                }
            self.dl_stack.append(frame)
            return

        frame = self._current()
        if not frame:
            return
        if tag == "dt" and not frame["qualified_name"]:
            frame["qualified_name"] = attributes.get("id", "").strip()
            frame["phase"] = "signature"
        elif tag == "dd" and frame["qualified_name"]:
            frame["phase"] = "description"

    def handle_endtag(self, tag: str) -> None:
        frame = self._current()
        if tag == "dt" and frame and frame["phase"] == "signature":
            frame["phase"] = "waiting"
        elif tag == "dd" and frame and frame["phase"] == "description":
            frame["phase"] = "waiting"
        elif tag == "dl" and self.dl_stack:
            completed = self.dl_stack.pop()
            if completed and completed["qualified_name"]:
                signature = _normalize_documentation_signature(
                    " ".join(completed["signature_parts"])
                )
                description = re.sub(
                    r"\s+", " ", " ".join(completed["description_parts"])
                ).strip()
                self.callables.append({
                    "callable_type": completed["callable_type"],
                    "qualified_name": completed["qualified_name"],
                    "signature": signature,
                    "summary": description[:1600],
                })

    def handle_data(self, data: str) -> None:
        frame = self._current()
        if not frame:
            return
        text = str(data or "").strip()
        if not text:
            return
        if frame["phase"] == "signature":
            frame["signature_parts"].append(text)
        elif frame["phase"] == "description" and len(frame["description_parts"]) < 80:
            frame["description_parts"].append(text)


def extract_python_documentation_callables(
    content: bytes | str,
    *,
    library: str,
    source_url: str,
    retrieved_utc: str | None = None,
    library_version: str | None = None,
) -> list[dict[str, Any]]:
    """Return API signatures only; arbitrary executable examples are not copied."""

    if isinstance(content, bytes):
        page = content.decode("utf-8", errors="replace")
    else:
        page = str(content or "")
    parser = _SphinxCallableParser()
    parser.feed(page)
    parser.close()

    results = []
    seen = set()
    retrieved_utc = retrieved_utc or utc_now()
    for item in parser.callables:
        qualified_name = item["qualified_name"].strip()
        function_name = qualified_name.rsplit(".", 1)[-1].strip()
        if not qualified_name or not function_name or qualified_name in seen:
            continue
        seen.add(qualified_name)
        signature = item.get("signature") or f"{qualified_name}(...)"
        if "(" not in signature:
            signature = f"{qualified_name}(...)"
        results.append({
            "library": library,
            "function": function_name,
            "qualified_name": qualified_name,
            "callable_type": item["callable_type"],
            "language": "python",
            "signature": signature[:1200],
            "summary": item.get("summary", "")[:1600],
            "tags": [library, function_name, item["callable_type"], "official_docs"],
            "source": {
                "source_id": "python_docs",
                "source_name": "Official Python documentation",
                "url": f"{source_url.split('#', 1)[0]}#{quote(qualified_name, safe='._-')}",
                "trust_score": 96,
                "retrieved_utc": retrieved_utc,
            },
            "discovery_method": "structured_documentation_signature",
            "library_version": str(library_version or ""),
        })
    return results


class CodeArtifactCatalog:
    """Deduplicated persistent catalog searched lazily by ``Code_brain``."""

    def __init__(
        self,
        functions_file: Path = LIBRARY_FUNCTIONS_FILE,
        templates_file: Path = LIBRARY_TEMPLATES_FILE,
    ) -> None:
        self.functions_file = Path(functions_file)
        self.templates_file = Path(templates_file)
        self._lock = threading.RLock()
        self._functions_mtime_ns = -1
        self._templates_mtime_ns = -1
        self._functions: dict[str, dict[str, Any]] = {}
        self._templates: dict[str, dict[str, Any]] = {}
        self._refresh(force=True)

    @staticmethod
    def _empty(catalog_type: str, key: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "catalog_type": catalog_type,
            key: {},
            "metadata": {
                "count": 0,
                "updated_utc": None,
                "deduplication": "stable library + qualified name + callable type",
            },
        }

    def _refresh(self, force: bool = False) -> None:
        with self._lock:
            function_mtime = (
                self.functions_file.stat().st_mtime_ns
                if self.functions_file.exists()
                else 0
            )
            template_mtime = (
                self.templates_file.stat().st_mtime_ns
                if self.templates_file.exists()
                else 0
            )
            if force or function_mtime != self._functions_mtime_ns:
                payload = load_json(
                    self.functions_file,
                    self._empty("library_functions", "functions"),
                )
                functions = payload.get("functions", {}) if isinstance(payload, dict) else {}
                self._functions = functions if isinstance(functions, dict) else {}
                self._functions_mtime_ns = function_mtime
            if force or template_mtime != self._templates_mtime_ns:
                payload = load_json(
                    self.templates_file,
                    self._empty("library_call_templates", "templates"),
                )
                templates = payload.get("templates", {}) if isinstance(payload, dict) else {}
                self._templates = templates if isinstance(templates, dict) else {}
                self._templates_mtime_ns = template_mtime

    @staticmethod
    def _normalized_function(value: dict[str, Any]) -> dict[str, Any] | None:
        library = re.sub(r"\s+", " ", str(value.get("library") or "")).strip()
        function_name = re.sub(r"\s+", " ", str(value.get("function") or "")).strip()
        qualified_name = re.sub(
            r"\s+", " ", str(value.get("qualified_name") or "")
        ).strip()
        callable_type = str(value.get("callable_type") or "function").lower()
        if not library or not function_name or not qualified_name:
            return None
        if callable_type not in CALLABLE_TYPES:
            callable_type = "function"
        function_id = stable_id(
            library,
            qualified_name,
            callable_type,
            prefix="library_function",
        )
        source = value.get("source") if isinstance(value.get("source"), dict) else {}
        library_version = str(value.get("library_version") or "")[:120]
        normalized_source = {
            "source_id": str(source.get("source_id") or "unknown")[:120],
            "source_name": str(source.get("source_name") or "Unknown source")[:240],
            "url": str(source.get("url") or "")[:1200],
            "trust_score": max(0, min(100, int(source.get("trust_score") or 0))),
            "retrieved_utc": str(source.get("retrieved_utc") or utc_now()),
        }
        risk_level, security_topics = _risk_profile(library, function_name)
        return {
            "id": function_id,
            "library": library[:160],
            "function": function_name[:160],
            "qualified_name": qualified_name[:320],
            "callable_type": callable_type,
            "language": str(value.get("language") or "python")[:40],
            "signature": str(value.get("signature") or f"{qualified_name}(...)")[:1200],
            "summary": re.sub(r"\s+", " ", str(value.get("summary") or "")).strip()[:2000],
            "tags": list(dict.fromkeys(
                str(tag).strip().lower()
                for tag in value.get("tags", [])
                if str(tag).strip()
            ))[:40],
            "source": normalized_source,
            "sources": [normalized_source],
            "library_version": library_version,
            "available_versions": [library_version] if library_version else [],
            "signature_history": [],
            "discovery_method": str(value.get("discovery_method") or "unknown")[:120],
            "risk_level": str(value.get("risk_level") or risk_level)[:80],
            "security_topics": list(dict.fromkeys(
                str(topic).strip()
                for topic in value.get("security_topics", security_topics)
                if str(topic).strip()
            ))[:20],
            "requires_security_review": bool(
                value.get("requires_security_review", bool(security_topics))
            ),
            "usage_policy": "Use the verified signature as API context; do not treat it as an implementation.",
        }

    @staticmethod
    def _template_for(function: dict[str, Any]) -> dict[str, Any]:
        library = function["library"]
        qualified_name = function["qualified_name"]
        callable_type = function["callable_type"]
        signature = function["signature"]
        arguments = _template_arguments(signature, callable_type)
        call_suffix = f"({arguments})"
        root_library = library.split(".", 1)[0]
        parts = qualified_name.split(".")

        if library == "builtins":
            import_statement = ""
            call_template = f"{function['function']}{call_suffix}"
        elif callable_type in {"method", "classmethod", "staticmethod"}:
            owner = parts[-2] if len(parts) > 1 else "instance"
            if callable_type in {"classmethod", "staticmethod"}:
                receiver = owner
            else:
                receiver = "instance"
            import_statement = f"import {library}"
            call_template = f"{receiver}.{function['function']}{call_suffix}"
        else:
            import_statement = f"import {library}"
            if qualified_name.startswith(f"{root_library}."):
                call_template = f"{qualified_name}{call_suffix}"
            else:
                call_template = f"{library}.{function['function']}{call_suffix}"

        template_id = stable_id(
            function["id"],
            "library_call",
            prefix="code_template",
        )
        return {
            "id": template_id,
            "schema_version": 2,
            "function_id": function["id"],
            "library": library,
            "function": function["function"],
            "qualified_name": qualified_name,
            "language": function["language"],
            "template_kind": "library_call",
            "import_statement": import_statement,
            "call_template": call_template[:1600],
            "summary": function["summary"],
            "tags": function["tags"],
            "source": function["source"],
            "safety_note": "Fill parameters and validate behavior before execution.",
        }

    def upsert_many(self, values: Iterable[dict[str, Any]]) -> dict[str, int]:
        inserted = updated = unchanged = rejected = 0
        now = utc_now()
        with self._lock:
            self._refresh()
            for value in values:
                if not isinstance(value, dict):
                    rejected += 1
                    continue
                function = self._normalized_function(value)
                if function is None:
                    rejected += 1
                    continue
                function_id = function["id"]
                existing = self._functions.get(function_id)
                if existing:
                    function["first_seen_utc"] = existing.get("first_seen_utc", now)
                    source_values = [
                        item
                        for item in [
                            *existing.get("sources", []),
                            existing.get("source", {}),
                            *function.get("sources", []),
                        ]
                        if isinstance(item, dict) and item.get("source_id")
                    ]
                    merged_sources = {}
                    for source_value in source_values:
                        source_key = (
                            source_value.get("source_id"),
                            source_value.get("url"),
                        )
                        current = merged_sources.get(source_key)
                        if not current or int(source_value.get("trust_score", 0)) >= int(
                            current.get("trust_score", 0)
                        ):
                            merged_sources[source_key] = source_value
                    function["sources"] = list(merged_sources.values())[:20]
                    function["available_versions"] = list(dict.fromkeys(
                        str(version)
                        for version in [
                            *existing.get("available_versions", []),
                            existing.get("library_version", ""),
                            *function.get("available_versions", []),
                            function.get("library_version", ""),
                        ]
                        if str(version).strip()
                    ))[:20]

                    existing_trust = int(existing.get("source", {}).get("trust_score", 0))
                    incoming_trust = int(function.get("source", {}).get("trust_score", 0))
                    signature_history = list(existing.get("signature_history", []))
                    if (
                        incoming_trust >= existing_trust
                        and existing.get("signature")
                        and existing.get("signature") != function.get("signature")
                    ):
                        signature_history.append({
                            "signature": existing.get("signature"),
                            "library_version": existing.get("library_version", ""),
                            "source_id": existing.get("source", {}).get("source_id"),
                            "replaced_utc": now,
                        })
                    function["signature_history"] = signature_history[-12:]

                    if incoming_trust < existing_trust:
                        for key in [
                            "signature", "summary", "source", "library_version",
                            "discovery_method",
                        ]:
                            function[key] = existing.get(key, function.get(key))
                        function["tags"] = list(dict.fromkeys([
                            *existing.get("tags", []),
                            *function.get("tags", []),
                        ]))[:40]
                    if _content_fingerprint(existing, {"updated_utc", "last_seen_utc"}) == _content_fingerprint(
                        function,
                        {"updated_utc", "last_seen_utc"},
                    ):
                        template_id = stable_id(
                            function_id,
                            "library_call",
                            prefix="code_template",
                        )
                        if template_id in self._templates:
                            if int(self._templates[template_id].get("schema_version", 0)) >= 2:
                                unchanged += 1
                                continue
                    updated += 1
                else:
                    function["first_seen_utc"] = now
                    inserted += 1
                function["last_seen_utc"] = now
                function["updated_utc"] = now
                self._functions[function_id] = function
                template = self._template_for(function)
                template["updated_utc"] = now
                self._templates[template["id"]] = template

            if inserted or updated:
                function_payload = self._empty("library_functions", "functions")
                function_payload["functions"] = dict(sorted(self._functions.items()))
                function_payload["metadata"].update({
                    "count": len(self._functions),
                    "updated_utc": now,
                    "record_contract": [
                        "library",
                        "function",
                        "qualified_name",
                        "signature",
                        "source",
                    ],
                })
                template_payload = self._empty("library_call_templates", "templates")
                template_payload["templates"] = dict(sorted(self._templates.items()))
                template_payload["metadata"].update({
                    "count": len(self._templates),
                    "updated_utc": now,
                    "generated_from": "Library_functions.json",
                })
                atomic_write_json(self.functions_file, function_payload)
                atomic_write_json(self.templates_file, template_payload)
                self._functions_mtime_ns = self.functions_file.stat().st_mtime_ns
                self._templates_mtime_ns = self.templates_file.stat().st_mtime_ns

        return {
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "rejected": rejected,
        }

    def search(self, query: Any, limit: int = 12, language: str | None = None) -> list[dict[str, Any]]:
        self._refresh()
        query_terms = text_terms(
            " ".join(str(item) for item in query)
            if isinstance(query, (list, tuple, set))
            else query
        )
        if not query_terms:
            return []
        results = []
        for function in self._functions.values():
            if language and function.get("language") != language:
                continue
            library = function.get("library", "").lower()
            function_name = function.get("function", "").lower()
            qualified_name = function.get("qualified_name", "").lower()
            searchable = set(text_terms(" ".join([
                library,
                function_name,
                qualified_name,
                function.get("signature", ""),
                function.get("summary", ""),
                " ".join(function.get("tags", [])),
            ]), limit=160))
            matched = [term for term in query_terms if term in searchable]
            if not matched:
                continue
            score = len(matched) * 2.0
            score += sum(8 for term in query_terms if term == function_name)
            score += sum(6 for term in query_terms if term == library)
            score += sum(3 for term in query_terms if term in qualified_name)
            score += function.get("source", {}).get("trust_score", 0) / 100
            template_id = stable_id(function["id"], "library_call", prefix="code_template")
            results.append({
                "score": round(score, 2),
                "matched_terms": matched,
                "function": function,
                "template": self._templates.get(template_id, {}),
            })
        results.sort(
            key=lambda item: (
                item["score"],
                item["function"].get("source", {}).get("trust_score", 0),
                item["function"].get("qualified_name", ""),
            ),
            reverse=True,
        )
        return results[: max(1, min(int(limit), 50))]

    def summary(self) -> dict[str, Any]:
        self._refresh()
        libraries = {item.get("library") for item in self._functions.values() if item.get("library")}
        return {
            "functions": len(self._functions),
            "templates": len(self._templates),
            "libraries": len(libraries),
            "functions_file": self.functions_file.name,
            "templates_file": self.templates_file.name,
        }

    def seed_local_standard_library(self) -> dict[str, int]:
        """Index documented signatures exposed by a conservative stdlib allowlist."""

        values = []
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        module_names = tuple(dict.fromkeys(
            (*SAFE_STANDARD_LIBRARY_MODULES, *SAFE_STANDARD_LIBRARY_CLASSES.keys())
        ))
        for library in module_names:
            try:
                module = importlib.import_module(library)
            except (ImportError, OSError):
                continue
            docs_page = library.replace(".", ".")
            base_url = f"https://docs.python.org/3/library/{docs_page}.html"
            for name, member in inspect.getmembers(module):
                if name.startswith("_") or not (inspect.isfunction(member) or inspect.isbuiltin(member)):
                    continue
                qualified_name = f"{library}.{name}"
                values.append({
                    "library": library,
                    "function": name,
                    "qualified_name": qualified_name,
                    "callable_type": "function",
                    "language": "python",
                    "signature": _safe_signature(member, qualified_name),
                    "summary": _first_doc_line(inspect.getdoc(member)),
                    "tags": [library, name, "standard_library", "runtime_introspection"],
                    "source": {
                        "source_id": "python_local_stdlib",
                        "source_name": "Installed Python standard library",
                        "url": f"{base_url}#{quote(qualified_name, safe='._-')}",
                        "trust_score": 95,
                        "retrieved_utc": utc_now(),
                    },
                    "library_version": version,
                    "discovery_method": "safe_runtime_introspection",
                })

            for class_name in SAFE_STANDARD_LIBRARY_CLASSES.get(library, ()):
                class_object = getattr(module, class_name, None)
                if class_object is None:
                    continue
                for method_name, member in inspect.getmembers(class_object):
                    if method_name.startswith("_") or not inspect.isroutine(member):
                        continue
                    qualified_name = f"{library}.{class_name}.{method_name}"
                    values.append({
                        "library": library,
                        "function": method_name,
                        "qualified_name": qualified_name,
                        "callable_type": "method",
                        "language": "python",
                        "signature": _safe_signature(member, qualified_name),
                        "summary": _first_doc_line(inspect.getdoc(member)),
                        "tags": [
                            library,
                            class_name.lower(),
                            method_name,
                            "standard_library",
                            "runtime_introspection",
                        ],
                        "source": {
                            "source_id": "python_local_stdlib",
                            "source_name": "Installed Python standard library",
                            "url": f"{base_url}#{quote(qualified_name, safe='._-')}",
                            "trust_score": 95,
                            "retrieved_utc": utc_now(),
                        },
                        "library_version": version,
                        "discovery_method": "safe_runtime_introspection",
                    })
        return self.upsert_many(values)


if __name__ == "__main__":
    catalog = CodeArtifactCatalog()
    print(json.dumps({
        "seed": catalog.seed_local_standard_library(),
        "catalog": catalog.summary(),
    }, ensure_ascii=False, indent=2))
