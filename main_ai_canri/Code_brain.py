"""
Code_brain.py
Canri AI
"""

import json
import re
import ast
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from Code_artifact_catalog import CodeArtifactCatalog
from Brain_storage import atomic_write_json, load_json_resilient

try:
    from Scanner_knowledge import scanner_evidence
except Exception:
    scanner_evidence = None


DATA_DIR = Path(__file__).parent / "data"

CODE_FILE = DATA_DIR / "code.json"
STATS_FILE = DATA_DIR / "Code_statistics.json"
DEPENDENCY_GRAPH_FILE = DATA_DIR / "Code_dependency_graph.json"
COMPOSITION_TABLE_FILE = DATA_DIR / "Code_composition_tables.json"
ASSEMBLY_PATTERNS_FILE = DATA_DIR / "Code_assembly_patterns.json"
PROJECT_RECIPES_FILE = DATA_DIR / "Code_project_recipes.json"
ADVANCED_PROFILES_FILE = DATA_DIR / "Code_advanced_profiles.json"
FUNCTION_SELECTION_PROFILES_FILE = DATA_DIR / "Code_function_selection_profiles.json"

GENERIC_CODE_TERMS = {
    "code",
    "coding",
    "generation",
    "code_generation",
    "function",
    "program",
    "create",
    "make",
    "build",
    "write",
    "data",
    "task",
    "unknown"
}


class CodeSelfReviewer:

    OPERATION_PATTERNS = {
        "add": (r"\badd\b", ("def add_", ".append(")),
        "list": (r"\blist\b", ("def list_", "enumerate(")),
        "search": (r"\bsearch\b", ("def search",)),
        "borrow": (r"\bborrow\b", ("def borrow_",)),
        "return": (r"\breturn\s+(?:a\s+)?book\b", ("def return_",)),
        "view": (r"\bview\b", ("def view_",)),
        "edit": (r"\bedit\b", ("def edit_",)),
        "delete": (r"\bdelete\b", ("def delete_", ".pop(")),
        "export": (r"\bexport\b", ("def export", ".write_text(")),
        "save": (r"\bsave\b", ("def save_",)),
        "load": (r"\bload\b", ("def load_",)),
        "total": (r"\b(?:total|sum)\b", ("def show_total", "sum(")),
        "mark_done": (r"\bmark\b.*\bdone\b", ("def mark_", '"done"')),
    }

    FIELD_MARKERS = {
        "amount", "category", "description", "title", "body", "name",
        "email", "phone", "date", "time", "tags", "quantity", "price",
        "question", "answer", "status", "priority", "author", "year"
    }

    def extract_request_requirements(self, request_text, program_kind=None):

        request = str(request_text or "")
        lowered = request.lower()
        requirements = []

        def add(identifier, kind, evidence, alternatives=None, **metadata):
            if any(item["id"] == identifier for item in requirements):
                return
            requirement = {
                "id": identifier,
                "kind": kind,
                "evidence": list(evidence),
                "alternatives": list(alternatives or [])
            }
            requirement.update(metadata)
            requirements.append(requirement)

        if any(marker in lowered for marker in ["runnable", "must run", "terminal", "command line"]):
            add("runnable_entry_point", "structure", ["def main(", 'if __name__ == "__main__"'])

        for operation, (request_pattern, evidence) in self.OPERATION_PATTERNS.items():
            if re.search(request_pattern, lowered, re.DOTALL):
                alternatives = []
                if operation == "total":
                    alternatives = [
                        ("def total_", "sum("),
                        ("def calculate_total", "sum(")
                    ]
                add(f"operation_{operation}", "operation", evidence, alternatives)

        file_names = list(dict.fromkeys(re.findall(
            r"\b[\w.-]+\.(?:jsonl?|txt|csv|py|md)\b",
            request,
            flags=re.IGNORECASE
        )))
        for file_name in file_names:
            add(
                f"file_{file_name.lower()}",
                "exact_file",
                [file_name.lower()]
            )

        structured_programs = {
            "expense_tracker", "notes_app", "contact_book", "library_manager",
            "shop_inventory", "calendar_app", "todo_app", "flashcards_app",
        }
        asks_for_record_fields = bool(
            program_kind in structured_programs
            or re.search(r"\b(?:each|every)\s+(?:item|record|book|note|expense|task)\b", lowered)
            or any(marker in lowered for marker in ["fields:", "data fields", "must have:"])
        )
        requested_fields = [
            field
            for field in sorted(self.FIELD_MARKERS)
            if asks_for_record_fields and re.search(rf"\b{re.escape(field)}\b", lowered)
        ]
        for field in requested_fields:
            add(f"field_{field}", "data_field", [f'"{field}"'], [(f"'{field}'",)])

        if "json" in lowered and any(marker in lowered for marker in ["save", "load", "persist"]):
            add("json_persistence", "persistence", ["json.loads", "json.dumps"])
        if any(marker in lowered for marker in ["do not use external", "no external", "standard library only"]):
            add("standard_library_only", "negative_constraint", [])
        if "only output" in lowered and "code" in lowered:
            add("code_only_output", "output_constraint", [])
        if program_kind:
            add(f"program_kind_{program_kind}", "program_kind", [])
        program_fields = {
            "expense_tracker": ["amount", "category", "description"],
            "notes_app": ["title", "body"],
            "contact_book": ["name", "phone", "email"],
            "library_manager": ["title", "author", "year"],
            "shop_inventory": ["name", "quantity", "price"],
        }
        for field in program_fields.get(program_kind, []):
            add(f"field_{field}", "data_field", [f'"{field}"'], [(f"'{field}'",)])

        if program_kind == "quiz_game":
            question_match = re.search(
                r"\b(?:exactly\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
                r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
                r"nineteen|twenty)\s+(?:multiple[- ]choice\s+)?questions?\b",
                lowered,
            )
            question_count = self.number_value(question_match.group(1)) if question_match else 10
            add(
                "quiz_question_count",
                "quiz_question_count",
                [],
                expected=question_count,
            )

            choice_match = re.search(
                r"\b(?:exactly\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
                r"(?:answer\s+)?(?:choices?|options?)\b",
                lowered,
            )
            choice_count = self.number_value(choice_match.group(1)) if choice_match else None
            if choice_count is not None or "multiple choice" in lowered or "multiple-choice" in lowered:
                add(
                    "quiz_choice_count",
                    "quiz_choice_count",
                    [],
                    expected=choice_count or 4,
                )
            if re.search(r"\b(?:1|one)\s*,\s*(?:2|two)\s*,\s*(?:3|three)\s*,?\s*(?:or|and)\s*(?:4|four)\b", lowered):
                add("quiz_numeric_choice_input", "quiz_numeric_choice_input", [])
            if "invalid input" in lowered or "ask again" in lowered or "reject invalid" in lowered:
                add("retry_invalid_input", "retry_invalid_input", [])
            if "play again" in lowered or "run again" in lowered:
                add("play_again", "play_again", [])
            score_match = re.search(r"\b(?:score\s+)?(?:of|out\s+of)\s+(\d+)\b", lowered)
            score_count = int(score_match.group(1)) if score_match else question_count
            add("quiz_score_denominator", "score_denominator", [], expected=score_count)

        if program_kind == "temperature_converter":
            add("temperature_input", "temperature_input", [])
            add("temperature_units", "temperature_units", [])
            add("temperature_conversion", "temperature_conversion", [])
            if "invalid" in lowered or "safely" in lowered:
                add("retry_invalid_input", "retry_invalid_input", [])
            if "exit" in lowered or "keep running" in lowered:
                add("repeat_until_exit", "repeat_until_exit", [])

        return requirements

    def number_value(self, value):

        values = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20,
        }
        normalized = str(value or "").strip().lower()
        return int(normalized) if normalized.isdigit() else values.get(normalized)

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

    def requirement_passed(self, requirement, code):

        lowered_code = str(code or "").lower()
        kind = requirement.get("kind")

        if kind == "quiz_question_count":
            expected = requirement.get("expected")
            questions = self.quiz_records(code)
            return isinstance(expected, int) and len(questions) == expected
        if kind == "quiz_choice_count":
            expected = requirement.get("expected")
            questions = self.quiz_records(code)
            return bool(questions) and isinstance(expected, int) and all(
                isinstance(item.get("choices"), (list, tuple))
                and len(item["choices"]) == expected
                for item in questions
            )
        if kind == "quiz_numeric_choice_input":
            questions = self.quiz_records(code)
            valid_answers = bool(questions) and all(
                isinstance(item.get("answer"), int)
                and 1 <= item["answer"] <= len(item.get("choices", []))
                for item in questions
            )
            return valid_answers and "int(" in lowered_code and "input(" in lowered_code
        if kind == "retry_invalid_input":
            return (
                all(marker in lowered_code for marker in ["while true", "input("])
                and any(
                    marker in lowered_code
                    for marker in ["please enter", "invalid", "except valueerror", "try:"]
                )
            )
        if kind == "play_again":
            return (
                "play again" in lowered_code
                and "while true" in lowered_code
                and ("def ask_to_play_again" in lowered_code or "again" in lowered_code)
            )
        if kind == "score_denominator":
            expected = requirement.get("expected")
            questions = self.quiz_records(code)
            return (
                isinstance(expected, int)
                and len(questions) == expected
                and ("len(questions)" in lowered_code or f"/{expected}" in lowered_code.replace(" ", ""))
            )
        if kind == "temperature_input":
            return "input(" in lowered_code and "float(" in lowered_code and "temperature" in lowered_code
        if kind == "temperature_units":
            return all(marker in lowered_code for marker in ["celsius", "fahrenheit"])
        if kind == "temperature_conversion":
            compact = re.sub(r"\s+", "", lowered_code)
            c_to_f = ("*9/5" in compact or "*1.8" in compact) and "+32" in compact
            f_to_c = "-32" in compact and ("*5/9" in compact or "/1.8" in compact)
            return c_to_f and f_to_c
        if kind == "repeat_until_exit":
            return all(marker in lowered_code for marker in ["while true", "input(", "exit", "break"])

        if requirement["kind"] == "negative_constraint":
            external_imports = [
                "import requests", "from requests", "import pandas", "from pandas",
                "import numpy", "from numpy", "import flask", "from flask"
            ]
            return not any(marker in lowered_code for marker in external_imports)
        if requirement["kind"] in {"output_constraint", "program_kind"}:
            return True
        required = requirement.get("evidence", [])
        if required and all(marker.lower() in lowered_code for marker in required):
            return True
        return any(
            all(marker.lower() in lowered_code for marker in alternative)
            for alternative in requirement.get("alternatives", [])
        )

    def review(self, code, language="python"):

        code = str(code or "")
        warnings = []
        errors = []
        suggestions = []

        if not code.strip():
            errors.append("No code was generated.")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "quality_score": 0
            }

        if language != "python":
            return {
                "valid": True,
                "errors": [],
                "warnings": ["Self review is strongest for Python right now."],
                "suggestions": [],
                "quality_score": 65
            }

        tree = None

        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            errors.append(
                f"Syntax error on line {error.lineno}: {error.msg}"
            )

        lowered = code.lower()

        placeholder_signals = [
            "production_draft",
            "creative_ready",
            "planner_ready",
            "helper, production draft variant",
            "return data",
            "pass  #",
            "todo",
            "placeholder"
        ]

        for signal in placeholder_signals:
            if signal in lowered:
                warnings.append(
                    f"Possible placeholder code detected: {signal}"
                )

        if tree is not None:
            functions = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ]

            if not functions:
                warnings.append("No functions were found.")

            for function in functions:
                meaningful_nodes = [
                    node
                    for node in function.body
                    if not (
                        isinstance(node, ast.Expr)
                        and isinstance(getattr(node, "value", None), ast.Constant)
                        and isinstance(node.value.value, str)
                    )
                ]

                if not meaningful_nodes:
                    warnings.append(
                        f"Function {function.name} has no real body."
                    )
                    continue

                if len(meaningful_nodes) == 1:
                    node = meaningful_nodes[0]
                    if isinstance(node, ast.Pass):
                        warnings.append(
                            f"Function {function.name} only contains pass."
                        )
                    elif (
                        isinstance(node, ast.Return)
                        and (
                            node.value is None
                            or (
                                isinstance(node.value, ast.Name)
                                and node.value.id in {"data", "input"}
                            )
                        )
                    ):
                        warnings.append(
                            f"Function {function.name} looks like a stub."
                        )

            has_main = any(
                isinstance(node, ast.FunctionDef) and node.name == "main"
                for node in ast.walk(tree)
            )
            has_main_guard = 'if __name__ == "__main__"' in code

            if has_main and not has_main_guard:
                suggestions.append("Add a main guard so the program runs directly.")

        quality_score = 100
        quality_score -= len(errors) * 40
        quality_score -= min(len(warnings) * 8, 40)
        quality_score -= min(len(suggestions) * 4, 12)
        quality_score = max(0, quality_score)

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": list(dict.fromkeys(warnings)),
            "suggestions": list(dict.fromkeys(suggestions)),
            "quality_score": quality_score
        }

    def improve(self, code, review, language="python"):

        improved = str(code or "").strip()
        changes = []

        if language != "python" or not improved:
            return improved, changes

        if (
            "Add a main guard so the program runs directly."
            in review.get("suggestions", [])
            and 'if __name__ == "__main__"' not in improved
            and re.search(r"^def\s+main\s*\(", improved, re.MULTILINE)
        ):
            improved += '\n\nif __name__ == "__main__":\n    main()\n'
            changes.append("Added Python main guard.")

        if improved and not improved.endswith("\n"):
            improved += "\n"
            changes.append("Added final newline.")

        return improved, changes

    def review_request_alignment(self, code, request_text="", program_kind=None):

        extracted = self.extract_request_requirements(request_text, program_kind)
        checks = []
        for requirement in extracted:
            checks.append({
                "requirement": requirement["id"],
                "kind": requirement["kind"],
                "passed": self.requirement_passed(requirement, code),
                "evidence": requirement.get("evidence", []),
                "alternatives": requirement.get("alternatives", [])
            })

        failed = [check for check in checks if not check["passed"]]
        return {
            "passed": not failed,
            "checks": checks,
            "failed": failed,
            "coverage": (
                round(sum(1 for check in checks if check["passed"]) / len(checks) * 100, 2)
                if checks
                else 100
            )
        }

    def review_and_improve(
        self,
        code,
        language="python",
        request_text="",
        program_kind=None
    ):

        first_review = self.review(code, language)
        improved_code, changes = self.improve(
            code,
            first_review,
            language
        )
        final_review = self.review(improved_code, language)
        request_alignment = self.review_request_alignment(
            improved_code,
            request_text,
            program_kind
        )
        blocking_warning_markers = [
            "only contains pass",
            "looks like a stub",
            "has no real body",
            "possible placeholder code detected"
        ]
        blocking_warnings = [
            warning
            for warning in final_review.get("warnings", [])
            if any(marker in warning.lower() for marker in blocking_warning_markers)
        ]

        return {
            "code": improved_code,
            "before": first_review,
            "after": final_review,
            "changes": changes,
            "improved": bool(changes),
            "ready": final_review.get("valid", False)
                and final_review.get("quality_score", 0) >= 70
                and request_alignment.get("passed", True)
                and not blocking_warnings,
            "request_alignment": request_alignment,
            "blocking_warnings": blocking_warnings
        }


class CodeExplainer:

    def extract_code_block(self, text):

        text = str(text or "")
        fenced = re.search(
            r"```(?:python|py|javascript|js|java|html|css|sql)?\s*(.*?)```",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if fenced:
            return fenced.group(1).strip()

        lines = text.splitlines()
        code_lines = []
        code_started = False

        code_markers = (
            "def ",
            "class ",
            "import ",
            "from ",
            "return ",
            "if ",
            "for ",
            "while ",
            "print(",
            "=",
            "{",
            "}",
            ";"
        )

        for line in lines:
            stripped = line.strip()
            lowered = stripped.lower()

            if not stripped and code_started:
                code_lines.append(line)
                continue

            looks_like_code = (
                stripped.startswith(code_markers)
                or lowered.startswith("elif ")
                or lowered.startswith("else:")
                or lowered.startswith("try:")
                or lowered.startswith("except ")
                or line.startswith((" ", "\t")) and code_started
            )

            if looks_like_code:
                code_started = True
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines).strip()

        return text.strip()

    def detect_language(self, code, surrounding_text=""):

        lowered = f"{surrounding_text}\n{code}".lower()

        if "def " in code or "import " in code or "print(" in code:
            return "python"
        if "function " in lowered or "console.log" in lowered:
            return "javascript"
        if "<html" in lowered or "</" in lowered:
            return "html"
        if "public static" in lowered or "system.out.println" in lowered:
            return "java"
        if "#include" in lowered:
            return "c_cpp"

        return "unknown"

    def explain_python(self, code):

        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            return {
                "valid": False,
                "summary": "This looks like Python code, but it has a syntax error.",
                "syntax_error": {
                    "line": error.lineno,
                    "message": error.msg
                },
                "imports": [],
                "functions": [],
                "classes": [],
                "control_flow": [],
                "variables": [],
                "calls": [],
                "line_by_line": []
            }

        imports = []
        functions = []
        classes = []
        control_flow = []
        variables = []
        calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend(f"{module}.{alias.name}".strip(".") for alias in node.names)
            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "line": node.lineno,
                    "returns_value": any(isinstance(child, ast.Return) and child.value is not None for child in ast.walk(node))
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [
                        child.name
                        for child in node.body
                        if isinstance(child, ast.FunctionDef)
                    ]
                })
            elif isinstance(node, ast.If):
                control_flow.append({"type": "if", "line": node.lineno})
            elif isinstance(node, ast.For):
                control_flow.append({"type": "for_loop", "line": node.lineno})
            elif isinstance(node, ast.While):
                control_flow.append({"type": "while_loop", "line": node.lineno})
            elif isinstance(node, ast.Try):
                control_flow.append({"type": "try_except", "line": node.lineno})
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    calls.append(func.id)
                elif isinstance(func, ast.Attribute):
                    calls.append(func.attr)

        line_by_line = []
        for number, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            explanation = "Runs a Python statement."
            if stripped.startswith("import ") or stripped.startswith("from "):
                explanation = "Loads external or standard-library code."
            elif stripped.startswith("def "):
                explanation = "Defines a reusable function."
            elif stripped.startswith("class "):
                explanation = "Defines a class/object structure."
            elif stripped.startswith("if "):
                explanation = "Checks a condition and chooses a branch."
            elif stripped.startswith(("for ", "while ")):
                explanation = "Starts a loop."
            elif stripped.startswith("return"):
                explanation = "Sends a value back from a function."
            elif "=" in stripped and "==" not in stripped:
                explanation = "Stores or updates a value."
            elif stripped.startswith("print("):
                explanation = "Prints information to the screen."

            line_by_line.append({
                "line": number,
                "code": stripped,
                "meaning": explanation
            })

        summary_parts = []
        if functions:
            summary_parts.append(f"defines {len(functions)} function(s)")
        if classes:
            summary_parts.append(f"defines {len(classes)} class(es)")
        if imports:
            summary_parts.append(f"uses {len(imports)} import(s)")
        if control_flow:
            summary_parts.append("uses control flow")

        summary = "This Python code "
        summary += ", ".join(summary_parts) if summary_parts else "runs simple statements"
        summary += "."

        return {
            "valid": True,
            "summary": summary,
            "imports": list(dict.fromkeys(imports)),
            "functions": functions,
            "classes": classes,
            "control_flow": control_flow,
            "variables": list(dict.fromkeys(variables)),
            "calls": list(dict.fromkeys(calls)),
            "line_by_line": line_by_line[:80]
        }

    def explain_generic(self, code, language):

        lines = [
            line.strip()
            for line in str(code).splitlines()
            if line.strip()
        ]

        return {
            "valid": True,
            "summary": f"This looks like {language} code with {len(lines)} non-empty line(s).",
            "imports": [],
            "functions": [],
            "classes": [],
            "control_flow": [],
            "variables": [],
            "calls": [],
            "line_by_line": [
                {
                    "line": index,
                    "code": line,
                    "meaning": "Code line detected; detailed analysis is strongest for Python right now."
                }
                for index, line in enumerate(lines[:80], start=1)
            ]
        }

    def format_answer(self, explanation):

        lines = [
            explanation.get("summary", "I analyzed the code.")
        ]

        if explanation.get("syntax_error"):
            error = explanation["syntax_error"]
            lines.append(f"Syntax issue: line {error.get('line')}: {error.get('message')}")

        if explanation.get("imports"):
            lines.append("Imports: " + ", ".join(explanation["imports"][:10]))

        if explanation.get("functions"):
            lines.append("Functions:")
            for function in explanation["functions"][:12]:
                args = ", ".join(function.get("args", []))
                lines.append(f"- {function['name']}({args}) on line {function.get('line')}")

        if explanation.get("classes"):
            lines.append("Classes:")
            for class_data in explanation["classes"][:8]:
                methods = ", ".join(class_data.get("methods", [])[:8])
                suffix = f" with methods: {methods}" if methods else ""
                lines.append(f"- {class_data['name']} on line {class_data.get('line')}{suffix}")

        if explanation.get("variables"):
            lines.append("Main variables: " + ", ".join(explanation["variables"][:12]))

        if explanation.get("control_flow"):
            flow = ", ".join(
                f"{item['type']} line {item['line']}"
                for item in explanation["control_flow"][:12]
            )
            lines.append("Control flow: " + flow)

        if explanation.get("line_by_line"):
            lines.append("Line-by-line:")
            for item in explanation["line_by_line"][:20]:
                lines.append(f"- Line {item['line']}: {item['meaning']} `{item['code']}`")

        return "\n".join(lines)

    def explain(self, text, existing_code="", language=None):

        code = existing_code or self.extract_code_block(text)
        detected_language = language or self.detect_language(code, text)

        if detected_language == "python":
            details = self.explain_python(code)
        else:
            details = self.explain_generic(code, detected_language)

        answer = self.format_answer(details)

        return {
            "language": detected_language,
            "code_analyzed": code,
            "explanation": details,
            "answer": answer,
            "summary": details.get("summary"),
            "confidence": 88 if details.get("valid") else 62
        }


