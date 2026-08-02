"""
MAIN.py
Canri AI
"""

import re
import time
from uuid import uuid4

from Brain_runtime import brain_runtime
from Graphics import start_graphics
from Agent_settings import load_agent_settings
from brains import BRAIN_MODULES

from Main_brain import brain as main_brain
from Manager_brain import brain as manager_brain

# מוחות
from Spelling_brain import brain as spelling_brain
from Understanding_brain import brain as understanding_brain
from Memory_brain import brain as memory_brain

from Research_brain import brain as research_brain
from Reasoning_brain import brain as reasoning_brain
from Response_brain import brain as response_brain

from Creative_brain import brain as creative_brain
from Code_brain import brain as code_brain

from Math_brain import brain as math_brain
from Science_brain import brain as science_brain
from Language_brain import brain as language_brain
from History_brain import brain as history_brain
from Geography_brain import brain as geography_brain

from Technology_brain import brain as technology_brain
from Game_brain import brain as game_brain

from Story_brain import brain as story_brain
from Character_brain import brain as character_brain
from World_brain import brain as world_brain
from Image_brain import brain as image_brain
from Movie_brain import brain as movie_brain
from Movie_settings import load_movie_settings
from Vision_brain import brain as vision_brain
from Voice_brain import brain as voice_brain

from Learning_brain import brain as learning_brain
from Fact_Check_brain import brain as fact_check_brain
from Quality_Control_brain import brain as quality_control_brain
from Collaboration_brain import brain as collaboration_brain
from Nervous_system_brain import brain as nervous_system_brain
from Planner_brain import brain as planner_brain
from Emotion_brain import brain as emotion_brain
from Answer_Enrichment_brain import brain as answer_enrichment_brain
from Project_context_brain import brain as project_context_brain
from LLM_bridge_brain import brain as llm_bridge_brain
from Local_LLM_brain import brain as local_llm_brain
from Agent_brain import brain as agent_brain

try:
    from Semantic_router import rank_semantic_domains, routes_for_domains
except Exception:
    rank_semantic_domains = None
    routes_for_domains = None

from Security_brain import brain as security_brain
from Knowledge_collector import start_background_collector
from Scanner_knowledge import start_background_web_scanners


ACTIVE_SESSION_ID = "session_" + uuid4().hex
END_TO_END_REQUEST_BUDGET_SECONDS = None


def remaining_request_timeout(deadline, cap):
    if deadline is None:
        return None
    return max(0.05, min(float(cap), deadline - time.perf_counter()))


def _register_all_brains_legacy():

    manager_brain.register_brain(
        "Spelling_brain",
        spelling_brain
    )

    manager_brain.register_brain(
        "Understanding_brain",
        understanding_brain
    )

    manager_brain.register_brain(
        "Memory_brain",
        memory_brain
    )

    manager_brain.register_brain(
        "Research_brain",
        research_brain
    )

    manager_brain.register_brain(
        "Reasoning_brain",
        reasoning_brain
    )

    manager_brain.register_brain(
        "Response_brain",
        response_brain
    )

    manager_brain.register_brain(
        "Creative_brain",
        creative_brain
    )

    manager_brain.register_brain(
        "Code_brain",
        code_brain
    )

    manager_brain.register_brain(
        "Math_brain",
        math_brain
    )

    manager_brain.register_brain(
        "Science_brain",
        science_brain
    )

    manager_brain.register_brain(
        "Language_brain",
        language_brain
    )

    manager_brain.register_brain(
        "History_brain",
        history_brain
    )

    manager_brain.register_brain(
        "Geography_brain",
        geography_brain
    )

    manager_brain.register_brain(
        "Technology_brain",
        technology_brain
    )

    manager_brain.register_brain(
        "Game_brain",
        game_brain
    )

    manager_brain.register_brain(
        "Story_brain",
        story_brain
    )

    manager_brain.register_brain(
        "Character_brain",
        character_brain
    )

    manager_brain.register_brain(
        "World_brain",
        world_brain
    )

    manager_brain.register_brain(
        "Image_brain",
        image_brain
    )

    manager_brain.register_brain(
        "Movie_brain",
        movie_brain
    )

    manager_brain.register_brain(
        "Vision_brain",
        vision_brain
    )

    manager_brain.register_brain(
        "Voice_brain",
        voice_brain
    )

    manager_brain.register_brain(
        "Learning_brain",
        learning_brain
    )

    manager_brain.register_brain(
        "Fact_Check_brain",
        fact_check_brain
    )

    manager_brain.register_brain(
        "Quality_Control_brain",
        quality_control_brain
    )

    manager_brain.register_brain(
        "Collaboration_brain",
        collaboration_brain
    )

    manager_brain.register_brain(
        "Nervous_system_brain",
        nervous_system_brain
    )

    manager_brain.register_brain(
        "Planner_brain",
        planner_brain
    )

    manager_brain.register_brain(
        "Emotion_brain",
        emotion_brain
    )

    manager_brain.register_brain(
        "Answer_Enrichment_brain",
        answer_enrichment_brain
    )

    manager_brain.register_brain(
        "Project_context_brain",
        project_context_brain
    )

    manager_brain.register_brain(
        "LLM_bridge_brain",
        llm_bridge_brain
    )

    manager_brain.register_brain(
        "Local_LLM_brain",
        local_llm_brain
    )

    manager_brain.register_brain(
        "Agent_brain",
        agent_brain
    )

    manager_brain.register_brain(
        "Security_brain",
        security_brain
    )


