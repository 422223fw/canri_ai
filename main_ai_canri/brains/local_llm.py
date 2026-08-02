"""Optional on-device language-model reasoning for Canri."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
from datetime import datetime, timezone
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
    "native_checkpoint_path": "domain_packages/local_llm/checkpoints/canri_native.pt",
    "native_tokenizer_path": "domain_packages/local_llm/data/canri_tokenizer.json",
    "native_training_status_path": "domain_packages/local_llm/training_status.json",
    "native_allow_experimental": False,
    "native_max_new_tokens": 256,
    "native_top_k": 40,
    "native_top_p": 0.92,
    "native_repetition_penalty": 1.1,
    "native_no_repeat_ngram_size": 4,
    "native_lexical_token_bias": 0.35,
    "native_shadow_enabled": False,
    "native_shadow_log_path": "data/Local_llm_shadow.jsonl",
    "native_shadow_max_output_characters": 4000,
}


class LocalModelError(RuntimeError):
    pass


class LocalLLMBrain:
    """Uses an explicitly configured local model and never calls a cloud API."""

    _models: dict[tuple[str, int], Any] = {}
    _model_lock = RLock()
    _shadow_lock = RLock()

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

    def build_native_prompt(self, data: dict[str, Any]) -> str:
        """Build a compact plain-text task for CANRI's small native context."""

        results = data.get("results", {})
        bridge = (
            results.get("LLM_bridge_brain", {})
            if isinstance(results, dict)
            else {}
        )
        if isinstance(bridge, dict):
            packet = bridge.get("context_packet", {})
            if isinstance(packet, dict) and str(packet.get("native_prompt") or "").strip():
                return str(packet["native_prompt"]).strip()

        request = str(data.get("original_text") or data.get("corrected_text") or "").strip()
        understanding = data.get("understanding", {})
        understanding = understanding if isinstance(understanding, dict) else {}
        contract = understanding.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        requirements = contract.get("requirements", [])
        if not isinstance(requirements, list):
            requirements = []
        failed = data.get("failed_requirements", [])
        failed = failed if isinstance(failed, list) else []
        evidence = self._compact_scanner(data)

        sections = [f"Task: {request[:1600]}"]
        if requirements:
            sections.append(
                "Requirements:\n"
                + "\n".join(f"- {str(item)[:240]}" for item in requirements[:8])
            )
        if failed:
            sections.append(
                "Correct these failures:\n"
                + "\n".join(f"- {str(item)[:240]}" for item in failed[:6])
            )
        if evidence:
            sections.append(
                "Reliable local context:\n"
                + "\n".join(
                    f"- {str(item.get('title') or '')[:100]}: "
                    f"{str(item.get('summary') or '')[:320]}"
                    for item in evidence[:3]
                )
            )
        sections.append(
            "Answer the task directly. Follow every requirement. Return only the user-facing result."
        )
        return "\n\n".join(sections)

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

    def _run_native(self, prompt: str, settings: dict[str, Any]) -> str:
        """Run CANRI's own from-scratch checkpoint without a remote service."""

        from domain_packages.local_llm.inference import generate_text

        project_root = DATA_DIR.parent
        checkpoint = project_root / str(
            settings.get("native_checkpoint_path")
            or DEFAULT_SETTINGS["native_checkpoint_path"]
        )
        tokenizer = project_root / str(
            settings.get("native_tokenizer_path")
            or DEFAULT_SETTINGS["native_tokenizer_path"]
        )
        status_path = project_root / str(
            settings.get("native_training_status_path")
            or DEFAULT_SETTINGS["native_training_status_path"]
        )
        readiness = load_json_resilient(status_path, default={})
        ready = bool(
            isinstance(readiness, dict)
            and readiness.get("ready_for_canri_default_backend") is True
        )
        if not ready and not settings.get("native_allow_experimental", False):
            status = (
                str(readiness.get("status") or "not_evaluated")
                if isinstance(readiness, dict)
                else "not_evaluated"
            )
            raise LocalModelError(
                "The native CANRI checkpoint is experimental and is not ready "
                f"for user answers (status: {status}). Continue training and evaluation, "
                "or explicitly set native_allow_experimental to true for testing."
            )
        return generate_text(
            prompt,
            checkpoint=checkpoint,
            tokenizer_path=tokenizer,
            max_new_tokens=max(1, int(settings.get("native_max_new_tokens", 256))),
            temperature=float(settings.get("temperature", 0.7)),
            top_k=max(0, int(settings.get("native_top_k", 40))),
            top_p=float(settings.get("native_top_p", 0.92)),
            repetition_penalty=float(
                settings.get("native_repetition_penalty", 1.1)
            ),
            no_repeat_ngram_size=max(
                0, int(settings.get("native_no_repeat_ngram_size", 4))
            ),
            lexical_token_bias=float(
                settings.get("native_lexical_token_bias", 0.35)
            ),
        )

    def _select_backend(self, settings: dict[str, Any]) -> str:
        configured = str(settings.get("backend") or "auto").casefold()
        if configured in {"llama_cpp", "ollama", "canri_native"}:
            return configured
        model_path = Path(str(settings.get("model_path") or "")).expanduser()
        if model_path.is_file():
            return "llama_cpp"
        if settings.get("ollama_model") and shutil.which("ollama"):
            return "ollama"
        raise LocalModelError(
            "No local backend is ready. Configure a GGUF model_path or an installed Ollama model."
        )

    def _append_shadow_record(self, record: dict[str, Any], settings: dict[str, Any]) -> None:
        project_root = DATA_DIR.parent
        configured = str(
            settings.get("native_shadow_log_path")
            or DEFAULT_SETTINGS["native_shadow_log_path"]
        )
        destination = project_root / configured
        try:
            destination.resolve().relative_to(project_root.resolve())
        except (OSError, ValueError) as error:
            raise LocalModelError("The native shadow log must remain inside CANRI.") from error
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._shadow_lock:
            with destination.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")

    def process_shadow(self, data: Any) -> dict[str, Any]:
        """Generate an experimental candidate without changing the user answer."""

        payload = data if isinstance(data, dict) else {"original_text": str(data)}
        settings = self.load_settings()
        if not settings.get("native_shadow_enabled", False):
            return {
                "brain": "Local_LLM_shadow",
                "status": "shadow_disabled",
                "available": False,
                "used_for_user_answer": False,
            }
        request = str(
            payload.get("original_text") or payload.get("corrected_text") or ""
        ).strip()
        if not request:
            return {
                "brain": "Local_LLM_shadow",
                "status": "shadow_skipped",
                "available": False,
                "reason": "empty_request",
                "used_for_user_answer": False,
            }
        shadow_settings = dict(settings)
        shadow_settings["native_allow_experimental"] = True
        shadow_settings["temperature"] = 0.0
        try:
            candidate = self._run_native(
                self.build_native_prompt(payload), shadow_settings
            ).strip()
            if not candidate:
                raise LocalModelError("The native model produced an empty shadow candidate.")
            maximum = max(
                256,
                int(settings.get("native_shadow_max_output_characters", 4000)),
            )
            candidate = candidate[:maximum]
            record = {
                "schema_version": 1,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "request_id": str(payload.get("_request_id") or ""),
                "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
                "candidate": candidate,
                "used_for_user_answer": False,
                "model_output_executed": False,
            }
            self._append_shadow_record(record, settings)
            return {
                "brain": "Local_LLM_shadow",
                "status": "shadow_completed",
                "available": True,
                "candidate_output": candidate,
                "used_for_user_answer": False,
                "model_output_executed": False,
                "request_sha256": record["request_sha256"],
            }
        except (LocalModelError, OSError, RuntimeError, ValueError) as error:
            return {
                "brain": "Local_LLM_shadow",
                "status": "shadow_unavailable",
                "available": False,
                "reason": str(error),
                "used_for_user_answer": False,
                "model_output_executed": False,
            }

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
            prompt = (
                self.build_native_prompt(payload)
                if backend == "canri_native"
                else self.build_prompt(payload, settings)
            )
            raw = (
                self._run_llama_cpp(prompt, settings)
                if backend == "llama_cpp"
                else self._run_ollama(prompt, settings)
                if backend == "ollama"
                else self._run_native(prompt, settings)
            )
            parsed = self._extract_json(raw)
            if not parsed and backend == "canri_native" and str(raw).strip():
                parsed = {
                    "final_output": str(raw).strip(),
                    "analysis_summary": "Native CANRI checkpoint response.",
                }
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
                "confidence": 58 if backend == "canri_native" else 82,
                "integration_mode": str(settings.get("integration_mode", "advisory")),
                "used_for_user_answer": False,
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