class CodeProjectReviewer:

    CAPABILITY_EVIDENCE = {
        "multi_file": lambda paths, text: len(paths) >= 5,
        "dependencies": lambda paths, text: any(
            path in paths for path in {"pyproject.toml", "requirements.txt"}
        ),
        "database": lambda paths, text: (
            "sqlite3" in text
            or "sqlalchemy" in text.lower()
            or any("database" in path for path in paths)
        ),
        "api": lambda paths, text: (
            "FastAPI(" in text
            or "APIRouter(" in text
            or "ThreadingHTTPServer(" in text
        ),
        "authentication": lambda paths, text: (
            "hash_password" in text
            and "verify_password" in text
            and ("Authorization" in text or "bearer" in text.lower())
        ),
        "async": lambda paths, text: "async def " in text and "await " in text,
        "concurrency": lambda paths, text: any(
            marker in text
            for marker in ["asyncio.to_thread", "TaskGroup", "ThreadPoolExecutor", "RLock("]
        ),
        "security": lambda paths, text: (
            "secrets." in text
            and "compare_digest" in text
            and "pbkdf2_hmac" in text
        ),
        "cryptography": lambda paths, text: any(
            marker in text for marker in ["Fernet", "AESGCM", "ChaCha20Poly1305"]
        ),
        "tests": lambda paths, text: (
            any(path.startswith("tests/") and path.endswith(".py") for path in paths)
            and "assert " in text
        ),
        "layered_architecture": lambda paths, text: all(
            path in paths
            for path in ["app/models.py", "app/repository.py", "app/service.py"]
        ),
        "hardware_integration": lambda paths, text: (
            "app/hardware.py" in paths
            and "class Sensor" in text
            and ("SerialSensor" in text or "gpio" in text.lower())
        ),
        "scientific_computing": lambda paths, text: (
            "app/science.py" in paths
            and "summarize_measurements" in text
            and "calibrate" in text
        ),
    }

    def normalize_files(self, project_files):
        if isinstance(project_files, dict):
            return {
                str(path).replace("\\", "/"): str(content)
                for path, content in project_files.items()
                if path and content is not None
            }
        normalized = {}
        for item in project_files or []:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("name")
            if path:
                normalized[str(path).replace("\\", "/")] = str(
                    item.get("content", "")
                )
        return normalized

    def review(self, project_files, requested_capabilities=None, existing_files=None):
        files = self.normalize_files(project_files)
        existing = self.normalize_files(existing_files)
        requested = {
            key
            for key, enabled in (requested_capabilities or {}).items()
            if enabled and key in self.CAPABILITY_EVIDENCE
        }
        paths = set(files)
        errors = []
        warnings = []
        file_checks = []

        for path, content in files.items():
            pure_path = PurePosixPath(path)
            invalid_path = (
                pure_path.is_absolute()
                or ".." in pure_path.parts
                or not pure_path.parts
            )
            if invalid_path:
                errors.append(f"Unsafe project path: {path}")
                continue
            if not content.strip() and not path.endswith("__init__.py"):
                errors.append(f"Project file is empty: {path}")

            check = {"path": path, "syntax_valid": None, "error": None}
            if path.endswith(".py"):
                try:
                    tree = ast.parse(content)
                    check["syntax_valid"] = True
                    for node in ast.walk(tree):
                        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            continue
                        meaningful = [
                            child
                            for child in node.body
                            if not (
                                isinstance(child, ast.Expr)
                                and isinstance(getattr(child, "value", None), ast.Constant)
                                and isinstance(child.value.value, str)
                            )
                        ]
                        if len(meaningful) == 1 and isinstance(meaningful[0], ast.Pass):
                            errors.append(f"Function {node.name} is empty in {path}.")
                        if len(meaningful) == 1 and isinstance(meaningful[0], ast.Raise):
                            raised = ast.unparse(meaningful[0]).lower()
                            if "notimplemented" in raised:
                                errors.append(f"Function {node.name} is not implemented in {path}.")
                except SyntaxError as error:
                    check["syntax_valid"] = False
                    check["error"] = f"line {error.lineno}: {error.msg}"
                    errors.append(f"Python syntax error in {path}: {check['error']}")
            file_checks.append(check)

        combined = "\n\n".join(files.values())
        lowered = combined.lower()
        placeholder_markers = [
            "production_draft",
            "planner_ready",
            "creative_ready",
            "not implemented",
            "insert code here",
        ]
        for marker in placeholder_markers:
            if marker in lowered:
                errors.append(f"Project contains placeholder marker: {marker}")

        dangerous_markers = [
            ("eval(", "Avoid eval() in generated applications."),
            ("exec(", "Avoid exec() in generated applications."),
            ("shell=true", "Avoid subprocess shell=True with user-controlled input."),
            ("pickle.loads", "Avoid deserializing untrusted pickle data."),
        ]
        for marker, message in dangerous_markers:
            if marker in lowered:
                errors.append(message)

        if re.search(r"(?:secret|password|api_key)\s*=\s*['\"][^'\"]{6,}['\"]", combined, re.I):
            errors.append("A credential or secret appears to be hard-coded.")

        capability_checks = []
        for capability in sorted(requested):
            passed = bool(self.CAPABILITY_EVIDENCE[capability](paths, combined))
            capability_checks.append({
                "capability": capability,
                "passed": passed,
            })
            if not passed:
                errors.append(f"Requested project capability is missing: {capability}")

        if "fastapi" in lowered:
            manifest = files.get("pyproject.toml", "") + files.get("requirements.txt", "")
            if "fastapi" not in manifest.lower():
                errors.append("FastAPI is imported but missing from the dependency manifest.")
        if "from cryptography" in lowered:
            manifest = files.get("pyproject.toml", "") + files.get("requirements.txt", "")
            if "cryptography" not in manifest.lower():
                errors.append("cryptography is imported but missing from the dependency manifest.")

        preservation_checks = []
        for path, original_content in existing.items():
            preserved = path in files and files[path] == original_content
            preservation_checks.append({"path": path, "preserved": preserved})
            if not preserved:
                errors.append(f"Existing file changed without a verified patch: {path}")

        if requested and "tests" not in requested:
            warnings.append("A professional project should normally include automated tests.")
        if len(files) > 1 and "README.md" not in files:
            warnings.append("Multi-file project has no README.md.")

        errors = list(dict.fromkeys(errors))
        warnings = list(dict.fromkeys(warnings))
        passed_capabilities = sum(1 for item in capability_checks if item["passed"])
        coverage = (
            round(passed_capabilities / len(capability_checks) * 100, 2)
            if capability_checks
            else 100.0
        )
        score = max(0, 100 - len(errors) * 14 - len(warnings) * 3)
        return {
            "ready": not errors and score >= 90 and coverage == 100.0,
            "quality_score": score,
            "capability_coverage": coverage,
            "errors": errors,
            "warnings": warnings,
            "file_checks": file_checks,
            "capability_checks": capability_checks,
            "preservation_checks": preservation_checks,
            "files_reviewed": len(files),
            "python_files_reviewed": sum(path.endswith(".py") for path in files),
        }


class AdvancedCodeProjectBuilder:

    CAPABILITY_MARKERS = {
        "multi_file": [
            "multi-file", "multiple files", "several files", "large system",
            "large project", "architecture", "production-ready", "professional project",
        ],
        "database": ["database", "sqlite", "sql", "persistence", "repository"],
        "api": ["api", "rest", "endpoint", "fastapi", "web service"],
        "authentication": ["authentication", "authenticate", "login", "user account", "bearer token"],
        "async": ["async", "asynchronous", "await", "non-blocking"],
        "concurrency": ["concurrent", "parallel", "worker", "thread", "task group"],
        "security": ["security", "secure", "password hashing", "authorization"],
        "cryptography": ["cryptography", "encrypt", "encryption", "decrypt", "fernet", "aes"],
        "tests": ["tests", "testing", "pytest", "test suite", "coverage", "regression"],
        "dependencies": ["dependencies", "requirements.txt", "pyproject.toml", "package"],
        "layered_architecture": ["architecture", "service layer", "repository", "separation of concerns"],
        "hardware_integration": [
            "hardware", "arduino", "raspberry pi", "gpio", "sensor", "serial",
            "microcontroller", "embedded", "firmware", "iot",
        ],
        "scientific_computing": [
            "science", "scientific", "physics", "measurement", "calibration",
            "experiment", "signal", "gravity", "temperature", "voltage",
        ],
    }

    def __init__(self, profiles=None):
        self.profiles = profiles if isinstance(profiles, dict) else {}

    def detect_capabilities(self, text, report=None, existing_files=None):
        lowered = str(text or "").lower()
        capabilities = {
            name: any(marker in lowered for marker in markers)
            for name, markers in self.CAPABILITY_MARKERS.items()
        }
        advanced_count = sum(
            capabilities[name]
            for name in [
                "database", "api", "authentication", "async", "concurrency",
                "security", "cryptography", "tests", "hardware_integration",
                "scientific_computing",
            ]
        )
        professional = any(
            marker in lowered
            for marker in [
                "advanced", "professional", "production-ready", "production ready",
                "large system", "large project", "robust architecture",
            ]
        )
        capabilities["multi_file"] = capabilities["multi_file"] or advanced_count >= 3
        capabilities["layered_architecture"] = (
            capabilities["layered_architecture"] or capabilities["multi_file"]
        )
        capabilities["dependencies"] = (
            capabilities["dependencies"] or capabilities["api"] or capabilities["cryptography"]
        )
        capabilities["tests"] = capabilities["tests"] or professional
        if capabilities["hardware_integration"]:
            capabilities["async"] = True
            capabilities["concurrency"] = True
            capabilities["multi_file"] = True
            capabilities["tests"] = True
        if capabilities["scientific_computing"]:
            capabilities["tests"] = True
        capabilities["security"] = (
            capabilities["security"] or capabilities["authentication"] or capabilities["cryptography"]
        )
        if capabilities["authentication"]:
            capabilities["database"] = True
            capabilities["api"] = True
        if capabilities["api"]:
            capabilities["async"] = True
            capabilities["database"] = True
        capabilities["existing_project"] = bool(existing_files) or any(
            marker in lowered
            for marker in [
                "existing project", "existing codebase", "current project",
                "without breaking", "preserve behavior", "regression-safe",
            ]
        )
        capabilities["professional"] = professional or capabilities["multi_file"]
        capabilities["advanced_project"] = (
            capabilities["multi_file"]
            or advanced_count >= 3
            or (
                capabilities["hardware_integration"]
                and capabilities["scientific_computing"]
            )
            or (capabilities["existing_project"] and professional)
        )
        return capabilities

    def project_slug(self, text):
        match = re.search(
            r"\b(?:called|named)\s+([a-zA-Z][a-zA-Z0-9_-]{1,30})",
            str(text or ""),
            re.I,
        )
        if match:
            return match.group(1).lower().replace("-", "_")
        for label, markers in [
            ("sensor_lab", ["sensor", "arduino", "raspberry pi", "gpio", "measurement"]),
            ("task_service", ["task", "todo"]),
            ("notes_service", ["note"]),
            ("expense_service", ["expense"]),
            ("inventory_service", ["inventory", "product"]),
            ("account_service", ["account", "user"]),
        ]:
            if any(marker in str(text or "").lower() for marker in markers):
                return label
        return "canri_service"

    def select_profile(self, capabilities):
        profiles = self.profiles.get("profiles", {})
        if not isinstance(profiles, dict):
            return {}
        eligible = []
        for profile in profiles.values():
            if not isinstance(profile, dict):
                continue
            required = profile.get("required_capabilities", [])
            if all(capabilities.get(capability) for capability in required):
                eligible.append(profile)
        if not eligible:
            default_id = self.profiles.get("default_profile")
            return profiles.get(default_id, {})
        return max(
            eligible,
            key=lambda profile: (
                len(profile.get("required_capabilities", [])),
                profile.get("score", 0),
            ),
        )

    def build_pyproject(self, project_name, capabilities):
        dependencies = []
        if capabilities.get("api"):
            dependencies.extend(["fastapi>=0.110", "uvicorn>=0.27"])
        if capabilities.get("cryptography"):
            dependencies.append("cryptography>=42")
        if capabilities.get("hardware_integration"):
            dependencies.append("pyserial>=3.5")
        dependency_lines = "\n".join(f'    "{item}",' for item in dependencies)
        return f'''[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name.replace('_', '-')}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
{dependency_lines}
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
'''

    def build_files(self, text, capabilities):
        project_name = self.project_slug(text)
        files = {
            "pyproject.toml": self.build_pyproject(project_name, capabilities),
            "app/__init__.py": '__all__ = ["service"]\n',
            "app/models.py": '''from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    owner_id: int
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str
''',
        }

        if capabilities.get("database"):
            files["app/database.py"] = '''import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DATABASE = Path("canri_service.db")


def connect(database_path: str | Path = DEFAULT_DATABASE) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction(database_path: str | Path = DEFAULT_DATABASE) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: str | Path = DEFAULT_DATABASE) -> None:
    with transaction(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS access_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            );
            """
        )
'''
            files["app/repository.py"] = '''import time
from pathlib import Path

from app.database import DEFAULT_DATABASE, transaction
from app.models import Item, User


class Repository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = database_path

    def create_user(self, username: str, password_hash: str) -> User:
        with transaction(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            return User(id=int(cursor.lastrowid), username=username)

    def find_user_credentials(self, username: str):
        with transaction(self.database_path) as connection:
            return connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

    def save_token(self, user_id: int, token_hash: str, expires_at: int) -> None:
        with transaction(self.database_path) as connection:
            connection.execute(
                "INSERT INTO access_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at),
            )

    def user_id_for_token(self, token_hash: str) -> int | None:
        with transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT user_id FROM access_tokens WHERE token_hash = ? AND expires_at > ?",
                (token_hash, int(time.time())),
            ).fetchone()
            return int(row["user_id"]) if row else None

    def create_item(self, owner_id: int, title: str, description: str) -> Item:
        with transaction(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO items (owner_id, title, description) VALUES (?, ?, ?)",
                (owner_id, title, description),
            )
            return Item(int(cursor.lastrowid), owner_id, title, description)

    def list_items(self, owner_id: int) -> list[Item]:
        with transaction(self.database_path) as connection:
            rows = connection.execute(
                "SELECT id, owner_id, title, description FROM items WHERE owner_id = ? ORDER BY id",
                (owner_id,),
            ).fetchall()
        return [Item(**dict(row)) for row in rows]
'''
        else:
            files["app/repository.py"] = '''from threading import RLock

from app.models import Item


class Repository:
    def __init__(self) -> None:
        self._items: list[Item] = []
        self._lock = RLock()

    def create_item(self, owner_id: int, title: str, description: str) -> Item:
        with self._lock:
            item = Item(len(self._items) + 1, owner_id, title, description)
            self._items.append(item)
            return item

    def list_items(self, owner_id: int) -> list[Item]:
        with self._lock:
            return [item for item in self._items if item.owner_id == owner_id]
'''

        if capabilities.get("security"):
            files["app/security.py"] = '''import base64
import binascii
import hashlib
import hmac
import secrets


PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, binascii.Error):
        return False


def create_access_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
'''

        if capabilities.get("cryptography"):
            files["app/crypto.py"] = '''from cryptography.fernet import Fernet, InvalidToken


class SecretBox:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise ValueError("Ciphertext authentication failed.") from error
'''

        security_imports = ""
        auth_methods = ""
        concurrency_methods = ""
        if capabilities.get("authentication"):
            security_imports = "from app.security import create_access_token, hash_password, hash_token, verify_password\n"
            auth_methods = '''
    async def register(self, username: str, password: str):
        clean_username = username.strip().lower()
        if len(clean_username) < 3:
            raise ValueError("Username must contain at least 3 characters.")
        encoded = await asyncio.to_thread(hash_password, password)
        return await asyncio.to_thread(
            self.repository.create_user, clean_username, encoded
        )

    async def authenticate(self, username: str, password: str) -> str:
        row = await asyncio.to_thread(
            self.repository.find_user_credentials, username.strip().lower()
        )
        if row is None or not await asyncio.to_thread(
            verify_password, password, row["password_hash"]
        ):
            raise PermissionError("Invalid credentials.")
        raw_token, token_digest = create_access_token()
        expires_at = int(time.time()) + 3600
        await asyncio.to_thread(
            self.repository.save_token, int(row["id"]), token_digest, expires_at
        )
        return raw_token

    async def authorize(self, raw_token: str) -> int:
        user_id = await asyncio.to_thread(
            self.repository.user_id_for_token, hash_token(raw_token)
        )
        if user_id is None:
            raise PermissionError("Invalid or expired access token.")
        return user_id
'''
        if capabilities.get("concurrency"):
            concurrency_methods = '''
    async def list_items_for_owners(self, owner_ids: list[int]):
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(self.list_items(owner_id))
                for owner_id in owner_ids
            ]
        return {
            owner_id: task.result()
            for owner_id, task in zip(owner_ids, tasks)
        }
'''
        files["app/service.py"] = f'''import asyncio
import time

from app.repository import Repository
{security_imports}

class ApplicationService:
    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository or Repository()
{auth_methods}
    async def create_item(self, owner_id: int, title: str, description: str = ""):
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Title is required.")
        return await asyncio.to_thread(
            self.repository.create_item,
            owner_id,
            clean_title,
            description.strip(),
        )

    async def list_items(self, owner_id: int):
        return await asyncio.to_thread(self.repository.list_items, owner_id)
{concurrency_methods}
'''

        if capabilities.get("api"):
            auth_dependency = ""
            auth_routes = ""
            current_user_expression = "1"
            security_scheme_import = ""
            if capabilities.get("authentication"):
                security_scheme_import = ", Depends\nfrom fastapi.security import HTTPAuthorizationCredentials, HTTPBearer"
                auth_dependency = '''
bearer = HTTPBearer(auto_error=True)


async def current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> int:
    try:
        return await service.authorize(credentials.credentials)
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
'''
                auth_routes = '''
@app.post("/auth/register", status_code=201)
async def register(payload: Credentials):
    try:
        return await service.register(payload.username, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/token")
async def token(payload: Credentials):
    try:
        return {"access_token": await service.authenticate(payload.username, payload.password)}
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
'''
                current_user_expression = "Depends(current_user_id)"
            files["app/api.py"] = f'''from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException{security_scheme_import}
from pydantic import BaseModel, Field

from app.database import initialize_database
from app.service import ApplicationService


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12, max_length=256)


class ItemInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


service = ApplicationService()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Canri Professional Service", lifespan=lifespan)
{auth_dependency}

@app.get("/health")
async def health():
    return {{"status": "ok"}}

{auth_routes}

@app.post("/items", status_code=201)
async def create_item(payload: ItemInput, owner_id: int = {current_user_expression}):
    try:
        return await service.create_item(owner_id, payload.title, payload.description)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/items")
async def list_items(owner_id: int = {current_user_expression}):
    return await service.list_items(owner_id)
'''
        else:
            files["app/main.py"] = '''import asyncio

from app.service import ApplicationService


async def main() -> None:
    service = ApplicationService()
    item = await service.create_item(1, "First item", "Created by the CLI")
    print(item)
    print(await service.list_items(1))


if __name__ == "__main__":
    asyncio.run(main())
'''

        if capabilities.get("tests"):
            if capabilities.get("security"):
                files["tests/test_security.py"] = '''from app.security import hash_password, verify_password


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
'''
            if capabilities.get("authentication"):
                files["tests/test_service.py"] = '''import asyncio

from app.database import initialize_database
from app.repository import Repository
from app.service import ApplicationService


def test_register_authenticate_and_create_item(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)
    service = ApplicationService(Repository(database_path))

    async def scenario():
        user = await service.register("alice", "correct horse battery staple")
        token = await service.authenticate("alice", "correct horse battery staple")
        owner_id = await service.authorize(token)
        item = await service.create_item(owner_id, "Read tests", "Keep behavior stable")
        items = await service.list_items(owner_id)
        assert user.username == "alice"
        assert item.title == "Read tests"
        assert items == [item]

    asyncio.run(scenario())
'''
            elif capabilities.get("database"):
                files["tests/test_service.py"] = '''import asyncio

from app.database import initialize_database
from app.repository import Repository
from app.service import ApplicationService


def test_create_and_list_item(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)
    service = ApplicationService(Repository(database_path))

    async def scenario():
        item = await service.create_item(1, "Read tests", "Keep behavior stable")
        assert await service.list_items(1) == [item]

    asyncio.run(scenario())
'''
            else:
                files["tests/test_service.py"] = '''import asyncio

from app.service import ApplicationService


def test_create_and_list_item():
    service = ApplicationService()

    async def scenario():
        item = await service.create_item(1, "Read tests", "Keep behavior stable")
        assert await service.list_items(1) == [item]

    asyncio.run(scenario())
'''
            if capabilities.get("api") and capabilities.get("authentication"):
                files["tests/test_api.py"] = '''from fastapi.testclient import TestClient

from app import api
from app.database import initialize_database
from app.repository import Repository
from app.service import ApplicationService


def test_authenticated_item_flow(tmp_path):
    database_path = tmp_path / "api.db"
    initialize_database(database_path)
    api.service = ApplicationService(Repository(database_path))

    with TestClient(api.app) as client:
        registered = client.post(
            "/auth/register",
            json={"username": "alice", "password": "correct horse battery staple"},
        )
        assert registered.status_code == 201
        authenticated = client.post(
            "/auth/token",
            json={"username": "alice", "password": "correct horse battery staple"},
        )
        assert authenticated.status_code == 200
        headers = {"Authorization": f"Bearer {authenticated.json()['access_token']}"}
        created = client.post(
            "/items",
            json={"title": "API test", "description": "verified"},
            headers=headers,
        )
        assert created.status_code == 201
        listed = client.get("/items", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["title"] == "API test"
'''
            elif capabilities.get("api"):
                files["tests/test_api.py"] = '''from fastapi.testclient import TestClient

from app.api import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
'''

        if capabilities.get("hardware_integration"):
            files["app/hardware.py"] = '''import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SensorReading:
    timestamp: float
    value: float
    unit: str


class Sensor(Protocol):
    def read(self) -> SensorReading:
        """Return one measurement from the device."""


class SimulatedSensor:
    def __init__(self, values: list[float], unit: str = "m/s^2") -> None:
        if not values:
            raise ValueError("At least one simulated value is required.")
        self._values = list(values)
        self._unit = unit
        self._index = 0

    def read(self) -> SensorReading:
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return SensorReading(time.time(), float(value), self._unit)


class SerialSensor:
    def __init__(self, port: str, baudrate: int = 115_200, timeout: float = 1.0) -> None:
        if not port.strip():
            raise ValueError("A serial port is required.")
        import serial

        self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def read(self) -> SensorReading:
        line = self._serial.readline().decode("utf-8", errors="strict").strip()
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            raise ValueError("Expected serial data in value,unit format.")
        value, unit = parts
        return SensorReading(time.time(), float(value), unit)

    def close(self) -> None:
        self._serial.close()
'''
            files["app/science.py"] = '''import math
from dataclasses import dataclass
from statistics import fmean, pstdev

from app.hardware import SensorReading


@dataclass(frozen=True, slots=True)
class MeasurementSummary:
    count: int
    mean: float
    minimum: float
    maximum: float
    standard_deviation: float
    unit: str


def calibrate(reading: SensorReading, scale: float = 1.0, offset: float = 0.0) -> SensorReading:
    value = reading.value * scale + offset
    if not math.isfinite(value):
        raise ValueError("Calibrated measurement must be finite.")
    return SensorReading(reading.timestamp, value, reading.unit)


def summarize_measurements(readings: list[SensorReading]) -> MeasurementSummary:
    if not readings:
        raise ValueError("At least one measurement is required.")
    units = {reading.unit for reading in readings}
    if len(units) != 1:
        raise ValueError("All measurements must use the same unit.")
    values = [reading.value for reading in readings]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Measurements must be finite.")
    return MeasurementSummary(
        count=len(values),
        mean=fmean(values),
        minimum=min(values),
        maximum=max(values),
        standard_deviation=pstdev(values),
        unit=readings[0].unit,
    )
'''
            files["app/controller.py"] = '''import asyncio

from app.hardware import Sensor, SensorReading
from app.science import calibrate


async def collect_measurements(
    sensor: Sensor,
    sample_count: int,
    interval_seconds: float = 0.1,
    scale: float = 1.0,
    offset: float = 0.0,
) -> list[SensorReading]:
    if sample_count < 1 or sample_count > 100_000:
        raise ValueError("sample_count must be between 1 and 100000.")
    if interval_seconds < 0:
        raise ValueError("interval_seconds cannot be negative.")
    readings = []
    for index in range(sample_count):
        raw = await asyncio.to_thread(sensor.read)
        readings.append(calibrate(raw, scale=scale, offset=offset))
        if interval_seconds and index + 1 < sample_count:
            await asyncio.sleep(interval_seconds)
    return readings
'''
            files["app/main.py"] = '''import asyncio

from app.controller import collect_measurements
from app.hardware import SimulatedSensor
from app.science import summarize_measurements


async def run() -> None:
    sensor = SimulatedSensor([9.79, 9.81, 9.82, 9.80])
    readings = await collect_measurements(sensor, sample_count=4, interval_seconds=0)
    summary = summarize_measurements(readings)
    print(summary)


if __name__ == "__main__":
    asyncio.run(run())
'''
            files["tests/test_hardware_science.py"] = '''import asyncio

import pytest

from app.controller import collect_measurements
from app.hardware import SensorReading, SimulatedSensor
from app.science import calibrate, summarize_measurements


def test_collect_calibrate_and_summarize_measurements():
    sensor = SimulatedSensor([9.8, 9.9])
    readings = asyncio.run(
        collect_measurements(sensor, 2, interval_seconds=0, offset=0.1)
    )
    summary = summarize_measurements(readings)
    assert summary.count == 2
    assert summary.minimum == pytest.approx(9.9)
    assert summary.maximum == pytest.approx(10.0)


def test_rejects_non_finite_calibration():
    with pytest.raises(ValueError):
        calibrate(SensorReading(0.0, float("inf"), "m/s^2"))
'''

        run_command = (
            "python -m uvicorn app.api:app --reload"
            if capabilities.get("api")
            else "python -m app.main"
        )
        security_note = (
            "Passwords are salted and hashed. Raw access tokens are returned once and only their hashes are stored."
            if capabilities.get("security")
            else "The project contains no built-in credential storage."
        )
        hardware_note = (
            "Hardware access is isolated behind a Sensor protocol and includes a deterministic simulator for tests."
            if capabilities.get("hardware_integration")
            else ""
        )
        files["README.md"] = f'''# {project_name.replace('_', ' ').title()}

This project uses separate model, repository, service, and transport layers.

## Install

```powershell
python -m venv .venv
.venv\\Scripts\\python -m pip install -e .[dev]
```

## Run

```powershell
{run_command}
```

## Test

```powershell
python -m pytest
```

{security_note}
{hardware_note}
'''
        return files

    def build(self, text, report=None, existing_files=None):
        capabilities = self.detect_capabilities(text, report, existing_files)
        profile = self.select_profile(capabilities)
        generated = self.build_files(text, capabilities)
        existing = CodeProjectReviewer().normalize_files(existing_files)
        files = dict(existing)
        conflicts = []
        added = []
        for path, content in generated.items():
            if path in files:
                if files[path] != content:
                    conflicts.append(path)
                continue
            files[path] = content
            added.append(path)
        return {
            "project_name": self.project_slug(text),
            "architecture_profile": profile,
            "project_files": files,
            "capabilities": capabilities,
            "change_safety": {
                "existing_files_preserved": sorted(existing),
                "added_files": sorted(added),
                "conflicting_files_not_overwritten": sorted(conflicts),
                "strategy": "preserve_existing_add_missing",
            },
        }


