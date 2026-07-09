"""
Quality_Control_brain.py
Canri AI

Audits whether the specialist brains actually satisfied the user request.
It does not answer the user directly. It produces feedback for Manager_brain
so weak or incomplete specialist results can be retried once before response.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
STATS_FILE = DATA_DIR / "Quality_control_statistics.json"


class QualityControlBrain:

    def __init__(self):
        self.statistics = self.load_json(STATS_FILE, {})
        print("Quality Control Brain Loaded")

    # ---------- storage ----------

    def load_json(self, path, default):
        if not path.exists() or path.stat().st_size == 0:
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self, passed, score):
        stats = self.statistics.get("Quality_Control_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_passed"] = bool(passed)
        stats["last_score"] = score
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        self.statistics["Quality_Control_brain"] = stats

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

    # ---------- input ----------

    def get_understanding_report(self, data):
        if not isinstance(data, dict):
            return {}
        report = data.get("understanding")
        return report if isinstance(report, dict) else {}

    def get_results(self, data):
        if not isinstance(data, dict):
            return {}

        merged = {}

        previous = data.get("results")
        if isinstance(previous, dict):
            merged.update(previous)

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            manager_previous = manager_context.get("previous_results")
            if isinstance(manager_previous, dict):
                merged.update(manager_previous)

        return merged

    def extract_text(self, data, report):
        if isinstance(data, str):
            return data

        parts = []

        if isinstance(data, dict):
            for key in ["original_text", "corrected_text", "user_message", "question", "text", "goal"]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in ["original_text", "corrected_text"]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    # ---------- request model ----------

    def request_requirements(self, text, report):
        lowered = text.lower()
        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()

        requirements = {
            "topic": topic,
            "intent": intent,
            "is_code_request": topic == "code" or intent in {"code_generation", "code_analysis"},
            "is_math_request": topic == "math" or intent == "math" or self.looks_like_math(lowered),
            "is_story_request": topic == "story" or intent == "story_creation",
            "is_reliability_request": any(
                marker in lowered
                for marker in ["reliable", "fact check", "check if", "verify", "sources", "local knowledge"]
            ),
            "code_only": any(
                marker in lowered
                for marker in [
                    "only output the final working python code",
                    "only output final working code",
                    "only output the final working code",
                    "only output code",
                    "do not output a plan",
                    "do not output modules",
                    "do not output placeholders",
                    "do not output draft structures"
                ]
            ),
            "wants_runnable": any(marker in lowered for marker in ["real runnable", "working code", "program must run", "runnable"]),
            "wants_json_save": "json" in lowered and any(marker in lowered for marker in ["save", "saving", "load", "history"]),
            "wants_percentages": "percentage" in lowered or "percentages" in lowered or "percent" in lowered,
            "wants_history": "history" in lowered,
            "wants_steps": "step by step" in lowered or "steps" in lowered,
        }

        return requirements

    def looks_like_math(self, lowered):
        return bool(
            re.search(r"\d|\bx\b", lowered)
            and (
                "=" in lowered
                or "^" in lowered
                or "**" in lowered
                or any(marker in lowered for marker in ["solve", "calculate", "equation"])
            )
        )

    def expected_brains(self, requirements):
        expected = []

        if requirements["is_code_request"]:
            expected.append("Code_brain")
        if requirements["is_math_request"]:
            expected.append("Math_brain")
        if requirements["is_story_request"]:
            expected.extend(["Story_brain", "Creative_brain"])
        if requirements["is_reliability_request"]:
            expected.extend(["Research_brain", "Fact_Check_brain"])

        if not expected:
            expected.extend(["Reasoning_brain"])

        return list(dict.fromkeys(expected))

    # ---------- checks ----------

    def add_issue(self, issues, target_brain, severity, problem, instruction, evidence=None):
        issues.append({
            "target_brain": target_brain,
            "severity": severity,
            "problem": problem,
            "instruction": instruction,
            "evidence": evidence or ""
        })

    def audit_expected_brains(self, results, requirements, issues):
        for brain_name in self.expected_brains(requirements):
            result = results.get(brain_name)
            if not isinstance(result, dict):
                self.add_issue(
                    issues,
                    brain_name,
                    "high",
                    f"{brain_name} was expected but did not produce a result.",
                    "Run this specialist brain and answer the user request directly."
                )
                continue

            if result.get("error") or result.get("skipped"):
                self.add_issue(
                    issues,
                    brain_name,
                    "high",
                    f"{brain_name} failed or was skipped.",
                    "Retry this brain with the original user request and avoid returning a placeholder.",
                    result.get("error") or result.get("reason", "")
                )

    def audit_code(self, results, requirements, issues):
        if not requirements["is_code_request"]:
            return

        result = results.get("Code_brain", {})
        code = str(
            result.get("generated_code")
            or result.get("code")
            or result.get("answer")
            or ""
        )
        lowered_code = code.lower()

        if not code.strip():
            self.add_issue(
                issues,
                "Code_brain",
                "critical",
                "No generated code was returned for a code request.",
                "Return complete runnable code, not module names or planning text."
            )
            return

        if requirements["code_only"]:
            forbidden = ["main pieces:", "plan:", "draft structure", "helper variant", "placeholder"]
            if any(marker in lowered_code for marker in forbidden):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    "The user asked for final code only, but the output looks like a draft or plan.",
                    "Return only the final runnable code."
                )

        if requirements["wants_runnable"] and "if __name__" not in code and "def main(" not in code:
            self.add_issue(
                issues,
                "Code_brain",
                "high",
                "Runnable program request is missing a main function or main guard.",
                "Add a proper main loop or main guard so the program runs in terminal."
            )

        if requirements["wants_json_save"] and ("json" not in lowered_code or ("dump" not in lowered_code and "write_text" not in lowered_code)):
            self.add_issue(
                issues,
                "Code_brain",
                "high",
                "The user asked for JSON saving/loading, but the code does not implement JSON persistence.",
                "Add JSON file persistence using the standard json module."
            )

        if requirements["wants_percentages"] and "%" not in code and "percent" not in lowered_code:
            self.add_issue(
                issues,
                "Code_brain",
                "medium",
                "The user asked for percentages, but the code does not support percentage calculations.",
                "Add percentage calculation support."
            )

        if requirements["wants_history"] and "history" not in lowered_code:
            self.add_issue(
                issues,
                "Code_brain",
                "medium",
                "The user asked for history, but the code does not track calculation history.",
                "Add a history list and save it to JSON."
            )

    def audit_math(self, results, requirements, issues):
        if not requirements["is_math_request"]:
            return

        result = results.get("Math_brain", {})
        success = result.get("success") is True
        confidence = result.get("confidence", 0)
        steps = result.get("steps", [])

        if not success:
            self.add_issue(
                issues,
                "Math_brain",
                "critical",
                "Math request was not solved.",
                "Solve the equation/calculation and return the final answer with steps.",
                result.get("warning", "")
            )
            return

        if requirements["wants_steps"] and not steps:
            self.add_issue(
                issues,
                "Math_brain",
                "medium",
                "The user asked for step-by-step solving, but no steps were returned.",
                "Return clear step-by-step reasoning."
            )

        if isinstance(confidence, (int, float)) and confidence < 70:
            self.add_issue(
                issues,
                "Math_brain",
                "medium",
                "Math answer confidence is too low.",
                "Recheck the calculation and raise confidence only if the answer is correct."
            )

    def audit_reliability(self, results, requirements, issues):
        if not requirements["is_reliability_request"]:
            return

        research = results.get("Research_brain", {})
        fact_check = results.get("Fact_Check_brain", {})

        facts = research.get("facts", []) if isinstance(research, dict) else []
        local_knowledge = research.get("local_knowledge", []) if isinstance(research, dict) else []

        if not facts and not local_knowledge:
            self.add_issue(
                issues,
                "Research_brain",
                "high",
                "Reliability request did not return facts or local knowledge.",
                "Use local knowledge and approved sources to provide relevant evidence."
            )

        if isinstance(fact_check, dict):
            confidence = fact_check.get("confidence", 0)
            if fact_check.get("needs_research") or confidence < 45:
                self.add_issue(
                    issues,
                    "Fact_Check_brain",
                    "medium",
                    "Fact check confidence is too low for a reliability request.",
                    "Check the strongest available local/research evidence and return a clearer verdict."
                )
        else:
            self.add_issue(
                issues,
                "Fact_Check_brain",
                "high",
                "Reliability request did not run Fact_Check_brain.",
                "Run fact checking before final response."
            )

    def audit_story(self, results, requirements, issues):
        if not requirements["is_story_request"]:
            return

        story_result = results.get("Story_brain", {})
        creative_result = results.get("Creative_brain", {})
        output = ""

        for result in [story_result, creative_result]:
            if isinstance(result, dict):
                output = output or str(
                    result.get("story")
                    or result.get("final_output")
                    or result.get("answer")
                    or result.get("draft")
                    or ""
                )

        if not output.strip():
            self.add_issue(
                issues,
                "Story_brain",
                "high",
                "Story request did not produce a final story.",
                "Return the final story, not a plan or simulation report."
            )
            return

        if "Goal:" in output and "Core idea:" in output:
            self.add_issue(
                issues,
                "Story_brain",
                "high",
                "Story output looks like a creative planning report instead of a story.",
                "Convert the selected creative result into the final story text."
            )

    def audit_response_risk(self, results, requirements, issues):
        response = results.get("Response_brain")
        if not isinstance(response, dict):
            return

        text = str(response.get("display_text") or response.get("answer") or "")
        lowered = text.lower()

        if requirements["is_math_request"] and "```python" in lowered:
            self.add_issue(
                issues,
                "Response_brain",
                "high",
                "Response selected code for a math request.",
                "Prefer Math_brain final_output for math requests."
            )

        if requirements["is_reliability_request"] and "```python" in lowered:
            self.add_issue(
                issues,
                "Response_brain",
                "high",
                "Response selected code for a factual reliability request.",
                "Prefer Research_brain and Fact_Check_brain outputs."
            )

        if "goal:" in lowered and "core idea:" in lowered and not requirements["is_code_request"]:
            self.add_issue(
                issues,
                "Response_brain",
                "medium",
                "Response exposed a creative simulation report instead of the final requested result.",
                "Show the final result, not internal creative report fields."
            )

    # ---------- output ----------

    def build_retry_requests(self, issues):
        retry_requests = []
        seen = set()

        non_retry_brains = {
            "Response_brain",
            "Quality_Control_brain",
            "Security_brain",
            "Learning_brain"
        }

        for issue in issues:
            brain_name = issue.get("target_brain")
            if not brain_name or brain_name in seen or brain_name in non_retry_brains:
                continue

            if issue.get("severity") in {"critical", "high", "medium"}:
                seen.add(brain_name)
                retry_requests.append({
                    "target_brain": brain_name,
                    "instruction": issue.get("instruction"),
                    "problem": issue.get("problem"),
                    "severity": issue.get("severity")
                })

        return retry_requests[:5]

    def quality_score(self, issues):
        score = 100
        penalty = {
            "critical": 35,
            "high": 24,
            "medium": 12,
            "low": 5
        }

        for issue in issues:
            score -= penalty.get(issue.get("severity"), 8)

        return max(0, min(score, 100))

    def process(self, data):
        report = self.get_understanding_report(data)
        results = self.get_results(data)
        text = self.extract_text(data, report)
        requirements = self.request_requirements(text, report)
        issues = []

        self.audit_expected_brains(results, requirements, issues)
        self.audit_code(results, requirements, issues)
        self.audit_math(results, requirements, issues)
        self.audit_reliability(results, requirements, issues)
        self.audit_story(results, requirements, issues)
        self.audit_response_risk(results, requirements, issues)

        retry_requests = self.build_retry_requests(issues)
        score = self.quality_score(issues)
        passed = score >= 78 and not retry_requests

        self.save_statistics(passed, score)

        return {
            "brain": "Quality_Control_brain",
            "passed": passed,
            "quality_score": score,
            "needs_retry": bool(retry_requests),
            "retry_requests": retry_requests,
            "issues": issues[:20],
            "requirements": requirements,
            "checked_brains": sorted(results.keys()),
            "confidence": score,
            "suggested_next_brains": [
                request["target_brain"]
                for request in retry_requests
            ] + ["Response_brain"],
            "rules": [
                "Check whether the selected specialist brain matched the user request.",
                "Do not answer the user directly.",
                "Return actionable retry feedback for Manager_brain.",
                "Retry only targeted brains to avoid infinite loops."
            ]
        }


brain = QualityControlBrain()
