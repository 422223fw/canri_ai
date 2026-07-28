"""Project-aware execution brain with explicit autonomy modes."""

from __future__ import annotations

import hashlib
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from Agent_settings import load_agent_profiles, normalize_agent_settings
from Brain_storage import atomic_write_json, load_json_resilient


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PENDING_FILE = DATA_DIR / "Agent_pending_actions.json"
AUDIT_FILE = DATA_DIR / "Agent_audit.jsonl"


class AgentPolicyError(RuntimeError):
    pass


class AgentBrain:
    """Reads, edits, and validates one selected workspace for Canri."""

    MUTATION_MARKERS = (
        "edit the project", "modify the project", "update the project", "fix the project",
        "write to the project", "create the file", "write the file", "save the code",
        "apply the changes", "implement in", "inside the project", "in the project",
        "continue the project", "continue from", "continue the same", "same project",
        "improve the project", "improve the same", "update the existing", "modify the existing",
        "תשנה את הפרויקט", "תעדכן את הפרויקט", "תתקן את הפרויקט", "תכתוב בפרויקט",
        "תיצור קובץ", "תכתוב בקובץ", "שמור את הקוד", "תיישם", "בפרויקט",
    )
    TEST_MARKERS = (
        "run tests", "run the tests", "test the project", "verify the project",
        "syntax check", "check syntax", "compile the project", "validate the files",
        "תריץ בדיקות", "הרץ בדיקות", "תבדוק את הפרויקט",
    )

    def __init__(self) -> None:
        self.profiles = load_agent_profiles()
        print("Agent Brain Loaded")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        report = data.get("understanding", {})
        values = [data.get("original_text", ""), data.get("corrected_text", "")]
        if isinstance(report, dict):
            values.extend(report.get(key, "") for key in ("original_text", "corrected_text", "goal", "prompt"))
        return " ".join(str(value) for value in values if value).strip()

    def _workspace(self, settings: dict[str, Any]) -> Path:
        raw = str(settings.get("workspace_path", "")).strip()
        if not raw:
            raise AgentPolicyError("No Agent workspace was selected in Settings.")
        try:
            root = Path(raw).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise AgentPolicyError(f"The Agent workspace is unavailable: {error}") from error
        if not root.is_dir():
            raise AgentPolicyError("The selected Agent workspace is not a directory.")
        return root

    def _resolve_path(self, root: Path, raw_path: Any, *, must_exist: bool = False) -> Path:
        text = str(raw_path or "").strip().strip('"\'')
        if not text:
            raise AgentPolicyError("An action is missing its file path.")
        candidate = Path(text)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve(strict=must_exist)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError) as error:
            raise AgentPolicyError(f"Path escapes or is unavailable in the Agent workspace: {text}") from error
        protected = {str(part).lower() for part in self.profiles.get("protected_path_parts", [])}
        relative_parts = {part.lower() for part in resolved.relative_to(root).parts}
        if protected.intersection(relative_parts):
            raise AgentPolicyError("Agent actions cannot modify source-control metadata.")
        if resolved.is_symlink():
            raise AgentPolicyError("Agent actions do not follow symbolic links.")
        return resolved

    @staticmethod
    def _relative(root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    @staticmethod
    def _action_preview(action: dict[str, Any]) -> dict[str, Any]:
        preview = {
            "type": action.get("type"),
            "path": action.get("path"),
            "command": action.get("command"),
            "reason": action.get("reason"),
        }
        content = action.get("content")
        if isinstance(content, str):
            preview["content_characters"] = len(content)
            preview["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return {key: value for key, value in preview.items() if value not in (None, "", [])}

    @staticmethod
    def _clean_command_parts(command: Any) -> list[str]:
        if isinstance(command, (list, tuple)):
            parts = [str(part).strip() for part in command if str(part).strip()]
        else:
            raw = str(command or "").strip()
            if not raw:
                return []
            if any(marker in raw for marker in ("\n", "\r", ";", "&&", "||", "|", ">", "<", "`", "$(")):
                raise AgentPolicyError("Shell operators and multi-command strings are not allowed.")
            try:
                parts = shlex.split(raw, posix=False)
            except ValueError as error:
                raise AgentPolicyError(f"The command could not be parsed: {error}") from error
            parts = [part[1:-1] if len(part) >= 2 and part[0] == part[-1] and part[0] in {'"', "'"} else part for part in parts]
        return parts

    def _validate_command(self, root: Path, command: Any, mode: str) -> list[str]:
        parts = self._clean_command_parts(command)
        if not parts:
            raise AgentPolicyError("A terminal action is missing its command.")

        executable = Path(parts[0]).name.lower()
        executable_without_suffix = executable[:-4] if executable.endswith(".exe") else executable
        blocked = {str(item).lower() for item in self.profiles.get("hard_blocked_executables", [])}
        if executable in blocked or executable_without_suffix in blocked:
            raise AgentPolicyError(f"The executable {executable!r} is blocked by Agent safety rules.")

        allow_key = "restricted_commands" if mode == "restricted" else "allowed_commands"
        allowed = {str(item).lower() for item in self.profiles.get(allow_key, [])}
        if executable not in allowed and executable_without_suffix not in allowed:
            raise AgentPolicyError(f"The executable {executable!r} is not in this Agent mode's allowlist.")

        joined = " ".join(parts[1:]).lower()
        lowered_arguments = [part.lower() for part in parts[1:]]
        for marker in self.profiles.get("hard_blocked_arguments", []):
            marker = str(marker).lower()
            if not marker:
                continue
            marker_found = (
                marker in joined
                if " " in marker
                else any(argument == marker or argument.startswith(marker + "=") for argument in lowered_arguments)
            )
            if marker_found:
                raise AgentPolicyError(f"The command contains a blocked operation: {marker}")

        if executable_without_suffix == "git":
            subcommand = parts[1].lower() if len(parts) > 1 else ""
            allowed_git = {"status", "diff", "log", "show", "branch"}
            if mode == "autonomous":
                allowed_git.update({"add", "commit"})
            if subcommand not in allowed_git:
                raise AgentPolicyError(f"git {subcommand or '<missing>'} is not allowed in Agent mode.")

        if executable_without_suffix in {"npm", "npx"}:
            subcommand = parts[1].lower() if len(parts) > 1 else ""
            if subcommand not in {"test", "run", "build"}:
                raise AgentPolicyError(f"npm/npx {subcommand or '<missing>'} is not allowed.")

        for part in parts[1:]:
            if not part or part.startswith("-"):
                continue
            possible = Path(part)
            if possible.is_absolute():
                try:
                    possible.resolve(strict=False).relative_to(root)
                except (OSError, RuntimeError, ValueError) as error:
                    raise AgentPolicyError("Command arguments cannot target paths outside the workspace.") from error
        return parts

    def _backup(self, root: Path, path: Path) -> str | None:
        if not path.exists() or not path.is_file():
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = root / ".canri_agent" / "backups" / stamp / path.relative_to(root)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        return self._relative(root, backup)

    def _validate_write(self, root: Path, action: dict[str, Any], settings: dict[str, Any]) -> Path:
        if not settings.get("allow_file_writes"):
            raise AgentPolicyError("File writes are disabled in Agent Settings.")
        path = self._resolve_path(root, action.get("path"), must_exist=False)
        extensions = {str(item).lower() for item in self.profiles.get("writable_extensions", [])}
        if path.suffix.lower() not in extensions and path.name not in {"Dockerfile", "Makefile", "requirements.txt"}:
            raise AgentPolicyError(f"Writing {path.suffix or 'this file type'} is not allowed.")
        content = action.get("content")
        if not isinstance(content, str):
            raise AgentPolicyError("A write action requires text content.")
        maximum = max(int(settings.get("max_single_file_bytes", 262144)), 4096) * 4
        if len(content.encode("utf-8")) > maximum:
            raise AgentPolicyError("The generated file is larger than the configured Agent limit.")
        return path

    def _read_file(self, root: Path, action: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(root, action.get("path"), must_exist=True)
        if not path.is_file():
            raise AgentPolicyError("The requested path is not a file.")
        maximum = int(settings.get("max_single_file_bytes", 262144))
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "type": "read_file",
            "path": self._relative(root, path),
            "content": text[:maximum],
            "truncated": len(text) > maximum,
            "ok": True,
        }

    def _search(self, root: Path, action: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
        query = str(action.get("query") or action.get("text") or "").strip()
        if not query:
            raise AgentPolicyError("A search action requires text.")
        ignored = set(self.profiles.get("ignored_directories", []))
        extensions = set(self.profiles.get("text_extensions", []))
        matches: list[dict[str, Any]] = []
        for directory, directory_names, file_names in os.walk(
            root,
            topdown=True,
            onerror=lambda _error: None,
            followlinks=False,
        ):
            directory_names[:] = [name for name in directory_names if name not in ignored]
            for file_name in file_names:
                if len(matches) >= 80:
                    break
                path = Path(directory) / file_name
                if path.is_symlink() or path.suffix.lower() not in extensions:
                    continue
                try:
                    if path.stat().st_size > int(settings.get("max_single_file_bytes", 262144)):
                        continue
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                    relative = path.relative_to(root)
                except (OSError, ValueError):
                    continue
                for number, line in enumerate(lines, start=1):
                    if query.casefold() in line.casefold():
                        matches.append({"path": relative.as_posix(), "line": number, "text": line[:300]})
                        if len(matches) >= 80:
                            break
            if len(matches) >= 80:
                break
        return {"type": "search", "query": query, "matches": matches, "ok": True}

    def _write_file(self, root: Path, action: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
        path = self._validate_write(root, action, settings)
        existed_before = path.exists()
        previous_content = ""
        if existed_before:
            previous_content = path.read_text(encoding="utf-8", errors="replace")
        backup = self._backup(root, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".canri_tmp")
        content = str(action["content"])
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

        before_lines = previous_content.splitlines()
        after_lines = content.splitlines()
        diff_lines = list(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"before/{self._relative(root, path)}",
            tofile=f"after/{self._relative(root, path)}",
            lineterm="",
        ))
        added_lines = sum(
            1 for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed_lines = sum(
            1 for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )
        preview_limit = 200_000
        diff_limit = 2_000
        return {
            "type": "write_file",
            "path": self._relative(root, path),
            "characters": len(content),
            "existed_before": existed_before,
            "before_line_count": len(before_lines),
            "after_line_count": len(after_lines),
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "after_content": content[:preview_limit],
            "after_content_truncated": len(content) > preview_limit,
            "diff_preview": "\n".join(diff_lines[:diff_limit]),
            "diff_truncated": len(diff_lines) > diff_limit,
            "backup": backup,
            "ok": True,
        }

    def _run_command(self, root: Path, action: dict[str, Any], settings: dict[str, Any], mode: str) -> dict[str, Any]:
        if not settings.get("allow_terminal"):
            raise AgentPolicyError("Terminal commands are disabled in Agent Settings.")
        parts = self._validate_command(root, action.get("command"), mode)
        timeout = int(settings.get("command_timeout_seconds", 120))
        completed = subprocess.run(
            parts,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "type": "run_command",
            "command": parts,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
            "ok": completed.returncode == 0,
        }

    def _execute_action(
        self,
        root: Path,
        action: dict[str, Any],
        settings: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        action_type = str(action.get("type", "")).strip().lower()
        if action_type == "read_file":
            return self._read_file(root, action, settings)
        if action_type == "search":
            return self._search(root, action, settings)
        if action_type in {"write_file", "create_file"}:
            return self._write_file(root, action, settings)
        if action_type == "run_command":
            return self._run_command(root, action, settings, mode)
        raise AgentPolicyError(f"Unsupported Agent action: {action_type or '<missing>'}")

    def _validate_planned_action(
        self,
        root: Path,
        action: dict[str, Any],
        settings: dict[str, Any],
        mode: str,
    ) -> None:
        action_type = str(action.get("type", "")).strip().lower()
        if action_type in {"write_file", "create_file"}:
            self._validate_write(root, action, settings)
            return
        if action_type == "run_command":
            if not settings.get("allow_terminal"):
                raise AgentPolicyError("Terminal commands are disabled in Agent Settings.")
            self._validate_command(root, action.get("command"), mode)
            return
        if action_type == "read_file":
            self._resolve_path(root, action.get("path"), must_exist=True)
            return
        if action_type == "search":
            if not str(action.get("query") or action.get("text") or "").strip():
                raise AgentPolicyError("A search action requires text.")
            return
        raise AgentPolicyError(f"Unsupported Agent action: {action_type or '<missing>'}")

    def _security_allows_mutation(self, data: dict[str, Any]) -> bool:
        security = data.get("results", {}).get("Security_brain", {})
        if not isinstance(security, dict):
            return True
        return not bool(
            security.get("blocked")
            or security.get("safe") is False
            or security.get("risk_level") in {"critical", "blocked"}
        )

    @staticmethod
    def _explicit_path(text: str) -> str | None:
        patterns = (
            r"(?:file|path|to|in)\s+[`\"]?([A-Za-z0-9_./\\ -]+\.(?:py|js|ts|json|md|txt|html|css|cs|java|cpp|go|rs))[`\"]?",
            r"(?:קובץ|נתיב)\s+[`\"]?([^`\"\n]+\.(?:py|js|ts|json|md|txt|html|css|cs|java|cpp|go|rs))[`\"]?",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _directive_actions(self, text: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
        actions: list[dict[str, Any]] = []
        control: dict[str, str] = {}
        approve = re.search(r"/agent\s+approve\s+([a-f0-9]{8,64})", text, re.IGNORECASE)
        reject = re.search(r"/agent\s+reject\s+([a-f0-9]{8,64})", text, re.IGNORECASE)
        if approve:
            control["approve"] = approve.group(1)
            return actions, control
        if reject:
            control["reject"] = reject.group(1)
            return actions, control

        run = re.search(r"/agent\s+run\s+([^\r\n]+)", text, re.IGNORECASE)
        if run:
            actions.append({"type": "run_command", "command": run.group(1).strip(), "reason": "explicit Agent command"})
        read = re.search(r"/agent\s+read\s+([^\r\n]+)", text, re.IGNORECASE)
        if read:
            actions.append({"type": "read_file", "path": read.group(1).strip(), "reason": "explicit Agent read"})
        search = re.search(r"/agent\s+search\s+([^\r\n]+)", text, re.IGNORECASE)
        if search:
            actions.append({"type": "search", "query": search.group(1).strip(), "reason": "explicit Agent search"})
        write = re.search(
            r"/agent\s+write\s+([^\r\n`]+)\s*```(?:[A-Za-z0-9_+-]+)?\s*\n(.*?)```",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if write:
            actions.append({
                "type": "write_file",
                "path": write.group(1).strip(),
                "content": write.group(2),
                "reason": "explicit Agent write",
            })
        return actions, control

    def _derived_actions(self, data: dict[str, Any], text: str) -> list[dict[str, Any]]:
        provided = data.get("agent_actions")
        if isinstance(provided, list):
            return [dict(action) for action in provided if isinstance(action, dict)][:100]

        lowered = text.casefold()
        mutation_requested = self._mutation_requested(data, lowered)
        test_requested = any(marker.casefold() in lowered for marker in self.TEST_MARKERS)
        syntax_requested = any(
            marker in lowered
            for marker in ("syntax check", "check syntax", "compile the project", "validate the files")
        )
        results = data.get("results", {})
        code_result = results.get("Code_brain", {}) if isinstance(results, dict) else {}
        creative_result = results.get("Creative_brain", {}) if isinstance(results, dict) else {}
        creative_consulted = bool(
            isinstance(creative_result, dict)
            and (
                creative_result.get("specialist_support")
                or creative_result.get("best_idea")
                or creative_result.get("proposed_output")
            )
        )
        write_reason = (
            "Code_brain project output produced after creative consultation"
            if creative_consulted
            else "Code_brain project output requested for this workspace"
        )
        actions: list[dict[str, Any]] = []

        if mutation_requested and isinstance(code_result, dict):
            project_files = code_result.get("project_files")
            if isinstance(project_files, dict) and project_files:
                changed_paths = {
                    str(path).replace("\\", "/")
                    for path in (code_result.get("changed_paths") or [])
                }
                project_update = str(code_result.get("output_mode", "")).casefold() == "project_update"
                selected_files = [
                    (path, content)
                    for path, content in project_files.items()
                    if not project_update
                    or not changed_paths
                    or str(path).replace("\\", "/") in changed_paths
                ]
                for path, content in selected_files[:100]:
                    if isinstance(content, str):
                        actions.append({
                            "type": "write_file",
                            "path": str(path),
                            "content": content,
                            "reason": write_reason,
                        })
            elif isinstance(code_result.get("generated_code"), str) and code_result["generated_code"].strip():
                target = self._explicit_path(text) or "canri_generated.py"
                actions.append({
                    "type": "write_file",
                    "path": target,
                    "content": code_result["generated_code"],
                    "reason": write_reason,
                })

        if test_requested:
            project = results.get("Project_context_brain", {}) if isinstance(results, dict) else {}
            files = project.get("project_summary", {}).get("extensions", {}) if isinstance(project, dict) else {}
            files = dict(files) if isinstance(files, dict) else {}
            generated_files = code_result.get("project_files", {}) if isinstance(code_result, dict) else {}
            if isinstance(generated_files, dict):
                for path in generated_files:
                    suffix = Path(str(path)).suffix.lower()
                    if suffix:
                        files[suffix] = int(files.get(suffix, 0) or 0) + 1
            if ".py" in files:
                command = (
                    ["python", "-m", "compileall", "-q", "."]
                    if syntax_requested
                    else ["python", "-m", "pytest", "-q"]
                )
                actions.append({
                    "type": "run_command",
                    "command": command,
                    "reason": "user requested a Python syntax check" if syntax_requested else "user requested project tests",
                })
            elif ".cs" in files:
                actions.append({"type": "run_command", "command": ["dotnet", "test"], "reason": "user requested project tests"})
            elif any(extension in files for extension in (".js", ".ts", ".tsx", ".jsx")):
                actions.append({"type": "run_command", "command": ["npm", "test"], "reason": "user requested project tests"})

        generated_files = code_result.get("project_files", {}) if isinstance(code_result, dict) else {}
        validation_paths = set(generated_files) if isinstance(generated_files, dict) else set()
        changed_validation_paths = {
            str(path).replace("\\", "/")
            for path in (code_result.get("changed_paths") or [])
        } if isinstance(code_result, dict) else set()
        if (
            isinstance(code_result, dict)
            and str(code_result.get("output_mode", "")).casefold() == "project_update"
            and changed_validation_paths
        ):
            validation_paths = changed_validation_paths
        python_paths = [
            str(path)
            for path in validation_paths
            if str(path).lower().endswith(".py")
        ][:50]
        if (
            mutation_requested
            and python_paths
            and not any(action.get("type") == "run_command" for action in actions)
        ):
            actions.append({
                "type": "run_command",
                "command": ["python", "-m", "py_compile", *python_paths],
                "reason": "automatic syntax validation for generated Python files",
            })
        return actions

    def _mutation_requested(self, data: dict[str, Any], lowered_text: str) -> bool:
        """Use Understanding's request contract as the source of truth for writes."""

        report = data.get("understanding", {})
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        continuation = contract.get("continuation", {})
        continuation = continuation if isinstance(continuation, dict) else {}
        requested_action = report.get("requested_action", {})
        requested_action = requested_action if isinstance(requested_action, dict) else {}
        semantic = report.get("semantic_frame", {})
        semantic = semantic if isinstance(semantic, dict) else {}

        structured_actions = {
            str(contract.get("action", "")).casefold(),
            str(requested_action.get("action_word", "")).casefold(),
            str(semantic.get("main_action", "")).casefold(),
        }
        for action in semantic.get("actions", []):
            if isinstance(action, dict):
                structured_actions.add(str(action.get("word", "")).casefold())

        mutating_actions = {
            "add", "apply", "build", "change", "continue", "create", "edit",
            "fix", "generate", "implement", "improve", "modify", "replace",
            "save", "update", "write",
        }
        intent = str(report.get("intent") or contract.get("intent") or "").casefold()
        structured_request = bool(
            structured_actions.intersection(mutating_actions)
            or continuation.get("requested")
            or (
                requested_action.get("is_action_request")
                and intent in {"code_generation", "code_editing", "debugging", "game_creation"}
            )
        )
        marker_request = any(marker.casefold() in lowered_text for marker in self.MUTATION_MARKERS)
        return structured_request or marker_request

    @staticmethod
    def _explicit_agent_request(data: dict[str, Any], text: str) -> bool:
        lowered = str(text or "").casefold()
        explicit_phrase = bool(re.search(r"\buse\s+agent\s+mode\b", lowered))
        report = data.get("understanding", {})
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        continuation = contract.get("continuation", {})
        continuation = continuation if isinstance(continuation, dict) else {}
        target = " ".join(
            str(value or "")
            for value in (
                contract.get("target"),
                contract.get("action_kind"),
                report.get("main_topic"),
            )
        ).casefold()
        return bool(
            explicit_phrase
            or continuation.get("agent_mode_requested")
            or ("agent" in target and "mode" in target)
        )

    @staticmethod
    def _continuation_context_used(data: dict[str, Any]) -> bool:
        report = data.get("understanding", {})
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        continuation = contract.get("continuation", {})
        continuation = continuation if isinstance(continuation, dict) else {}
        memory = data.get("memory", {})
        memory = memory if isinstance(memory, dict) else {}
        conversation = memory.get("conversation", {})
        conversation = conversation if isinstance(conversation, dict) else {}
        return bool(
            continuation.get("requested")
            or conversation.get("continuation_request")
            or conversation.get("agent_continuation")
            or data.get("existing_project_files")
        )

    def _load_pending(self) -> dict[str, Any]:
        loaded = load_json_resilient(PENDING_FILE, default={"schema_version": 1, "pending": {}})
        if not isinstance(loaded, dict):
            return {"schema_version": 1, "pending": {}}
        loaded.setdefault("schema_version", 1)
        loaded.setdefault("pending", {})
        return loaded

    def _save_pending(self, pending: dict[str, Any]) -> None:
        atomic_write_json(PENDING_FILE, pending, indent=2, ensure_ascii=False)

    def _queue_approval(
        self,
        root: Path,
        actions: list[dict[str, Any]],
        data: dict[str, Any],
    ) -> str:
        pending = self._load_pending()
        action_id = uuid4().hex[:12]
        pending["pending"][action_id] = {
            "id": action_id,
            "created_utc": self._utc_now(),
            "workspace": str(root),
            "session_id": str(data.get("session_id", "default")),
            "actions": actions,
            "previews": [self._action_preview(action) for action in actions],
        }
        self._save_pending(pending)
        return action_id

    def _take_pending(self, action_id: str, root: Path, session_id: str) -> list[dict[str, Any]]:
        pending = self._load_pending()
        item = pending.get("pending", {}).get(action_id)
        if not isinstance(item, dict):
            raise AgentPolicyError("That Agent approval ID was not found or has already been used.")
        if str(item.get("session_id")) != str(session_id):
            raise AgentPolicyError("That Agent approval belongs to another chat session.")
        try:
            pending_root = Path(str(item.get("workspace", ""))).resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise AgentPolicyError("The approved workspace is no longer available.") from error
        if pending_root != root:
            raise AgentPolicyError("The selected Agent workspace changed after approval was requested.")
        actions = [dict(action) for action in item.get("actions", []) if isinstance(action, dict)]
        del pending["pending"][action_id]
        self._save_pending(pending)
        return actions

    def _reject_pending(self, action_id: str, session_id: str) -> bool:
        pending = self._load_pending()
        item = pending.get("pending", {}).get(action_id)
        if not isinstance(item, dict) or str(item.get("session_id")) != str(session_id):
            return False
        del pending["pending"][action_id]
        self._save_pending(pending)
        return True

    def _audit(self, record: dict[str, Any]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _format_display(status: str, root: Path, results: list[dict[str, Any]], action_id: str | None = None) -> str:
        if status == "approval_required":
            previews = [result for result in results]
            lines = [
                f"Agent prepared {len(previews)} action(s) for {root}.",
                "No file or command was changed yet.",
            ]
            for item in previews[:20]:
                target = item.get("path")
                if not target and isinstance(item.get("command"), list):
                    target = " ".join(item["command"])
                elif not target:
                    target = item.get("command")
                lines.append(f"- {item.get('type')}: {target or item.get('query', '')}")
            lines.append(f"Approve with: /agent approve {action_id}")
            lines.append(f"Reject with: /agent reject {action_id}")
            return "\n".join(lines)

        written = [item for item in results if item.get("type") == "write_file" and item.get("ok")]
        commands = [item for item in results if item.get("type") == "run_command"]
        added = sum(int(item.get("added_lines", 0) or 0) for item in written)
        removed = sum(int(item.get("removed_lines", 0) or 0) for item in written)
        lines = [f"Agent completed {len(results)} action(s) in {root}."]
        if written:
            lines.append(
                f"I updated {len(written)} file(s): +{added} line(s), -{removed} line(s)."
            )
        for item in results[:30]:
            if item.get("type") == "write_file":
                lines.append(
                    f"- {item.get('path')}: +{item.get('added_lines', 0)} "
                    f"-{item.get('removed_lines', 0)}, {item.get('after_line_count', 0)} total lines."
                )
            elif item.get("type") == "run_command":
                command = " ".join(item.get("command", []))
                lines.append(f"- Ran `{command}` with exit code {item.get('returncode')}.")
            elif item.get("type") == "read_file":
                lines.append(f"- Read {item.get('path')}.")
            elif item.get("type") == "search":
                lines.append(f"- Found {len(item.get('matches', []))} match(es) for {item.get('query')!r}.")
            if item.get("error"):
                lines.append(f"  Error: {item['error']}")
        if written and not commands:
            lines.append("The files were saved. No validation command was requested or executed.")
        return "\n".join(lines)

    def process(self, data: Any) -> dict[str, Any]:
        payload = data if isinstance(data, dict) else {"original_text": str(data)}
        text = self._text(payload)
        explicit_agent_request = self._explicit_agent_request(payload, text)
        settings = normalize_agent_settings(payload.get("agent_settings", {}))
        mode = settings.get("mode", "off")
        if mode == "off":
            if explicit_agent_request:
                return {
                    "brain": "Agent_brain",
                    "status": "configuration_required",
                    "skipped": True,
                    "reason": "agent_mode_off",
                    "display_text": (
                        "Agent mode was requested, but it is disabled in Settings. "
                        "Choose Restricted, Approval, or Autonomous mode and select a workspace."
                    ),
                    "confidence": 100,
                    "user_visible": True,
                    "explicit_agent_request": True,
                }
            return {
                "brain": "Agent_brain",
                "status": "disabled",
                "skipped": True,
                "reason": "agent_mode_off",
                "confidence": 100,
                "user_visible": False,
            }

        try:
            root = self._workspace(settings)
        except AgentPolicyError as error:
            return {
                "brain": "Agent_brain",
                "status": "configuration_required",
                "error": "agent_workspace_unavailable",
                "display_text": str(error),
                "confidence": 0,
                "user_visible": True,
            }

        directive_actions, control = self._directive_actions(text)
        session_id = str(payload.get("session_id", "default"))
        continuation_context_used = self._continuation_context_used(payload)
        results_context = payload.get("results", {})
        creative_result = (
            results_context.get("Creative_brain", {})
            if isinstance(results_context, dict)
            else {}
        )
        code_result = (
            results_context.get("Code_brain", {})
            if isinstance(results_context, dict)
            else {}
        )
        delivery_explanation = (
            code_result.get("delivery_explanation", {})
            if isinstance(code_result, dict)
            else {}
        )
        delivery_explanation = (
            delivery_explanation
            if isinstance(delivery_explanation, dict)
            else {}
        )
        report = payload.get("understanding", {})
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        output_constraints = contract.get("output_constraints", {})
        output_constraints = output_constraints if isinstance(output_constraints, dict) else {}
        allow_delivery_notes = not bool(output_constraints.get("only_output"))
        creative_consultation_used = bool(
            isinstance(creative_result, dict)
            and (
                creative_result.get("specialist_support")
                or creative_result.get("best_idea")
                or creative_result.get("proposed_output")
            )
        )

        if "reject" in control:
            rejected = self._reject_pending(control["reject"], session_id)
            display = "Agent action was rejected and removed." if rejected else "Agent approval ID was not found for this chat."
            return {
                "brain": "Agent_brain",
                "status": "rejected" if rejected else "not_found",
                "display_text": display,
                "confidence": 100 if rejected else 40,
                "user_visible": True,
            }

        try:
            approved = "approve" in control
            if approved:
                actions = self._take_pending(control["approve"], root, session_id)
            else:
                actions = directive_actions or self._derived_actions(payload, text)

            if not actions:
                project = payload.get("results", {}).get("Project_context_brain", {})
                summary = project.get("project_summary", {}) if isinstance(project, dict) else {}
                visible = bool(explicit_agent_request or self._mutation_requested(payload, text.casefold()))
                return {
                    "brain": "Agent_brain",
                    "status": "no_changes" if visible else "observing",
                    "mode": mode,
                    "workspace": str(root),
                    "project_summary": summary,
                    "actions": [],
                    "display_text": (
                        "Agent inspected the selected project, but no verified file change was produced. "
                        "The code specialist must return concrete project files before Agent can apply them."
                        if visible else ""
                    ),
                    "missing": ["verified project files"] if visible else [],
                    "needs_help": visible,
                    "confidence": 30 if visible else 90,
                    "user_visible": visible,
                    "explicit_agent_request": explicit_agent_request,
                    "continuation_context_used": continuation_context_used,
                    "creative_consultation_used": creative_consultation_used,
                }

            mutating = [action for action in actions if action.get("type") in {"write_file", "create_file", "run_command"}]
            if mutating and not self._security_allows_mutation(payload):
                raise AgentPolicyError("Security_brain did not approve project mutation for this request.")

            for action in actions:
                self._validate_planned_action(root, action, settings, mode)

            if mode == "approval" and mutating and not approved:
                action_id = self._queue_approval(root, actions, payload)
                previews = [self._action_preview(action) for action in actions]
                return {
                    "brain": "Agent_brain",
                    "status": "approval_required",
                    "mode": mode,
                    "workspace": str(root),
                    "approval_id": action_id,
                    "planned_actions": previews,
                    "display_text": self._format_display("approval_required", root, previews, action_id),
                    "confidence": 95,
                    "user_visible": True,
                    "explicit_agent_request": explicit_agent_request,
                    "continuation_context_used": continuation_context_used,
                    "creative_consultation_used": creative_consultation_used,
                }

            execution_results: list[dict[str, Any]] = []
            for action in actions:
                try:
                    result = self._execute_action(root, action, settings, mode)
                except (AgentPolicyError, OSError, subprocess.SubprocessError) as error:
                    result = {**self._action_preview(action), "ok": False, "error": str(error)}
                execution_results.append(result)

            successful = sum(bool(item.get("ok")) for item in execution_results)
            status = "completed" if successful == len(execution_results) else "partially_completed" if successful else "blocked"
            audit_record = {
                "created_utc": self._utc_now(),
                "request_id": payload.get("_request_id"),
                "session_id": session_id,
                "mode": mode,
                "workspace": str(root),
                "status": status,
                "actions": [self._action_preview(action) for action in actions],
                "results": [
                    {key: value for key, value in item.items() if key not in {"content", "stdout", "stderr"}}
                    for item in execution_results
                ],
            }
            self._audit(audit_record)
            display_text = self._format_display(status, root, execution_results)
            if continuation_context_used:
                display_text += (
                    "\nI continued the active chat's existing Agent project and preserved "
                    "files that were not part of this change."
                )
            if creative_consultation_used:
                display_text += "\nA creative enhancement pass was considered before the code was applied."
            if allow_delivery_notes and delivery_explanation:
                summary = str(delivery_explanation.get("summary") or "").strip()
                if summary:
                    display_text += f"\n{summary}"
                implemented = [
                    str(item).strip()
                    for item in delivery_explanation.get("implemented_features", [])
                    if str(item).strip()
                ][:8]
                if implemented:
                    display_text += "\nImplemented: " + "; ".join(implemented) + "."
                validation = delivery_explanation.get("validation", {})
                if isinstance(validation, dict) and validation:
                    validation_text = ", ".join(
                        f"{key}={value}"
                        for key, value in validation.items()
                        if value not in (None, "", [], {})
                    )
                    if validation_text:
                        display_text += f"\nValidation: {validation_text}."
                run_instruction = str(delivery_explanation.get("run_instruction") or "").strip()
                if run_instruction:
                    display_text += f"\nRun: {run_instruction}"
            return {
                "brain": "Agent_brain",
                "status": status,
                "mode": mode,
                "workspace": str(root),
                "actions_attempted": len(actions),
                "actions_completed": successful,
                "action_results": execution_results,
                "changed_files": [
                    {
                        "path": item.get("path"),
                        "added_lines": item.get("added_lines", 0),
                        "removed_lines": item.get("removed_lines", 0),
                        "line_count": item.get("after_line_count", 0),
                    }
                    for item in execution_results
                    if item.get("type") == "write_file" and item.get("ok")
                ],
                "display_text": display_text,
                "confidence": round(100 * successful / max(1, len(actions)), 2),
                "user_visible": True,
                "audit_recorded": True,
                "explicit_agent_request": explicit_agent_request,
                "continuation_context_used": continuation_context_used,
                "creative_consultation_used": creative_consultation_used,
            }
        except AgentPolicyError as error:
            return {
                "brain": "Agent_brain",
                "status": "blocked",
                "mode": mode,
                "workspace": str(root),
                "display_text": f"Agent did not execute the action: {error}",
                "error": "agent_policy_blocked",
                "confidence": 100,
                "user_visible": True,
            }


brain = AgentBrain()
