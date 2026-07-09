"""
MAIN.py
Canri AI
"""

from uuid import uuid4

from Graphics import start_graphics

from Main_brain import MainBrain
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

from Learning_brain import brain as learning_brain
from Fact_Check_brain import brain as fact_check_brain
from Quality_Control_brain import brain as quality_control_brain
from Planner_brain import brain as planner_brain
from Emotion_brain import brain as emotion_brain

from Security_brain import brain as security_brain
from Knowledge_collector import start_background_collector


ACTIVE_SESSION_ID = "session_" + uuid4().hex


def register_all_brains():

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
        "Planner_brain",
        planner_brain
    )

    manager_brain.register_brain(
        "Emotion_brain",
        emotion_brain
    )

    manager_brain.register_brain(
        "Security_brain",
        security_brain
    )


def build_basic_understanding(message, corrected_text):

    text = corrected_text or message or ""
    lowered = text.lower()

    topic_rules = [
        ("code", ["code", "python", "javascript", "java", "function", "api", "json"]),
        ("game", ["game", "player", "level", "inventory", "enemy"]),
        ("science", ["science", "physics", "chemistry", "biology", "gravity", "atom"]),
        ("language", ["translate", "translation", "grammar", "synonym", "antonym", "language"]),
        ("geography", ["country", "city", "capital", "map", "gps", "river", "mountain"]),
        ("technology", ["technology", "hardware", "cpu", "gpu", "computer", "robot"]),
        ("history", ["history", "war", "empire", "ancient"]),
        ("math", ["math", "calculate", "equation", "number"]),
        ("security", ["security", "password", "hack", "bomb", "suicide"]),
        ("image_generation", ["generate image", "create image", "make image", "draw", "illustration", "poster", "logo"]),
        ("vision", ["image", "photo", "picture", "video", "file"]),
        ("voice", ["audio", "voice", "sound", "recording"]),
        ("story", ["story", "character", "world", "plot"])
    ]

    main_topic = "general"
    for topic, keywords in topic_rules:
        if any(keyword in lowered for keyword in keywords):
            main_topic = topic
            break

    intent = "question" if "?" in text or any(word in lowered for word in ["what", "how", "why", "מה", "איך", "למה"]) else "request"

    return {
        "original_text": message,
        "corrected_text": corrected_text,
        "main_topic": main_topic,
        "intent": intent,
        "words": [
            {
                "word": word,
                "exists": True,
                "connections": []
            }
            for word in text.split()[:40]
        ],
        "possible_tasks": [
            intent
        ]
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


def process_user_message(message, attached_files=None, progress_callback=None, session_id=None):

    attached_files = attached_files or []
    session_id = session_id or ACTIVE_SESSION_ID

    emit_progress(progress_callback, "spelling", "Checking spelling and cleanup")
    spelling_report = spelling_brain.process(message)
    corrected_text = spelling_report.get("corrected_text", message)

    emit_progress(
        progress_callback,
        "understanding",
        "Building Understanding_brain report"
    )

    try:
        understanding_report = understanding_brain.process({
            "original_text": message,
            "corrected_text": corrected_text,
            "attached_files": attached_files,
            "spelling": spelling_report
        })
    except Exception as error:
        understanding_report = build_basic_understanding(
            message,
            corrected_text
        )
        understanding_report["understanding_error"] = str(error)

    context = {
        "session_id": session_id,
        "_progress_callback": progress_callback,
        "original_text": message,
        "corrected_text": corrected_text,
        "attached_files": attached_files,
        "spelling": spelling_report,
        "understanding": understanding_report
    }

    emit_progress(progress_callback, "memory", "Searching and storing session memory")
    memory_result = memory_brain.process(context)

    if isinstance(memory_result, dict):
        context["memory"] = memory_result.get("memory", {})

    emit_progress(progress_callback, "manager", "Routing request through specialist brains")
    manager_result = manager_brain.process(context)
    response_result = manager_result.get("results", {}).get("Response_brain")

    if isinstance(response_result, dict):
        response_result["thinking_trace"] = build_thinking_trace(
            spelling_report,
            understanding_report,
            memory_result,
            manager_result
        )
        try:
            memory_brain.store_response(
                session_id,
                message,
                response_result.get("display_text") or response_result.get("answer", ""),
                response_result,
                manager_result
            )
        except Exception:
            pass
        emit_progress(progress_callback, "complete", "Response ready")
        return response_result

    emit_progress(progress_callback, "complete", "Fallback response ready")
    fallback_text = str(manager_result)
    try:
        memory_brain.store_response(
            session_id,
            message,
            fallback_text,
            {},
            manager_result
        )
    except Exception:
        pass
    return {
        "display_text": fallback_text,
        "answer": fallback_text,
        "thinking_trace": build_thinking_trace(
            spelling_report,
            understanding_report,
            memory_result,
            manager_result
        )
    }


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

    return {
        key: value
        for key, value in summary.items()
        if value not in [None, "", [], {}]
    }


def build_thinking_trace(spelling_report, understanding_report, memory_result, manager_result):

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
        "manager": {
            "domains_detected": manager_result.get("domains_detected"),
            "dictionary_context": manager_result.get("dictionary_context"),
            "local_data_context": manager_result.get("local_data_context"),
            "knowledge_context": manager_result.get("knowledge_context"),
            "brains_used": manager_result.get("brains_used"),
            "phases": manager_result.get("phases"),
            "system_confidence": manager_result.get("system_confidence"),
            "suggested_next_brains": manager_result.get("suggested_next_brains"),
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

    brain = MainBrain()

    start_graphics(
        message_handler=process_user_message
    )

    print("Canri AI Closed")


if __name__ == "__main__":
    main()