class CodeBrain:

    def __init__(self):

        self.code_database = []
        self.statistics = {}
        self.dependency_graph = {}
        self.composition_tables = {}
        self.assembly_patterns = {}
        self.project_recipes = {}
        self.advanced_profiles = {}
        self.function_selection_profiles = {}
        self.recipe_by_kind = {}
        self.code_by_id = {}
        self.library_catalog = CodeArtifactCatalog()
        self.self_reviewer = CodeSelfReviewer()
        self.project_reviewer = CodeProjectReviewer()
        self.code_explainer = CodeExplainer()

        self.load_data()
        self.advanced_project_builder = AdvancedCodeProjectBuilder(
            self.advanced_profiles
        )

        print("Code Brain Loaded")

    def load_data(self):

        if CODE_FILE.exists():
            self.code_database = load_json_resilient(
                CODE_FILE,
                self.code_database
            )

        if STATS_FILE.exists():
            self.statistics = load_json_resilient(
                STATS_FILE,
                self.statistics
            )

        if DEPENDENCY_GRAPH_FILE.exists():
            self.dependency_graph = load_json_resilient(
                DEPENDENCY_GRAPH_FILE,
                self.dependency_graph
            )

        if COMPOSITION_TABLE_FILE.exists():
            self.composition_tables = load_json_resilient(
                COMPOSITION_TABLE_FILE,
                self.composition_tables
            )

        if ASSEMBLY_PATTERNS_FILE.exists():
            self.assembly_patterns = load_json_resilient(
                ASSEMBLY_PATTERNS_FILE,
                self.assembly_patterns
            )

        if PROJECT_RECIPES_FILE.exists():
            self.project_recipes = load_json_resilient(
                PROJECT_RECIPES_FILE,
                self.project_recipes
            )

        if ADVANCED_PROFILES_FILE.exists():
            self.advanced_profiles = load_json_resilient(
                ADVANCED_PROFILES_FILE,
                self.advanced_profiles
            )

        if FUNCTION_SELECTION_PROFILES_FILE.exists():
            self.function_selection_profiles = load_json_resilient(
                FUNCTION_SELECTION_PROFILES_FILE,
                self.function_selection_profiles
            )

        self.code_by_id = {
            item.get("id"): item
            for item in self.code_database
            if item.get("id")
        }
        recipe_values = (
            self.project_recipes.values()
            if isinstance(self.project_recipes, dict)
            else self.project_recipes
        )
        for recipe in recipe_values:
            if not isinstance(recipe, dict) or not recipe.get("kind"):
                continue
            self.recipe_by_kind.setdefault(recipe["kind"], []).append(recipe)
        for recipes in self.recipe_by_kind.values():
            recipes.sort(
                key=lambda item: (item.get("quality_score", 0), item.get("version", 0)),
                reverse=True
            )

    def choose_project_recipe(self, program_kind, text=""):

        recipes = self.recipe_by_kind.get(program_kind, [])
        if not recipes:
            return {}
        lowered = str(text).lower()
        return max(
            recipes,
            key=lambda recipe: (
                sum(1 for marker in recipe.get("trigger_terms", []) if marker in lowered),
                recipe.get("quality_score", 0),
                recipe.get("version", 0)
            )
        )

    def save_statistics(self):

        atomic_write_json(
            STATS_FILE,
            self.statistics,
            indent=2,
            ensure_ascii=False
        )

    def extract_existing_project_files(self, data, existing_code=""):

        candidates = []
        if isinstance(data, dict):
            candidates.extend([
                data.get("existing_project_files"),
                data.get("project_files"),
            ])
            results = data.get("results")
            if isinstance(results, dict):
                code_result = results.get("Code_brain")
                if isinstance(code_result, dict):
                    candidates.append(code_result.get("project_files"))

        for candidate in candidates:
            normalized = self.project_reviewer.normalize_files(candidate)
            if normalized:
                return normalized

        if existing_code:
            return {"app/legacy.py": str(existing_code)}
        return {}

    def is_advanced_project_request(self, text, report=None, existing_files=None):

        capabilities = self.advanced_project_builder.detect_capabilities(
            text,
            report,
            existing_files
        )
        return bool(capabilities.get("advanced_project"))

    def build_advanced_project_result(
        self,
        text,
        terms,
        task_type,
        report=None,
        existing_files=None
    ):

        project = self.advanced_project_builder.build(
            text,
            report,
            existing_files
        )
        files = project["project_files"]
        capabilities = project["capabilities"]
        review = self.project_reviewer.review(
            files,
            capabilities,
            existing_files
        )
        entrypoint = "app/api.py" if "app/api.py" in files else "app/main.py"
        generated_code = files.get(entrypoint, "")

        return {
            "brain": "Code_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": True,
            "language": "python",
            "task_type": task_type,
            "program_kind": "advanced_python_project",
            "output_mode": "project_bundle",
            "professional_mode": True,
            "project_name": project["project_name"],
            "architecture_profile": project.get("architecture_profile", {}),
            "project_files": files,
            "existing_project_files": self.project_reviewer.normalize_files(
                existing_files
            ),
            "generated_code": generated_code,
            "entrypoint": entrypoint,
            "capabilities": capabilities,
            "project_review": review,
            "change_safety": project["change_safety"],
            "terms_used": terms,
            "confidence": 94 if review.get("ready") else 68,
            "matched_functions": sum(path.endswith(".py") for path in files),
            "selected": sorted(files),
            "assembly_plan": {
                "architecture": "layered_service_repository_transport",
                "steps": [
                    "Extract requested technical capabilities and output constraints.",
                    "Separate models, persistence, business logic, and transport layers.",
                    "Use parameterized SQL and one-way password hashing for stored credentials.",
                    "Keep blocking SQLite and password work outside the async event loop.",
                    "Generate tests and validate every Python file before returning the project.",
                ],
                "quality_gates": [
                    "all Python files parse",
                    "requested capability coverage is 100 percent",
                    "no placeholder functions",
                    "no dangerous eval, exec, shell=True, or hard-coded credentials",
                    "existing files are preserved unless a verified patch is available",
                ],
                "data_files_used": [
                    "Code_advanced_profiles.json",
                    "Code_project_recipes.json",
                    "Code_dependency_graph.json",
                ],
            },
            "request_text": text,
            "missing": list(review.get("errors", [])),
            "needs_creative_brain": False,
            "needs_security": bool(
                capabilities.get("security")
                or capabilities.get("authentication")
                or capabilities.get("cryptography")
            ),
            "suggested_next_brains": [
                "Security_brain",
                "Quality_Control_brain",
                "Response_brain",
            ],
            "rules": [
                "Prefer a complete reviewed project bundle for explicit advanced requests.",
                "Do not overwrite existing project files without a validated patch.",
                "Use established cryptographic libraries for reversible encryption.",
            ],
        }

    def finalize_code_result(
        self,
        result,
        scanner_articles=None,
        library_context=None
    ):

        if not isinstance(result, dict):
            return result

        scanner_articles = [
            item for item in (scanner_articles or [])
            if isinstance(item, dict)
        ][:8]
        result["scanner_knowledge_used"] = scanner_articles
        result["scanner_sources_used"] = list(dict.fromkeys(
            source.get("source_id")
            for item in scanner_articles
            for source in item.get("sources", [])
            if isinstance(source, dict) and source.get("source_id")
        ))
        result["scanner_usage_policy"] = (
            "Use official documentation and package metadata as design evidence; "
            "never paste unverified forum or repository code into the output."
        )
        library_context = [
            item for item in (library_context or [])
            if isinstance(item, dict) and isinstance(item.get("function"), dict)
        ][:12]
        result["library_api_context"] = [
            {
                "score": item.get("score", 0),
                "matched_terms": item.get("matched_terms", []),
                "library": item["function"].get("library"),
                "function": item["function"].get("function"),
                "qualified_name": item["function"].get("qualified_name"),
                "callable_type": item["function"].get("callable_type"),
                "signature": item["function"].get("signature"),
                "summary": item["function"].get("summary"),
                "source": item["function"].get("source", {}),
                "risk_level": item["function"].get("risk_level", "standard"),
                "requires_security_review": item["function"].get(
                    "requires_security_review",
                    False
                ),
                "call_template": item.get("template", {}).get("call_template"),
                "import_statement": item.get("template", {}).get("import_statement"),
            }
            for item in library_context
        ]
        result["library_catalog_used"] = bool(library_context)
        catalog_requires_security = any(
            item["function"].get("requires_security_review", False)
            for item in library_context[:5]
        )
        if catalog_requires_security:
            result["needs_security"] = True
            next_brains = result.get("suggested_next_brains", [])
            if isinstance(next_brains, list) and "Security_brain" not in next_brains:
                next_brains.insert(0, "Security_brain")
                result["suggested_next_brains"] = next_brains
        data_files_used = result.get("data_files_used", [])
        if not isinstance(data_files_used, list):
            data_files_used = []
        for file_name in ["Library_functions.json", "Code_library_templates.json"]:
            if file_name not in data_files_used:
                data_files_used.append(file_name)
        result["data_files_used"] = data_files_used

        project_files = self.project_reviewer.normalize_files(
            result.get("project_files")
        )
        code = result.get(
            "generated_code",
            ""
        )

        if project_files:
            project_review = self.project_reviewer.review(
                project_files,
                result.get("capabilities", {}),
                result.get("existing_project_files")
            )
            result["project_files"] = project_files
            result["project_review"] = project_review
            result["self_reviewed"] = True
            result["self_improved"] = False
            result["self_review"] = {
                "ready": project_review.get("ready", False),
                "after": project_review,
                "changes": [],
                "improved": False,
                "request_alignment": {
                    "passed": project_review.get("capability_coverage") == 100.0,
                    "coverage": project_review.get("capability_coverage", 0),
                    "checks": project_review.get("capability_checks", []),
                },
            }
            result["code_metrics"] = {
                "files": len(project_files),
                "python_files": project_review.get("python_files_reviewed", 0),
                "syntax_valid": not any(
                    check.get("syntax_valid") is False
                    for check in project_review.get("file_checks", [])
                ),
            }
            if not project_review.get("ready", False):
                result.setdefault("warnings", []).append(
                    "Project self-review found blocking issues."
                )
            return result

        if not code:
            return result

        review = self.self_reviewer.review_and_improve(
            code,
            result.get("language") or "python",
            result.get("request_text", ""),
            result.get("program_kind")
        )

        result["generated_code"] = review.get(
            "code",
            code
        )
        result["self_review"] = {
            "before": review.get("before", {}),
            "after": review.get("after", {}),
            "changes": review.get("changes", []),
            "improved": review.get("improved", False),
            "ready": review.get("ready", False)
        }
        result["self_review"]["request_alignment"] = review.get(
            "request_alignment",
            {}
        )
        result["self_reviewed"] = True
        result["self_improved"] = review.get(
            "improved",
            False
        )
        try:
            tree = ast.parse(result["generated_code"])
            result["code_metrics"] = {
                "lines": len(result["generated_code"].splitlines()),
                "functions": sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree)),
                "classes": sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree)),
                "imports": sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)),
                "syntax_valid": True
            }
        except SyntaxError:
            result["code_metrics"] = {
                "lines": len(result["generated_code"].splitlines()),
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "syntax_valid": False
            }

        if not review.get("ready", False):
            result.setdefault(
                "warnings",
                []
            )
            result["warnings"].append(
                "Code self-review found issues or low confidence."
            )

        return result

    def get_understanding_report(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return {}

        understanding = data.get(
            "understanding",
            {}
        )

        if isinstance(
            understanding,
            dict
        ) and (
            "words" in understanding
            or "main_topic" in understanding
            or "intent" in understanding
        ):

            return understanding

        if (
            "words" in data
            or "main_topic" in data
            or "intent" in data
        ):

            return data

        return {}

    def get_memory_report(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return {}

        memory = data.get(
            "memory",
            {}
        )

        if isinstance(
            memory,
            dict
        ):

            return memory

        return {}

    def collect_memory_terms(
        self,
        memory_report
    ):

        terms = []

        if not isinstance(
            memory_report,
            dict
        ):

            return terms

        for key in [
            "topic_matches",
            "intent_matches",
            "keyword_matches",
            "recent_matches",
            "similar_tasks"
        ]:

            matches = memory_report.get(
                key,
                []
            )

            if not isinstance(
                matches,
                list
            ):
                continue

            for match in matches[:12]:

                if isinstance(
                    match,
                    dict
                ):

                    for match_key in [
                        "topic",
                        "intent",
                        "keyword",
                        "task",
                        "main_topic",
                        "text",
                        "summary"
                    ]:

                        value = match.get(
                            match_key
                        )

                        if value:
                            terms.append(
                                str(value)
                            )

                    for value in match.get(
                        "keywords",
                        []
                    )[:8]:
                        terms.append(
                            str(value)
                        )

                elif match:

                    terms.append(
                        str(match)
                    )

        return [
            term.lower().strip()
            for term in terms
            if str(term).strip()
        ]

    def extract_existing_code(
        self,
        data
    ):

        if not isinstance(
            data,
            dict
        ):

            return ""

        for key in [
            "existing_code",
            "code_context",
            "current_code",
            "generated_code",
            "project_code"
        ]:

            value = data.get(
                key
            )

            if value:
                return str(value)

        previous_attempt = data.get("previous_attempt")
        if isinstance(previous_attempt, dict):
            for key in ["generated_code", "code", "project_code"]:
                value = previous_attempt.get(key)
                if value:
                    return str(value)

        request_text = " ".join(
            str(data.get(key, ""))
            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "text",
                "goal",
                "prompt"
            ]
            if data.get(key)
        ).lower()

        continuation_markers = [
            "continue from",
            "same program",
            "same code",
            "previous code",
            "code you just wrote",
            "program you just wrote",
            "improve the same",
            "not a new project",
            "keep the same",
            "add these features",
            "continue the code",
            "use the previous code",
            "המשך",
            "תמשיך",
            "אותו קוד",
            "אותה תוכנה",
            "שפר את אותו",
            "תמשיך",
            "אותו קוד",
            "אותה תוכנה",
            "שפר את אותו"
        ]

        if any(marker in request_text for marker in continuation_markers):
            memory = data.get("memory", {})
            if isinstance(memory, dict):
                conversation = memory.get("conversation", {})
                if isinstance(conversation, dict):
                    usable = conversation.get("usable_previous_code")
                    if isinstance(usable, dict) and usable.get("code"):
                        return str(usable["code"])
                    source = conversation.get("continuation_source", {})
                    if isinstance(source, dict):
                        for artifact in source.get("artifacts", []):
                            if isinstance(artifact, dict) and artifact.get("type") == "code" and artifact.get("content"):
                                return str(artifact["content"])
                    code_blocks = conversation.get("recent_code_blocks", [])
                    if isinstance(code_blocks, list):
                        for block in reversed(code_blocks):
                            if isinstance(block, dict) and block.get("code"):
                                return str(block["code"])

        return ""

    def merge_continuation_request(self, current_text, memory_report):

        current = str(current_text or "").strip()
        if not isinstance(memory_report, dict):
            return current
        conversation = memory_report.get("conversation", {})
        if not isinstance(conversation, dict):
            return current

        lowered = current.lower()
        continuation_requested = bool(conversation.get("continuation_request")) or any(
            marker in lowered
            for marker in [
                "continue", "same code", "same program", "same project",
                "you just wrote", "previous code", "improve it", "fix it",
                "add to it", "not a new project",
            ]
        )
        if not continuation_requested:
            return current

        source = conversation.get("continuation_source", {})
        previous_request = source.get("user") if isinstance(source, dict) else None
        if not previous_request:
            previous = conversation.get("last_completed_turn", {})
            if isinstance(previous, dict):
                previous_request = previous.get("user")
        if not previous_request:
            recent = conversation.get("recent_turns", [])
            if isinstance(recent, list):
                for turn in reversed(recent):
                    if isinstance(turn, dict) and turn.get("user"):
                        previous_request = turn["user"]
                        break

        previous = str(previous_request or "").strip()
        if not previous or previous.lower() == current.lower():
            return current
        return (
            "Previous project requirements to preserve:\n"
            f"{previous[:6000]}\n\n"
            "Current requested changes:\n"
            f"{current}"
        )

    def is_code_analysis_request(
        self,
        text,
        report
    ):

        lowered = str(text).lower()
        intent = str(
            report.get(
                "intent",
                ""
            )
        ).lower()

        requested_action = report.get(
            "requested_action",
            {}
        )

        if intent == "code_analysis":
            return True

        if isinstance(requested_action, dict) and requested_action.get("intent_override") == "code_analysis":
            return True

        markers = [
            "analyze this code",
            "analyze code",
            "explain this code",
            "explain code",
            "what does this code do",
            "what this code does",
            "review this code"
        ]

        has_marker = any(
            marker in lowered
            for marker in markers
        )

        has_code_signal = any(
            signal in lowered
            for signal in [
                "```",
                "def ",
                "class ",
                "import ",
                "return ",
                "print(",
                "function ",
                "console.log",
                "{",
                "};"
            ]
        )

        return has_marker and has_code_signal

    def extract_analysis_source_text(
        self,
        data,
        report,
        fallback
    ):

        if isinstance(
            data,
            dict
        ):
            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "text",
                "prompt"
            ]:
                value = data.get(
                    key
                )
                if value:
                    return str(value)

        for key in [
            "original_text",
            "corrected_text"
        ]:
            value = report.get(
                key
            )
            if value:
                return str(value)

        return str(fallback or "")

    def extract_text(
        self,
        data,
        report
    ):

        parts = []

        if isinstance(
            data,
            str
        ):

            parts.append(
                data
            )

        if isinstance(
            data,
            dict
        ):

            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "query",
                "text",
                "prompt"
            ]:

                value = data.get(
                    key
                )

                if value:
                    parts.append(
                        str(value)
                    )

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value:
                parts.append(
                    str(value)
                )

        return " ".join(
            parts
        )

    def collect_terms(
        self,
        data,
        report,
        text
    ):

        terms = []

        if isinstance(
            data,
            dict
        ):

            terms.extend(
                data.get(
                    "required_tags",
                    []
                )
            )

            for key in [
                "language",
                "target_language",
                "framework",
                "feature",
                "task"
            ]:

                value = data.get(
                    key
                )

                if value:
                    terms.append(
                        str(value)
                    )

        for key in [
            "main_topic",
            "intent"
        ]:

            value = report.get(
                key
            )

            if value and value != "unknown":
                terms.append(
                    str(value)
                )

        topics = report.get(
            "topics",
            {}
        )

        if isinstance(
            topics,
            dict
        ):

            for topic in topics:
                terms.append(
                    str(topic)
                )

        for task in report.get(
            "possible_tasks",
            []
        ):

            terms.append(
                str(task).replace(
                    "_",
                    " "
                )
            )

        meaning_frame = report.get(
            "meaning_frame",
            {}
        )

        if isinstance(
            meaning_frame,
            dict
        ):

            for key in [
                "subject",
                "action",
                "object",
                "question_focus"
            ]:

                value = meaning_frame.get(
                    key
                )

                if value:
                    terms.append(
                        str(value)
                    )

            for value in meaning_frame.get(
                "content_terms",
                []
            )[:30]:
                terms.append(
                    str(value)
                )

        semantic_frame = report.get(
            "semantic_frame",
            {}
        )

        if isinstance(
            semantic_frame,
            dict
        ):

            for key in [
                "main_action",
                "main_target",
                "subject",
                "question_focus"
            ]:

                value = semantic_frame.get(
                    key
                )

                if value:
                    terms.append(
                        str(value)
                    )

            for list_key in [
                "targets",
                "modifiers",
                "relations"
            ]:

                values = semantic_frame.get(
                    list_key,
                    []
                )

                if isinstance(
                    values,
                    list
                ):
                    terms.extend(
                        str(value)
                        for value in values[:20]
                    )

            for action in semantic_frame.get(
                "actions",
                []
            )[:12]:
                if isinstance(action, dict) and action.get("word"):
                    terms.append(
                        str(action.get("word"))
                    )

            for chunk in semantic_frame.get(
                "phrase_chunks",
                []
            )[:15]:
                if isinstance(chunk, dict):
                    if chunk.get("text"):
                        terms.append(
                            str(chunk.get("text"))
                        )
                    if chunk.get("head"):
                        terms.append(
                            str(chunk.get("head"))
                        )

        for tag in report.get(
            "advanced_word_tags",
            []
        )[:60]:

            if not isinstance(tag, dict):
                continue

            word = tag.get(
                "word"
            )

            if word:
                terms.append(
                    str(word)
                )

            if tag.get("semantic_tag") in {
                "action_command",
                "action",
                "target_or_concept",
                "proper_or_technical_name"
            }:
                terms.append(
                    str(tag.get("semantic_tag")).replace("_", " ")
                )

        sentence_graph = report.get(
            "sentence_graph",
            {}
        )

        if isinstance(
            sentence_graph,
            dict
        ):

            for edge in sentence_graph.get(
                "edges",
                []
            )[:40]:

                if not isinstance(
                    edge,
                    dict
                ):
                    continue

                for key in [
                    "from_word",
                    "relation",
                    "to_word"
                ]:

                    value = edge.get(
                        key
                    )

                    if value:
                        terms.append(
                            str(value).replace(
                                "_",
                                " "
                            )
                        )

        if isinstance(
            data,
            dict
        ):

            reasoning = data.get(
                "reasoning",
                {}
            )

            if isinstance(
                reasoning,
                dict
            ):

                decision = reasoning.get(
                    "decision_summary",
                    {}
                )

                if isinstance(
                    decision,
                    dict
                ):
                    terms.append(
                        str(
                            decision.get(
                                "recommended_response_strategy",
                                ""
                            )
                        )
                    )

                    for value in decision.get(
                        "must_follow",
                        []
                    )[:12]:
                        terms.append(
                            str(value)
                        )

        for word_data in report.get(
            "words",
            []
        ):

            if not isinstance(
                word_data,
                dict
            ):
                continue

            word = str(
                word_data.get(
                    "word",
                    ""
                )
            ).strip()

            if (
                word
                and len(word) > 1
                and word_data.get(
                    "exists",
                    True
                )
            ):
                terms.append(
                    word
                )

            for connection in word_data.get(
                "connections",
                []
            )[:8]:
                terms.append(
                    str(connection)
                )

        tokens = re.findall(
            r"[a-zA-Z][a-zA-Z0-9_\-\+\.#]{1,}",
            text
        )

        terms.extend(tokens)

        clean_terms = []

        for term in terms:

            term = re.sub(
                r"[^a-zA-Z0-9_\-\+\.#\s]",
                " ",
                str(term)
            )

            term = re.sub(
                r"\s+",
                " ",
                term
            ).strip().lower()

            if (
                term
                and len(term) > 1
                and term not in GENERIC_CODE_TERMS
                and term not in clean_terms
            ):
                clean_terms.append(term)

        return clean_terms

    def detect_language(
        self,
        terms,
        text
    ):

        aliases = {
            "python": ["python", "py", "פייתון"],
            "javascript": ["javascript", "js", "node", "react"],
            "html": ["html"],
            "css": ["css"],
            "java": ["java"],
            "csharp": ["c#", "csharp", "c sharp"],
            "cpp": ["c++", "cpp"],
            "c": [" c ", "clang"],
            "php": ["php"],
            "sql": ["sql"]
        }

        lowered = f" {text.lower()} "

        for language, names in aliases.items():
            for name in names:
                if name in terms:
                    return language

                if len(name) <= 2:
                    pattern = r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])"
                    if re.search(pattern, lowered):
                        return language
                    continue

                if name in lowered:
                    return language

        return None

    def detect_task_type(
        self,
        terms,
        text
    ):

        lowered = text.lower()

        task_map = {
            "web_api": ["api", "endpoint", "route", "server", "http"],
            "database": ["database", "sql", "insert", "select", "query"],
            "game": ["game", "player", "enemy", "inventory", "score"],
            "file_io": ["file", "json", "csv", "read", "write"],
            "security": ["password", "hash", "encrypt", "token", "login"],
            "algorithm": ["sort", "search", "binary", "algorithm", "pathfinding"],
            "ui": ["button", "form", "card", "grid", "css", "html"],
            "testing": ["test", "unit", "assert"],
            "basic": ["hello", "function", "class", "loop", "variable"]
        }

        for task, keywords in task_map.items():
            if any(
                keyword in terms
                or keyword in lowered
                for keyword in keywords
            ):
                return task

        return "general_code"

    def find_by_tags(
        self,
        tags
    ):

        results = []

        for item in self.code_database:

            item_tags = item.get(
                "tags",
                []
            )

            for tag in tags:

                if tag in item_tags:

                    results.append(
                        item
                    )

                    break

        return results

    def score_item(
        self,
        item,
        terms,
        language=None,
        task_type=None
    ):

        score = 0
        matched = []

        searchable_parts = [
            item.get("id", ""),
            item.get("name", ""),
            item.get("language", ""),
            item.get("category", ""),
            item.get("description", ""),
            " ".join(item.get("tags", []))
        ]

        searchable = " ".join(searchable_parts).lower()

        for term in terms:
            if term in GENERIC_CODE_TERMS:
                continue
            if term and term in searchable:
                score += 3
                matched.append(term)

        item_language = item.get(
            "language",
            ""
        )

        if language and item_language == language:
            score += 12
            matched.append(language)

        tags = item.get(
            "tags",
            []
        )

        if task_type and task_type in tags:
            score += 6
            matched.append(task_type)

        stats_score = self.score_function(
            item
        )

        score += stats_score / 20

        graph_node = self.dependency_graph.get(
            item.get(
                "id",
                ""
            ),
            {}
        )

        if graph_node:

            score += graph_node.get(
                "confidence",
                60
            ) / 35

            if task_type and task_type == graph_node.get(
                "category"
            ):

                score += 5
                matched.append(
                    task_type
                )

        return score, list(dict.fromkeys(matched))

    def search_code(
        self,
        terms,
        language=None,
        task_type=None
    ):

        results = []

        for item in self.code_database:

            score, matched = self.score_item(
                item,
                terms,
                language,
                task_type
            )

            if score > 0 and matched:
                results.append({
                    "score": round(score, 2),
                    "matched_terms": matched,
                    "item": item
                })

        results.sort(
            key=lambda result: result["score"],
            reverse=True
        )

        return results

    def score_function(
        self,
        function_data
    ):

        function_id = function_data.get(
            "id",
            ""
        )

        stats = self.statistics.get(
            function_id,
            {}
        )

        success_rate = stats.get(
            "success_rate",
            50
        )

        times_used = stats.get(
            "times_used",
            0
        )

        return (
            success_rate
            +
            (times_used * 0.01)
        )

    def choose_best_functions(
        self,
        functions
    ):

        scored = []

        for func in functions:

            score = self.score_function(
                func
            )

            scored.append(
                (
                    score,
                    func
                )
            )

        scored.sort(
            reverse=True,
            key=lambda x: x[0]
        )

        return [
            item[1]
            for item in scored
        ]

    def build_code(
        self,
        functions
    ):

        parts = []

        for func in functions:

            code = func.get(
                "code",
                ""
            )

            if code:

                parts.append(code)

        return "\n\n".join(parts)

    def is_python_text_rpg_request(self, text, terms, language, task_type):

        lowered = str(text).lower()
        term_set = set(terms)

        needs = {
            "python": language == "python" or "python" in term_set or "python" in lowered,
            "game": (
                task_type == "game"
                or "game" in term_set
                or "game" in lowered
                or "rpg" in term_set
                or "rpg" in lowered
            ),
            "inventory": "inventory" in term_set or "inventory" in lowered,
            "save_load": (
                "save" in term_set
                or "load" in term_set
                or "json" in term_set
                or "save/load" in lowered
            ),
            "command_loop": (
                "command" in term_set
                or "loop" in term_set
                or "command loop" in lowered
            )
        }

        return all(needs.values())

    def is_code_only_request(self, text):

        lowered = str(text).lower()

        code_only_signals = [
            "only output the final working python code",
            "actual python code",
            "actual code",
            "real python code",
            "real code",
            "only output code",
            "only output real python code",
            "do not output modules",
            "do not output planning",
            "no planning structures",
            "code that runs",
            "working code",
            "first working code",
            "final working python code",
            "final working python program",
            "final working code",
            "runnable python code",
            "runnable python program",
            "real runnable python",
            "real runnable"
        ]

        return any(
            signal in lowered
            for signal in code_only_signals
        )

    def is_direct_runnable_python_request(self, text, report=None):

        lowered = str(text or "").lower()
        report = report or {}
        intent = str(report.get("intent", "")).lower()

        if "python" not in lowered and "py " not in lowered:
            return False

        direct_markers = [
            "real runnable",
            "runnable",
            "working code",
            "final working code",
            "final working python code",
            "only output code",
            "only output the final working python code",
            "do not output a plan",
            "do not output modules",
            "do not output placeholders",
            "do not output draft structures"
        ]

        program_markers = [
            "program",
            "app",
            "tool",
            "terminal",
            "command-line",
            "command line",
            "cli",
            "script"
        ]

        return (
            intent == "code_generation"
            or self.is_code_only_request(lowered)
            or (
                any(marker in lowered for marker in direct_markers)
                and any(marker in lowered for marker in program_markers)
            )
        )

    def is_skeleton_request(self, text):

        lowered = str(text).lower()

        negated_skeleton_signals = [
            "do not output a plan, modules, variants, helpers, placeholders, or draft structures",
            "do not output modules, variants, helpers, placeholders, or draft structures",
            "do not output draft structures",
            "not a plan",
            "not a draft",
            "not draft structures",
            "no draft structures",
            "no placeholders",
            "without draft structures"
        ]

        if any(
            signal in lowered
            for signal in negated_skeleton_signals
        ):
            return False

        if (
            "do not output" in lowered
            and any(
                signal in lowered
                for signal in [
                    "modules",
                    "variants",
                    "helpers",
                    "placeholders",
                    "draft structures",
                    "planning structures"
                ]
            )
        ):
            return False

        skeleton_signals = [
            "skeleton",
            "stub",
            "placeholder",
            "draft structure",
            "code structure",
            "planning structure",
            "modules only",
            "just the structure",
            "only structure",
            "outline only",
            "שלד",
            "טיוטה",
            "מבנה בלבד"
        ]

        return any(
            signal in lowered
            for signal in skeleton_signals
        )

    def build_python_text_rpg_code(self):

        return '''import json
from pathlib import Path


SAVE_FILE = Path("save_game.json")


def new_game():
    return {
        "player": {
            "name": "Hero",
            "hp": 30,
            "max_hp": 30,
            "attack": 6,
            "gold": 0,
            "inventory": ["small potion"]
        },
        "location": "village",
        "enemy": None,
        "running": True
    }


def describe_state(state):
    player = state["player"]
    print()
    print(f"Location: {state['location']}")
    print(f"HP: {player['hp']}/{player['max_hp']} | Gold: {player['gold']}")

    if state["enemy"]:
        enemy = state["enemy"]
        print(f"Enemy: {enemy['name']} ({enemy['hp']} HP)")


def show_inventory(state):
    inventory = state["player"]["inventory"]

    if not inventory:
        print("Inventory is empty.")
        return

    print("Inventory:")
    for index, item in enumerate(inventory, start=1):
        print(f"{index}. {item}")


def spawn_enemy(name="slime", hp=12, attack=3, gold=5):
    return {
        "name": name,
        "hp": hp,
        "attack": attack,
        "gold": gold
    }


def explore(state):
    if state["enemy"]:
        print("You cannot explore while an enemy is here.")
        return

    state["enemy"] = spawn_enemy()
    print("A slime appears.")


def attack_enemy(state):
    player = state["player"]
    enemy = state.get("enemy")

    if not enemy:
        print("There is nothing to attack.")
        return

    enemy["hp"] -= player["attack"]
    print(f"You hit the {enemy['name']} for {player['attack']} damage.")

    if enemy["hp"] <= 0:
        print(f"You defeated the {enemy['name']} and found {enemy['gold']} gold.")
        player["gold"] += enemy["gold"]
        state["enemy"] = None
        return

    player["hp"] -= enemy["attack"]
    print(f"The {enemy['name']} hits you for {enemy['attack']} damage.")

    if player["hp"] <= 0:
        print("You were defeated. Game over.")
        state["running"] = False


def use_item(state, item_name):
    player = state["player"]
    inventory = player["inventory"]

    if item_name not in inventory:
        print(f"You do not have {item_name}.")
        return

    if item_name == "small potion":
        player["hp"] = min(player["max_hp"], player["hp"] + 10)
        inventory.remove(item_name)
        print("You used a small potion and restored 10 HP.")
    else:
        print(f"You cannot use {item_name} right now.")


def save_game(state, path=SAVE_FILE):
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Game saved to {path}.")


def load_game(path=SAVE_FILE):
    if not path.exists():
        print("No save file found. Starting a new game.")
        return new_game()

    return json.loads(path.read_text(encoding="utf-8"))


def print_help():
    print("Commands:")
    print("  look              show current status")
    print("  explore           find an enemy")
    print("  attack            attack the current enemy")
    print("  inventory         show inventory")
    print("  use small potion  use a potion")
    print("  save              save the game")
    print("  load              load the game")
    print("  help              show commands")
    print("  quit              exit")


def handle_command(state, command):
    command = command.strip().lower()

    if command == "look":
        describe_state(state)
    elif command == "explore":
        explore(state)
    elif command == "attack":
        attack_enemy(state)
    elif command == "inventory":
        show_inventory(state)
    elif command.startswith("use "):
        use_item(state, command[4:])
    elif command == "save":
        save_game(state)
    elif command == "load":
        state.clear()
        state.update(load_game())
    elif command == "help":
        print_help()
    elif command == "quit":
        state["running"] = False
    else:
        print("Unknown command. Type 'help' for commands.")


def game_loop():
    state = new_game()
    print("Simple Text RPG")
    print_help()

    while state["running"]:
        describe_state(state)
        command = input("> ")
        handle_command(state, command)

    print("Goodbye.")


if __name__ == "__main__":
    game_loop()
'''

    def build_python_text_rpg_result(self, text, terms):

        code_only = self.is_code_only_request(
            text
        )

        steps = [
            "Create a game state dictionary with player, inventory, enemy, location, and running flag.",
            "Add inventory commands for listing and using items.",
            "Add enemy spawning and attack flow.",
            "Add JSON save/load functions.",
            "Add a command parser that routes user input to game actions.",
            "Run everything inside a simple command loop."
        ]

        return {
            "brain": "Code_brain",
            "used_understanding_report": True,
            "used_memory_report": True,
            "language": "python",
            "task_type": "game",
            "output_mode": "code_only" if code_only else "code_with_plan",
            "terms_used": terms,
            "confidence": 92,
            "matched_functions": 6,
            "selected": [
                "new_game",
                "show_inventory",
                "spawn_enemy",
                "attack_enemy",
                "save_game",
                "game_loop"
            ],
            "assembly_plan": {
                "task_type": "game",
                "ordered_ids": [
                    "new_game",
                    "inventory",
                    "enemy",
                    "combat",
                    "save_load_json",
                    "command_loop"
                ],
                "steps": steps,
                "dependencies_added": [],
                "composition_rules_used": [
                    {
                        "id": "python_text_rpg_state_flow",
                        "connection_type": "state_dictionary_to_command_loop",
                        "score": 95
                    }
                ],
                "connection_notes": [
                    "Every command receives and mutates the same game state dictionary.",
                    "Save/load serializes the full state through JSON.",
                    "Combat, inventory, and exploration are connected through handle_command()."
                ],
                "adaptation_notes": [
                    "Built as a first working version, not just helper stubs.",
                    "Uses only Python standard library modules."
                ],
                "data_files_used": [
                    "code.json",
                    "Code_dependency_graph.json",
                    "Code_composition_tables.json",
                    "Code_assembly_patterns.json"
                ]
            },
            "dependencies_added": [],
            "composition_rules_used": [
                {
                    "id": "python_text_rpg_state_flow",
                    "connection_type": "state_dictionary_to_command_loop",
                    "score": 95
                }
            ],
            "adapter_notes": [
                "Specialized assembly path selected for Python text RPG request."
            ],
            "existing_code_detected": False,
            "match_details": [],
            "generated_code": self.build_python_text_rpg_code(),
            "missing": [],
            "needs_creative_brain": False,
            "creative_fallback": None,
            "needs_security": False,
            "suggested_next_brains": [
                "Security_brain",
                "Response_brain"
            ],
            "simulation": {
                "strategy": "plan_then_compose",
                "virtual_variants_considered": 24,
                "selected_reason": "Most complete simple version with inventory, combat, JSON persistence, and command loop.",
                "stop_reason": "Working baseline is complete enough for first version."
            },
            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Build a working first version when the user asks for first working code.",
                "Do not execute generated code here; only assemble and report code."
            ]
        }

    def detect_direct_program_kind(self, text, task_type):

        lowered = str(text).lower()
        domain_text = re.sub(
            r"\b(?:python\s+)?standard[\s-]+library\b",
            "",
            lowered
        )

        equation_signals = [
            "equation calculator", "calculator for equations", "solve equations",
            "solve an equation", "linear equation calculator",
            "quadratic equation calculator", "polynomial equation calculator",
            "\u05de\u05d7\u05e9\u05d1\u05d5\u05df \u05de\u05e9\u05d5\u05d5\u05d0\u05d5\u05ea",
        ]
        if any(signal in domain_text for signal in equation_signals):
            return "equation_calculator"

        recipe_matches = []
        for kind, recipes in self.recipe_by_kind.items():
            aliases = {
                str(alias).lower()
                for recipe in recipes
                for alias in recipe.get("aliases", [])
                if alias
            }
            matched = [alias for alias in aliases if alias in domain_text]
            if matched:
                recipe_matches.append((max(len(alias) for alias in matched), kind))
        if recipe_matches:
            recipe_matches.sort(reverse=True)
            return recipe_matches[0][1]

        checks = [
            ("name_greeter", [
                "asks for the user's name", "ask for the user's name",
                "asks for names", "hello, <name>", "hello <name>",
            ]),
            ("temperature_converter", [
                "temperature converter", "convert temperature", "convert celsius",
                "convert fahrenheit", "celsius or fahrenheit", "celsius to fahrenheit",
                "fahrenheit to celsius",
            ]),
            ("weather_app", ["weather app", "weather", "humidity", "forecast", "weather api"]),
            ("expense_tracker", ["expense tracker", "expenses", "amount spent", "total amount", "search expenses", "category"]),
            ("calendar_app", ["calendar", "appointment", "appointments", "event planner", "events by date", "schedule event"]),
            ("todo_app", ["to-do", "todo", "task list", "tasks", "mark a task"]),
            ("contact_book", ["contact", "phone book", "address book", "email book"]),
            ("library_manager", ["library", "books", "book tracker", "borrowed books", "reading list"]),
            ("flashcards_app", ["flashcards", "flash cards", "study cards", "review cards"]),
            ("shop_inventory", ["shop inventory", "store inventory", "inventory tracker", "stock", "products in stock"]),
            ("habit_tracker", ["habit tracker", "daily habits", "habit log"]),
            ("grade_book", ["grade book", "gradebook", "student grades"]),
            ("recipe_manager", ["recipe manager", "cookbook", "recipes"]),
            ("bookmark_manager", ["bookmark manager", "bookmarks", "saved links"]),
            ("workout_log", ["workout log", "exercise tracker", "fitness log"]),
            ("time_tracker", ["time tracker", "time log", "hours worked"]),
            ("event_registration", ["event registration", "attendee list", "registrations"]),
            ("file_catalog", ["file catalog", "file organizer", "document catalog"]),
            ("notes_app", ["notes", "note taking", "save notes", "notebook"]),
            ("password_manager", ["password manager", "accounts", "account names", "view one account"]),
            ("quiz_game", ["quiz", "question game", "multiple choice"]),
            ("guessing_game", ["guessing game", "guess number", "number game"]),
            ("password_generator", ["password generator", "generate password", "random password"]),
            ("calculator", ["calculator", "calculate", "math app", "add subtract", "multiply", "divide"]),
            ("json_cli", ["json", "file", "save", "load"])
        ]

        for kind, signals in checks:
            if any(signal in domain_text for signal in signals):
                return kind

        if task_type == "file_io":
            return "json_cli"

        return "number_summary"

    def detect_existing_program_kind(self, code):

        lowered = str(code or "").lower()
        markers = [
            ("equation_calculator", ["def parse_equation", "def solve_equation"]),
            ("notes_app", ["def add_note", "def list_notes"]),
            ("expense_tracker", ["def add_expense", "def show_total"]),
            ("library_manager", ["def add_book", "def borrow_book"]),
            ("quiz_game", ["questions =", "def run_quiz"]),
            ("temperature_converter", ["celsius", "fahrenheit", "def convert"]),
            ("todo_app", ["def add_task", "def list_tasks"]),
            ("contact_book", ["def add_contact", "def list_contacts"]),
            ("shop_inventory", ["quantity", "price", "def add_"]),
            ("weather_app", ["def fetch_weather", "humidity"]),
            ("name_greeter", ["hello, {name}", "enter your name"]),
            ("calculator", ["def calculate", "operator"]),
        ]
        for kind, required in markers:
            if all(marker in lowered for marker in required):
                return kind
        return None

    def requested_count(self, text, target_pattern, default, minimum=1, maximum=50):

        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20,
        }
        match = re.search(
            rf"\b(?:exactly\s+)?(\d+|{'|'.join(number_words)})\s+(?:{target_pattern})\b",
            str(text or "").lower(),
        )
        if not match:
            return default
        raw = match.group(1)
        value = int(raw) if raw.isdigit() else number_words.get(raw, default)
        return max(minimum, min(int(value), maximum))

    def build_quiz_game_code(self, text):

        question_count = self.requested_count(
            text,
            r"(?:multiple[- ]choice\s+)?questions?",
            10,
            minimum=1,
            maximum=50,
        )
        bank = [
            {"question": "Which keyword defines a function in Python?", "choices": ["class", "def", "func", "method"], "answer": 2},
            {"question": "Which planet is known as the Red Planet?", "choices": ["Venus", "Earth", "Mars", "Jupiter"], "answer": 3},
            {"question": "What is 9 multiplied by 7?", "choices": ["56", "63", "72", "79"], "answer": 2},
            {"question": "Which gas do plants absorb during photosynthesis?", "choices": ["Oxygen", "Hydrogen", "Carbon dioxide", "Nitrogen"], "answer": 3},
            {"question": "What is the capital of Japan?", "choices": ["Seoul", "Tokyo", "Kyoto", "Beijing"], "answer": 2},
            {"question": "Which file extension is commonly used for JSON data?", "choices": [".json", ".py", ".html", ".exe"], "answer": 1},
            {"question": "How many sides does a hexagon have?", "choices": ["Five", "Six", "Seven", "Eight"], "answer": 2},
            {"question": "Which ocean is the largest?", "choices": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": 4},
            {"question": "Who wrote Romeo and Juliet?", "choices": ["Charles Dickens", "Jane Austen", "William Shakespeare", "Mark Twain"], "answer": 3},
            {"question": "What does CPU stand for?", "choices": ["Central Processing Unit", "Computer Personal Utility", "Core Program User", "Central Program Upload"], "answer": 1},
            {"question": "What is the freezing point of water in Celsius?", "choices": ["0", "10", "32", "100"], "answer": 1},
            {"question": "Which data type stores True or False in Python?", "choices": ["str", "float", "bool", "list"], "answer": 3},
            {"question": "What is the square root of 81?", "choices": ["7", "8", "9", "10"], "answer": 3},
            {"question": "Which continent contains Egypt?", "choices": ["Africa", "Asia", "Europe", "South America"], "answer": 1},
            {"question": "Which instrument measures temperature?", "choices": ["Barometer", "Thermometer", "Compass", "Altimeter"], "answer": 2},
            {"question": "Which symbol starts a Python comment?", "choices": ["//", "#", "--", "/*"], "answer": 2},
            {"question": "How many minutes are in one hour?", "choices": ["30", "45", "60", "90"], "answer": 3},
            {"question": "Which animal is a mammal?", "choices": ["Shark", "Frog", "Dolphin", "Trout"], "answer": 3},
            {"question": "What is H2O commonly called?", "choices": ["Salt", "Water", "Oxygen", "Hydrogen"], "answer": 2},
            {"question": "Which direction is opposite to east?", "choices": ["North", "South", "West", "Up"], "answer": 3},
        ]
        questions = list(bank[:question_count])
        while len(questions) < question_count:
            number = len(questions) + 2
            correct = number + 3
            questions.append({
                "question": f"What is {number} + 3?",
                "choices": [str(correct - 1), str(correct), str(correct + 1), str(correct + 2)],
                "answer": 2,
            })
        questions_literal = json.dumps(questions, ensure_ascii=True, indent=4)

        return f'''QUESTIONS = {questions_literal}


def read_choice(choice_count):
    valid_choices = {{str(index) for index in range(1, choice_count + 1)}}

    while True:
        raw = input("Your answer: ").strip()
        if raw in valid_choices:
            return int(raw)
        print(f"Please enter a number from 1 to {{choice_count}}.")


def run_quiz():
    score = 0

    for question_number, item in enumerate(QUESTIONS, start=1):
        print(f"\\nQuestion {{question_number}}/{{len(QUESTIONS)}}")
        print(item["question"])

        for choice_number, choice in enumerate(item["choices"], start=1):
            print(f"{{choice_number}}. {{choice}}")

        selected = read_choice(len(item["choices"]))
        if selected == item["answer"]:
            print("Correct.")
            score += 1
        else:
            correct = item["choices"][item["answer"] - 1]
            print(f"Incorrect. The correct answer is {{item['answer']}}. {{correct}}")

    print(f"\\nFinal score: {{score}}/{{len(QUESTIONS)}}")


def ask_to_play_again():
    while True:
        answer = input("Play again? (yes/no): ").strip().lower()
        if answer in {{"yes", "y"}}:
            return True
        if answer in {{"no", "n"}}:
            return False
        print("Please enter yes or no.")


def main():
    print("Terminal Quiz Game")

    while True:
        run_quiz()
        if not ask_to_play_again():
            print("Goodbye.")
            break


if __name__ == "__main__":
    main()
'''

    def build_temperature_converter_code(self):

        return '''def read_temperature():
    while True:
        raw = input("Temperature value (or 'exit'): ").strip()
        if raw.lower() == "exit":
            return None

        try:
            return float(raw)
        except ValueError:
            print("Please enter a valid number or type exit.")


def read_unit():
    aliases = {
        "c": "celsius",
        "celsius": "celsius",
        "f": "fahrenheit",
        "fahrenheit": "fahrenheit",
    }

    while True:
        raw = input("Unit (Celsius/Fahrenheit or 'exit'): ").strip().lower()
        if raw == "exit":
            return None
        if raw in aliases:
            return aliases[raw]
        print("Please enter Celsius, Fahrenheit, C, F, or exit.")


def convert_temperature(value, source_unit):
    if source_unit == "celsius":
        return (value * 9 / 5) + 32, "Fahrenheit"
    return (value - 32) * 5 / 9, "Celsius"


def main():
    print("Temperature Converter")

    while True:
        value = read_temperature()
        if value is None:
            break

        source_unit = read_unit()
        if source_unit is None:
            break

        converted, target_unit = convert_temperature(value, source_unit)
        print(f"Converted temperature: {converted:.2f} {target_unit}")

    print("Goodbye.")


if __name__ == "__main__":
    main()
'''

    def build_equation_calculator_code(self):

        return '''import math
import re


TOLERANCE = 1e-9


def normalize_expression(expression):
    normalized = expression.lower().replace("**", "^").replace(" ", "")
    if not normalized:
        raise ValueError("An equation side cannot be empty.")
    if not re.fullmatch(r"[0-9x.+\\-^]+", normalized):
        raise ValueError("Use only numbers, x, +, -, ^, and =.")
    return normalized


def parse_polynomial_expression(expression):
    expression = normalize_expression(expression)
    terms = re.findall(r"[+-]?[^+-]+", expression)
    coefficients = {2: 0.0, 1: 0.0, 0: 0.0}

    for term in terms:
        if "x^" in term and not term.endswith("x^2"):
            raise ValueError("Only linear and quadratic equations are supported.")

        if term.endswith("x^2"):
            coefficient_text = term[:-3]
            degree = 2
        elif term.endswith("x"):
            coefficient_text = term[:-1]
            degree = 1
        elif "x" in term or "^" in term:
            raise ValueError(f"Invalid term: {term}")
        else:
            coefficient_text = term
            degree = 0

        if degree > 0 and coefficient_text in {"", "+", "-"}:
            coefficient = -1.0 if coefficient_text == "-" else 1.0
        else:
            try:
                coefficient = float(coefficient_text)
            except ValueError as error:
                raise ValueError(f"Invalid term: {term}") from error
        coefficients[degree] += coefficient

    return coefficients[2], coefficients[1], coefficients[0]


def parse_equation(equation):
    if equation.count("=") != 1:
        raise ValueError("Enter exactly one equals sign.")
    left, right = equation.split("=", 1)
    left_coefficients = parse_polynomial_expression(left)
    right_coefficients = parse_polynomial_expression(right)
    return tuple(
        left_value - right_value
        for left_value, right_value in zip(left_coefficients, right_coefficients)
    )


def solve_equation(a, b, c):
    if abs(a) <= TOLERANCE:
        if abs(b) <= TOLERANCE:
            return {
                "status": "all_real" if abs(c) <= TOLERANCE else "no_solution",
                "solutions": [],
            }
        return {"status": "solved", "solutions": [-c / b]}

    discriminant = (b * b) - (4 * a * c)
    if discriminant < -TOLERANCE:
        return {"status": "no_real_solution", "solutions": []}
    if abs(discriminant) <= TOLERANCE:
        return {"status": "solved", "solutions": [-b / (2 * a)]}

    root = math.sqrt(discriminant)
    solutions = sorted([(-b - root) / (2 * a), (-b + root) / (2 * a)])
    return {"status": "solved", "solutions": solutions}


def evaluate_polynomial(coefficients, x):
    a, b, c = coefficients
    return (a * x * x) + (b * x) + c


def verify_solutions(coefficients, solutions):
    return all(
        math.isclose(evaluate_polynomial(coefficients, value), 0.0, abs_tol=1e-7)
        for value in solutions
    )


def format_number(value):
    if math.isclose(value, round(value), abs_tol=TOLERANCE):
        return str(int(round(value)))
    return f"{value:.10g}"


def format_result(result):
    status = result["status"]
    if status == "all_real":
        return "Every real number is a solution."
    if status == "no_solution":
        return "The equation has no solution."
    if status == "no_real_solution":
        return "The equation has no real solutions."
    solutions = ", ".join(format_number(value) for value in result["solutions"])
    return f"Solution(s): {solutions}"


def main():
    print("Linear and Quadratic Equation Calculator")
    print("Examples: 2x + 3 = 7 or x^2 - 5x + 6 = 0")

    while True:
        equation = input("Equation (or 'exit'): ").strip()
        if equation.lower() == "exit":
            print("Goodbye.")
            break
        try:
            coefficients = parse_equation(equation)
            result = solve_equation(*coefficients)
            if not verify_solutions(coefficients, result["solutions"]):
                raise ArithmeticError("The calculated solution could not be verified.")
            print(format_result(result))
        except (ValueError, ArithmeticError) as error:
            print(f"Invalid equation: {error}")


if __name__ == "__main__":
    main()
'''

    def build_json_record_cli_code(
        self,
        title,
        file_name,
        fields,
        search_fields,
        numeric_fields=None,
        total_expression=None,
        total_label=None
    ):

        numeric_fields = numeric_fields or []
        field_lines = ",\n    ".join(
            repr(field)
            for field in fields
        )
        search_field_lines = ",\n    ".join(
            repr(field)
            for field in search_fields
        )
        numeric_field_lines = ",\n    ".join(
            repr(field)
            for field in numeric_fields
        )
        total_expression = total_expression or "0"
        total_label = total_label or "Total"

        return f'''import json
from pathlib import Path


DATA_FILE = Path("{file_name}")
FIELDS = [
    {field_lines}
]
SEARCH_FIELDS = [
    {search_field_lines}
]
NUMERIC_FIELDS = [
    {numeric_field_lines}
]


def load_records():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Could not read {{DATA_FILE}}, starting with an empty list.")
        return []

    if not isinstance(data, list):
        return []

    records = []
    for item in data:
        if isinstance(item, dict):
            records.append(normalize_record(item))

    return records


def save_records(records):
    DATA_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def normalize_record(item):
    record = {{}}
    for field in FIELDS:
        value = item.get(field, "")
        if field in NUMERIC_FIELDS:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0.0
        else:
            value = str(value).strip()
        record[field] = value
    return record


def input_value(field):
    value = input(field.replace("_", " ").title() + ": ").strip()
    if field in NUMERIC_FIELDS:
        try:
            return float(value)
        except ValueError:
            print("Invalid number, using 0.")
            return 0.0
    return value


def add_record(records):
    record = {{}}
    for field in FIELDS:
        record[field] = input_value(field)

    if not any(str(value).strip() for value in record.values()):
        print("Nothing was added.")
        return

    records.append(record)
    save_records(records)
    print("Saved.")


def list_records(records):
    if not records:
        print("No records yet.")
        return

    for index, record in enumerate(records, start=1):
        parts = [f"{{field}}={{record.get(field, '')}}" for field in FIELDS]
        print(f"{{index}}. " + " | ".join(parts))


def search_records(records, keyword):
    keyword = keyword.strip().lower()
    if not keyword:
        print("Search keyword cannot be empty.")
        return

    matches = [
        record
        for record in records
        if any(keyword in str(record.get(field, "")).lower() for field in SEARCH_FIELDS)
    ]

    list_records(matches)


def get_record_index(records, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid number.")
        return None

    if index < 0 or index >= len(records):
        print("Number is out of range.")
        return None

    return index


def delete_record(records, raw_index):
    index = get_record_index(records, raw_index)
    if index is None:
        return

    removed = records.pop(index)
    save_records(records)
    print("Deleted: " + " | ".join(str(removed.get(field, "")) for field in FIELDS))


def show_total(records):
    total = sum({total_expression} for record in records)
    print(f"{total_label}: {{total:.2f}}")


def print_help():
    print("Commands:")
    print("  add               Add a record")
    print("  list              List records")
    print("  search <keyword>  Search records")
    print("  delete <number>   Delete a record")
    print("  total             Show total value")
    print("  help              Show commands")
    print("  quit              Save and exit")


def main():
    records = load_records()
    print("{title}")
    print_help()

    while True:
        command = input("> ").strip()
        lower = command.lower()

        if lower == "add":
            add_record(records)
        elif lower == "list":
            list_records(records)
        elif lower.startswith("search "):
            search_records(records, command[7:].strip())
        elif lower.startswith("delete "):
            delete_record(records, command[7:].strip())
        elif lower == "total":
            show_total(records)
        elif lower == "help":
            print_help()
        elif lower == "quit":
            save_records(records)
            print("Saved. Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

    def build_notes_app_code(self):

        return '''import json
from datetime import datetime
from pathlib import Path


NOTES_FILE = Path("notes.json")
EXPORT_FILE = Path("notes_export.txt")


def parse_tags(raw_tags):
    return [
        tag.strip().lower()
        for tag in raw_tags.split(",")
        if tag.strip()
    ]


def normalize_note(item):
    if not isinstance(item, dict):
        return None

    title = str(item.get("title", "Untitled")).strip() or "Untitled"
    body = str(item.get("body", item.get("text", ""))).strip()
    created_at = item.get("created_at") or datetime.now().isoformat(timespec="seconds")
    updated_at = item.get("updated_at", "")
    tags = item.get("tags", [])

    if isinstance(tags, str):
        tags = parse_tags(tags)
    elif isinstance(tags, list):
        tags = [
            str(tag).strip().lower()
            for tag in tags
            if str(tag).strip()
        ]
    else:
        tags = []

    return {
        "title": title,
        "body": body,
        "tags": tags,
        "created_at": str(created_at),
        "updated_at": str(updated_at)
    }


def load_notes():
    if not NOTES_FILE.exists():
        return []

    try:
        data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Could not read notes.json, starting with an empty list.")
        return []

    if not isinstance(data, list):
        return []

    notes = []
    for item in data:
        note = normalize_note(item)
        if note is not None:
            notes.append(note)

    return notes


def save_notes(notes):
    NOTES_FILE.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_note(notes):
    title = input("Title: ").strip()
    body = input("Note: ").strip()
    tags = parse_tags(input("Tags, separated by commas: ").strip())

    if not title or not body:
        print("Title and note are required.")
        return

    notes.append({
        "title": title,
        "body": body,
        "tags": tags,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": ""
    })
    save_notes(notes)
    print("Note saved.")


def list_notes(notes):
    if not notes:
        print("No notes yet.")
        return

    for index, note in enumerate(notes, start=1):
        tags = ", ".join(note.get("tags", [])) or "no tags"
        print(f"{index}. {note['title']} [{tags}] ({note['created_at']})")


def get_note_index(notes, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid note number.")
        return None

    if index < 0 or index >= len(notes):
        print("Note number is out of range.")
        return None

    return index


def view_note(notes, raw_index):
    index = get_note_index(notes, raw_index)
    if index is None:
        return

    note = notes[index]
    tags = ", ".join(note.get("tags", [])) or "no tags"
    print(f"\\n{note['title']}")
    print("-" * len(note["title"]))
    print(note["body"])
    print(f"Tags: {tags}")
    if note.get("updated_at"):
        print(f"Updated: {note['updated_at']}")


def edit_note(notes, raw_index):
    index = get_note_index(notes, raw_index)
    if index is None:
        return

    note = notes[index]
    print("Press Enter to keep the current value.")
    title = input(f"Title [{note['title']}]: ").strip()
    body = input("Note body: ").strip()
    current_tags = ", ".join(note.get("tags", []))
    raw_tags = input(f"Tags [{current_tags}]: ").strip()

    if title:
        note["title"] = title
    if body:
        note["body"] = body
    if raw_tags:
        note["tags"] = parse_tags(raw_tags)

    note["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_notes(notes)
    print("Note updated.")


def note_matches(note, keyword):
    keyword = keyword.strip().lower()
    if keyword in note.get("title", "").lower():
        return True
    if keyword in note.get("body", "").lower():
        return True
    return any(keyword in tag.lower() for tag in note.get("tags", []))


def search_notes(notes, keyword):
    keyword = keyword.strip().lower()
    if not keyword:
        print("Search keyword cannot be empty.")
        return

    matches = [
        (index, note)
        for index, note in enumerate(notes, start=1)
        if note_matches(note, keyword)
    ]

    if not matches:
        print("No matching notes found.")
        return

    for index, note in matches:
        tags = ", ".join(note.get("tags", [])) or "no tags"
        print(f"{index}. {note['title']} [{tags}] ({note['created_at']})")


def delete_note(notes, raw_index):
    index = get_note_index(notes, raw_index)
    if index is None:
        return

    removed = notes.pop(index)
    save_notes(notes)
    print(f"Deleted note: {removed['title']}")


def export_notes(notes, path=EXPORT_FILE):
    lines = ["Notes Export", "=" * 12, ""]

    for index, note in enumerate(notes, start=1):
        tags = ", ".join(note.get("tags", [])) or "no tags"
        lines.append(f"{index}. {note['title']}")
        lines.append(f"Created: {note['created_at']}")
        if note.get("updated_at"):
            lines.append(f"Updated: {note['updated_at']}")
        lines.append(f"Tags: {tags}")
        lines.append(note.get("body", ""))
        lines.append("")

    path.write_text("\\n".join(lines), encoding="utf-8")
    print(f"Exported {len(notes)} notes to {path}.")


def print_help():
    print("Commands:")
    print("  add                Add a new note")
    print("  list               List all notes")
    print("  view <number>      View a note")
    print("  edit <number>      Edit a note")
    print("  search <keyword>   Search title, body, or tags")
    print("  delete <number>    Delete a note")
    print("  export             Export notes to notes_export.txt")
    print("  help               Show commands")
    print("  quit               Save and exit")


def main():
    notes = load_notes()
    print("Notes App")
    print_help()

    while True:
        command = input("> ").strip()
        lower = command.lower()

        if lower == "add":
            add_note(notes)
        elif lower == "list":
            list_notes(notes)
        elif lower.startswith("view "):
            view_note(notes, command[5:].strip())
        elif lower.startswith("edit "):
            edit_note(notes, command[5:].strip())
        elif lower.startswith("search "):
            search_notes(notes, command[7:].strip())
        elif lower.startswith("delete "):
            delete_note(notes, command[7:].strip())
        elif lower == "export":
            export_notes(notes)
        elif lower == "help":
            print_help()
        elif lower == "quit":
            save_notes(notes)
            print("Notes saved. Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

    def build_library_manager_code(self):

        return '''import json
from pathlib import Path


DATA_FILE = Path("library.json")


def normalize_year(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_book(item):
    """Convert current and older book records to the current format."""
    if isinstance(item, str):
        return {
            "title": item.strip() or "Untitled",
            "author": "Unknown",
            "year": None,
            "borrowed": False,
        }
    if not isinstance(item, dict):
        return None

    title = str(item.get("title", item.get("name", "Untitled"))).strip()
    author = str(item.get("author", item.get("writer", "Unknown"))).strip()
    year = normalize_year(item.get("year", item.get("published_year")))

    borrowed = bool(item.get("borrowed", False))
    old_status = str(item.get("status", "")).strip().lower()
    if old_status in {"borrowed", "checked out", "unavailable"}:
        borrowed = True
    elif old_status in {"available", "returned"}:
        borrowed = False

    return {
        "title": title or "Untitled",
        "author": author or "Unknown",
        "year": year,
        "borrowed": borrowed,
    }


def load_books():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read {DATA_FILE}: {error}")
        return []

    # Older files may wrap the list in a books or items object.
    if isinstance(data, dict):
        data = data.get("books", data.get("items", []))
    if not isinstance(data, list):
        return []

    books = []
    for item in data:
        book = normalize_book(item)
        if book is not None:
            books.append(book)
    return books


def save_books(books):
    temporary_file = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    try:
        temporary_file.write_text(
            json.dumps(books, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_file.replace(DATA_FILE)
    except OSError as error:
        print(f"Could not save {DATA_FILE}: {error}")
        return False
    return True


def read_year():
    raw_year = input("Year: ").strip()
    year = normalize_year(raw_year)
    if raw_year and year is None:
        print("Year must be a whole number.")
    return year


def add_book(books):
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    year = read_year()
    if not title or not author:
        print("Title and author are required.")
        return

    books.append({
        "title": title,
        "author": author,
        "year": year,
        "borrowed": False,
    })
    if save_books(books):
        print("Book added.")


def print_book_rows(indexed_books):
    if not indexed_books:
        print("No books found.")
        return

    for index, book in indexed_books:
        year = book["year"] if book["year"] is not None else "Unknown year"
        status = "Borrowed" if book["borrowed"] else "Available"
        print(f"{index}. {book['title']} | {book['author']} | {year} | {status}")


def list_books(books):
    print_book_rows(list(enumerate(books, start=1)))


def search_books(books):
    keyword = input("Title or author: ").strip().lower()
    if not keyword:
        print("Search text cannot be empty.")
        return

    matches = [
        (index, book)
        for index, book in enumerate(books, start=1)
        if keyword in book["title"].lower() or keyword in book["author"].lower()
    ]
    print_book_rows(matches)


def get_book_index(books):
    raw_number = input("Book number: ").strip()
    try:
        index = int(raw_number) - 1
    except ValueError:
        print("Please enter a valid book number.")
        return None

    if index < 0 or index >= len(books):
        print("Book number is out of range.")
        return None
    return index


def borrow_book(books):
    index = get_book_index(books)
    if index is None:
        return
    if books[index]["borrowed"]:
        print("That book is already borrowed.")
        return
    books[index]["borrowed"] = True
    if save_books(books):
        print("Book borrowed.")


def return_book(books):
    index = get_book_index(books)
    if index is None:
        return
    if not books[index]["borrowed"]:
        print("That book is already available.")
        return
    books[index]["borrowed"] = False
    if save_books(books):
        print("Book returned.")


def delete_book(books):
    index = get_book_index(books)
    if index is None:
        return
    removed = books.pop(index)
    if save_books(books):
        print(f"Deleted: {removed['title']}")


def print_help():
    print("Commands:")
    print("  add      Add a book")
    print("  list     List all books")
    print("  search   Search by title or author")
    print("  borrow   Borrow a book by number")
    print("  return   Return a book by number")
    print("  delete   Delete a book by number")
    print("  help     Show commands")
    print("  quit     Save and exit")


def main():
    books = load_books()
    print("Library Manager")
    print_help()

    while True:
        command = input("> ").strip().lower()
        if command == "add":
            add_book(books)
        elif command == "list":
            list_books(books)
        elif command == "search":
            search_books(books)
        elif command == "borrow":
            borrow_book(books)
        elif command == "return":
            return_book(books)
        elif command == "delete":
            delete_book(books)
        elif command == "help":
            print_help()
        elif command in {"quit", "exit"}:
            save_books(books)
            print("Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

    def build_direct_python_program_code(self, text, task_type, program_kind=None):

        lowered = str(text).lower()
        program_kind = program_kind or self.detect_direct_program_kind(text, task_type)

        if program_kind == "name_greeter":
            return '''def main():
    while True:
        name = input("Enter your name (or type 'exit'): ").strip()

        if name.lower() == "exit":
            print("Goodbye!")
            break

        if not name:
            print("Please enter a name or type exit.")
            continue

        print(f"Hello, {name}!")


if __name__ == "__main__":
    main()
'''

        if program_kind == "library_manager":
            return self.apply_requested_file_name(
                self.build_library_manager_code(),
                text
            )

        recipe = self.choose_project_recipe(program_kind, text)
        if recipe.get("generator") == "json_record_cli":
            code = self.build_json_record_cli_code(
                recipe.get("title", program_kind.replace("_", " ").title()),
                recipe.get("file_name", f"{program_kind}.json"),
                recipe.get("fields", ["name", "description"]),
                recipe.get("search_fields", recipe.get("fields", ["name"])),
                numeric_fields=recipe.get("numeric_fields", []),
                total_expression=recipe.get("total_expression"),
                total_label=recipe.get("total_label")
            )
            return self.apply_requested_file_name(code, text)

        if program_kind == "temperature_converter":
            return self.build_temperature_converter_code()

        if program_kind == "equation_calculator":
            return self.build_equation_calculator_code()

        if program_kind == "weather_app":
            return '''import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


def fetch_weather(city):
    url = f"https://wttr.in/{quote(city)}?format=j1"

    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Could not fetch live weather data: {error}")
        print("Using safe mock weather data instead.")
        return mock_weather_data(city)


def mock_weather_data(city):
    return {
        "nearest_area": [
            {
                "areaName": [
                    {
                        "value": city
                    }
                ]
            }
        ],
        "current_condition": [
            {
                "temp_C": "22",
                "humidity": "55",
                "weatherDesc": [
                    {
                        "value": "Partly cloudy"
                    }
                ]
            }
        ]
    }


def parse_weather(data):
    current = data["current_condition"][0]
    return {
        "temperature_c": current.get("temp_C", "unknown"),
        "humidity": current.get("humidity", "unknown"),
        "condition": current.get("weatherDesc", [{}])[0].get("value", "unknown")
    }


def print_weather(city, weather):
    print(f"Weather for {city}")
    print(f"Temperature: {weather['temperature_c']} C")
    print(f"Humidity: {weather['humidity']}%")
    print(f"Condition: {weather['condition']}")


def main():
    while True:
        city = input("City (or 'exit'): ").strip()
        if city.lower() == "exit":
            break
        if not city:
            print("Please enter a city name.")
            continue

        try:
            data = fetch_weather(city)
            weather = parse_weather(data)
            print_weather(city, weather)
        except (KeyError, IndexError, TypeError) as error:
            print(error)


if __name__ == "__main__":
    main()
'''

        if program_kind == "calendar_app":
            return self.build_json_record_cli_code(
                "Calendar App",
                "calendar_events.json",
                ["date", "time", "title", "description"],
                ["date", "title", "description"],
                total_label="Events",
                total_expression="1"
            )

        if program_kind == "library_manager":
            return self.build_json_record_cli_code(
                "Library Manager",
                "library_books.json",
                ["title", "author", "year", "status"],
                ["title", "author", "status"],
                numeric_fields=["year"],
                total_label="Books",
                total_expression="1"
            )

        if program_kind == "flashcards_app":
            return self.build_json_record_cli_code(
                "Flashcards App",
                "flashcards.json",
                ["question", "answer", "tag"],
                ["question", "answer", "tag"],
                total_label="Cards",
                total_expression="1"
            )

        if program_kind == "shop_inventory":
            return self.build_json_record_cli_code(
                "Shop Inventory",
                "shop_inventory.json",
                ["name", "sku", "category", "quantity", "price"],
                ["name", "sku", "category"],
                numeric_fields=["quantity", "price"],
                total_label="Inventory value",
                total_expression='record.get("quantity", 0) * record.get("price", 0)'
            )

        if program_kind == "todo_app":
            return '''import json
from pathlib import Path


TASKS_FILE = Path("tasks.json")


def load_tasks():
    if not TASKS_FILE.exists():
        return []

    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Could not read tasks.json, starting with an empty list.")
        return []

    if not isinstance(data, list):
        return []

    tasks = []
    for item in data:
        if isinstance(item, dict) and "text" in item:
            tasks.append({
                "text": str(item["text"]),
                "done": bool(item.get("done", False))
            })

    return tasks


def save_tasks(tasks):
    TASKS_FILE.write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_task(tasks, text):
    text = text.strip()
    if not text:
        print("Task text cannot be empty.")
        return

    tasks.append({
        "text": text,
        "done": False
    })
    save_tasks(tasks)
    print("Task added.")


def list_tasks(tasks):
    if not tasks:
        print("No tasks yet.")
        return

    for index, task in enumerate(tasks, start=1):
        mark = "x" if task["done"] else " "
        print(f"{index}. [{mark}] {task['text']}")


def get_task_index(tasks, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid task number.")
        return None

    if index < 0 or index >= len(tasks):
        print("Task number is out of range.")
        return None

    return index


def mark_done(tasks, raw_index):
    index = get_task_index(tasks, raw_index)
    if index is None:
        return

    tasks[index]["done"] = True
    save_tasks(tasks)
    print("Task marked as done.")


def delete_task(tasks, raw_index):
    index = get_task_index(tasks, raw_index)
    if index is None:
        return

    removed = tasks.pop(index)
    save_tasks(tasks)
    print(f"Deleted: {removed['text']}")


def print_help():
    print("Commands:")
    print("  add <task>      Add a new task")
    print("  list            Show all tasks")
    print("  done <number>   Mark a task as done")
    print("  delete <number> Delete a task")
    print("  help            Show this help")
    print("  exit            Save and exit")


def main():
    tasks = load_tasks()
    print("To-Do List")
    print_help()

    while True:
        command = input("> ").strip()
        if not command:
            continue

        lower_command = command.lower()

        if lower_command == "exit":
            save_tasks(tasks)
            print("Tasks saved. Goodbye.")
            break
        elif lower_command == "help":
            print_help()
        elif lower_command == "list":
            list_tasks(tasks)
        elif lower_command.startswith("add "):
            add_task(tasks, command[4:])
        elif lower_command.startswith("done "):
            mark_done(tasks, command[5:].strip())
        elif lower_command.startswith("delete "):
            delete_task(tasks, command[7:].strip())
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

        if program_kind == "contact_book":
            return '''import json
from pathlib import Path


CONTACTS_FILE = Path("contacts.json")


def load_contacts():
    if not CONTACTS_FILE.exists():
        return []

    try:
        data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    return data if isinstance(data, list) else []


def save_contacts(contacts):
    CONTACTS_FILE.write_text(
        json.dumps(contacts, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_contact(contacts):
    name = input("Name: ").strip()
    phone = input("Phone: ").strip()
    email = input("Email: ").strip()

    if not name:
        print("Name is required.")
        return

    contacts.append({
        "name": name,
        "phone": phone,
        "email": email
    })
    save_contacts(contacts)
    print("Contact saved.")


def list_contacts(contacts):
    if not contacts:
        print("No contacts yet.")
        return

    for index, contact in enumerate(contacts, start=1):
        print(f"{index}. {contact['name']} | {contact.get('phone', '')} | {contact.get('email', '')}")


def search_contacts(contacts, query):
    query = query.lower()
    matches = [
        contact
        for contact in contacts
        if query in contact.get("name", "").lower()
        or query in contact.get("phone", "").lower()
        or query in contact.get("email", "").lower()
    ]
    list_contacts(matches)


def main():
    contacts = load_contacts()
    print("Contact Book")
    print("Commands: add, list, search, quit")

    while True:
        command = input("> ").strip().lower()

        if command == "add":
            add_contact(contacts)
        elif command == "list":
            list_contacts(contacts)
        elif command == "search":
            search_contacts(contacts, input("Search: ").strip())
        elif command == "quit":
            save_contacts(contacts)
            break
        else:
            print("Unknown command.")


if __name__ == "__main__":
    main()
'''

        if program_kind == "notes_app":
            return self.build_notes_app_code()

        if program_kind == "password_manager":
            return '''import json
from pathlib import Path


ACCOUNTS_FILE = Path("accounts.json")


def load_accounts():
    if not ACCOUNTS_FILE.exists():
        return []

    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Could not read accounts.json, starting with an empty list.")
        return []

    if not isinstance(data, list):
        return []

    accounts = []
    for item in data:
        if isinstance(item, dict) and item.get("name"):
            accounts.append({
                "name": str(item.get("name", "")),
                "username": str(item.get("username", "")),
                "password": str(item.get("password", "")),
                "notes": str(item.get("notes", ""))
            })

    return accounts


def save_accounts(accounts):
    ACCOUNTS_FILE.write_text(
        json.dumps(accounts, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_account(accounts):
    name = input("Account name: ").strip()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    notes = input("Notes: ").strip()

    if not name or not password:
        print("Account name and password are required.")
        return

    accounts.append({
        "name": name,
        "username": username,
        "password": password,
        "notes": notes
    })
    save_accounts(accounts)
    print("Account saved.")


def list_accounts(accounts):
    if not accounts:
        print("No accounts saved.")
        return

    for index, account in enumerate(accounts, start=1):
        print(f"{index}. {account['name']}")


def search_accounts(accounts, keyword):
    keyword = keyword.strip().lower()
    if not keyword:
        print("Search keyword cannot be empty.")
        return

    matches = [
        (index, account)
        for index, account in enumerate(accounts, start=1)
        if keyword in account.get("name", "").lower()
    ]

    if not matches:
        print("No matching accounts found.")
        return

    for index, account in matches:
        print(f"{index}. {account['name']}")


def get_account_index(accounts, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid account number.")
        return None

    if index < 0 or index >= len(accounts):
        print("Account number is out of range.")
        return None

    return index


def view_account(accounts, raw_index):
    index = get_account_index(accounts, raw_index)
    if index is None:
        return

    account = accounts[index]
    print(f"Account: {account['name']}")
    print(f"Username: {account.get('username', '')}")
    print(f"Password: {account.get('password', '')}")
    if account.get("notes"):
        print(f"Notes: {account['notes']}")


def delete_account(accounts, raw_index):
    index = get_account_index(accounts, raw_index)
    if index is None:
        return

    removed = accounts.pop(index)
    save_accounts(accounts)
    print(f"Deleted account: {removed['name']}")


def print_help():
    print("Commands:")
    print("  add                Add a new account")
    print("  list               List account names")
    print("  search <keyword>   Search accounts by name")
    print("  view <number>      View one account")
    print("  delete <number>    Delete an account")
    print("  help               Show commands")
    print("  quit               Save and exit")


def main():
    accounts = load_accounts()
    print("Terminal Password Manager")
    print("Warning: this simple demo stores passwords in plain JSON.")
    print("Use it only for learning or test data, not real passwords.")
    print_help()

    while True:
        command = input("> ").strip()
        lower = command.lower()

        if lower == "add":
            add_account(accounts)
        elif lower == "list":
            list_accounts(accounts)
        elif lower.startswith("search "):
            search_accounts(accounts, command[7:].strip())
        elif lower.startswith("view "):
            view_account(accounts, command[5:].strip())
        elif lower.startswith("delete "):
            delete_account(accounts, command[7:].strip())
        elif lower == "help":
            print_help()
        elif lower == "quit":
            save_accounts(accounts)
            print("Accounts saved. Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

        if program_kind == "expense_tracker":
            return '''import json
from pathlib import Path


EXPENSES_FILE = Path("expenses.json")


def load_expenses():
    if not EXPENSES_FILE.exists():
        return []

    try:
        data = json.loads(EXPENSES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Could not read expenses.json, starting with an empty list.")
        return []

    if not isinstance(data, list):
        return []

    expenses = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            amount = float(item.get("amount", 0))
        except (TypeError, ValueError):
            amount = 0.0
        expenses.append({
            "amount": amount,
            "category": str(item.get("category", "uncategorized")).strip() or "uncategorized",
            "description": str(item.get("description", "")).strip()
        })

    return expenses


def save_expenses(expenses):
    EXPENSES_FILE.write_text(
        json.dumps(expenses, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def format_amount(amount):
    return f"{amount:.2f}"


def add_expense(expenses):
    raw_amount = input("Amount: ").strip()
    category = input("Category: ").strip()
    description = input("Description: ").strip()

    try:
        amount = float(raw_amount)
    except ValueError:
        print("Amount must be a number.")
        return

    if amount < 0:
        print("Amount cannot be negative.")
        return

    if not category:
        category = "uncategorized"

    expenses.append({
        "amount": amount,
        "category": category,
        "description": description
    })
    save_expenses(expenses)
    print("Expense saved.")


def list_expenses(expenses):
    if not expenses:
        print("No expenses yet.")
        return

    for index, expense in enumerate(expenses, start=1):
        print(
            f"{index}. "
            f"{format_amount(expense['amount'])} | "
            f"{expense['category']} | "
            f"{expense.get('description', '')}"
        )


def search_by_category(expenses, category):
    category = category.strip().lower()
    if not category:
        print("Category cannot be empty.")
        return

    matches = [
        (index, expense)
        for index, expense in enumerate(expenses, start=1)
        if category in expense.get("category", "").lower()
    ]

    if not matches:
        print("No matching expenses found.")
        return

    for index, expense in matches:
        print(
            f"{index}. "
            f"{format_amount(expense['amount'])} | "
            f"{expense['category']} | "
            f"{expense.get('description', '')}"
        )


def show_total(expenses):
    total = sum(expense.get("amount", 0) for expense in expenses)
    print(f"Total spent: {format_amount(total)}")


def get_expense_index(expenses, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid expense number.")
        return None

    if index < 0 or index >= len(expenses):
        print("Expense number is out of range.")
        return None

    return index


def delete_expense(expenses, raw_index):
    index = get_expense_index(expenses, raw_index)
    if index is None:
        return

    removed = expenses.pop(index)
    save_expenses(expenses)
    print(
        "Deleted expense: "
        f"{format_amount(removed['amount'])} | "
        f"{removed['category']} | "
        f"{removed.get('description', '')}"
    )


def print_help():
    print("Commands:")
    print("  add                  Add an expense")
    print("  list                 List all expenses")
    print("  search <category>    Search expenses by category")
    print("  total                Show total amount spent")
    print("  delete <number>      Delete an expense")
    print("  help                 Show commands")
    print("  quit                 Save and exit")


def main():
    expenses = load_expenses()
    print("Expense Tracker")
    print_help()

    while True:
        command = input("> ").strip()
        lower = command.lower()

        if lower == "add":
            add_expense(expenses)
        elif lower == "list":
            list_expenses(expenses)
        elif lower.startswith("search "):
            search_by_category(expenses, command[7:].strip())
        elif lower == "total":
            show_total(expenses)
        elif lower.startswith("delete "):
            delete_expense(expenses, command[7:].strip())
        elif lower == "help":
            print_help()
        elif lower == "quit":
            save_expenses(expenses)
            print("Expenses saved. Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for commands.")


if __name__ == "__main__":
    main()
'''

        if program_kind == "notes_app":
            return '''import json
from datetime import datetime
from pathlib import Path


NOTES_FILE = Path("notes.json")


def load_notes():
    if not NOTES_FILE.exists():
        return []

    try:
        data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    return data if isinstance(data, list) else []


def save_notes(notes):
    NOTES_FILE.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_note(notes):
    title = input("Title: ").strip()
    body = input("Note: ").strip()

    if not title or not body:
        print("Title and note are required.")
        return

    notes.append({
        "title": title,
        "body": body,
        "created_at": datetime.now().isoformat(timespec="seconds")
    })
    save_notes(notes)
    print("Note saved.")


def list_notes(notes):
    if not notes:
        print("No notes yet.")
        return

    for index, note in enumerate(notes, start=1):
        print(f"{index}. {note['title']} ({note['created_at']})")


def get_note_index(notes, raw_index):
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a valid note number.")
        return None

    if index < 0 or index >= len(notes):
        print("Note number is out of range.")
        return None

    return index


def view_note(notes, raw_index):
    index = get_note_index(notes, raw_index)
    if index is None:
        return

    note = notes[index]
    print(f"\\n{note['title']}")
    print("-" * len(note["title"]))
    print(note["body"])


def search_notes(notes, keyword):
    keyword = keyword.strip().lower()
    if not keyword:
        print("Search keyword cannot be empty.")
        return

    matches = [
        (index, note)
        for index, note in enumerate(notes, start=1)
        if keyword in note.get("title", "").lower()
        or keyword in note.get("body", "").lower()
    ]

    if not matches:
        print("No matching notes found.")
        return

    for index, note in matches:
        print(f"{index}. {note['title']} ({note['created_at']})")


def delete_note(notes, raw_index):
    index = get_note_index(notes, raw_index)
    if index is None:
        return

    removed = notes.pop(index)
    save_notes(notes)
    print(f"Deleted note: {removed['title']}")


def print_help():
    print("Commands:")
    print("  add                Add a new note")
    print("  list               List all notes")
    print("  view <number>      View a note")
    print("  search <keyword>   Search notes")
    print("  delete <number>    Delete a note")
    print("  help               Show commands")
    print("  quit               Save and exit")


def main():
    notes = load_notes()
    print("Notes App")
    print_help()

    while True:
        command = input("> ").strip()
        lower = command.lower()

        if lower == "add":
            add_note(notes)
        elif lower == "list":
            list_notes(notes)
        elif lower.startswith("view "):
            view_note(notes, command[5:].strip())
        elif lower.startswith("search "):
            search_notes(notes, command[7:].strip())
        elif lower.startswith("delete "):
            delete_note(notes, command[7:].strip())
        elif lower == "help":
            print_help()
        elif lower == "quit":
            save_notes(notes)
            break
        else:
            print("Unknown command.")


if __name__ == "__main__":
    main()
'''

        if program_kind == "quiz_game":
            return self.build_quiz_game_code(text)

        if program_kind == "guessing_game":
            return '''import random


def main():
    secret = random.randint(1, 100)
    attempts = 0
    print("Guess the number from 1 to 100.")

    while True:
        raw = input("Your guess: ").strip()

        try:
            guess = int(raw)
        except ValueError:
            print("Please enter a number.")
            continue

        attempts += 1

        if guess < secret:
            print("Too low.")
        elif guess > secret:
            print("Too high.")
        else:
            print(f"Correct. You guessed it in {attempts} attempts.")
            break


if __name__ == "__main__":
    main()
'''

        if program_kind == "password_generator":
            return '''import random
import string


def generate_password(length=16):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(characters) for _ in range(length))


def main():
    raw = input("Password length (default 16): ").strip()

    try:
        length = int(raw) if raw else 16
    except ValueError:
        length = 16

    length = max(8, min(length, 128))
    print(generate_password(length))


if __name__ == "__main__":
    main()
'''

        if program_kind == "calculator":
            return '''import json
from datetime import datetime
from pathlib import Path


HISTORY_FILE = Path("calculator_history.json")


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    return data if isinstance(data, list) else []


def save_history(history):
    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def calculate(left, operator, right):
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        if right == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return left / right
    if operator == "%":
        return left * right / 100
    raise ValueError("Unknown operator.")


def format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def show_history(history):
    if not history:
        print("No calculations yet.")
        return

    for index, item in enumerate(history, start=1):
        print(f"{index}. {item['expression']} = {item['result']}")


def main():
    history = load_history()

    print("Simple Calculator")
    print("Type: number operator number")
    print("Example: 4 * 7")
    print("Percentage example: 20 % 150 means 20 percent of 150")
    print("Type history to show saved calculations.")
    print("Type exit to quit.")

    while True:
        raw = input("> ").strip()
        if raw.lower() == "exit":
            save_history(history)
            break
        if raw.lower() == "history":
            show_history(history)
            continue

        parts = raw.split()
        if len(parts) != 3:
            print("Use format: number operator number")
            continue

        try:
            left = float(parts[0])
            operator = parts[1]
            right = float(parts[2])
            result = calculate(left, operator, right)
            expression = f"{format_number(left)} {operator} {format_number(right)}"
            print(format_number(result))
            history.append({
                "time": datetime.now().isoformat(timespec="seconds"),
                "expression": expression,
                "result": format_number(result)
            })
            save_history(history)
        except (ValueError, ZeroDivisionError) as error:
            print(error)


if __name__ == "__main__":
    main()
'''

        if program_kind == "json_cli":
            return '''import json
from pathlib import Path


DATA_FILE = Path("data.json")


def load_items():
    if not DATA_FILE.exists():
        return []

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_items(items):
    DATA_FILE.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def main():
    items = load_items()

    while True:
        command = input("add/list/clear/quit > ").strip().lower()

        if command == "add":
            text = input("Item text: ").strip()
            if text:
                items.append(text)
                save_items(items)
                print("Saved.")
        elif command == "list":
            if not items:
                print("No items yet.")
            for index, item in enumerate(items, start=1):
                print(f"{index}. {item}")
        elif command == "clear":
            items.clear()
            save_items(items)
            print("Cleared.")
        elif command == "quit":
            break
        else:
            print("Unknown command.")


if __name__ == "__main__":
    main()
'''

        return '''def calculate_summary(numbers):
    if not numbers:
        return {
            "count": 0,
            "total": 0,
            "average": 0,
            "minimum": None,
            "maximum": None
        }

    total = sum(numbers)
    return {
        "count": len(numbers),
        "total": total,
        "average": total / len(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers)
    }


def read_numbers():
    raw = input("Enter numbers separated by spaces: ").strip()
    numbers = []

    for part in raw.split():
        try:
            numbers.append(float(part))
        except ValueError:
            print(f"Skipping invalid number: {part}")

    return numbers


def main():
    numbers = read_numbers()
    summary = calculate_summary(numbers)

    print("Summary")
    print(f"Count: {summary['count']}")
    print(f"Total: {summary['total']}")
    print(f"Average: {summary['average']}")
    print(f"Minimum: {summary['minimum']}")
    print(f"Maximum: {summary['maximum']}")


if __name__ == "__main__":
    main()
'''

    def apply_requested_file_name(self, code, text):

        file_names = re.findall(
            r"\b[\w.-]+\.(?:jsonl?|txt|csv)\b",
            str(text),
            flags=re.IGNORECASE
        )
        if not file_names:
            return code

        requested = file_names[0]
        return re.sub(
            r'Path\("[^"\n]+\.(?:jsonl?|txt|csv)"\)',
            f'Path("{requested}")',
            code,
            count=1,
            flags=re.IGNORECASE
        )

    def derive_enhancement_decisions(self, text, program_kind, code):

        requirements = self.self_reviewer.extract_request_requirements(
            text,
            program_kind,
        )
        verified = [
            item["id"]
            for item in requirements
            if self.self_reviewer.requirement_passed(item, code)
        ]
        failed = [
            item["id"]
            for item in requirements
            if item["id"] not in verified
        ]
        lowered = str(text or "").lower()
        strict_output = "only output" in lowered
        improvements = [
            {
                "id": "failure_path_validation",
                "applied": "try:" in code or "while True" in code,
                "reason": "Keep invalid input inside a recoverable interaction path.",
            },
            {
                "id": "clean_exit",
                "applied": "exit" in code.lower() or "quit" in code.lower(),
                "reason": "Interactive programs should have a predictable exit path.",
            },
            {
                "id": "request_specific_structure",
                "applied": program_kind not in {"json_cli", "number_summary"},
                "reason": "Prefer a domain-specific implementation over a generic record template.",
            },
        ]
        return {
            "basis": "request_contract_and_verified_behavior",
            "verified_requirement_ids": verified,
            "failed_requirement_ids": failed,
            "improvements_considered": improvements,
            "strict_output": strict_output,
            "visible_after_code": False if strict_output else None,
            "policy": (
                "Add robustness and useful depth inside the requested program, but never add "
                "unrequested output sections or trade correctness for code length."
            ),
        }

    def quality_correction_contract(self, data):

        if not isinstance(data, dict) or data.get("retry_target") != "Code_brain":
            return {}
        direct = data.get("quality_correction", {})
        feedback = data.get("quality_feedback", {})
        request = data.get("retry_request", {})
        requirements = feedback.get("requirements", {}) if isinstance(feedback, dict) else {}
        contract = dict(direct) if isinstance(direct, dict) else {}
        contract.setdefault(
            "quality_score",
            feedback.get("quality_score") if isinstance(feedback, dict) else None,
        )
        contract.setdefault(
            "expected_program_kind",
            request.get("expected_program_kind") or requirements.get("expected_program_kind"),
        )
        contract.setdefault(
            "required_features",
            request.get("required_features") or requirements.get("requested_code_features", []),
        )
        contract.setdefault(
            "failed_requirements",
            request.get("failed_requirement_checks") or data.get("failed_requirements", []),
        )
        contract["force_regeneration"] = bool(
            contract.get("force_regeneration")
            or contract.get("quality_score") == 0
            or "wrong program kind" in str(request.get("problem", "")).lower()
        )
        return contract

    def select_program_functions(self, program_kind, code, text="", correction_contract=None):

        profile = self.function_selection_profiles.get(program_kind, {})
        required = list(profile.get("required_functions", []))
        function_aliases = {
            str(name): [str(alias) for alias in aliases]
            for name, aliases in profile.get("function_aliases", {}).items()
            if isinstance(aliases, list)
        }
        correction_contract = correction_contract or {}
        request_terms = set(re.findall(
            r"[a-z][a-z0-9_]{2,}",
            " ".join([
                str(text or ""),
                " ".join(str(item) for item in correction_contract.get("required_features", [])),
                " ".join(str(item) for item in correction_contract.get("failed_requirements", [])),
            ]).lower(),
        ))
        function_nodes = []
        call_graph = {}
        try:
            tree = ast.parse(code)
            function_nodes = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            defined = {node.name for node in function_nodes}
            for node in function_nodes:
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        if child.func.id in defined and child.func.id != node.name:
                            calls.append(child.func.id)
                call_graph[node.name] = list(dict.fromkeys(calls))
        except (SyntaxError, ValueError):
            defined = set()
        names_in_order = [node.name for node in function_nodes]
        required_candidates = {
            name: [name] + function_aliases.get(name, [])
            for name in required
        }
        resolved_required = {
            name: next(
                (candidate for candidate in candidates if candidate in defined),
                None,
            )
            for name, candidates in required_candidates.items()
        }
        function_scores = {}
        for name in defined:
            name_terms = set(name.lower().split("_"))
            score = len(name_terms.intersection(request_terms)) * 15
            if name == "main":
                score += 100
            if name in required or name in resolved_required.values():
                score += 120
            if call_graph.get(name):
                score += min(20, len(call_graph[name]) * 4)
            function_scores[name] = score

        selected = [name for name in resolved_required.values() if name]
        if not required:
            selected = [
                name
                for name, _ in sorted(
                    function_scores.items(),
                    key=lambda item: (item[1], item[0] == "main"),
                    reverse=True,
                )
            ]
        dependency_queue = list(selected)
        while dependency_queue:
            current = dependency_queue.pop(0)
            for dependency in call_graph.get(current, []):
                if dependency not in selected:
                    selected.append(dependency)
                    dependency_queue.append(dependency)
        selected_names = set(selected)
        selected = [name for name in names_in_order if name in selected_names]
        missing = [name for name, resolved in resolved_required.items() if not resolved]
        return {
            "program_kind": program_kind,
            "purpose": profile.get("purpose", "Fulfil the request contract."),
            "required_functions": required,
            "resolved_required_functions": resolved_required,
            "selected_functions": selected,
            "missing_functions": missing,
            "available_functions": sorted(defined),
            "function_scores": function_scores,
            "call_graph": call_graph,
            "selection_basis": [
                "program function profile",
                "request and failed-requirement terms",
                "AST call dependencies",
                "runnable entry point",
            ],
            "forbidden_substitutes": profile.get("forbidden_substitutes", []),
            "complete": bool(selected) and not missing,
        }

    def build_direct_python_program_result(
        self,
        text,
        terms,
        task_type,
        existing_code="",
        correction_contract=None,
    ):

        detected_kind = self.detect_direct_program_kind(
            text,
            task_type
        )
        existing_kind = self.detect_existing_program_kind(existing_code)
        lowered = str(text or "").lower()
        continuation_requested = bool(existing_code) and any(
            marker in lowered
            for marker in [
                "continue", "same", "previous", "you just wrote", "fix the",
                "improve the", "add to", "keep the existing",
            ]
        )
        correction_contract = correction_contract or {}
        expected_kind = correction_contract.get("expected_program_kind")
        program_kind = expected_kind or detected_kind
        if (
            continuation_requested
            and existing_kind
            and detected_kind in {"json_cli", "number_summary"}
            and not expected_kind
        ):
            program_kind = existing_kind

        code = self.build_direct_python_program_code(
            text,
            task_type,
            program_kind=program_kind,
        )
        code = self.apply_requested_file_name(code, text)
        recipe = self.choose_project_recipe(program_kind, text)
        enhancement_decisions = self.derive_enhancement_decisions(
            text,
            program_kind,
            code,
        )
        function_selection = self.select_program_functions(
            program_kind,
            code,
            text,
            correction_contract,
        )

        return {
            "brain": "Code_brain",
            "used_understanding_report": True,
            "used_memory_report": True,
            "language": "python",
            "task_type": task_type,
            "program_kind": program_kind,
            "output_mode": "code_only",
            "terms_used": terms,
            "confidence": 86,
            "matched_functions": len(function_selection["selected_functions"]),
            "selected": function_selection["selected_functions"] or [
                f"direct_python_{program_kind}"
            ],
            "function_selection": function_selection,
            "quality_correction_applied": bool(correction_contract),
            "quality_correction_contract": correction_contract,
            "assembly_plan": {
                "task_type": task_type,
                "program_kind": program_kind,
                "ordered_ids": [f"direct_python_{program_kind}"],
                "steps": [
                    "Build a program specification from the full request contract and prior code context.",
                    "Assemble request-specific behavior from verified standard-library components.",
                    "Run CodeSelfReviewer for syntax, placeholder, and main-guard checks.",
                    "Return final code instead of module names or draft helper variants."
                ],
                "composition_rules_used": [
                    {
                        "id": f"direct_python_{program_kind}",
                        "connection_type": "complete_program_template",
                        "score": 90
                    }
                ],
                "project_recipe_id": recipe.get("id"),
                "architecture": recipe.get("architecture", "single_file_cli"),
                "quality_gates": recipe.get("quality_gates", [
                    "syntax validation",
                    "request requirement coverage",
                    "persistence round trip",
                    "invalid input handling"
                ]),
                "data_files_used": [
                    "Code_function_selection_profiles.json",
                    "Code_project_recipes.json",
                    "Code_assembly_patterns.json",
                    "Code_composition_tables.json",
                    "Code_dependency_graph.json"
                ]
            },
            "dependencies_added": [],
            "composition_rules_used": [
                {
                    "id": f"direct_python_{program_kind}",
                    "connection_type": "complete_program_template",
                    "score": 90
                }
            ],
            "adapter_notes": [
                "Direct runnable program mode was used because the user requested code only.",
                f"Selected direct Python program kind: {program_kind}.",
                "Previous conversation code was detected and used as continuation context." if existing_code else "No previous code context was needed."
            ],
            "existing_code_detected": bool(existing_code),
            "existing_program_kind": existing_kind,
            "continuation_requested": continuation_requested,
            "continuation_preservation": {
                "previous_kind_preserved": bool(
                    continuation_requested and existing_kind == program_kind
                ),
                "previous_code_available": bool(existing_code),
                "strategy": (
                    "rebuild_known_program_from_merged_requirements"
                    if continuation_requested and existing_kind
                    else "request_contract_generation"
                ),
            },
            "match_details": [],
            "generated_code": code,
            "request_text": text,
            "generation_basis": enhancement_decisions,
            "project_recipe": {
                "id": recipe.get("id"),
                "kind": recipe.get("kind", program_kind),
                "architecture": recipe.get("architecture", "single_file_cli"),
                "acceptance_criteria": recipe.get("acceptance_criteria", [])
            },
            "missing": [],
            "needs_creative_brain": False,
            "creative_fallback": None,
            "needs_security": "api" in str(text).lower() or "url" in str(text).lower(),
            "suggested_next_brains": [
                "Security_brain",
                "Response_brain"
            ],
            "rules": [
                "When the user requests code only, return runnable code instead of modules, variants, placeholders, or planning structures."
            ]
        }

    def order_functions(
        self,
        functions
    ):

        unique = {}

        for func in functions:

            function_id = func.get(
                "id"
            )

            if function_id and function_id not in unique:
                unique[function_id] = func

        def sort_key(func):

            function_id = func.get(
                "id",
                ""
            )

            node = self.dependency_graph.get(
                function_id,
                {}
            )

            return (
                node.get(
                    "order_group",
                    50
                ),
                func.get(
                    "language",
                    ""
                ),
                func.get(
                    "category",
                    ""
                ),
                function_id
            )

        ordered = sorted(
            unique.values(),
            key=sort_key
        )

        return self.apply_dependency_order(
            ordered
        )

    def apply_dependency_order(
        self,
        functions
    ):

        by_id = {
            func.get("id"): func
            for func in functions
            if func.get("id")
        }

        visited = set()
        ordered = []

        def visit(func):

            function_id = func.get(
                "id"
            )

            if not function_id or function_id in visited:
                return

            node = self.dependency_graph.get(
                function_id,
                {}
            )

            for required_id in node.get(
                "requires",
                []
            ):

                required = by_id.get(
                    required_id
                )

                if required:
                    visit(
                        required
                    )

            visited.add(
                function_id
            )

            ordered.append(
                func
            )

        for func in functions:
            visit(
                func
            )

        return ordered

    def add_missing_dependencies(
        self,
        selected,
        language
    ):

        expanded = list(selected)
        selected_ids = {
            item.get("id")
            for item in expanded
            if item.get("id")
        }
        added = []

        for item in list(selected):

            node = self.dependency_graph.get(
                item.get(
                    "id",
                    ""
                ),
                {}
            )

            for required_id in node.get(
                "requires",
                []
            ):

                if required_id in selected_ids:
                    continue

                required_item = self.code_by_id.get(
                    required_id
                )

                if not required_item:
                    continue

                if (
                    language
                    and required_item.get(
                        "language"
                    ) != language
                ):
                    continue

                expanded.append(
                    required_item
                )

                selected_ids.add(
                    required_id
                )

                added.append(
                    required_id
                )

        return expanded, added

    def find_composition_rules(
        self,
        ordered
    ):

        ordered_ids = [
            item.get("id")
            for item in ordered
            if item.get("id")
        ]

        id_set = set(
            ordered_ids
        )

        rules = []
        connection_notes = []

        for rule in self.composition_tables.values():

            rule_order = rule.get(
                "order",
                []
            )

            if len(rule_order) < 2:
                continue

            if set(rule_order).issubset(id_set):

                rules.append(
                    rule
                )

                connection_notes.extend(
                    rule.get(
                        "adapter_notes",
                        []
                    )[:2]
                )

            if len(rules) >= 10:
                break

        if not rules:

            for first, second in zip(
                ordered,
                ordered[1:]
            ):

                first_node = self.dependency_graph.get(
                    first.get(
                        "id",
                        ""
                    ),
                    {}
                )

                second_node = self.dependency_graph.get(
                    second.get(
                        "id",
                        ""
                    ),
                    {}
                )

                first_category = first_node.get(
                    "category",
                    first.get("category", "general")
                )

                second_category = second_node.get(
                    "category",
                    second.get("category", "general")
                )

                dynamic_rule = {
                    "id": f"dynamic_{first.get('id')}__{second.get('id')}",
                    "connection_type": self.infer_connection_type(
                        first_category,
                        second_category
                    ),
                    "score": 72
                }

                rules.append(
                    dynamic_rule
                )

                connection_notes.append(
                    "Connect adjacent snippets by passing explicit parameters and return values."
                )

                if len(rules) >= 6:
                    break

        return rules, list(dict.fromkeys(connection_notes))

    def infer_connection_type(
        self,
        first_category,
        second_category
    ):

        categories = {
            first_category,
            second_category
        }

        if categories & {
            "json_load",
            "json_save",
            "file_read",
            "file_write",
            "csv_read",
            "csv_write"
        }:
            return "file_data_flow"

        if categories & {
            "database",
            "sql"
        }:
            return "database_flow"

        if categories & {
            "api",
            "server",
            "route"
        }:
            return "web_request_flow"

        if categories & {
            "login",
            "password",
            "token"
        }:
            return "security_flow"

        if categories & {
            "game",
            "player",
            "enemy",
            "inventory",
            "score"
        }:
            return "game_state_flow"

        return "function_flow"

    def build_adaptation_notes(
        self,
        ordered,
        existing_code
    ):

        notes = []
        filtered = []

        existing_lower = existing_code.lower()

        for item in ordered:

            name = item.get(
                "name",
                ""
            )

            code = item.get(
                "code",
                ""
            )

            duplicate = (
                existing_code
                and name
                and name.lower() in existing_lower
            )

            if duplicate:
                notes.append(
                    f"Existing code already appears to contain {name}; avoid adding a duplicate."
                )
                continue

            if existing_code and code:
                if "import " in code or "from " in code:
                    notes.append(
                        "Move imports to the top of the existing file before merging."
                    )

            filtered.append(
                item
            )

        return filtered, list(dict.fromkeys(notes))

    def choose_assembly_pattern(
        self,
        language,
        ordered_ids
    ):

        if not language:
            return None

        id_set = set(
            ordered_ids
        )

        best_pattern = None
        best_score = 0

        for pattern in self.assembly_patterns.values():

            if pattern.get(
                "language"
            ) != language:
                continue

            steps = set(
                pattern.get(
                    "steps",
                    []
                )
            )

            overlap = len(
                id_set & steps
            )

            if overlap > best_score:
                best_score = overlap
                best_pattern = pattern

        if best_score == 0:
            return None

        return {
            "id": best_pattern.get("id"),
            "name": best_pattern.get("name"),
            "quality_score": best_pattern.get("quality_score"),
            "matched_steps": best_score
        }

    def build_assembly_plan(
        self,
        selected,
        language,
        task_type,
        memory_terms,
        existing_code
    ):

        expanded, dependencies_added = self.add_missing_dependencies(
            selected,
            language
        )

        ordered = self.order_functions(
            expanded
        )

        ordered, adaptation_notes = self.build_adaptation_notes(
            ordered,
            existing_code
        )

        composition_rules, connection_notes = self.find_composition_rules(
            ordered
        )

        ordered_ids = [
            item.get("id")
            for item in ordered
            if item.get("id")
        ]

        pattern = self.choose_assembly_pattern(
            language,
            ordered_ids
        )

        steps = []

        for index, item in enumerate(
            ordered,
            start=1
        ):

            node = self.dependency_graph.get(
                item.get(
                    "id",
                    ""
                ),
                {}
            )

            steps.append({
                "step": index,
                "id": item.get("id"),
                "name": item.get("name"),
                "language": item.get("language"),
                "category": item.get("category"),
                "order_group": node.get("order_group", 50),
                "requires": node.get("requires", []),
                "glue_strategy": node.get(
                    "glue_strategy",
                    "connect_by_function_call_or_return_value"
                )
            })

        return {
            "task_type": task_type,
            "ordered_ids": ordered_ids,
            "steps": steps,
            "dependencies_added": dependencies_added,
            "composition_rules_used": [
                {
                    "id": rule.get("id"),
                    "connection_type": rule.get("connection_type"),
                    "score": rule.get("score")
                }
                for rule in composition_rules
            ],
            "connection_notes": connection_notes,
            "adaptation_notes": adaptation_notes,
            "memory_terms_used": memory_terms[:20],
            "assembly_pattern": pattern,
            "data_files_used": [
                "Code_dependency_graph.json",
                "Code_composition_tables.json",
                "Code_assembly_patterns.json",
                "Code_statistics.json"
            ]
        }, ordered

    def run_creative_fallback(
        self,
        data,
        needs_creative
    ):

        if not needs_creative:
            return None

        try:

            from Creative_brain import CreativeBrain

            creative_brain = CreativeBrain()

            return creative_brain.create_code(
                data
            )

        except Exception as error:

            return {
                "brain": "Creative_brain",
                "error": str(error),
                "purpose": "code_fallback"
            }

    def update_statistics(
        self,
        selected
    ):

        for item in selected:

            function_id = item.get(
                "id",
                ""
            )

            if not function_id:
                continue

            stats = self.statistics.get(
                function_id,
                {}
            )

            stats["times_used"] = stats.get(
                "times_used",
                0
            ) + 1

            stats.setdefault(
                "success_rate",
                80
            )

            stats["last_used_utc"] = datetime.now(
                timezone.utc
            ).isoformat()

            self.statistics[function_id] = stats

        if selected:
            self.save_statistics()

    def process(
        self,
        data
    ):

        if not isinstance(data, dict):
            data = {
                "original_text": str(data)
            }

        report = self.get_understanding_report(
            data
        )

        memory_report = self.get_memory_report(
            data
        )

        memory_terms = self.collect_memory_terms(
            memory_report
        )

        existing_code = self.extract_existing_code(
            data
        )

        text = self.extract_text(
            data,
            report
        )
        text = self.merge_continuation_request(
            text,
            memory_report,
        )

        scanner_articles = (
            scanner_evidence(
                data,
                limit=8,
                collections={"code", "general", "trusted_knowledge"}
            )
            if scanner_evidence is not None
            else []
        )

        retry_request = data.get("retry_request", {})
        retry_instructions = data.get("retry_instructions", [])
        correction_contract = self.quality_correction_contract(data)
        if (
            data.get("retry_target") == "Code_brain"
            and isinstance(retry_request, dict)
            and retry_instructions
        ):
            correction_details = [
                retry_request.get("problem"),
                *data.get("failed_requirements", []),
                *retry_instructions,
            ]
            correction_details = list(dict.fromkeys(
                str(item).strip()
                for item in correction_details
                if str(item or "").strip()
            ))
            text = (
                f"{text}\n\nQuality correction requirements:\n- "
                + "\n- ".join(correction_details)
            )

        terms = self.collect_terms(
            data,
            report,
            text
        )

        for memory_term in memory_terms:

            clean_memory_term = re.sub(
                r"[^a-zA-Z0-9_\-\+\.#\s]",
                " ",
                memory_term
            )

            clean_memory_term = re.sub(
                r"\s+",
                " ",
                clean_memory_term
            ).strip().lower()

            if (
                clean_memory_term
                and clean_memory_term not in terms
                and clean_memory_term not in GENERIC_CODE_TERMS
            ):
                terms.append(
                    clean_memory_term
                )

        language = self.detect_language(
            terms,
            text
        )

        task_type = self.detect_task_type(
            terms,
            text
        )

        library_context = self.library_catalog.search(
            [text, *terms],
            limit=12,
            language="python" if language in [None, "python"] else language
        )
        expanded_terms = list(terms)
        for match in library_context[:8]:
            function_data = match.get("function", {})
            for term in [
                function_data.get("library"),
                function_data.get("function"),
                function_data.get("qualified_name"),
                *function_data.get("tags", [])[:8]
            ]:
                clean_term = str(term or "").strip().lower()
                if clean_term and clean_term not in expanded_terms:
                    expanded_terms.append(clean_term)

        if self.is_code_analysis_request(
            text,
            report
        ):

            analysis_text = self.extract_analysis_source_text(
                data,
                report,
                text
            )

            explanation = self.code_explainer.explain(
                analysis_text,
                existing_code,
                language
            )

            result = {
                "brain": "Code_brain",
                "used_understanding_report": bool(report),
                "mode": "code_analysis",
                "language": explanation.get("language"),
                "task_type": "code_analysis",
                "confidence": explanation.get("confidence", 80),
                "code_analyzed": explanation.get("code_analyzed"),
                "code_explanation": explanation.get("explanation"),
                "summary": explanation.get("summary"),
                "answer": explanation.get("answer"),
                "needs_security": False,
                "suggested_next_brains": [
                    "Response_brain"
                ],
                "rules": [
                    "When the user asks to analyze code, explain the pasted code instead of generating new code.",
                    "Use AST-based explanation for Python when possible.",
                    "Return a screen-ready answer plus structured code_explanation."
                ]
            }
            result["scanner_knowledge_used"] = scanner_articles
            result["library_api_context"] = [
                {
                    "library": item["function"].get("library"),
                    "function": item["function"].get("function"),
                    "qualified_name": item["function"].get("qualified_name"),
                    "signature": item["function"].get("signature"),
                    "source": item["function"].get("source", {}),
                }
                for item in library_context[:8]
            ]
            return result

        code_only = self.is_code_only_request(
            text
        )

        direct_python_requested = self.is_direct_runnable_python_request(
            text,
            report
        )

        skeleton_requested = self.is_skeleton_request(
            text
        )

        existing_project_files = self.extract_existing_project_files(
            data,
            existing_code
        )

        if (
            not skeleton_requested
            and self.is_advanced_project_request(
                text,
                report,
                existing_project_files
            )
        ):
            return self.finalize_code_result(
                self.build_advanced_project_result(
                    text,
                    terms,
                    task_type,
                    report,
                    existing_project_files
                ),
                scanner_articles,
                library_context
            )

        if self.is_python_text_rpg_request(
            text,
            terms,
            language,
            task_type
        ):
            return self.finalize_code_result(
                self.build_python_text_rpg_result(
                    text,
                    terms
                ),
                scanner_articles,
                library_context
            )

        if (
            not skeleton_requested
            and (
                direct_python_requested
                or language in [None, "python"]
            )
            and (
                code_only
                or direct_python_requested
                or "python" in str(text).lower()
                or report.get("intent") == "code_generation"
            )
        ):
            return self.finalize_code_result(
                self.build_direct_python_program_result(
                    text,
                    terms,
                    task_type,
                    existing_code,
                    correction_contract=correction_contract,
                ),
                scanner_articles,
                library_context
            )

        matches = self.search_code(
            expanded_terms,
            language,
            task_type
        )

        selected_results = matches[:8]

        selected = [
            result["item"]
            for result in selected_results
        ]

        assembly_plan, assembled = self.build_assembly_plan(
            selected,
            language,
            task_type,
            memory_terms,
            existing_code
        )

        generated_code = self.build_code(
            assembled
        )

        missing = []

        if not selected:
            missing.append("No matching code snippets found")

        if not language:
            missing.append("Programming language was not clearly detected")

        confidence = 0

        if selected_results:
            confidence = min(
                selected_results[0]["score"] * 8,
                100
            )

        if not language:
            confidence = min(
                confidence,
                35
            )

        if not terms:
            confidence = 0

        confidence = round(
            confidence,
            2
        )

        needs_creative = (
            len(assembled) == 0
            or confidence < 45
            or language is None
        )

        needs_security = any(
            term in terms
            for term in [
                "password",
                "token",
                "encrypt",
                "login",
                "security",
                "shell",
                "subprocess"
            ]
        )

        creative_fallback = self.run_creative_fallback(
            data,
            needs_creative
        )

        self.update_statistics(
            assembled
        )

        result = {

            "brain":
                "Code_brain",

            "used_understanding_report":
                bool(report),

            "used_memory_report":
                bool(memory_report),

            "language":
                language,

            "task_type":
                task_type,

            "terms_used":
                terms,

            "library_terms_used": [
                term for term in expanded_terms
                if term not in terms
            ][:40],

            "confidence":
                confidence,

            "matched_functions":
                len(assembled),

            "selected":
                [
                    x.get(
                        "name",
                        "unknown"
                    )
                    for x in assembled
                ],

            "assembly_plan":
                assembly_plan,

            "dependencies_added":
                assembly_plan.get(
                    "dependencies_added",
                    []
                ),

            "composition_rules_used":
                assembly_plan.get(
                    "composition_rules_used",
                    []
                ),

            "adapter_notes":
                assembly_plan.get(
                    "adaptation_notes",
                    []
                ),

            "existing_code_detected":
                bool(existing_code),

            "match_details": [
                {
                    "id": result["item"].get("id"),
                    "name": result["item"].get("name"),
                    "language": result["item"].get("language"),
                    "category": result["item"].get("category"),
                    "score": result["score"],
                    "matched_terms": result["matched_terms"]
                }
                for result in selected_results
            ],

            "generated_code":
                generated_code,

            "missing":
                missing,

            "needs_creative_brain":
                needs_creative,

            "creative_fallback":
                creative_fallback,

            "needs_security":
                needs_security,

            "suggested_next_brains": [
                brain_name
                for brain_name, enabled in [
                    ("Creative_brain", needs_creative),
                    ("Security_brain", needs_security),
                    ("Technology_brain", language is None),
                    ("Response_brain", True)
                ]
                if enabled
            ],

            "rules": [
                "Use the Understanding_brain report as the main input.",
                "Search local code snippets before asking Creative_brain.",
                "If local snippets are weak or missing, route missing parts to Creative_brain.",
                "Route security-sensitive code to Security_brain.",
                "Do not execute generated code here; only assemble and report code."
            ]
        }

        return self.finalize_code_result(
            result,
            scanner_articles,
            library_context
        )


brain = CodeBrain()
