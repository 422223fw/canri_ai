"""
Quality_Control_brain.py
Canri AI

Audits whether the specialist brains actually satisfied the user request.
It does not answer the user directly. It produces feedback for Manager_brain
so weak or incomplete specialist results can be retried once before response.
"""

import ast
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

    def get_data_context(self, data):

        if not isinstance(data, dict):
            return {}

        data_context = data.get("data_context")
        if isinstance(data_context, dict):
            return data_context

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            data_context = manager_context.get("data_context")
            if isinstance(data_context, dict):
                return data_context

        return {}

    def get_knowledge_context(self, data):

        if not isinstance(data, dict):
            return {}

        knowledge = data.get("knowledge")
        if isinstance(knowledge, dict):
            return knowledge

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            knowledge = manager_context.get("knowledge")
            if isinstance(knowledge, dict):
                return knowledge

        return {}

    def get_shared_context(self, data):

        if not isinstance(data, dict):
            return {}

        shared = data.get("shared_context")
        if isinstance(shared, dict):
            return shared

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            shared = manager_context.get("shared_context")
            if isinstance(shared, dict):
                return shared

        return {}

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
        contract = report.get("request_contract", {})
        if not isinstance(contract, dict):
            contract = {}

        requirements = {
            "has_request_contract": bool(contract),
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
            "requested_sentence_count": self.extract_requested_sentence_count(lowered),
            "expected_program_kind": self.detect_expected_program_kind(lowered),
            "requested_code_features": self.extract_requested_code_features(lowered),
            "needs_local_data": any(
                marker in lowered
                for marker in [
                    "local knowledge",
                    "use local",
                    "from data",
                    "from the dictionaries",
                    "reliable",
                    "verify",
                    "fact check",
                    "what is",
                    "explain"
                ]
            ),
            "is_image_request": topic == "image_generation" or intent == "image_generation" or any(
                marker in lowered
                for marker in ["create image", "generate image", "draw", "illustration", "logo", "poster"]
            ),
            "is_voice_request": topic == "voice" or any(
                marker in lowered
                for marker in ["audio", "voice", "recording", "transcribe"]
            ),
            "is_vision_request": topic == "vision" or any(
                marker in lowered
                for marker in ["image file", "photo", "video", "attachment", ".png", ".jpg", ".mp4"]
            ),
            "atomic_requirements": contract.get("requirements", report.get("requirements", [])),
            "output_constraints": contract.get("output_constraints", report.get("output_constraints", {})),
            "global_picture": contract.get("global_picture", report.get("global_picture", {})),
            "detail_inventory": contract.get("detail_inventory", report.get("detail_inventory", {})),
            "continuation": bool(contract.get("continuation", {}).get("requested")),
        }

        return requirements

    def requirement_output(self, results, requirements):

        preferred = []
        if requirements.get("is_code_request"):
            preferred.append("Code_brain")
        elif requirements.get("is_math_request"):
            preferred.append("Math_brain")
        elif requirements.get("is_story_request"):
            preferred.extend(["Story_brain", "Creative_brain"])
        elif requirements.get("is_reliability_request"):
            preferred.extend(["Research_brain", "Fact_Check_brain"])
        preferred.append("Response_brain")

        parts = []
        for brain_name in preferred:
            text = self.text_from_result(results.get(brain_name, {}))
            if text:
                parts.append(text)
        return "\n".join(parts)

    def atomic_requirement_check(self, requirement, output, results, requirements):

        requirement = requirement if isinstance(requirement, dict) else {"text": str(requirement)}
        requirement_id = requirement.get("id") or "unnamed_requirement"
        kind = requirement.get("kind", "explicit_constraint")
        feature = requirement.get("feature")
        code_result = results.get("Code_brain", {})
        code = ""
        if isinstance(code_result, dict):
            code = str(code_result.get("generated_code") or code_result.get("code") or "")

        if kind == "feature" and feature:
            passed = self.code_feature_present(feature, code) if requirements.get("is_code_request") else True
            return passed, f"feature:{feature}"

        if requirement_id == "runnable_output":
            syntax_ok = self.python_syntax_error(code) is None if code else False
            structure_ok = self.code_has_real_structure(code)
            self_review = code_result.get("self_review", {}) if isinstance(code_result, dict) else {}
            ready = self_review.get("ready")
            passed = bool(code and syntax_ok and structure_ok and ready is not False)
            return passed, "syntax + structure + self-review"

        if requirement_id == "only_output":
            response = self.text_from_result(results.get("Response_brain", {})) or output
            forbidden = requirements.get("output_constraints", {}).get("forbidden_sections", [])
            lowered = response.lower()
            leaked = self.looks_like_internal_report(response)
            if "plan" in forbidden and ("main pieces:" in lowered or "plan:" in lowered):
                leaked = True
            if requirements.get("code_only") and "quality note:" in lowered:
                leaked = True
            return not leaked, "final-output leakage check"

        if kind == "explicit_constraint" and requirements.get("is_code_request"):
            ignored = {
                "program", "must", "include", "support", "user", "users", "with",
                "from", "into", "only", "output", "final", "full", "working",
                "python", "code", "real", "runnable", "same", "project", "the",
                "and", "that", "this", "when", "then", "using", "file"
            }
            terms = [
                term
                for term in re.findall(r"[a-z][a-z0-9_]{2,}", requirement.get("text", "").lower())
                if term not in ignored
            ]
            unique_terms = list(dict.fromkeys(terms))[:14]
            if not unique_terms:
                return True, "no lexical terms required"
            lowered_code = code.lower()
            found = [term for term in unique_terms if term in lowered_code]
            threshold = max(1, min(3, (len(unique_terms) + 2) // 3))
            return len(found) >= threshold, f"matched terms: {', '.join(found)}"

        return True, "covered by specialist and domain checks"

    def audit_atomic_requirements(self, results, requirements, issues):

        output = self.requirement_output(results, requirements)
        for requirement in requirements.get("atomic_requirements", [])[:80]:
            passed, evidence = self.atomic_requirement_check(
                requirement,
                output,
                results,
                requirements
            )
            if passed:
                continue
            target = "Code_brain" if requirements.get("is_code_request") else "Manager_brain"
            self.add_issue(
                issues,
                target,
                "high",
                f"Request requirement failed: {requirement.get('text', requirement.get('id', 'unknown'))}",
                "Implement this exact requirement and preserve every requirement that already passed.",
                evidence
            )

    def audit_small_details(self, results, requirements, issues):

        inventory = requirements.get("detail_inventory", {})
        if not isinstance(inventory, dict):
            inventory = {}
        global_picture = requirements.get("global_picture", {})
        if (
            requirements.get("has_request_contract")
            and (not isinstance(global_picture, dict) or not global_picture.get("goal"))
        ):
            self.add_issue(
                issues,
                "Understanding_brain",
                "high",
                "The request has no preserved global goal.",
                "Rebuild the request contract with a global picture before routing."
            )

        output = self.requirement_output(results, requirements)
        code_result = results.get("Code_brain", {})
        code = ""
        if isinstance(code_result, dict):
            code = str(code_result.get("generated_code") or code_result.get("code") or "")

        if requirements.get("is_code_request"):
            lowered_code = code.lower()
            for file_name in inventory.get("file_names", [])[:12]:
                if str(file_name).lower() in lowered_code:
                    continue
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    f"Requested file detail is missing: {file_name}",
                    f"Use the exact requested file name {file_name} in the final program.",
                    "detail_inventory.file_names"
                )

        if requirements.get("is_story_request"):
            lowered_output = output.lower()
            ignored_names = {
                "write", "create", "continue", "story", "only", "canri"
            }
            for entity in inventory.get("named_entities", [])[:12]:
                normalized = str(entity).strip().lower()
                if not normalized or normalized in ignored_names or normalized in lowered_output:
                    continue
                self.add_issue(
                    issues,
                    "Story_brain",
                    "high",
                    f"Requested named detail is missing: {entity}",
                    f"Preserve the requested name or named element exactly: {entity}.",
                    "detail_inventory.named_entities"
                )

        explicit_count = inventory.get("coverage", {}).get("explicit_detail_count", 0)
        atomic_count = len(requirements.get("atomic_requirements", []))
        if explicit_count and atomic_count < explicit_count:
            self.add_issue(
                issues,
                "Understanding_brain",
                "high",
                "Some small prompt details were not converted into checkable requirements.",
                "Rebuild atomic requirements from every explicit detail before answering.",
                f"details={explicit_count}, requirements={atomic_count}"
            )

    def extract_requested_sentence_count(self, lowered):

        match = re.search(r"\b(\d+)\s*(?:more\s+)?sentences?\b", lowered)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def detect_expected_program_kind(self, lowered):

        checks = [
            ("expense_tracker", ["expense tracker", "expenses", "amount spent", "total amount", "search expenses", "category"]),
            ("calendar_app", ["calendar", "appointment", "appointments", "event planner", "schedule event"]),
            ("contact_book", ["contact book", "contacts", "phone book", "address book"]),
            ("library_manager", ["library manager", "book tracker", "books", "borrowed books", "reading list"]),
            ("flashcards_app", ["flashcards", "flash cards", "study cards"]),
            ("shop_inventory", ["shop inventory", "store inventory", "inventory tracker", "stock", "products in stock"]),
            ("todo_app", ["to-do", "todo", "task list", "tasks", "mark a task"]),
            ("notes_app", ["note app", "notes app", "notes", "note taking"]),
            ("weather_app", ["weather app", "weather", "temperature", "humidity"]),
            ("calculator", ["calculator", "calculate", "addition", "subtraction", "multiplication", "division"]),
            ("quiz_game", ["quiz", "multiple choice"]),
        ]

        for kind, signals in checks:
            if any(signal in lowered for signal in signals):
                return kind

        return None

    def extract_requested_code_features(self, lowered):

        features = []
        checks = [
            ("calendar_events", ["calendar", "appointment", "appointments", "event", "events by date", "schedule event"]),
            ("contact_records", ["contacts", "contact book", "phone", "email"]),
            ("library_books", ["library", "books", "author", "borrowed books", "reading list"]),
            ("flashcards", ["flashcards", "flash cards", "question", "answer", "study cards"]),
            ("shop_inventory", ["shop inventory", "store inventory", "inventory", "stock", "products in stock"]),
            ("edit_existing_item", ["edit an existing", "edit a note", "edit note", "update an existing", "modify an existing"]),
            ("tags", ["add tags", "tags to", "by tag", "tags", "tag"]),
            ("search_title_body_tag", ["search notes by title", "search by title", "search notes by word", "search notes", "search by tag", "title, body, or tag"]),
            ("export_txt", ["export", "txt file", "readable txt", "notes_export.txt"]),
            ("old_json_compatibility", ["compatible with old", "old notes", "same notes.json format", "keep the same notes.json"]),
            ("expense_amount", ["amount", "amount spent"]),
            ("expense_category", ["category", "search expenses by category"]),
            ("expense_description", ["description"]),
            ("search_expense_category", ["search expenses by category", "search by category"]),
            ("expense_total", ["total amount spent", "show the total", "total spent"]),
            ("expenses_json", ["expenses.json"]),
            ("json_persistence", ["json file", "notes.json", "save notes", "load notes", "save tasks", "load tasks"]),
            ("delete_item", ["delete a note", "delete notes", "delete a task", "delete task", "delete an expense", "delete expense"]),
            ("list_items", ["list notes", "list tasks", "list all", "list all expenses"]),
            ("add_item", ["add notes", "add note", "add tasks", "add task", "add expenses", "add an expense", "add expense"])
        ]

        for feature, signals in checks:
            if any(signal in lowered for signal in signals):
                features.append(feature)

        return list(dict.fromkeys(features))

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
        if requirements.get("is_image_request"):
            expected.append("Image_brain")
        if requirements.get("is_voice_request"):
            expected.append("Voice_brain")
        if requirements.get("is_vision_request"):
            expected.append("Vision_brain")

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

        if self.has_placeholder_code(code):
            self.add_issue(
                issues,
                "Code_brain",
                "high",
                "Generated code still contains placeholders or empty helper behavior.",
                "Replace placeholders with real working logic that satisfies the requested features."
            )

        syntax_error = self.python_syntax_error(code)
        if syntax_error:
            self.add_issue(
                issues,
                "Code_brain",
                "critical",
                "Generated Python code has a syntax error.",
                "Fix the code so it can be parsed by Python before returning it.",
                syntax_error
            )

        expected_kind = requirements.get("expected_program_kind")
        actual_kind = result.get("program_kind")
        if expected_kind and actual_kind and expected_kind != actual_kind:
            self.add_issue(
                issues,
                "Code_brain",
                "critical",
                f"Wrong program kind selected: expected {expected_kind}, got {actual_kind}.",
                "Select the dedicated complete program template for the user's requested app type."
            )

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

    def has_placeholder_code(self, code):

        lowered = str(code).lower()
        placeholder_markers = [
            "todo",
            "placeholder",
            "not implemented",
            "helper, production draft",
            "helper, planner ready",
            "helper, creative ready"
        ]

        if any(marker in lowered for marker in placeholder_markers):
            return True

        if "return data" in lowered and (
            lowered.count("return data") >= 2
            or "helper" in lowered
            or "production_draft" in lowered
        ):
            return True

        if re.search(r"def\s+\w+\([^)]*\):\s*(?:\"\"\".*?\"\"\"\s*)?pass\b", str(code), re.DOTALL):
            return True

        return False

    def python_syntax_error(self, code):

        text = str(code).strip()
        if text.startswith("```"):
            match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()

        if not re.search(r"\b(import|from|def|class|if __name__|print\()", text):
            return None

        try:
            ast.parse(text)
        except SyntaxError as error:
            return f"line {error.lineno}: {error.msg}"

        return None

    def code_feature_present(self, feature, code):

        lowered = str(code).lower()

        if feature == "edit_existing_item":
            return "def edit_" in lowered and "updated_at" in lowered

        if feature == "tags":
            return '"tags"' in lowered and ("parse_tags" in lowered or "tag" in lowered)

        if feature == "search_title_body_tag":
            return (
                "def search_" in lowered
                and "title" in lowered
                and "body" in lowered
                and "tags" in lowered
            )

        if feature == "export_txt":
            return "def export_" in lowered and ".txt" in lowered and "write_text" in lowered

        if feature == "old_json_compatibility":
            return ("normalize_" in lowered and '"tags": []' in lowered) or "item.get(\"text\"" in lowered

        if feature == "calendar_events":
            return "calendar" in lowered and "date" in lowered and "time" in lowered and "events" in lowered

        if feature == "contact_records":
            return "contacts.json" in lowered and "phone" in lowered and "email" in lowered

        if feature == "library_books":
            return "library" in lowered and "title" in lowered and "author" in lowered

        if feature == "flashcards":
            return "flashcards.json" in lowered and "question" in lowered and "answer" in lowered

        if feature == "shop_inventory":
            return "inventory" in lowered and "quantity" in lowered and "price" in lowered

        if feature == "expense_amount":
            return '"amount"' in lowered and "float(" in lowered

        if feature == "expense_category":
            return '"category"' in lowered

        if feature == "expense_description":
            return '"description"' in lowered

        if feature == "search_expense_category":
            return "def search" in lowered and "category" in lowered and ".lower()" in lowered

        if feature == "expense_total":
            return ("def show_total" in lowered or "total =" in lowered) and "sum(" in lowered

        if feature == "expenses_json":
            return "expenses.json" in lowered

        if feature == "json_persistence":
            return "json.loads" in lowered and "json.dumps" in lowered and "write_text" in lowered

        if feature == "delete_item":
            return "def delete_" in lowered and ".pop(" in lowered

        if feature == "list_items":
            return "def list_" in lowered and "enumerate" in lowered

        if feature == "add_item":
            return "def add_" in lowered and ".append(" in lowered

        return True

    def audit_requested_code_features(self, results, requirements, issues):

        if not requirements["is_code_request"]:
            return

        features = requirements.get("requested_code_features", [])
        if not features:
            return

        result = results.get("Code_brain", {})
        code = str(
            result.get("generated_code")
            or result.get("code")
            or result.get("answer")
            or ""
        )

        missing = [
            feature
            for feature in features
            if not self.code_feature_present(feature, code)
        ]

        for feature in missing[:8]:
            self.add_issue(
                issues,
                "Code_brain",
                "high",
                f"Requested feature is missing: {feature}.",
                "Read every numbered requirement and update the code so this exact feature is implemented."
            )

    def audit_math(self, results, requirements, issues):
        if not requirements["is_math_request"]:
            return

        result = results.get("Math_brain", {})
        success = result.get("success") is True
        confidence = result.get("confidence", 0)
        steps = result.get("steps", [])
        verification = result.get("verification", {})

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

        if not isinstance(verification, dict) or verification.get("passed") is not True:
            self.add_issue(
                issues,
                "Math_brain",
                "high",
                "Math answer was not independently verified.",
                "Substitute the result back into the original problem and return verification evidence."
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

        requested_sentence_count = requirements.get("requested_sentence_count")
        if requested_sentence_count:
            sentence_count = self.count_sentences(output)
            if sentence_count and abs(sentence_count - requested_sentence_count) > 1:
                self.add_issue(
                    issues,
                    "Story_brain",
                    "medium",
                    f"Story sentence count is off: requested {requested_sentence_count}, got about {sentence_count}.",
                    "Rewrite the final story to match the requested sentence count more closely."
                )

    def count_sentences(self, text):

        sentences = [
            sentence.strip()
            for sentence in re.split(r"[.!?]+", str(text))
            if sentence.strip()
        ]
        return len(sentences)

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

        if requirements["code_only"]:
            has_code_block = "```" in text or re.search(r"\b(import|from|def|class)\s+[a-zA-Z_]", text)
            if not has_code_block:
                self.add_issue(
                    issues,
                    "Response_brain",
                    "high",
                    "The final response does not look like code even though the user asked for code only.",
                    "Return only the final code block or raw code."
                )

            forbidden_response_markers = [
                "here is a first code structure draft",
                "main pieces:",
                "plan:",
                "quality note:"
            ]
            if any(marker in lowered for marker in forbidden_response_markers):
                self.add_issue(
                    issues,
                    "Response_brain",
                    "medium",
                    "The final code-only response contains notes, plan text, or quality chatter.",
                    "For code-only requests, show the code only after Quality_Control passes."
                )

    def text_from_result(self, result):

        if not isinstance(result, dict):
            return str(result)

        parts = []
        for key in [
            "display_text",
            "answer",
            "final_output",
            "story",
            "draft",
            "summary",
            "generated_code",
            "result",
            "best_answer"
        ]:
            value = result.get(key)
            if value:
                parts.append(str(value))

        creative_help = result.get("creative_help") or result.get("creative_fallback")
        if isinstance(creative_help, dict):
            for key in ["answer", "final_output", "story", "generated_code", "concept", "title"]:
                value = creative_help.get(key)
                if value:
                    parts.append(str(value))

        return "\n".join(parts)

    def looks_like_internal_report(self, text):

        lowered = str(text).lower()
        markers = [
            "goal:",
            "core idea:",
            "novel twist:",
            "validation:",
            "tradeoff:",
            "implementation:",
            "direction:"
        ]
        return sum(1 for marker in markers if marker in lowered) >= 3

    def looks_like_story_template(self, text):

        lowered = str(text).lower()
        story_markers = [
            " lived in ",
            " wanted to ",
            "one morning",
            "felt nervous",
            "opened the door",
            "next chapter"
        ]
        return sum(1 for marker in story_markers if marker in lowered) >= 3

    def code_has_real_structure(self, text):

        code = str(text)
        lowered = code.lower()
        if not code.strip():
            return False
        if "```python" in lowered:
            return True
        if re.search(r"\b(import|from|def|class)\s+[a-zA-Z_]", code):
            return True
        if 'if __name__ == "__main__"' in code:
            return True
        return False

    def audit_domain_mismatch(self, results, requirements, issues):

        response = results.get("Response_brain", {})
        response_text = self.text_from_result(response)

        if requirements["is_code_request"]:
            code = self.text_from_result(results.get("Code_brain", {}))
            if not self.code_has_real_structure(code):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    "Code request did not produce a real code structure.",
                    "Return actual runnable code or a concrete code analysis result, not a story or abstract concept."
                )

            if self.looks_like_story_template(response_text):
                self.add_issue(
                    issues,
                    "Response_brain",
                    "high",
                    "Final response looks like a story even though the user asked for code.",
                    "Select Code_brain output and return code only when requested."
                )

        if requirements["is_story_request"]:
            story_text = self.text_from_result(results.get("Story_brain", {}))
            creative_text = self.text_from_result(results.get("Creative_brain", {}))
            combined = f"{story_text}\n{creative_text}\n{response_text}"

            if self.code_has_real_structure(response_text) and not story_text.strip():
                self.add_issue(
                    issues,
                    "Response_brain",
                    "high",
                    "Final response looks like code even though the user asked for a story.",
                    "Select Story_brain or Creative_brain final story output."
                )

            if self.looks_like_internal_report(combined):
                self.add_issue(
                    issues,
                    "Story_brain",
                    "high",
                    "Story flow is exposing internal creative planning fields.",
                    "Return only the final story text."
                )

        if requirements["is_reliability_request"] and self.looks_like_story_template(response_text):
            self.add_issue(
                issues,
                "Response_brain",
                "high",
                "Final response looks fictional even though the user asked for reliable information.",
                "Select Research_brain or Fact_Check_brain evidence-based output."
            )

    def audit_context_usage(self, data, requirements, issues):

        if not requirements.get("needs_local_data"):
            return

        data_context = self.get_data_context(data)
        knowledge = self.get_knowledge_context(data)
        shared_context = self.get_shared_context(data)

        has_data = bool(data_context.get("available") or data_context.get("matches"))
        has_knowledge = bool(knowledge.get("available") or knowledge.get("matches"))
        has_shared = bool(
            shared_context.get("local_data", {}).get("available")
            or shared_context.get("dictionary", {}).get("available")
            or shared_context.get("knowledge", {}).get("available")
        )

        if not has_data and not has_knowledge and not has_shared:
            self.add_issue(
                issues,
                "Manager_brain",
                "medium",
                "The request needs local/reliable context, but no DATA or knowledge context was available.",
                "Attach Data_context and Knowledge_context to the specialist brains before final response."
            )

    def audit_internal_report_leakage(self, results, requirements, issues):

        bad_markers = [
            "goal:",
            "core idea:",
            "novel twist:",
            "validation:",
            "tradeoff:",
            "direction:"
        ]

        for brain_name, result in results.items():
            if not isinstance(result, dict):
                continue

            text = " ".join(
                str(result.get(key, ""))
                for key in ["answer", "final_output", "story", "draft", "summary"]
            ).lower()

            if text and sum(1 for marker in bad_markers if marker in text) >= 3:
                target = brain_name
                self.add_issue(
                    issues,
                    target,
                    "high",
                    f"{brain_name} appears to expose an internal simulation/report instead of the final user-facing result.",
                    "Return the final user-facing result only; keep internal planning inside thinking_trace."
                )

    # ---------- output ----------

    def build_retry_requests(self, issues):
        retry_requests = []

        non_retry_brains = {
            "Response_brain",
            "Quality_Control_brain",
            "Security_brain",
            "Learning_brain"
        }

        grouped = {}
        for issue in issues:
            brain_name = issue.get("target_brain")
            if not brain_name or brain_name in non_retry_brains:
                continue
            if issue.get("severity") in {"critical", "high", "medium"}:
                grouped.setdefault(brain_name, []).append(issue)

        severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        for brain_name, brain_issues in grouped.items():
            brain_issues.sort(
                key=lambda item: severity_order.get(item.get("severity"), 0),
                reverse=True
            )
            retry_requests.append({
                "target_brain": brain_name,
                "instruction": " ".join(
                    str(item.get("instruction", ""))
                    for item in brain_issues[:8]
                    if item.get("instruction")
                ),
                "problem": " | ".join(
                    str(item.get("problem", ""))
                    for item in brain_issues[:8]
                    if item.get("problem")
                ),
                "severity": brain_issues[0].get("severity"),
                "failed_requirements": [
                    item.get("problem")
                    for item in brain_issues[:8]
                ]
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

    def build_requirement_checks(self, results, requirements):

        checks = []

        for brain_name in self.expected_brains(requirements):
            result = results.get(brain_name)
            checks.append({
                "requirement": f"run_{brain_name}",
                "passed": isinstance(result, dict) and not result.get("error") and not result.get("skipped"),
                "target_brain": brain_name
            })

        if requirements.get("is_code_request"):
            code_result = results.get("Code_brain", {})
            code = ""
            if isinstance(code_result, dict):
                code = str(
                    code_result.get("generated_code")
                    or code_result.get("code")
                    or code_result.get("answer")
                    or ""
                )

            expected_kind = requirements.get("expected_program_kind")
            if expected_kind:
                checks.append({
                    "requirement": f"program_kind_{expected_kind}",
                    "passed": isinstance(code_result, dict) and code_result.get("program_kind") == expected_kind,
                    "target_brain": "Code_brain"
                })

            for feature in requirements.get("requested_code_features", []):
                checks.append({
                    "requirement": feature,
                    "passed": self.code_feature_present(feature, code),
                    "target_brain": "Code_brain"
                })

        if requirements.get("is_math_request"):
            math_result = results.get("Math_brain", {})
            checks.append({
                "requirement": "math_solved",
                "passed": isinstance(math_result, dict) and math_result.get("success") is True,
                "target_brain": "Math_brain"
            })
            checks.append({
                "requirement": "math_verified",
                "passed": isinstance(math_result, dict) and math_result.get("verification", {}).get("passed") is True,
                "target_brain": "Math_brain"
            })
            if requirements.get("wants_steps"):
                checks.append({
                    "requirement": "step_by_step",
                    "passed": isinstance(math_result, dict) and bool(math_result.get("steps")),
                    "target_brain": "Math_brain"
                })

        output = self.requirement_output(results, requirements)
        for requirement in requirements.get("atomic_requirements", [])[:40]:
            passed, evidence = self.atomic_requirement_check(
                requirement,
                output,
                results,
                requirements
            )
            checks.append({
                "requirement": requirement.get("id", requirement.get("text", "explicit_requirement")),
                "description": requirement.get("text", ""),
                "passed": passed,
                "evidence": evidence,
                "target_brain": "Code_brain" if requirements.get("is_code_request") else "Manager_brain"
            })

        return checks

    def process(self, data):
        report = self.get_understanding_report(data)
        results = self.get_results(data)
        text = self.extract_text(data, report)
        requirements = self.request_requirements(text, report)
        issues = []

        self.audit_expected_brains(results, requirements, issues)
        self.audit_code(results, requirements, issues)
        self.audit_requested_code_features(results, requirements, issues)
        self.audit_math(results, requirements, issues)
        self.audit_reliability(results, requirements, issues)
        self.audit_story(results, requirements, issues)
        self.audit_response_risk(results, requirements, issues)
        self.audit_domain_mismatch(results, requirements, issues)
        self.audit_context_usage(data, requirements, issues)
        self.audit_internal_report_leakage(results, requirements, issues)
        self.audit_atomic_requirements(results, requirements, issues)
        self.audit_small_details(results, requirements, issues)

        retry_requests = self.build_retry_requests(issues)
        score = self.quality_score(issues)
        requirement_checks = self.build_requirement_checks(results, requirements)
        passed = score >= 78 and not retry_requests

        self.save_statistics(passed, score)

        return {
            "brain": "Quality_Control_brain",
            "passed": passed,
            "quality_score": score,
            "needs_retry": bool(retry_requests),
            "retry_requests": retry_requests,
            "issues": issues[:20],
            "requirement_checks": requirement_checks[:40],
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