def register_all_brains():
    """Register every specialist through the organized brains catalog."""

    missing = []
    for name in BRAIN_MODULES:
        if name in {"Main_brain", "Manager_brain"}:
            continue
        brain_object = globals().get(name.lower())
        if brain_object is None:
            missing.append(name)
            continue
        manager_brain.register_brain(name, brain_object)

    if missing:
        # Preserve startup compatibility while the remaining legacy modules
        # are migrated physically into the brains package.
        _register_all_brains_legacy()


def build_basic_understanding(message, corrected_text):

    text = corrected_text or message or ""
    lowered = text.lower()
    words = re.findall(r"[A-Za-z\u0590-\u05FF][A-Za-z0-9_\-\u0590-\u05FF']*", lowered)
    word_reports = []
    sentence_graph = {}
    try:
        word_reports = understanding_brain.analyze_words(words)
        sentence_graph = understanding_brain.build_sentence_graph(words, word_reports)
    except Exception:
        word_reports = []
        sentence_graph = {}

    ranked = []
    if rank_semantic_domains is not None:
        try:
            ranked = rank_semantic_domains(
                text,
                word_reports=word_reports,
                scanner_matches=[],
                code_context={"has_code": bool(re.search(r"```|\bdef\s+\w+\s*\(|\bclass\s+\w+", text))},
                limit=6,
            )
        except Exception:
            ranked = []
    main_topic = str(ranked[0].get("domain") or "general") if ranked else "general"
    try:
        intent, intent_confidence, intent_hits = understanding_brain.detect_intent(
            text,
            words,
            main_topic,
        )
        requested_action = understanding_brain.detect_requested_action(
            text,
            words,
            word_reports,
            sentence_graph,
            main_topic,
            intent,
        )
        intent = requested_action.get("intent_override") or intent
    except Exception:
        intent = "question" if "?" in text else "request"
        intent_confidence = 35
        intent_hits = {}
        requested_action = {
            "is_action_request": False,
            "action_word": None,
            "target": None,
        }

    routes = routes_for_domains(ranked[:1]) if routes_for_domains and ranked else []
    only_match = re.search(r"only\s+output\s+(?:the\s+)?([^\n.!?]{2,100})", lowered)
    fallback_requirements = []
    for line in text.splitlines():
        clean = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if clean and (
            re.match(r"^(?:must|include|add|support|use|show|return|only)\b", clean.lower())
            or " must " in clean.lower()
        ):
            fallback_requirements.append({
                "id": f"fallback_{len(fallback_requirements) + 1}",
                "text": clean,
                "kind": "explicit_constraint"
            })

    return {
        "original_text": message,
        "corrected_text": corrected_text,
        "main_topic": main_topic,
        "intent": intent,
        "intent_confidence": intent_confidence,
        "intent_hits": intent_hits,
        "requested_action": requested_action,
        "words": word_reports[:40],
        "semantic_domain_profiles": ranked,
        "central_domains": [main_topic] if main_topic != "general" else [],
        "central_domain_details": ranked[:1],
        "routing_hints": list(dict.fromkeys(["Memory_brain", *routes, "Response_brain"])),
        "possible_tasks": [
            intent
        ],
        "request_contract": {
            "action": requested_action.get("action_word"),
            "topic": main_topic,
            "intent": intent,
            "requirements": fallback_requirements,
            "output_constraints": {
                "requested_format": "code" if intent == "code_generation" else "answer",
                "only_output": only_match.group(1).strip() if only_match else None,
                "forbidden_sections": [
                    name
                    for name, marker in [
                        ("plan", "do not output a plan"),
                        ("placeholders", "do not output placeholders"),
                        ("explanation", "do not output an explanation")
                    ]
                    if marker in lowered
                ],
                "must_be_runnable": "runnable" in lowered or "must run" in lowered
            },
            "continuation": {
                "requested": any(marker in lowered for marker in ["continue", "same code", "same story", "previous"])
            }
        }
    }


