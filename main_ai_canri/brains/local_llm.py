"""Optional on-device language-model reasoning for Canri."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any

from Brain_storage import load_json_resilient


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETTINGS_FILE = DATA_DIR / "Local_model_settings.json"
DEFAULT_SETTINGS = {
    "schema_version": 1,
    "enabled": False,
    "backend": "auto",
    "model_path": "",
    "ollama_model": "",
    "context_tokens": 8192,
    "max_output_tokens": 4096,
    "temperature": 0.15,
    "timeout_seconds": 0,
    "max_prompt_characters": 48000,
    "max_project_files": 80,
    "max_total_output_bytes": 2_097_152,
}


class LocalModelError(RuntimeError):
    pass


class LocalLLMBrain:
    """Uses an explicitly configured local model and never calls a cloud API."""

    _models: dict[tuple[str, int], Any] = {}
    _model_lock = RLock()

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = Path(settings_path or SETTINGS_FILE)
        print("Local LLM Brain Loaded")

    def load_settings(self) -> dict[str, Any]:
        loaded = load_json_resilient(self.settings_path, default=DEFAULT_SETTINGS)
        settings = dict(DEFAULT_SETTINGS)
        if isinstance(loaded, dict):
            settings.update(loaded)
        return settings

    @staticmethod
    def _safe_path(value: Any) -> str | None:
        raw = str(value or "").strip().replace("\\", "/")
        if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
            return None
        path = PurePosixPath(raw)
        if any(part in {"", ".", ".."} for part in path.parts):
            return None
        return path.as_posix()

    @staticmethod
    def _compact_scanner(data: dict[str, Any]) -> list[dict[str, Any]]:
        scanner = data.get("scanner_knowledge", {})
        matches = scanner.get("matches", []) if isinstance(scanner, dict) else []
        compact = []
        for item in matches[:8]:
            if not isinstance(item, dict):
                continue
            compact.append({
                "title": item.get("title"),
                "summary": str(item.get("summary", ""))[:1200],
                "collection": item.get("collection"),
                "trust_score": item.get("trust_score", 0),
                "url": item.get("url"),
            })
        return compact

    @staticmethod
    def _compact_project(data: dict[str, Any]) -> dict[str, Any]:
        results = data.get("results", {})
        project = results.get("Project_context_brain", {}) if isinstance(results, dict) else {}
        if not isinstance(project, dict):
            return {}
        files = project.get("selected_files", {}) or project.get("files", {})
        compact_files = {}
        if isinstance(files, dict):
            for path, content in list(files.items())[:40]:
                compact_files[str(path)] = str(content)[:6000]
        elif isinstance(files, list):
            for item in files[:40]:
                if not isinstance(item, dict):
                    continue
                path = item.get("path") or item.get("file")
                if path:
                    compact_files[str(path)] = str(item.get("content", ""))[:6000]
        return {
            "workspace": project.get("workspace"),
            "summary": project.get("summary"),
            "files": compact_files,
            "cross_file_context": project.get("cross_file_context", {}),
        }

    def build_prompt(self, data: dict[str, Any], settings: dict[str, Any]) -> str:
        report = data.get("understanding", {})
        report = report if isinstance(report, dict) else {}
        results = data.get("results", {})
        results = results if isinstance(results, dict) else {}
        payload = {
            "user_request": data.get("original_text") or data.get("corrected_text"),
            "request_contract": report.get("request_contract", {}),
            "semantic_frame": report.get("semantic_frame", {}),
            "central_domains": report.get("central_domains", []),
            "routing_hints": report.get("routing_hints", []),
            "conversation": data.get("memory", {}).get("conversation", {})
            if isinstance(data.get("memory"), dict) else {},
            "project": self._compact_project(data),
            "scanner_evidence": self._compact_scanner(data),
            "creative_guidance": results.get("Creative_brain", {}),
            "quality_correction": {
                "retry_request": data.get("retry_request", {}),
                "failed_requirements": data.get("failed_requirements", []),
                "retry_instructions": data.get("retry_instructions", []),
            },
        }
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        limit = max(8000, int(settings.get("max_prompt_characters", 48000)))
        serialized = serialized[:limit]
        return (
            "You are Canri's local reasoning engine. Solve the exact user request, preserve "
            "every explicit requirement, use only relevant evidence, and do not expose internal "
            "plans. For code, prefer a maintainable architecture, complete implementations, tests, "
            "safe failure handling, and behavior-preserving project edits. Do not add complexity "
            "that the request does not justify. Never claim that code was executed.\n\n"
            "Return exactly one JSON object with this schema:\n"
            "{\"final_output\":\"user-facing answer or code\","
            "\"analysis_summary\":\"short internal summary\","
            "\"project_files\":{\"relative/path\":\"complete content\"},"
            "\"entrypoint\":\"relative/path or empty\","
            "\"tests\":[\"test descriptions\"],"
            "\"requirements_addressed\":[\"requirement\"]}\n"
            "Use project_files only when a multi-file project or Agent edit is requested. "
            "Paths must be relative and must not contain '..'.\n\n"
            f"INPUT={serialized}"
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        candidate = str(text or "").strip()
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
        try:
            loaded = json.loads(candidate)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start < 0 or end <= start:
                return {}
            try:
                loaded = json.loads(candidate[start:end + 1])
                return loaded if isinstance(loaded, dict) else {}
            except json.JSONDecodeError:
                return {}

    def _normalize_output(
        self,
        loaded: dict[str, Any],
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        maximum_files = max(1, int(settings.get("max_project_files", 80)))
        maximum_bytes = max(65_536, int(settings.get("max_total_output_bytes", 2_097_152)))
        normalized_files = {}
        rejected_paths = []
        total_bytes = 0
        files = loaded.get("project_files", {})
        if isinstance(files, dict):
            for raw_path, raw_content in files.items():
                path = self._safe_path(raw_path)
                if path is None:
                    rejected_paths.append(str(raw_path))
                    continue
                content = str(raw_content)
                size = len(content.encode("utf-8"))
                if len(normalized_files) >= maximum_files or total_bytes + size > maximum_bytes:
                    break
                normalized_files[path] = content
                total_bytes += size

        entrypoint = self._safe_path(loaded.get("entrypoint"))
        if entrypoint and normalized_files and entrypoint not in normalized_files:
            entrypoint = None
        final_output = str(loaded.get("final_output") or "").strip()
        if not final_output and not normalized_files:
            raise LocalModelError("The local model returned no usable final output.")
        return {
            "final_output": final_output,
            "analysis_summary": str(loaded.get("analysis_summary") or "")[:2000],
            "project_files": normalized_files,
            "entrypoint": entrypoint,
            "tests": [str(item)[:500] for item in loaded.get("tests", [])[:30]],
            "requirements_addressed": [
                str(item)[:500]
                for item in loaded.get("requirements_addressed", [])[:80]
            ],
            "rejected_paths": rejected_paths,
            "total_project_bytes": total_bytes,
        }

    @classmethod
    def _llama_model(cls, model_path: Path, context_tokens: int):
        key = (str(model_path), context_tokens)
        with cls._model_lock:
            if key in cls._models:
                return cls._models[key]
            try:
                from llama_cpp import Llama
            except ImportError as error:
                raise LocalModelError(
                    "llama-cpp-python is not installed for the configured GGUF model."
                ) from error
            model = Llama(
                model_path=str(model_path),
                n_ctx=context_tokens,
                verbose=False,
            )
            cls._models[key] = model
            return model

    def _run_llama_cpp(self, prompt: str, settings: dict[str, Any]) -> str:
        model_path = Path(str(settings.get("model_path") or "")).expanduser()
        if not model_path.is_file():
            raise LocalModelError("The configured GGUF model_path does not exist.")
        model = self._llama_model(
            model_path.resolve(),
            max(2048, int(settings.get("context_tokens", 8192))),
        )
        response = model.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max(256, int(settings.get("max_output_tokens", 4096))),
            temperature=max(0.0, min(float(settings.get("temperature", 0.15)), 2.0)),
        )
        return str(response["choices"][0]["message"]["content"])

    def _run_ollama(self, prompt: str, settings: dict[str, Any]) -> str:
        executable = shutil.which("ollama")
        model_name = str(settings.get("ollama_model") or "").strip()
        if not executable:
            raise LocalModelError("The Ollama executable was not found.")
        if not model_name:
            raise LocalModelError("No ollama_model is configured.")
        timeout_value = float(settings.get("timeout_seconds", 0) or 0)
        completed = subprocess.run(
            [executable, "run", model_name],
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_value if timeout_value > 0 else None,
            shell=False,
        )
        if completed.returncode != 0:
            raise LocalModelError(
                (completed.stderr or "Ollama returned an error.").strip()[:1000]
            )
        return completed.stdout

    def _select_backend(self, settings: dict[str, Any]) -> str:
        configured = str(settings.get("backend") or "auto").casefold()
        if configured in {"llama_cpp", "ollama"}:
            return configured
        model_path = Path(str(settings.get("model_path") or "")).expanduser()
        if model_path.is_file():
            return "llama_cpp"
        if settings.get("ollama_model") and shutil.which("ollama"):
            return "ollama"
        raise LocalModelError(
            "No local backend is ready. Configure a GGUF model_path or an installed Ollama model."
        )

    def process(self, data: Any) -> dict[str, Any]:
        payload = data if isinstance(data, dict) else {"original_text": str(data)}
        settings = self.load_settings()
        if not settings.get("enabled"):
            return {
                "brain": "Local_LLM_brain",
                "status": "disabled",
                "available": False,
                "reason": "Local model reasoning is disabled in Local_model_settings.json.",
                "external_api_used": False,
            }
        try:
            backend = self._select_backend(settings)
            prompt = self.build_prompt(payload, settings)
            raw = (
                self._run_llama_cpp(prompt, settings)
                if backend == "llama_cpp"
                else self._run_ollama(prompt, settings)
            )
            parsed = self._extract_json(raw)
            if not parsed:
                raise LocalModelError("The local model did not return valid JSON.")
            normalized = self._normalize_output(parsed, settings)
            return {
                "brain": "Local_LLM_brain",
                "status": "completed",
                "available": True,
                "backend": backend,
                "external_api_used": False,
                "model_output_executed": False,
                "confidence": 82,
                **normalized,
            }
        except (LocalModelError, OSError, subprocess.SubprocessError) as error:
            return {
                "brain": "Local_LLM_brain",
                "status": "unavailable",
                "available": False,
                "reason": str(error),
                "external_api_used": False,
            }


brain = LocalLLMBrain()


__all__ = ["LocalLLMBrain", "LocalModelError", "brain"]
