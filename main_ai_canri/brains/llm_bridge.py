"""Bounded bridge between CANRI's deterministic LFM and native local LLM.

The bridge never replaces a specialist, executes model output, or bypasses
Security/Quality. It selects the most useful request, memory, evidence, and
specialist messages that fit the model context, then reviews the model's
candidate before Response_brain may use it for general conversation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from Brain_storage import load_json_resilient


CANRI_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = CANRI_ROOT / "data" / "Local_model_settings.json"
WORD_PATTERN = re.compile(r"[A-Za-z0-9_\u0590-\u05FF]+")
INTERNAL_MARKERS = (
    "here is the useful conclusion",
    "core idea:",
    "novel twist:",
    "direction:",
    "retry_request",
    "quality note:",
    "manager_context",
)
INFRASTRUCTURE_BRAINS = {
    "Memory_brain",
    "Understanding_brain",
    "Manager_brain",
    "Security_brain",
    "Quality_Control_brain",
    "Learning_brain",
    "Nervous_system_brain",
    "Collaboration_brain",
    "Answer_Enrichment_brain",
    "Response_brain",
    "LLM_bridge_brain",
    "Local_LLM_brain",
    "Local_LLM_shadow",
}


class LLMBridgeBrain:
    def __init__(self, settings_path: Path | None = None):
        self.settings_path = Path(settings_path or SETTINGS_FILE)
        self._tokenizer_key: tuple[str, int] | None = None
        self._tokenizer = None
        print("LLM Bridge Brain Loaded")

    def load_settings(self) -> dict[str, Any]:
        loaded = load_json_resilient(self.settings_path, default={})
        return loaded if isinstance(loaded, dict) else {}

    @staticmethod
    def resolve_canri_path(value: Any) -> Path | None:
        relative = str(value or "").strip()
        if not relative:
            return None
        candidate = Path(relative)
        return candidate if candidate.is_absolute() else CANRI_ROOT / candidate

    def release_readiness(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Read the sealed quality gate that controls user-facing LLM output."""

        report_path = self.resolve_canri_path(
            settings.get("native_sealed_evaluation_path")
        )
        report = load_json_resilient(report_path, default={}) if report_path else {}
        if not isinstance(report, dict):
            report = {}
        automated = bool(report.get("automated_gate_passed"))
        manual = bool(report.get("manual_review_approved"))
        return {
            "report_available": bool(report),
            "report_path": str(report_path) if report_path else "",
            "status": str(report.get("status") or "not_evaluated"),
            "automated_gate_passed": automated,
            "manual_review_approved": manual,
            "ready_for_user_answer": automated and manual,
            "reference_loss": (
                report.get("reference_metrics", {}).get("loss")
                if isinstance(report.get("reference_metrics"), dict)
                else None
            ),
            "generation_score": (
                report.get("generation_metrics", {}).get("average_score")
                if isinstance(report.get("generation_metrics"), dict)
                else None
            ),
            "semantic_pass_rate": (
                report.get("generation_metrics", {}).get("semantic_pass_rate")
                if isinstance(report.get("generation_metrics"), dict)
                else None
            ),
        }

    def tokenizer(self, settings: dict[str, Any]):
        relative = str(settings.get("native_tokenizer_path") or "").strip()
        path = (CANRI_ROOT / relative).resolve()
        if not relative or not path.is_file():
            return None
        key = (str(path), path.stat().st_mtime_ns)
        if self._tokenizer_key == key and self._tokenizer is not None:
            return self._tokenizer
        try:
            from domain_packages.local_llm.tokenizer import CanriTokenizer

            self._tokenizer = CanriTokenizer.load(path)
            self._tokenizer_key = key
            return self._tokenizer
        except (ImportError, OSError, ValueError, json.JSONDecodeError):
            return None

    def token_count(self, text: str, settings: dict[str, Any]) -> int:
        tokenizer = self.tokenizer(settings)
        if tokenizer is not None:
            return len(tokenizer.encode(str(text), add_special_tokens=False))
        return max(1, (len(str(text).encode("utf-8", errors="replace")) + 3) // 4)

    def fit_tokens(self, text: str, limit: int, settings: dict[str, Any]) -> str:
        value = str(text or "").strip()
        limit = max(1, int(limit))
        tokenizer = self.tokenizer(settings)
        if tokenizer is None:
            return value[: limit * 4]
        token_ids = tokenizer.encode(value, add_special_tokens=False)
        if len(token_ids) <= limit:
            return value
        return tokenizer.decode(token_ids[:limit]).rstrip()

    @staticmethod
    def as_text(value: Any, character_limit: int = 6000) -> str:
        if value in (None, "", [], {}):
            return ""
        if isinstance(value, str):
            return value[:character_limit]
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )[:character_limit]
        except (TypeError, ValueError, RecursionError):
            return str(value)[:character_limit]

    @staticmethod
    def requirement_texts(understanding: dict[str, Any]) -> list[str]:
        contract = understanding.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        output = []
        for item in contract.get("requirements", []):
            if isinstance(item, dict):
                text = item.get("text") or item.get("requirement") or item.get("id")
            else:
                text = item
            if str(text or "").strip():
                output.append(str(text).strip())
        constraints = contract.get("output_constraints", {})
        if isinstance(constraints, dict) and constraints:
            output.append("Output constraints: " + LLMBridgeBrain.as_text(constraints, 1200))
        return output[:24]

    @staticmethod
    def useful_result_text(brain_name: str, result: dict[str, Any]) -> str:
        fields = (
            "final_output",
            "display_text",
            "answer",
            "generated_code",
            "story",
            "support_response",
            "summary",
            "result",
            "best_answer",
            "facts",
            "plan",
        )
        parts = []
        for field in fields:
            value = result.get(field)
            if value not in (None, "", [], {}):
                parts.append(f"{field}: {LLMBridgeBrain.as_text(value, 5000)}")
                if len(parts) >= 2:
                    break
        project_files = result.get("project_files")
        if isinstance(project_files, dict) and project_files:
            parts.append("project files: " + ", ".join(str(path) for path in list(project_files)[:20]))
        return f"{brain_name}\n" + "\n".join(parts) if parts else ""

    def specialist_sections(self, results: dict[str, Any]) -> list[tuple[str, str]]:
        sections = []
        for brain_name, result in results.items():
            if brain_name in INFRASTRUCTURE_BRAINS or not isinstance(result, dict):
                continue
            if result.get("error") or result.get("skipped"):
                continue
            text = self.useful_result_text(brain_name, result)
            if text:
                sections.append((f"SPECIALIST {brain_name}", text))
        return sections[:12]

    @staticmethod
    def conversation_value(data: dict[str, Any]) -> Any:
        memory = data.get("memory", {})
        if not isinstance(memory, dict):
            return {}
        conversation = memory.get("conversation", {})
        if not isinstance(conversation, dict):
            return conversation
        compact = {
            key: conversation.get(key)
            for key in (
                "title",
                "turn_count",
                "summary",
                "continuation_request",
                "continuation_kind",
                "continuation_source",
                "relevant_turns",
                "recent_turns",
                "last_completed_turn",
                "thread_state",
            )
            if conversation.get(key) not in (None, "", [], {})
        }
        return compact or conversation

    def build_packet(self, data: dict[str, Any]) -> dict[str, Any]:
        settings = self.load_settings()
        context_window = max(128, int(settings.get("native_context_tokens", 500)))
        output_reserve = max(32, int(settings.get("native_output_reserve_tokens", 160)))
        prompt_budget = max(64, context_window - min(output_reserve, context_window // 2) - 8)
        instruction = (
            "[OUTPUT]\nAnswer the user directly. Use specialist conclusions as authoritative. "
            "For general conversation, be natural and helpful. Return only the proposed user-facing answer."
        )
        instruction_tokens = self.token_count(instruction, settings)
        request = str(data.get("original_text") or data.get("corrected_text") or "").strip()
        understanding = data.get("understanding", {})
        understanding = understanding if isinstance(understanding, dict) else {}
        results = data.get("results", {})
        results = results if isinstance(results, dict) else {}
        requirements = self.requirement_texts(understanding)
        quality = data.get("quality_feedback") or results.get("Quality_Control_brain", {})
        failed = data.get("failed_requirements", [])
        if not failed and isinstance(quality, dict):
            failed = quality.get("failed_requirements", [])

        mandatory = [
            ("ROLE", "You are CANRI's local conversation and synthesis assistant. Never replace a specialist, invent evidence, expose internal reports, or execute code."),
            ("USER REQUEST", request),
            ("REQUEST CONTRACT", "\n".join(f"- {item}" for item in requirements)),
            ("QUALITY CORRECTIONS", self.as_text(failed, 2400)),
        ]
        optional = [
            *self.specialist_sections(results),
            ("RELEVANT MEMORY", self.as_text(data.get("memory", {}).get("matches", []) if isinstance(data.get("memory"), dict) else "", 4000)),
            ("CONVERSATION", self.as_text(self.conversation_value(data), 8000)),
            ("UNDERSTANDING", self.as_text({
                "intent": understanding.get("intent"),
                "topic": understanding.get("main_topic"),
                "requested_action": understanding.get("requested_action"),
                "meaning_frame": understanding.get("meaning_frame"),
            }, 2400)),
            ("RETRIEVED KNOWLEDGE", self.as_text(data.get("knowledge") or data.get("data_context"), 5000)),
        ]

        selected = []
        dropped = []
        # Reserve the output instruction and separator overhead before fitting
        # context. This prevents a long report from truncating the final rule.
        separator_tokens = self.token_count("\n\n", settings)
        remaining = max(24, prompt_budget - instruction_tokens - separator_tokens)
        for title, value in [*mandatory, *optional]:
            value = str(value or "").strip()
            if not value:
                continue
            header = f"[{title}]\n"
            header_tokens = self.token_count(header, settings)
            available = remaining - header_tokens
            if available < 4:
                dropped.append(title)
                continue
            fitted = self.fit_tokens(value, available, settings)
            section = header + fitted
            used = self.token_count(section, settings)
            if not fitted:
                dropped.append(title)
                continue
            selected.append(section)
            remaining -= used + separator_tokens
            if self.token_count(value, settings) > available:
                dropped.append(f"{title}:truncated")

        prompt = "\n\n".join([instruction, *selected]).strip()
        while selected and self.token_count(prompt, settings) > prompt_budget:
            removed = selected.pop()
            dropped.append(removed.split("]", 1)[0].lstrip("[") + ":budget")
            prompt = "\n\n".join([instruction, *selected]).strip()
        prompt = self.fit_tokens(prompt, prompt_budget, settings)
        conversation_text = self.as_text(self.conversation_value(data), 20_000)
        full_conversation_used = bool(
            conversation_text
            and "CONVERSATION:truncated" not in dropped
            and "CONVERSATION" not in dropped
        )
        return {
            "native_prompt": prompt,
            "context_window_tokens": context_window,
            "prompt_budget_tokens": prompt_budget,
            "prompt_tokens": self.token_count(prompt, settings),
            "output_reserve_tokens": output_reserve,
            "full_conversation_used": full_conversation_used,
            "selection_mode": "full_when_fits_else_priority_truncation",
            "selected_sections": [
                "OUTPUT",
                *[
                    item.split("]", 1)[0].lstrip("[")
                    for item in selected
                    if item.startswith("[")
                ],
            ],
            "dropped_or_truncated_sections": dropped,
            "specialist_count": len(self.specialist_sections(results)),
        }

    @staticmethod
    def terms(text: str) -> set[str]:
        return {
            token.casefold()
            for token in WORD_PATTERN.findall(str(text or ""))
            if len(token) > 1
        }

    def review_candidate(self, data: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
        results = data.get("results", {})
        results = results if isinstance(results, dict) else {}
        local = results.get("Local_LLM_brain", {})
        local = local if isinstance(local, dict) else {}
        candidate = str(local.get("final_output") or "").strip()
        request = str(data.get("original_text") or data.get("corrected_text") or "")
        specialist_count = int(packet.get("specialist_count", 0) or 0)
        previous_bridge = results.get("LLM_bridge_brain", {})
        if isinstance(previous_bridge, dict):
            previous_packet = previous_bridge.get("context_packet", {})
            if isinstance(previous_packet, dict):
                specialist_count = max(
                    specialist_count,
                    int(previous_packet.get("specialist_count", 0) or 0),
                )
        lowered = candidate.casefold()
        request_terms = self.terms(request)
        candidate_terms = self.terms(candidate)
        overlap = len(request_terms.intersection(candidate_terms)) / max(1, len(request_terms))
        issues = []
        if local.get("status") != "completed" or not candidate:
            issues.append("model_candidate_missing")
        if len(candidate) < 8:
            issues.append("candidate_too_short")
        if any(marker in lowered for marker in INTERNAL_MARKERS):
            issues.append("internal_report_leak")
        if request_terms and overlap < 0.04:
            issues.append("weak_request_relevance")
        if candidate.count("�"):
            issues.append("invalid_text_encoding")
        if any(marker in lowered for marker in ("<|user|>", "<|assistant|>", "[user request]", "task:")):
            issues.append("model_protocol_leak")
        candidate_word_list = WORD_PATTERN.findall(candidate.casefold())
        if len(candidate_word_list) >= 12:
            unique_ratio = len(set(candidate_word_list)) / len(candidate_word_list)
            if unique_ratio < 0.35:
                issues.append("excessive_repetition")
        request_has_hebrew = bool(re.search(r"[\u0590-\u05FF]", request))
        candidate_has_hebrew = bool(re.search(r"[\u0590-\u05FF]", candidate))
        if request_has_hebrew and not candidate_has_hebrew:
            issues.append("language_mismatch")
        settings = self.load_settings()
        readiness = self.release_readiness(settings)
        if not readiness["ready_for_user_answer"]:
            issues.append("sealed_quality_gate_not_passed")
        accepted_for_general_chat = not issues and specialist_count == 0
        return {
            "candidate_available": bool(candidate),
            "candidate_accepted": accepted_for_general_chat,
            "candidate_role": "general_conversation" if accepted_for_general_chat else "advisory_only",
            "candidate_relevance": round(overlap, 4),
            "candidate_issues": issues,
            "assistant_suggestion": candidate[:8000],
            "final_output": candidate if accepted_for_general_chat else "",
            "specialists_preserved": specialist_count > 0,
            "release_readiness": readiness,
        }

    def process(self, data: Any) -> dict[str, Any]:
        payload = data if isinstance(data, dict) else {"original_text": str(data)}
        packet = self.build_packet(payload)
        results = payload.get("results", {})
        local_present = isinstance(results, dict) and isinstance(
            results.get("Local_LLM_brain"), dict
        )
        review = self.review_candidate(payload, packet) if local_present else {
            "candidate_available": False,
            "candidate_accepted": False,
            "candidate_role": "context_preparation",
            "candidate_issues": [],
            "specialists_preserved": True,
            "release_readiness": self.release_readiness(self.load_settings()),
        }
        return {
            "brain": "LLM_bridge_brain",
            "status": "candidate_reviewed" if local_present else "context_ready",
            "available": True,
            "replaces_specialists": False,
            "executes_output": False,
            "quality_has_final_authority": True,
            "communication": {
                "reads_from": [
                    item.get("brain")
                    for item in payload.get("results", {}).values()
                    if isinstance(item, dict) and item.get("brain")
                ][:30] if isinstance(payload.get("results"), dict) else [],
                "writes_to": ["Local_LLM_brain", "Quality_Control_brain", "Response_brain"],
            },
            "context_packet": packet,
            **review,
        }


brain = LLMBridgeBrain()


__all__ = ["LLMBridgeBrain", "brain"]