def emit_progress(progress_callback, stage, detail=None, data=None):

    if not progress_callback:
        return

    try:
        progress_callback({
            "stage": stage,
            "detail": detail,
            "data": data or {}
        })
    except Exception:
        pass


def safe_processing_fallback(message):

    if re.search(r"[\u0590-\u05FF]", str(message or "")):
        return "לא הצלחתי להשלים את הבקשה בצורה אמינה. אפשר לנסות שוב או לנסח אותה מעט אחרת."

    return (
        "I could not complete the request reliably. "
        "Please try again or rephrase it slightly."
    )


def process_user_message(message, attached_files=None, progress_callback=None, session_id=None):

    attached_files = attached_files or []
    session_id = session_id or ACTIVE_SESSION_ID
    request_id = "request_" + uuid4().hex
    request_deadline = (
        time.perf_counter() + END_TO_END_REQUEST_BUDGET_SECONDS
        if END_TO_END_REQUEST_BUDGET_SECONDS is not None
        else None
    )

    if not manager_brain.brains:
        register_all_brains()

    emit_progress(progress_callback, "spelling", "Checking spelling and cleanup")
    spelling_execution = brain_runtime.invoke(
        "Spelling_brain",
        spelling_brain,
        message,
        phase="input_spelling",
        timeout_seconds=remaining_request_timeout(request_deadline, 2.5),
        request_id=request_id
    )
    spelling_report = spelling_execution.result
    if not spelling_execution.ok:
        spelling_report = {
            "brain": "Spelling_brain",
            "original_text": message,
            "corrected_text": message,
            "corrections": [],
            "error": spelling_execution.result.get("error")
        }
    corrected_text = spelling_report.get("corrected_text", message)

    emit_progress(
        progress_callback,
        "understanding",
        "Building Understanding_brain report"
    )

    understanding_execution = brain_runtime.invoke(
        "Understanding_brain",
        understanding_brain,
        {
            "_request_id": request_id,
            "original_text": message,
            "corrected_text": corrected_text,
            "attached_files": attached_files,
            "spelling": spelling_report
        },
        phase="input_understanding",
        timeout_seconds=remaining_request_timeout(request_deadline, 5.0),
        request_id=request_id
    )
    understanding_report = understanding_execution.result
    if not understanding_execution.ok:
        understanding_report = build_basic_understanding(
            message,
            corrected_text
        )
        understanding_report["understanding_error"] = (
            understanding_execution.result.get("error", "understanding_failed")
        )

    context = {
        "_request_id": request_id,
        "session_id": session_id,
        "_progress_callback": progress_callback,
        "original_text": message,
        "corrected_text": corrected_text,
        "attached_files": attached_files,
        "spelling": spelling_report,
        "understanding": understanding_report
    }
    context["agent_settings"] = load_agent_settings()
    movie_settings = load_movie_settings()
    context["movie_render_settings"] = movie_settings
    context["execute_movie_render"] = bool(movie_settings.get("allow_paid_render"))
    context["movie_render_model"] = movie_settings.get("model", "gen4.5")
    context["movie_render_budget_usd"] = movie_settings.get("budget_usd", 25.0)
    if request_deadline is not None:
        context["_request_deadline_monotonic"] = request_deadline

    emit_progress(progress_callback, "memory", "Searching and storing session memory")
    memory_execution = brain_runtime.invoke(
        "Memory_brain",
        memory_brain,
        context,
        phase="input_memory",
        timeout_seconds=remaining_request_timeout(request_deadline, 3.5),
        request_id=request_id
    )
    memory_result = memory_execution.result

    if memory_execution.ok and isinstance(memory_result, dict):
        context["memory"] = memory_result.get("memory", {})
    else:
        context["memory"] = {
            "session_id": session_id,
            "memory_found": 0,
            "conversation": {},
            "error": memory_result.get("error", "memory_unavailable")
        }

    emit_progress(progress_callback, "manager", "Routing request through specialist brains")
    manager_execution = brain_runtime.invoke(
        "Manager_brain",
        manager_brain,
        context,
        phase="request_orchestration",
        timeout_seconds=remaining_request_timeout(
            request_deadline,
            END_TO_END_REQUEST_BUDGET_SECONDS
        ),
        request_id=request_id
    )
    manager_result = manager_execution.result
    response_result = manager_result.get("results", {}).get("Response_brain")

    if isinstance(response_result, dict):
        agent_result = manager_result.get("results", {}).get("Agent_brain", {})
        if isinstance(agent_result, dict) and agent_result.get("action_results"):
            # The GUI uses this structured result to show a review card with
            # file-level additions, removals, and a code preview.
            response_result["agent_changes"] = agent_result
        storage_payload = {
            "session_id": session_id,
            "user_text": message,
            "canri_text": response_result.get("display_text")
            or response_result.get("answer", ""),
            "response_result": response_result,
            "manager_result": manager_result,
        }
        try:
            stored_turn = memory_brain.store_response(
                session_id,
                message,
                response_result.get("display_text") or response_result.get("answer", ""),
                response_result,
                manager_result
            )
            brain_runtime.record_information_exchange(
                "Memory_brain",
                storage_payload,
                stored_turn,
                request_id=request_id,
                caller_brain="Response_brain",
                phase="response_memory_write",
            )
        except Exception as error:
            brain_runtime.record_information_exchange(
                "Memory_brain",
                storage_payload,
                {"stored": False, "error_type": type(error).__name__},
                request_id=request_id,
                caller_brain="Response_brain",
                phase="response_memory_write",
                status="error",
            )
        memory_usage = brain_runtime.finalize_request_memory(
            request_id,
            session_id=session_id,
            user_preview=message,
        )
        response_result["memory_usage"] = memory_usage
        response_result["thinking_trace"] = build_thinking_trace(
            spelling_report,
            understanding_report,
            memory_result,
            manager_result,
            memory_usage,
        )
        brain_runtime.flush_statistics()
        emit_progress(progress_callback, "complete", "Response ready")
        return response_result

    emit_progress(progress_callback, "complete", "Fallback response ready")
    fallback_text = safe_processing_fallback(message)
    fallback_storage_payload = {
        "session_id": session_id,
        "user_text": message,
        "canri_text": fallback_text,
        "response_result": {},
        "manager_result": manager_result,
    }
    try:
        stored_turn = memory_brain.store_response(
            session_id,
            message,
            fallback_text,
            {},
            manager_result
        )
        brain_runtime.record_information_exchange(
            "Memory_brain",
            fallback_storage_payload,
            stored_turn,
            request_id=request_id,
            caller_brain="Response_brain",
            phase="fallback_memory_write",
        )
    except Exception as error:
        brain_runtime.record_information_exchange(
            "Memory_brain",
            fallback_storage_payload,
            {"stored": False, "error_type": type(error).__name__},
            request_id=request_id,
            caller_brain="Response_brain",
            phase="fallback_memory_write",
            status="error",
        )
    memory_usage = brain_runtime.finalize_request_memory(
        request_id,
        session_id=session_id,
        user_preview=message,
    )
    brain_runtime.flush_statistics()
    return {
        "display_text": fallback_text,
        "answer": fallback_text,
        "memory_usage": memory_usage,
        "thinking_trace": build_thinking_trace(
            spelling_report,
            understanding_report,
            memory_result,
            manager_result,
            memory_usage,
        )
    }


