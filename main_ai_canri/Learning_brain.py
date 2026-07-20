"""
Learning_brain.py
Canri AI

Learning_brain learns from brain reports and system performance.
It does not blindly trust output. It rates local reliability, records lessons,
tracks brain performance, and asks Creative_brain for help when a brain is stuck.
"""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json, load_json_resilient


DATA_DIR = Path(__file__).parent / "data"
LEARNING_HISTORY_FILE = DATA_DIR / "Learning_history.json"
LEARNING_STATS_FILE = DATA_DIR / "Learning_statistics.json"
BRAIN_PERFORMANCE_FILE = DATA_DIR / "Brain_performance.json"
LEARNING_RULES_FILE = DATA_DIR / "Learning_rules.json"
IMPROVEMENT_QUEUE_FILE = DATA_DIR / "Improvement_queue.json"

MAX_HISTORY_ENTRIES = 1500
MAX_QUEUE_ENTRIES = 1500

DEFAULT_RULES = [
    {
        "id": "learn_only_from_same_chat_context",
        "name": "Learn only from active chat context",
        "rule": "Do not let memories from one chat change answers in another chat unless the user explicitly asks to use older chats.",
        "priority": 100
    },
    {
        "id": "prefer_current_user_intent",
        "name": "Prefer current user intent",
        "rule": "The current Understanding_brain intent is stronger than older memory matches.",
        "priority": 95
    },
    {
        "id": "code_request_requires_code_output",
        "name": "Code request requires code output",
        "rule": "If the current intent is code_generation, prefer Code_brain output over Story_brain, Creative_brain narrative output, or Research_brain facts.",
        "priority": 95
    },
    {
        "id": "story_request_requires_story_output",
        "name": "Story request requires story output",
        "rule": "If the current intent is story_creation, show the final story, not the evolution report or research facts.",
        "priority": 90
    },
    {
        "id": "do_not_learn_bad_routing",
        "name": "Do not learn bad routing",
        "rule": "If a code prompt produced a story, mark that as a failure pattern and do not reinforce it.",
        "priority": 90
    },
    {
        "id": "memory_is_supporting_signal",
        "name": "Memory is supporting signal",
        "rule": "Memory can add context, but it must not override current topic, intent, safety, or explicit user instructions.",
        "priority": 88
    }
]


