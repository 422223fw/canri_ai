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
import sys
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json


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

        atomic_write_json(STATS_FILE, self.statistics)

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

    def get_cognitive_workspace(self, data):
        if not isinstance(data, dict):
            return {}
        workspace = data.get("cognitive_workspace", {})
        return workspace if isinstance(workspace, dict) else {}

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

    def advanced_code_capabilities(self, lowered):
        markers = {
            "multi_file": [
                "multi-file", "multiple files", "several files", "large system",
                "large project", "architecture", "production-ready", "professional project",
            ],
            "database": ["database", "sqlite", "sql", "repository"],
            "api": ["api", "rest", "endpoint", "fastapi", "web service"],
            "authentication": ["authentication", "authenticate", "login", "bearer token"],
            "async": ["async", "asynchronous", "await", "non-blocking"],
            "concurrency": ["concurrent", "parallel", "worker", "thread", "task group"],
            "security": ["security", "secure", "password hashing", "authorization"],
            "cryptography": ["cryptography", "encrypt", "encryption", "decrypt", "fernet", "aes"],
            "tests": ["tests", "testing", "pytest", "test suite", "coverage", "regression"],
            "dependencies": ["dependencies", "requirements.txt", "pyproject.toml"],
            "hardware_integration": [
                "hardware", "arduino", "raspberry pi", "gpio", "sensor",
                "serial", "microcontroller", "embedded", "firmware", "iot",
            ],
            "scientific_computing": [
                "science", "scientific", "physics", "measurement", "calibration",
                "experiment", "gravity", "temperature", "voltage", "signal",
            ],
        }
        detected = {
            name: any(marker in lowered for marker in values)
            for name, values in markers.items()
        }
        advanced_count = sum(
            detected[name]
            for name in [
                "database", "api", "authentication", "async", "concurrency",
                "security", "cryptography", "tests", "hardware_integration",
                "scientific_computing",
            ]
        )
        detected["advanced_project"] = (
            detected["multi_file"]
            or advanced_count >= 3
            or detected["hardware_integration"]
        )
        if detected["authentication"]:
            detected["database"] = True
            detected["api"] = True
            detected["security"] = True
        if detected["api"]:
            detected["database"] = True
            detected["async"] = True
            detected["dependencies"] = True
        if detected["cryptography"]:
            detected["security"] = True
            detected["dependencies"] = True
        if detected["hardware_integration"]:
            detected["async"] = True
            detected["concurrency"] = True
            detected["dependencies"] = True
            detected["tests"] = True
        if detected["advanced_project"]:
            detected["multi_file"] = True
        return detected

    def project_files_from_result(self, result):
        if not isinstance(result, dict):
            return {}
        value = result.get("project_files")
        if isinstance(value, dict):
            return {
                str(path).replace("\\", "/"): str(content)
                for path, content in value.items()
            }
        files = {}
        for item in value or []:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("name")
            if path:
                files[str(path).replace("\\", "/")] = str(item.get("content", ""))
        return files

    def code_text_from_result(self, result):
        files = self.project_files_from_result(result)
        if files:
            return "\n\n".join(
                f"# FILE: {path}\n{files[path]}"
                for path in sorted(files)
            )
        if not isinstance(result, dict):
            return str(result or "")
        return str(
            result.get("generated_code")
            or result.get("code")
            or result.get("answer")
            or ""
        )

    def request_requirements(self, text, report):
        lowered = text.lower()
        advanced_capabilities = self.advanced_code_capabilities(lowered)
        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()
        contract = report.get("request_contract", {})
        if not isinstance(contract, dict):
            contract = {}
        expected_program_kind = self.detect_expected_program_kind(lowered)
        inferred_code_request = bool(
            topic == "code"
            or intent in {"code_generation", "code_analysis"}
            or (
                expected_program_kind
                and any(marker in lowered for marker in [
                    "python", "code", "program", "app", "terminal", "runnable",
                ])
            )
        )

        requirements = {
            "has_request_contract": bool(contract),
            "topic": topic,
            "intent": intent,
            "is_code_request": inferred_code_request,
            "is_code_analysis": intent == "code_analysis",
            "is_code_generation": inferred_code_request and intent != "code_analysis",
            "is_math_request": topic == "math" or intent == "math" or self.looks_like_math(lowered),
            "is_story_request": topic == "story" or intent == "story_creation",
            "is_reliability_request": not inferred_code_request and any(
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
            "requested_question_count": self.extract_requested_item_count(
                lowered,
                r"(?:multiple[- ]choice\s+)?questions?",
            ),
            "requested_choice_count": self.extract_requested_item_count(
                lowered,
                r"(?:answer\s+)?(?:choices?|options?)",
            ),
            "expected_program_kind": expected_program_kind,
            "requested_code_features": self.extract_requested_code_features(
                lowered,
                expected_program_kind,
            ),
            "advanced_code_capabilities": advanced_capabilities,
            "is_advanced_code_project": advanced_capabilities.get("advanced_project", False),
            "needs_local_data": (
                not inferred_code_request
                and any(
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
                )
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

        for brain_name in preferred:
            text = self.text_from_result(results.get(brain_name, {}))
            if text:
                return text
        return ""

    def semantic_explicit_code_check(self, requirement_text, code):

        requested = str(requirement_text or "").lower()
        lowered = str(code or "").lower()

        question_count = self.extract_requested_item_count(
            requested,
            r"(?:multiple[- ]choice\s+)?questions?",
        )
        if question_count is not None:
            actual = len(self.quiz_records(code))
            return actual == question_count, f"semantic:question count {actual}/{question_count}"

        choice_count = self.extract_requested_item_count(
            requested,
            r"(?:answer\s+)?(?:choices?|options?)",
        )
        if choice_count is not None:
            questions = self.quiz_records(code)
            counts = [len(item.get("choices", [])) for item in questions]
            return bool(counts) and all(count == choice_count for count in counts), f"semantic:choice counts {counts}"

        if "invalid input" in requested or "ask again" in requested or "invalid numbers" in requested or "invalid units" in requested:
            passed = self.code_feature_present("retry_invalid_input", code)
            return passed, "semantic:invalid input is retried"

        if "keep running" in requested and "exit" in requested:
            return self.code_feature_present("repeat_until_exit", code), "semantic:loop exits on request"

        if "standard library" in requested:
            try:
                tree = ast.parse(code)
            except (SyntaxError, ValueError):
                return False, "semantic:code cannot be parsed for import validation"
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    imported.add(node.module.split(".", 1)[0])
            external = imported - set(getattr(sys, "stdlib_module_names", set())) - {"__future__"}
            return not external, f"semantic:external imports {sorted(external)}"

        if "only output" in requested and "code" in requested:
            return True, "semantic:output format is checked on Response_brain"

        if "play again" in requested or "run again" in requested:
            return self.code_feature_present("play_again", code), "semantic:repeat complete run"

        score_match = re.search(r"\b(?:score\s+)?(?:of|out\s+of)\s+(\d+)\b", requested)
        if score_match:
            expected = int(score_match.group(1))
            passed, evidence = self.quantified_code_constraint_passed(
                {
                    "target": "score_denominator",
                    "quantity": expected,
                    "mode": "exact",
                },
                code,
            )
            return passed, f"semantic:{evidence}"

        if "celsius" in requested and "fahrenheit" in requested and "convert" in requested:
            return self.code_feature_present("temperature_conversion", code), "semantic:both temperature formulas"

        repeats_for_names = (
            "name" in requested
            and "exit" in requested
            and any(marker in requested for marker in ["keep asking", "until", "repeat", "loop"])
        )
        if repeats_for_names:
            passed = all(marker in lowered for marker in ["while", "input(", "exit", "break"])
            return passed, "semantic:name input loop exits with break"

        asks_for_name = "name" in requested and any(
            marker in requested for marker in ["ask for", "asks for", "enter your name", "user's name"]
        )
        if asks_for_name:
            passed = "input(" in lowered and re.search(r"\bname\b", lowered) is not None
            return passed, "semantic:name is read from input"

        greets_name = "hello" in requested and "name" in requested and any(
            marker in requested for marker in ["print", "prints", "display", "show"]
        )
        if greets_name:
            passed = all(marker in lowered for marker in ["print(", "hello"]) and bool(
                re.search(r"\bname\b", lowered)
            )
            return passed, "semantic:personalized greeting is printed"

        return None

    def atomic_requirement_check(self, requirement, output, results, requirements):

        requirement = requirement if isinstance(requirement, dict) else {"text": str(requirement)}
        requirement_id = requirement.get("id") or "unnamed_requirement"
        kind = requirement.get("kind", "explicit_constraint")
        feature = requirement.get("feature")
        code_result = results.get("Code_brain", {})
        code = ""
        if isinstance(code_result, dict):
            code = self.code_text_from_result(code_result)

        if kind == "feature" and feature:
            passed = self.code_feature_present(feature, code) if requirements.get("is_code_generation") else True
            return passed, f"feature:{feature}"

        if kind == "quantified_constraint" and requirements.get("is_code_generation"):
            return self.quantified_code_constraint_passed(requirement, code)

        if kind == "interaction_constraint" and requirements.get("is_code_generation"):
            interaction_feature = {
                "repeat_until_exit": "repeat_until_exit",
                "retry_invalid_input": "retry_invalid_input",
                "play_again": "play_again",
                "preserve_previous_work": None,
            }.get(requirement_id)
            if interaction_feature:
                return self.code_feature_present(interaction_feature, code), f"interaction:{interaction_feature}"
            if requirement_id == "preserve_previous_work":
                continuation = code_result.get("continuation_preservation", {}) if isinstance(code_result, dict) else {}
                return bool(
                    continuation.get("previous_kind_preserved")
                    or code_result.get("existing_code_detected")
                ), "continuation preservation metadata"

        if requirement_id == "runnable_output":
            if not requirements.get("is_code_generation"):
                return True, "not a code-generation request"
            project_review = code_result.get("project_review", {}) if isinstance(code_result, dict) else {}
            if self.project_files_from_result(code_result):
                syntax_ok = not self.project_syntax_errors(code_result)
                structure_ok = bool(project_review.get("ready"))
            else:
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

        if kind == "negative_constraint":
            lowered_requirement = requirement.get("text", "").lower()
            if any(
                marker in lowered_requirement
                for marker in ["external librar", "third-party", "third party"]
            ):
                try:
                    tree = ast.parse(code)
                except (SyntaxError, ValueError):
                    return False, "code could not be parsed for import checking"

                imported_roots = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                        imported_roots.add(node.module.split(".", 1)[0])

                local_modules = {
                    Path(name).stem
                    for name in self.project_files_from_result(code_result)
                    if str(name).endswith(".py")
                }
                allowed = set(getattr(sys, "stdlib_module_names", set())) | local_modules | {"__future__"}
                external = sorted(imported_roots - allowed)
                return not external, f"external imports: {', '.join(external) or 'none'}"

            if any(
                marker in lowered_requirement
                for marker in ["do not output", "do not return", "do not include"]
            ):
                response = self.text_from_result(results.get("Response_brain", {})) or output
                leaked = self.looks_like_internal_report(response)
                return not leaked, "prohibited internal-output check"

            # Unknown prohibitions are not converted into positive lexical
            # requirements. Dedicated domain checks remain responsible for
            # proving violations without creating false failures.
            return True, "covered by prohibition-specific checks"

        if kind == "explicit_constraint" and requirements.get("is_code_generation"):
            semantic_check = self.semantic_explicit_code_check(
                requirement.get("text", ""),
                code,
            )
            if semantic_check is not None:
                return semantic_check

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
            return len(found) >= threshold, f"lexical evidence: {', '.join(found)}"

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
            severity = "medium" if str(evidence).startswith("lexical evidence:") else "high"
            self.add_issue(
                issues,
                target,
                severity,
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
            code = self.code_text_from_result(code_result)

        if requirements.get("is_code_generation"):
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
            story_output = self.text_from_result(results.get("Story_brain", {}))
            lowered_output = (story_output or output).lower()
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

    def extract_requested_item_count(self, lowered, target_pattern):

        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20,
        }
        match = re.search(
            rf"\b(?:exactly\s+)?(\d+|{'|'.join(number_words)})\s+{target_pattern}\b",
            str(lowered or ""),
        )
        if not match:
            return None
        value = match.group(1)
        return int(value) if value.isdigit() else number_words.get(value)

    def detect_expected_program_kind(self, lowered):

        equation_signals = [
            "equation calculator", "calculator for equations", "solve equations",
            "solve an equation", "linear equation calculator",
            "quadratic equation calculator", "polynomial equation calculator",
            "\u05de\u05d7\u05e9\u05d1\u05d5\u05df \u05de\u05e9\u05d5\u05d5\u05d0\u05d5\u05ea",
        ]
        if any(signal in lowered for signal in equation_signals):
            return "equation_calculator"

        checks = [
            ("name_greeter", [
                "asks for the user's name", "ask for the user's name",
                "asks for names", "hello, <name>", "hello <name>",
            ]),
            ("expense_tracker", ["expense tracker", "expenses", "amount spent", "total amount", "search expenses", "category"]),
            ("calendar_app", ["calendar", "appointment", "appointments", "event planner", "schedule event"]),
            ("contact_book", ["contact book", "contacts", "phone book", "address book"]),
            ("library_manager", ["library manager", "library management", "book management", "book tracker", "book library", "borrowed books", "reading list"]),
            ("flashcards_app", ["flashcards", "flash cards", "study cards"]),
            ("shop_inventory", ["shop inventory", "store inventory", "inventory tracker", "stock", "products in stock"]),
            ("todo_app", ["to-do", "todo", "task list", "tasks", "mark a task"]),
            ("notes_app", ["note app", "notes app", "notes", "note taking"]),
            ("temperature_converter", [
                "temperature converter", "convert temperature", "convert celsius",
                "convert fahrenheit", "celsius or fahrenheit", "celsius to fahrenheit",
                "fahrenheit to celsius",
            ]),
            ("weather_app", ["weather app", "weather", "humidity", "forecast", "weather api"]),
            ("calculator", ["calculator", "calculate", "addition", "subtraction", "multiplication", "division"]),
            ("quiz_game", ["quiz", "multiple choice"]),
        ]

        for kind, signals in checks:
            if any(signal in lowered for signal in signals):
                return kind

        return None

    def extract_requested_code_features(self, lowered, program_kind=None):

        features = []
        shared_checks = [
            ("old_json_compatibility", [
                "compatible with old", "compatible with older", "older library.json",
                "older notes.json", "old json", "same json format", "keep the same",
                "backward compatible", "backwards compatible",
            ]),
            ("json_persistence", ["json file", "library.json", "notes.json", "save notes", "load notes", "save tasks", "load tasks", "save and load"]),
            ("delete_item", ["delete a note", "delete notes", "delete a task", "delete task", "delete an expense", "delete expense", "delete a book", "delete book"]),
            ("list_items", ["list notes", "list tasks", "list books", "list all", "list all expenses"]),
            ("add_item", ["add notes", "add note", "add tasks", "add task", "add books", "add a book", "add book", "add expenses", "add an expense", "add expense"])
        ]

        kind_checks = {
            "name_greeter": [
                ("prompt_for_name", ["name"]),
                ("personalized_greeting", ["hello"]),
                ("repeat_until_exit", ["exit", "keep asking", "until the user types exit"]),
            ],
            "calendar_app": [
                ("calendar_events", ["calendar", "appointment", "appointments", "event", "events by date", "schedule event"]),
            ],
            "contact_book": [
                ("contact_records", ["contacts", "contact book", "phone", "email"]),
            ],
            "library_manager": [
                ("library_books", ["library manager", "library management", "book management", "book library", "book tracker", "books with title", "borrowed books", "reading list", "book author"]),
                ("borrow_book", ["borrow", "borrowed"]),
                ("return_book", ["return"]),
            ],
            "flashcards_app": [
                ("flashcards", ["flashcards", "flash cards", "question", "answer", "study cards"]),
            ],
            "shop_inventory": [
                ("shop_inventory", ["shop inventory", "store inventory", "inventory", "stock", "products in stock"]),
            ],
            "notes_app": [
                ("edit_existing_item", ["edit an existing", "edit a note", "edit note", "update an existing", "modify an existing"]),
                ("tags", ["add tags", "tags to", "by tag", "tags", "tag"]),
                ("search_title_body_tag", ["search notes by title", "search by title", "search notes by word", "search notes", "search by tag", "title, body, or tag"]),
                ("export_txt", ["export", "txt file", "readable txt", "notes_export.txt"]),
            ],
            "expense_tracker": [
                ("expense_amount", ["amount", "amount spent"]),
                ("expense_category", ["category", "search expenses by category"]),
                ("expense_description", ["description"]),
                ("search_expense_category", ["search expenses by category", "search by category"]),
                ("expense_total", ["total amount spent", "show the total", "total spent"]),
                ("expenses_json", ["expenses.json"]),
            ],
            "quiz_game": [
                ("quiz_multiple_choice", ["multiple choice", "multiple-choice", "answer choices", "answer options"]),
                ("quiz_numeric_choice", ["entering 1, 2, 3, or 4", "enter 1, 2, 3, or 4", "answer by entering"]),
                ("retry_invalid_input", ["invalid input", "ask again", "reject invalid"]),
                ("quiz_final_score", ["final score", "score out of"]),
                ("play_again", ["play again", "run again"]),
            ],
            "temperature_converter": [
                ("temperature_value", ["temperature value", "temperature"]),
                ("temperature_units", ["celsius", "fahrenheit"]),
                ("temperature_conversion", ["convert", "converted temperature"]),
                ("retry_invalid_input", ["invalid number", "invalid unit", "invalid input", "safely"]),
                ("repeat_until_exit", ["keep running until", "types exit", "enter exit"]),
            ],
            "equation_calculator": [
                ("parse_equation", ["equation", "equations"]),
                ("solve_linear_equation", ["linear", "equation calculator", "solve equations"]),
                ("solve_quadratic_equation", ["quadratic", "x^2", "x**2"]),
                ("verify_equation_solution", ["verify", "check the solution", "equation calculator"]),
                ("repeat_until_exit", ["keep running", "until", "exit", "terminal"]),
            ],
        }

        checks = [*shared_checks, *kind_checks.get(program_kind, [])]

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
        identity = (str(target_brain), str(problem).strip().lower())
        if any(
            (str(item.get("target_brain")), str(item.get("problem", "")).strip().lower()) == identity
            for item in issues
            if isinstance(item, dict)
        ):
            return
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
        if requirements.get("is_code_analysis"):
            explanation = str(
                result.get("answer")
                or result.get("summary")
                or result.get("code_explanation")
                or ""
            ).strip()
            if result.get("mode") != "code_analysis" or not explanation:
                self.add_issue(
                    issues,
                    "Code_brain",
                    "critical",
                    "The code-analysis request did not return a concrete explanation.",
                    "Analyze the supplied code and return a clear explanation of its behavior."
                )
            if not result.get("code_analyzed"):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    "The explanation does not identify the code that was analyzed.",
                    "Preserve the supplied code and analyze that exact snippet."
                )
            return

        project_files = self.project_files_from_result(result)
        code = self.code_text_from_result(result)
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

        syntax_errors = self.project_syntax_errors(result) if project_files else []
        syntax_error = self.python_syntax_error(code) if not project_files else None
        if syntax_error or syntax_errors:
            self.add_issue(
                issues,
                "Code_brain",
                "critical",
                "Generated Python code has a syntax error.",
                "Fix the code so it can be parsed by Python before returning it.",
                syntax_error or "; ".join(syntax_errors[:5])
            )

        if requirements.get("is_advanced_code_project"):
            if len(project_files) < 5:
                self.add_issue(
                    issues,
                    "Code_brain",
                    "critical",
                    "The advanced request did not return a real multi-file project.",
                    "Return structured project_files with separate model, repository, service, transport, and test files."
                )
            project_review = result.get("project_review", {})
            if not isinstance(project_review, dict) or not project_review.get("ready"):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "critical",
                    "The generated project did not pass project-level self-review.",
                    "Fix every project review error before returning the project.",
                    project_review.get("errors", []) if isinstance(project_review, dict) else []
                )
            requested_capabilities = requirements.get("advanced_code_capabilities", {})
            delivered_capabilities = result.get("capabilities", {})
            for capability, requested in requested_capabilities.items():
                if capability == "advanced_project" or not requested:
                    continue
                if not delivered_capabilities.get(capability):
                    self.add_issue(
                        issues,
                        "Code_brain",
                        "high",
                        f"Advanced capability was requested but not delivered: {capability}.",
                        "Regenerate the project with executable evidence for this capability."
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

        function_selection = result.get("function_selection", {})
        if isinstance(function_selection, dict) and function_selection:
            if function_selection.get("missing_functions"):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "critical",
                    "The selected program is missing required functions: "
                    + ", ".join(function_selection.get("missing_functions", [])[:12]) + ".",
                    "Regenerate the requested program with every required function and its call dependencies.",
                    function_selection,
                )
            elif not function_selection.get("complete"):
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    "Code function selection did not produce a complete executable function set.",
                    "Select the request-specific entry point and every function it depends on.",
                    function_selection,
                )

        if expected_kind == "quiz_game":
            questions = self.quiz_records(code)
            expected_questions = requirements.get("requested_question_count")
            if expected_questions is not None and len(questions) != expected_questions:
                self.add_issue(
                    issues,
                    "Code_brain",
                    "high",
                    f"Quiz question count is wrong: expected {expected_questions}, got {len(questions)}.",
                    "Generate exactly the requested number of complete question records.",
                )
            expected_choices = requirements.get("requested_choice_count")
            if expected_choices is not None and questions:
                choice_counts = [len(item.get("choices", [])) for item in questions]
                if any(count != expected_choices for count in choice_counts):
                    self.add_issue(
                        issues,
                        "Code_brain",
                        "high",
                        f"Quiz choice count is wrong: expected {expected_choices} choices for every question.",
                        "Give every question exactly the requested number of answer choices.",
                        choice_counts,
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

        if (
            requirements["wants_runnable"]
            and not project_files
            and "if __name__" not in code
            and "def main(" not in code
        ):
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

    def project_syntax_errors(self, result):
        errors = []
        for path, content in self.project_files_from_result(result).items():
            if not path.endswith(".py"):
                continue
            try:
                ast.parse(content)
            except SyntaxError as error:
                errors.append(f"{path}: line {error.lineno}: {error.msg}")
        return errors

    def literal_assignment(self, code, variable_name):

        try:
            tree = ast.parse(str(code or ""))
        except (SyntaxError, ValueError):
            return None
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(target, ast.Name) and target.id == variable_name for target in targets):
                continue
            try:
                return ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                return None
        return None

    def quiz_records(self, code):

        questions = self.literal_assignment(code, "QUESTIONS")
        if not isinstance(questions, (list, tuple)):
            return []
        return [item for item in questions if isinstance(item, dict)]

    def quantified_code_constraint_passed(self, requirement, code):

        target = str(requirement.get("target", "")).lower()
        quantity = requirement.get("quantity")
        mode = requirement.get("mode", "exact")
        questions = self.quiz_records(code)

        if target in {"question", "multiple_choice_question"}:
            actual = len(questions)
        elif target in {"answer_choice", "answer_option", "choice", "option"}:
            if not questions:
                return False, "no literal quiz question records"
            counts = [len(item.get("choices", [])) for item in questions]
            passed = all(
                count == quantity if mode == "exact"
                else count >= quantity if mode == "minimum"
                else count <= quantity
                for count in counts
            )
            return passed, f"choice counts per question: {counts}"
        elif target == "score_denominator":
            compact = re.sub(r"\s+", "", str(code or "").lower())
            passed = bool(
                isinstance(quantity, int)
                and len(questions) == quantity
                and ("len(questions)" in compact or f"/{quantity}" in compact)
            )
            return passed, f"score denominator expected: {quantity}"
        elif requirement.get("values") and target == "user_input":
            values = [str(value) for value in requirement.get("values", [])]
            literal_values = set(re.findall(r"['\"](\d+)['\"]", str(code or "")))
            question_counts = [
                len(item.get("choices", []))
                for item in questions
                if isinstance(item.get("choices"), (list, tuple))
            ]
            range_driven = bool(
                values
                and question_counts
                and all(count == len(values) for count in question_counts)
                and "range(1, choice_count + 1)" in str(code or "")
            )
            passed = (
                set(values).issubset(literal_values) or range_driven
            ) and "input(" in str(code or "").lower()
            return passed, (
                f"allowed input values found: {sorted(literal_values)}; "
                f"choice counts: {question_counts}"
            )
        else:
            return True, "quantity handled by the domain specialist"

        if not isinstance(quantity, int):
            return False, "missing numeric quantity"
        passed = (
            actual == quantity if mode == "exact"
            else actual >= quantity if mode == "minimum"
            else actual <= quantity
        )
        return passed, f"actual {target} count: {actual}"

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
            return (
                "normalize_" in lowered
                and "isinstance(" in lowered
                and ".get(" in lowered
            )

        if feature == "prompt_for_name":
            return "input(" in lowered and re.search(r"\bname\b", lowered) is not None

        if feature == "personalized_greeting":
            return "print(" in lowered and "hello" in lowered and re.search(r"\bname\b", lowered) is not None

        if feature == "repeat_until_exit":
            return all(marker in lowered for marker in ["while", "input(", "exit", "break"])

        if feature == "calendar_events":
            return "calendar" in lowered and "date" in lowered and "time" in lowered and "events" in lowered

        if feature == "contact_records":
            return "contacts.json" in lowered and "phone" in lowered and "email" in lowered

        if feature == "library_books":
            return "library" in lowered and "title" in lowered and "author" in lowered

        if feature == "borrow_book":
            return "def borrow_" in lowered and "borrowed" in lowered

        if feature == "return_book":
            return "def return_" in lowered and "borrowed" in lowered

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

        if feature == "parse_equation":
            return "def parse_equation" in lowered and "=" in code

        if feature == "solve_linear_equation":
            return "def solve_equation" in lowered and "-c / b" in lowered

        if feature == "solve_quadratic_equation":
            return "discriminant" in lowered and "math.sqrt" in lowered

        if feature == "verify_equation_solution":
            return "def verify_solutions" in lowered and "math.isclose" in lowered

        if feature == "quiz_multiple_choice":
            questions = self.quiz_records(code)
            return bool(questions) and all(
                isinstance(item.get("choices"), (list, tuple))
                and len(item.get("choices", [])) >= 2
                and isinstance(item.get("answer"), int)
                for item in questions
            )

        if feature == "quiz_numeric_choice":
            questions = self.quiz_records(code)
            return (
                bool(questions)
                and "input(" in lowered
                and "int(" in lowered
                and all(
                    1 <= item.get("answer", 0) <= len(item.get("choices", []))
                    for item in questions
                )
            )

        if feature == "retry_invalid_input":
            return (
                "while true" in lowered
                and "input(" in lowered
                and any(marker in lowered for marker in ["please enter", "invalid", "except valueerror"])
            )

        if feature == "quiz_final_score":
            return "final score" in lowered and (
                "len(questions)" in lowered or re.search(r"/\s*\d+", code) is not None
            )

        if feature == "play_again":
            return "play again" in lowered and "while true" in lowered

        if feature == "temperature_value":
            return "temperature" in lowered and "float(" in lowered and "input(" in lowered

        if feature == "temperature_units":
            return "celsius" in lowered and "fahrenheit" in lowered

        if feature == "temperature_conversion":
            compact = re.sub(r"\s+", "", lowered)
            return (
                ("*9/5" in compact or "*1.8" in compact)
                and "+32" in compact
                and "-32" in compact
                and ("*5/9" in compact or "/1.8" in compact)
            )

        if feature == "repeat_until_exit":
            return all(marker in lowered for marker in ["while true", "input(", "exit", "break"])

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

        if not requirements.get("is_code_generation"):
            return

        features = requirements.get("requested_code_features", [])
        if not features:
            return

        result = results.get("Code_brain", {})
        code = self.code_text_from_result(result)

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

        project_files = self.project_files_from_result(result)
        if project_files:
            return self.code_text_from_result(result)
        for key in [
            "display_text",
            "final_output",
            "story",
            "answer",
            "generated_code",
            "best_answer",
            "result",
            "summary",
            "draft"
        ]:
            value = result.get(key)
            if value:
                return str(value)

        creative_help = result.get("creative_help") or result.get("creative_fallback")
        if isinstance(creative_help, dict):
            for key in ["answer", "final_output", "story", "generated_code", "concept", "title"]:
                value = creative_help.get(key)
                if value:
                    return str(value)

        return ""

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
            if requirements.get("is_code_analysis"):
                result = results.get("Code_brain", {})
                if not isinstance(result, dict) or result.get("mode") != "code_analysis" or not result.get("answer"):
                    self.add_issue(
                        issues,
                        "Code_brain",
                        "high",
                        "Code analysis did not produce a screen-ready explanation.",
                        "Return the analysis result instead of a generated program."
                    )
            elif not self.code_has_real_structure(code):
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

            text = self.text_from_result(result).lower()

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

    def build_retry_requests(
        self,
        issues,
        requirements=None,
        requirement_checks=None,
        quality_score=None,
    ):
        retry_requests = []
        requirements = requirements or {}
        requirement_checks = requirement_checks or []

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
            if issue.get("severity") in {"critical", "high"}:
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
                ],
                "failed_requirement_checks": [
                    check.get("requirement")
                    for check in requirement_checks
                    if isinstance(check, dict)
                    and check.get("target_brain") == brain_name
                    and check.get("passed") is False
                ],
                "expected_program_kind": (
                    requirements.get("expected_program_kind")
                    if brain_name == "Code_brain"
                    else None
                ),
                "required_features": (
                    requirements.get("requested_code_features", [])
                    if brain_name == "Code_brain"
                    else []
                ),
                "quality_score": quality_score,
                "force_regeneration": bool(
                    quality_score == 0
                    or any(
                        "wrong program kind" in str(item.get("problem", "")).lower()
                        for item in brain_issues
                    )
                ),
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

        if requirements.get("is_code_generation"):
            code_result = results.get("Code_brain", {})
            code = ""
            if isinstance(code_result, dict):
                code = self.code_text_from_result(code_result)

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

        if requirements.get("is_code_analysis"):
            code_result = results.get("Code_brain", {})
            checks.append({
                "requirement": "code_explained",
                "passed": (
                    isinstance(code_result, dict)
                    and code_result.get("mode") == "code_analysis"
                    and bool(code_result.get("answer"))
                    and bool(code_result.get("code_analyzed"))
                ),
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
        cognitive_workspace = self.get_cognitive_workspace(data)
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

        score = self.quality_score(issues)
        requirement_checks = self.build_requirement_checks(results, requirements)
        existing_check_ids = {
            str(check.get("requirement"))
            for check in requirement_checks
            if isinstance(check, dict)
        }
        for item in cognitive_workspace.get("requirements", [])[:80]:
            if not isinstance(item, dict) or item.get("status") != "passed":
                continue
            requirement_id = str(item.get("id") or item.get("text"))
            if requirement_id in existing_check_ids:
                continue
            requirement_checks.append({
                "requirement": requirement_id,
                "description": item.get("text", ""),
                "passed": item.get("status") == "passed",
                "evidence": item.get("evidence"),
                "target_brain": (item.get("owners") or ["Manager_brain"])[0],
                "source": item.get("verification_source"),
            })
        retry_requests = self.build_retry_requests(
            issues,
            requirements,
            requirement_checks,
            score,
        )
        passed_requirement_ids = list(dict.fromkeys([
            *cognitive_workspace.get("passed_requirement_ids", []),
            *[
                check.get("requirement")
                for check in requirement_checks
                if isinstance(check, dict) and check.get("passed") is True
            ],
        ]))
        for request in retry_requests:
            request["preserve_requirement_ids"] = passed_requirement_ids[:80]
        blocking_issues = [
            issue
            for issue in issues
            if issue.get("severity") in {"critical", "high"}
        ]
        advisory_issues = [
            issue
            for issue in issues
            if issue.get("severity") in {"medium", "low"}
        ]
        passed = not retry_requests and not blocking_issues

        self.save_statistics(passed, score)

        return {
            "brain": "Quality_Control_brain",
            "passed": passed,
            "quality_score": score,
            "needs_retry": bool(retry_requests),
            "retry_requests": retry_requests,
            "issues": issues[:20],
            "blocking_issues": blocking_issues[:20],
            "advisory_issues": advisory_issues[:20],
            "requirement_checks": requirement_checks[:40],
            "requirements": requirements,
            "cognitive_workspace_used": bool(cognitive_workspace),
            "workspace_decision": cognitive_workspace.get("decision", {}),
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