def manage_chat_memory(action, chat_id=None, title=None):

    if action == "create":
        return memory_brain.create_session(chat_id, title)
    if action == "rename":
        return memory_brain.rename_session(chat_id, title)
    if action == "delete":
        return memory_brain.delete_session(chat_id)
    if action == "clear_all":
        return memory_brain.clear_conversation_memory()
    raise ValueError(f"Unknown chat memory action: {action}")


def summarize_brain_result(result):

    if not isinstance(result, dict):
        return {
            "type": type(result).__name__
        }

    summary = {
        "brain": result.get("brain"),
        "confidence": result.get("confidence"),
        "error": result.get("error"),
        "skipped": result.get("skipped"),
        "needs_help": result.get("needs_help"),
        "needs_creative_brain": result.get("needs_creative_brain"),
        "needs_security": result.get("needs_security"),
        "keys": sorted(str(key) for key in result.keys())[:20]
    }

    for key in [
        "main_topic",
        "intent",
        "task_type",
        "language",
        "memory_found",
        "matched_functions",
        "articles_found",
        "source",
        "verdict"
    ]:
        if key in result:
            summary[key] = result.get(key)

    if isinstance(result.get("simulation"), dict):
        summary["simulation"] = result["simulation"]

    if isinstance(result.get("evolution"), dict):
        evolution = result["evolution"]
        summary["evolution"] = {
            "rounds_completed": evolution.get("rounds_completed"),
            "stop_reason": evolution.get("stop_reason"),
            "algorithm": evolution.get("algorithm")
        }

    if isinstance(result.get("quality"), dict):
        summary["quality"] = result["quality"]

    if isinstance(result.get("assembly_plan"), dict):
        plan = result["assembly_plan"]
        summary["assembly_plan"] = {
            "task_type": plan.get("task_type"),
            "steps": plan.get("steps", [])[:8],
            "ordered_ids": plan.get("ordered_ids", [])[:12],
            "data_files_used": plan.get("data_files_used", [])
        }

    if isinstance(result.get("visible_work_summary"), dict):
        summary["visible_work_summary"] = result["visible_work_summary"]

    if isinstance(result.get("suggested_follow_up_tasks"), list):
        summary["suggested_follow_up_tasks"] = result["suggested_follow_up_tasks"][:4]

    return {
        key: value
        for key, value in summary.items()
        if value not in [None, "", [], {}]
    }