class LearningBrain:

    def __init__(self):

        self.history = self.load_json(LEARNING_HISTORY_FILE, [])
        self.statistics = self.load_json(LEARNING_STATS_FILE, {})
        self.performance = self.load_json(BRAIN_PERFORMANCE_FILE, {})
        self.rules = self.load_json(LEARNING_RULES_FILE, [])
        self.improvement_queue = self.load_json(IMPROVEMENT_QUEUE_FILE, [])
        self.rules = self.normalize_rules(self.rules)

        print("Learning Brain Loaded")

    # ---------- loading ----------

    def load_json(self, path, default):

        if not path.exists():
            return default

        return load_json_resilient(path, default)

    def write_json(self, path, data):

        atomic_write_json(path, data)

    def save_all(self):

        self.write_json(LEARNING_HISTORY_FILE, self.history)
        self.write_json(LEARNING_STATS_FILE, self.statistics)
        self.write_json(BRAIN_PERFORMANCE_FILE, self.performance)
        self.write_json(LEARNING_RULES_FILE, self.rules)
        self.write_json(IMPROVEMENT_QUEUE_FILE, self.improvement_queue)

    def normalize_rules(self, rules):

        if isinstance(rules, dict):
            rules = list(rules.values())

        if not isinstance(rules, list):
            rules = []

        by_id = {}

        for rule in DEFAULT_RULES + rules:
            if not isinstance(rule, dict):
                continue

            rule_id = rule.get("id") or self.slugify(rule.get("name") or rule.get("rule") or "learning_rule")
            normalized = dict(rule)
            normalized["id"] = rule_id
            normalized.setdefault("priority", 50)
            by_id[rule_id] = normalized

        return sorted(
            by_id.values(),
            key=lambda item: item.get("priority", 0),
            reverse=True
        )

    def slugify(self, text):

        text = re.sub(r"[^a-zA-Z0-9]+", "_", str(text).lower()).strip("_")
        return text or "learning_rule"

    # ---------- extraction ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "unknown",
                "intent": "unknown"
            }

        if isinstance(data.get("understanding"), dict):
            return data["understanding"]

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_memory_report(self, data):

        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data["memory"]

        return {}

    def get_results(self, data):

        if not isinstance(data, dict):
            return {}

        if isinstance(data.get("results"), dict):
            return data["results"]

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict) and isinstance(manager_context.get("previous_results"), dict):
            return manager_context["previous_results"]

        return {}

    def get_chat_id(self, data, memory_report):

        if isinstance(data, dict):
            for key in ["chat_id", "conversation_id", "session_id"]:
                if data.get(key):
                    return str(data[key])

        if isinstance(memory_report, dict):
            for key in ["chat_id", "active_chat_id", "conversation_id", "session_id"]:
                if memory_report.get(key):
                    return str(memory_report[key])

        return "local_session"

    def get_user_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in ["original_text", "corrected_text", "user_message", "question", "text", "goal", "task"]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def text_signature(self, text):

        tokens = re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}", str(text).lower())
        useful = [
            token
            for token in tokens
            if token not in {"the", "and", "for", "with", "what", "how", "why", "this", "that"}
        ]
        return " ".join(useful[:18])

    # ---------- reliability ----------

    def local_reliability_score(self, brain_name, result, report=None):

        if not isinstance(result, dict):
            return {
                "score": 20,
                "level": "weak",
                "reasons": ["result is not structured"]
            }

        score = 50
        reasons = []
        report = report or {}
        intent = str(report.get("intent", "")).lower()

        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            score += (confidence - 50) * 0.35
            reasons.append(f"confidence={confidence}")
        else:
            score -= 10
            reasons.append("missing confidence")

        if result.get("error"):
            score -= 35
            reasons.append("error present")

        if result.get("needs_research") or result.get("needs_creative_brain"):
            score -= 10
            reasons.append("needs fallback")

        if result.get("needs_security"):
            score -= 5
            reasons.append("security review needed")

        if result.get("facts") or result.get("evidence") or result.get("local_matches"):
            score += 8
            reasons.append("has supporting data")

        if result.get("decision_summary") or result.get("reasoning_chain") or result.get("graph_used"):
            score += 7
            reasons.append("uses structured reasoning")

        if result.get("creative_fallback"):
            score += 5
            reasons.append("creative fallback available")

        alignment = self.output_alignment_score(brain_name, result, intent)
        score += alignment["delta"]
        reasons.extend(alignment["reasons"])

        score = round(max(0, min(score, 100)), 2)

        return {
            "score": score,
            "level": self.reliability_level(score),
            "reasons": reasons
        }

    def reliability_level(self, score):

        if score >= 80:
            return "strong"
        if score >= 60:
            return "usable"
        if score >= 40:
            return "uncertain"
        return "weak"

    def learning_eligibility(self, brain_name, result, rating, results, report):

        reasons = []
        eligible = rating.get("score", 0) >= 75
        if not eligible:
            reasons.append("reliability_below_learning_threshold")

        if not isinstance(result, dict) or result.get("error") or result.get("skipped"):
            eligible = False
            reasons.append("result_failed_or_skipped")

        quality = results.get("Quality_Control_brain", {})
        if isinstance(quality, dict) and quality.get("passed") is False:
            eligible = False
            reasons.append("quality_control_failed")

        factual_keys = {"facts", "verified_facts", "findings", "claims", "sources", "evidence"}
        contains_factual_material = isinstance(result, dict) and bool(factual_keys.intersection(result.keys()))
        fact_check = results.get("Fact_Check_brain", {})
        if contains_factual_material and brain_name != "Fact_Check_brain":
            fact_verified = isinstance(fact_check, dict) and (
                fact_check.get("verified") is True
                or fact_check.get("verdict") in {"verified", "likely_true", "opinion_not_fact_checkable"}
            )
            if not fact_verified:
                eligible = False
                reasons.append("factual_output_not_verified")

        if brain_name == "Fact_Check_brain" and isinstance(result, dict):
            if result.get("verdict") in {"uncertain", "not_verified", "needs_research"}:
                eligible = False
                reasons.append("fact_check_not_conclusive")

        if isinstance(result, dict) and result.get("self_reviewed") and not result.get("self_review", {}).get("ready"):
            eligible = False
            reasons.append("code_self_review_failed")

        return {
            "eligible": eligible,
            "threshold": 75,
            "scope": "current_chat_and_matching_intent",
            "topic": report.get("main_topic", "unknown"),
            "intent": report.get("intent", "unknown"),
            "reasons": reasons or ["verified_reliable_output"]
        }

    def output_alignment_score(self, brain_name, result, intent):

        delta = 0
        reasons = []
        text = self.result_text(result).lower()

        if intent == "code_generation":
            has_code = self.looks_like_code(text)
            has_story = self.looks_like_story(text)

            if brain_name == "Code_brain" and has_code:
                delta += 14
                reasons.append("code request has code-like output")
            elif brain_name in {"Story_brain", "Creative_brain"} and has_story and not has_code:
                delta -= 25
                reasons.append("code request produced narrative-like output")
            elif brain_name == "Code_brain" and not has_code:
                delta -= 18
                reasons.append("Code_brain output does not look like runnable code")

        if intent == "story_creation":
            if self.looks_like_story(text):
                delta += 12
                reasons.append("story request has narrative output")
            if "core idea:" in text or "validation:" in text or "direction:" in text:
                delta -= 18
                reasons.append("story request exposed creative process instead of final story")

        if result.get("blocked") or result.get("safe") is False:
            delta -= 20
            reasons.append("safety block or unsafe result")

        return {
            "delta": delta,
            "reasons": reasons
        }

    def result_text(self, result):

        if not isinstance(result, dict):
            return str(result)

        parts = []

        for key in [
            "final_output", "answer", "response", "summary", "generated_code",
            "code", "story", "text", "result"
        ]:
            value = result.get(key)
            if isinstance(value, str):
                parts.append(value)

        if not parts:
            try:
                parts.append(json.dumps(result, ensure_ascii=False)[:4000])
            except TypeError:
                parts.append(str(result))

        return "\n".join(parts)

    def looks_like_code(self, text):

        code_markers = [
            "def ", "class ", "import ", "if __name__", "print(",
            "while ", "for ", "return ", "json.", "path("
        ]
        return sum(1 for marker in code_markers if marker in text) >= 2

    def looks_like_story(self, text):

        story_markers = [
            "one morning", "felt", "found", "opened", "whisper",
            "chapter", "walked", "city", "forest", "door"
        ]
        sentences = len(re.findall(r"[.!?]", text))
        return sentences >= 3 and sum(1 for marker in story_markers if marker in text) >= 1

    # ---------- learning ----------

    def analyze_results(self, results, report):

        learned = []
        weaknesses = []
        improvements = []
        reliability = {}
        fallback_tasks = []
        lessons = []
        failure_patterns = []

        for brain_name, result in results.items():
            if isinstance(result, dict) and result.get("internal_only"):
                continue
            rating = self.local_reliability_score(brain_name, result, report)
            eligibility = self.learning_eligibility(
                brain_name,
                result,
                rating,
                results,
                report
            )
            rating["learning_eligibility"] = eligibility
            reliability[brain_name] = rating

            self.update_brain_performance(brain_name, result, rating)

            if rating["level"] in ["strong", "usable"] and eligibility["eligible"]:
                learned.append(f"{brain_name} produced {rating['level']} output.")
                lessons.append(self.build_success_lesson(brain_name, report, rating))

            if rating["level"] in ["strong", "usable"] and not eligibility["eligible"]:
                weaknesses.append(
                    f"{brain_name} was not promoted to learned knowledge: "
                    + ", ".join(eligibility["reasons"])
                )

            if rating["level"] in ["weak", "uncertain"]:
                weaknesses.append(f"{brain_name} output is {rating['level']}: {', '.join(rating['reasons'])}")
                improvements.append(f"Improve {brain_name} or route similar failures through Creative_brain.")
                failure_patterns.append(self.build_failure_pattern(brain_name, report, rating))
                fallback_tasks.append({
                    "brain": brain_name,
                    "problem": "; ".join(rating["reasons"]),
                    "result": result
                })

            if isinstance(result, dict) and result.get("missing_information"):
                improvements.append(f"{brain_name} needs clearer input before execution.")

            if isinstance(result, dict) and result.get("needs_security"):
                improvements.append(f"{brain_name} should be reviewed by Security_brain.")

        return learned, weaknesses, improvements, reliability, fallback_tasks, lessons, failure_patterns

    def build_success_lesson(self, brain_name, report, rating):

        return {
            "type": "success_pattern",
            "brain": brain_name,
            "topic": report.get("main_topic", "unknown"),
            "intent": report.get("intent", "unknown"),
            "reliability": rating["score"],
            "scope": rating.get("learning_eligibility", {}).get("scope", "current_chat_and_matching_intent"),
            "verification": rating.get("learning_eligibility", {}),
            "lesson": f"For {report.get('intent', 'unknown')} in {report.get('main_topic', 'unknown')}, {brain_name} can be trusted when reliability stays {rating['level']}."
        }

    def build_failure_pattern(self, brain_name, report, rating):

        return {
            "type": "failure_pattern",
            "brain": brain_name,
            "topic": report.get("main_topic", "unknown"),
            "intent": report.get("intent", "unknown"),
            "reliability": rating["score"],
            "reasons": rating["reasons"],
            "avoid": f"Do not let {brain_name} dominate {report.get('intent', 'unknown')} answers when this pattern repeats."
        }

    def update_brain_performance(self, brain_name, result, rating):

        stats = self.performance.get(brain_name, {
            "uses": 0,
            "errors": 0,
            "fallbacks": 0,
            "average_confidence": 0,
            "average_reliability": 0
        })

        uses = stats.get("uses", 0)
        confidence = 0

        if isinstance(result, dict) and isinstance(result.get("confidence"), (int, float)):
            confidence = result["confidence"]

        stats["uses"] = uses + 1
        stats["errors"] = stats.get("errors", 0) + (1 if isinstance(result, dict) and result.get("error") else 0)
        stats["fallbacks"] = stats.get("fallbacks", 0) + (
            1
            if isinstance(result, dict)
            and (
                result.get("needs_creative_brain")
                or result.get("creative_fallback")
                or result.get("needs_research")
            )
            else 0
        )
        stats["average_confidence"] = round(
            ((stats.get("average_confidence", 0) * uses) + confidence) / max(stats["uses"], 1),
            2
        )
        stats["average_reliability"] = round(
            ((stats.get("average_reliability", 0) * uses) + rating["score"]) / max(stats["uses"], 1),
            2
        )
        stats["last_reliability_level"] = rating["level"]
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()

        self.performance[brain_name] = stats

    def add_history_entry(
        self,
        report,
        memory_report,
        chat_id,
        user_text,
        learned,
        weaknesses,
        improvements,
        reliability,
        lessons,
        failure_patterns,
        creative_help
    ):

        entry = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "chat_id": chat_id,
            "request_signature": self.text_signature(user_text),
            "main_topic": report.get("main_topic", "unknown"),
            "intent": report.get("intent", "unknown"),
            "meaning_frame": report.get("meaning_frame", {}),
            "graph_confidence": report.get("graph_confidence"),
            "learned": learned,
            "weaknesses_found": weaknesses,
            "improvement_suggestions": improvements,
            "lessons": lessons,
            "failure_patterns": failure_patterns,
            "reliability": reliability,
            "creative_help": creative_help,
            "rules_applied": self.applicable_rules(report)
        }

        self.history.append(entry)
        self.history = self.history[-MAX_HISTORY_ENTRIES:]

        return entry

    def applicable_rules(self, report):

        intent = str(report.get("intent", "")).lower()
        topic = str(report.get("main_topic", "")).lower()
        applied = []

        for rule in self.rules:
            text = f"{rule.get('id', '')} {rule.get('name', '')} {rule.get('rule', '')}".lower()
            if intent and intent in text:
                applied.append(rule)
            elif topic and topic in text:
                applied.append(rule)
            elif "current user intent" in text or "same chat" in text:
                applied.append(rule)

        return applied[:10]

    def update_improvement_queue(self, improvements):

        existing = {
            item.get("suggestion")
            for item in self.improvement_queue
            if isinstance(item, dict)
        }

        for suggestion in improvements:
            if suggestion in existing:
                continue

            self.improvement_queue.append({
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "suggestion": suggestion,
                "status": "open",
                "priority": self.priority_for_suggestion(suggestion)
            })

        self.improvement_queue = self.improvement_queue[-MAX_QUEUE_ENTRIES:]

    def priority_for_suggestion(self, suggestion):

        lowered = suggestion.lower()

        if "security" in lowered or "error" in lowered:
            return "high"
        if "creative" in lowered or "fallback" in lowered:
            return "medium"
        return "low"

    def update_statistics(self, entry):

        stats = self.statistics.get("Learning_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["history_entries"] = len(self.history)
        stats["open_improvements"] = len([
            item
            for item in self.improvement_queue
            if item.get("status") == "open"
        ])
        stats["last_topic"] = entry.get("main_topic")
        stats["last_intent"] = entry.get("intent")
        stats["last_chat_id"] = entry.get("chat_id")
        stats["last_lessons"] = len(entry.get("lessons", []))
        stats["last_failure_patterns"] = len(entry.get("failure_patterns", []))
        stats["rules_loaded"] = len(self.rules)
        stats["average_last_reliability"] = self.average_reliability(entry.get("reliability", {}))
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        self.statistics["Learning_brain"] = stats

    def average_reliability(self, reliability):

        scores = [
            value.get("score")
            for value in reliability.values()
            if isinstance(value, dict) and isinstance(value.get("score"), (int, float))
        ]

        if not scores:
            return 0

        return round(sum(scores) / len(scores), 2)

    # ---------- creative help ----------

    def request_creative_help(self, fallback_tasks, report, memory_report):

        if not fallback_tasks:
            return []

        serious_tasks = [
            task
            for task in fallback_tasks
            if any(
                marker in task.get("problem", "").lower()
                for marker in ["error", "does not look", "produced narrative", "unsafe"]
            )
        ][:3]

        if not serious_tasks:
            return []

        creative_results = []

        try:
            from Creative_brain import CreativeBrain

            creative = CreativeBrain()

            for task in serious_tasks:
                creative_results.append(
                    creative.solve_brain_task(
                        task["brain"],
                        {
                            "understanding": report,
                            "memory": memory_report,
                            "problem": task["problem"],
                            "goal": f"help {task['brain']} recover from weak output"
                        },
                        "learning_repair"
                    )
                )

        except Exception as error:
            creative_results.append({
                "brain": "Creative_brain",
                "error": str(error)
            })

        return creative_results

    def learning_guidance(self, report, reliability, lessons, failure_patterns):

        intent = report.get("intent", "unknown")
        topic = report.get("main_topic", "unknown")

        strongest = sorted(
            reliability.items(),
            key=lambda item: item[1].get("score", 0),
            reverse=True
        )
        weakest = sorted(
            reliability.items(),
            key=lambda item: item[1].get("score", 100)
        )

        guidance = {
            "current_topic": topic,
            "current_intent": intent,
            "prefer_brains": [name for name, rating in strongest[:4] if rating.get("score", 0) >= 60],
            "avoid_dominating_brains": [name for name, rating in weakest[:4] if rating.get("score", 100) < 50],
            "strong_lessons": lessons[:8],
            "failure_patterns": failure_patterns[:8],
            "rule_summary": [
                rule.get("rule")
                for rule in self.applicable_rules(report)[:6]
            ]
        }

        if intent == "code_generation":
            guidance["output_rule"] = "Final answer should prefer runnable code output over story, research facts, or internal process reports."
        elif intent == "story_creation":
            guidance["output_rule"] = "Final answer should prefer the final story text over creative evolution reports."
        else:
            guidance["output_rule"] = "Final answer should follow the current user intent and use memory only as support."

        return guidance

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        results = self.get_results(data)
        chat_id = self.get_chat_id(data, memory_report)
        user_text = self.get_user_text(data, report)

        (
            learned,
            weaknesses,
            improvements,
            reliability,
            fallback_tasks,
            lessons,
            failure_patterns
        ) = self.analyze_results(results, report)

        if not results:
            weaknesses.append("No brain results were provided to Learning_brain.")
            improvements.append("Run Learning_brain after Manager_brain has collected brain results.")

        creative_help = self.request_creative_help(
            fallback_tasks,
            report,
            memory_report
        )

        if creative_help:
            learned.append("Creative_brain generated repair suggestions for weak brain outputs.")

        self.update_improvement_queue(improvements)

        entry = self.add_history_entry(
            report,
            memory_report,
            chat_id,
            user_text,
            learned,
            weaknesses,
            improvements,
            reliability,
            lessons,
            failure_patterns,
            creative_help
        )

        self.update_statistics(entry)
        self.save_all()

        confidence = 60
        if results:
            average_reliability = sum(
                item["score"]
                for item in reliability.values()
            ) / max(len(reliability), 1)
            confidence = round(min(100, average_reliability + 10), 2)

        guidance = self.learning_guidance(
            report,
            reliability,
            lessons,
            failure_patterns
        )

        return {
            "brain": "Learning_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "results_analyzed": len(results),
            "learned": learned,
            "weaknesses_found": weaknesses,
            "improvement_suggestions": improvements,
            "lessons": lessons,
            "failure_patterns": failure_patterns,
            "learning_guidance": guidance,
            "reliability": reliability,
            "creative_help": creative_help,
            "updated_statistics": True,
            "learning_entry": entry,
            "confidence": confidence,
            "suggested_next_brains": [
                brain_name
                for brain_name in [
                    "Creative_brain" if fallback_tasks else None,
                    "Planner_brain" if improvements else None,
                    "Response_brain"
                ]
                if brain_name
            ],
            "rules": [
                "Rate local reliability before learning from output.",
                "Do not treat low-confidence output as true.",
                "Current chat and current intent are stronger than older memory.",
                "Learn success patterns and failure patterns separately.",
                "Do not reinforce a wrong output type, such as story output for a code request.",
                "Use Creative_brain to repair weak or stuck brain outputs.",
                "Store lessons separately from Memory_brain conversation memory."
            ]
        }


brain = LearningBrain()