def build_thinking_trace(
    spelling_report,
    understanding_report,
    memory_result,
    manager_result,
    memory_usage=None,
):

    results = manager_result.get("results", {}) if isinstance(manager_result, dict) else {}

    return {
        "title": "Canri thinking trace",
        "note": (
            "This is a visible decision trace: inputs, detected intent, "
            "brains used, confidence, selected outputs, and simulation summaries. "
            "It is not hidden private chain-of-thought."
        ),
        "spelling": {
            "corrected_text": spelling_report.get("corrected_text"),
            "changed": spelling_report.get("changed"),
            "confidence": spelling_report.get("confidence"),
            "mode": spelling_report.get("mode"),
            "mode_reason": spelling_report.get("mode_reason"),
            "input_size": spelling_report.get("input_size"),
            "corrections_count": spelling_report.get("corrections_count"),
            "changed_count": spelling_report.get("changed_count"),
            "changed_items": [
                item
                for item in spelling_report.get("corrections", [])
                if isinstance(item, dict) and item.get("changed")
            ][:20]
        } if isinstance(spelling_report, dict) else {},
        "understanding": {
            "main_topic": understanding_report.get("main_topic"),
            "topics": understanding_report.get("topics"),
            "central_domains": understanding_report.get("central_domains"),
            "central_domain_details": understanding_report.get("central_domain_details"),
            "intent": understanding_report.get("intent"),
            "language": understanding_report.get("language"),
            "features": understanding_report.get("features"),
            "possible_tasks": understanding_report.get("possible_tasks"),
            "routing_hints": understanding_report.get("routing_hints"),
            "meaning_frame": understanding_report.get("meaning_frame"),
            "graph_confidence": understanding_report.get("graph_confidence"),
            "sentence_graph": {
                "nodes": understanding_report.get("sentence_graph", {}).get("nodes", [])[:30],
                "edges": understanding_report.get("sentence_graph", {}).get("edges", [])[:40],
                "confidence": understanding_report.get("sentence_graph", {}).get("confidence")
            },
            "confidence": understanding_report.get("confidence")
        } if isinstance(understanding_report, dict) else {},
        "memory": memory_result.get("memory", {}) if isinstance(memory_result, dict) else {},
        "memory_usage": memory_usage if isinstance(memory_usage, dict) else {},
        "manager": {
            "domains_detected": manager_result.get("domains_detected"),
            "dictionary_context": manager_result.get("dictionary_context"),
            "local_data_context": manager_result.get("local_data_context"),
            "knowledge_context": manager_result.get("knowledge_context"),
            "brains_used": manager_result.get("brains_used"),
            "phases": manager_result.get("phases"),
            "system_confidence": manager_result.get("system_confidence"),
            "suggested_next_brains": manager_result.get("suggested_next_brains"),
            "suggested_follow_up_tasks": manager_result.get("suggested_follow_up_tasks"),
            "visible_work_summary": manager_result.get("visible_work_summary"),
            "missing_or_skipped": manager_result.get("missing_or_skipped")
        } if isinstance(manager_result, dict) else {},
        "brain_results": {
            brain_name: summarize_brain_result(result)
            for brain_name, result in results.items()
            if brain_name != "Response_brain"
        }
    }


def main():

    print("=" * 50)
    print("Starting Canri AI")
    print("=" * 50)

    register_all_brains()

    try:
        start_background_collector()
    except Exception as error:
        print(f"Knowledge collector skipped: {error}")

    try:
        start_background_web_scanners()
    except Exception as error:
        print(f"Web scanners skipped: {error}")

    startup_status = main_brain.process({"command": "startup"})
    print(f"Canri AI {startup_status['version']} ready")

    start_graphics(
        message_handler=process_user_message,
        memory_handler=manage_chat_memory
    )

    print("Canri AI Closed")


if __name__ == "__main__":
    main()
