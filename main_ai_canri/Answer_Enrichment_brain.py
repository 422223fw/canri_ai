"""Build useful, request-aware additions for Canri's final answer.

This brain never replaces a specialist result. It prepares a small visible
afterword only when the user's output contract permits one. Strict requests
such as "only output code" always win over enrichment.
"""

import ast
import re


class AnswerEnrichmentBrain:

    INTERNAL_ONLY = True

    def get_report(self, data):
        if not isinstance(data, dict):
            return {}
        report = data.get("understanding")
        return report if isinstance(report, dict) else data

    def get_results(self, data):
        if not isinstance(data, dict):
            return {}
        results = data.get("results", {})
        return results if isinstance(results, dict) else {}

    def user_text(self, data, report):
        for source in [report, data if isinstance(data, dict) else {}]:
            for key in ["original_text", "corrected_text", "text", "prompt", "goal"]:
                value = source.get(key) if isinstance(source, dict) else None
                if value:
                    return str(value)
        return ""

    def strict_output(self, report, text):
        contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
        constraints = contract.get("output_constraints", {}) if isinstance(contract, dict) else {}
        enhancement = contract.get("enhancement_policy", {}) if isinstance(contract, dict) else {}
        lowered = str(text).lower()
        return bool(
            constraints.get("only_output")
            or enhancement.get("strict_output")
            or any(marker in lowered for marker in [
                "only output", "only return", "code only",
                "not a plan or explanation",
                "without explanation", "no explanation",
            ])
        )

    def code_summary(self, code_result):
        code = str(code_result.get("generated_code") or "")
        program_kind = str(code_result.get("program_kind") or "program").replace("_", " ")
        functions = []
        classes = []
        imports = []
        has_main = False
        try:
            tree = ast.parse(code)
            functions = [
                node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "relative import")
            has_main = any(name == "main" for name in functions)
        except (SyntaxError, ValueError):
            pass

        details = [f"This is a runnable {program_kind} implementation."]
        visible_functions = [name for name in functions if name != "main"][:8]
        if visible_functions:
            details.append(
                "Its main operations are implemented by: "
                + ", ".join(f"`{name}()`" for name in visible_functions)
                + "."
            )
        if classes:
            details.append("It defines: " + ", ".join(f"`{name}`" for name in classes[:5]) + ".")
        if imports:
            details.append("It uses: " + ", ".join(f"`{name}`" for name in imports[:6]) + ".")
        if has_main:
            details.append("`main()` owns the command loop and program entry point.")
        return " ".join(details)

    def correction_summary(self, code_result):
        changes = []
        review = code_result.get("self_review", {})
        if isinstance(review, dict):
            changes.extend(str(item) for item in review.get("changes", []) if str(item).strip())

        correction = code_result.get("quality_correction_contract", {})
        if isinstance(correction, dict) and code_result.get("quality_correction_applied"):
            failed = [
                str(item).strip()
                for item in correction.get("failed_requirements", [])
                if str(item).strip()
            ]
            if failed:
                changes.append("The correction focused on: " + "; ".join(failed[:6]))
            if correction.get("expected_program_kind"):
                changes.append(
                    "The program type was kept aligned with `"
                    + str(correction["expected_program_kind"])
                    + "`."
                )

        if code_result.get("continuation_requested"):
            preservation = code_result.get("continuation_preservation", {})
            if isinstance(preservation, dict) and preservation.get("previous_kind_preserved"):
                changes.append("The previous program type was preserved while applying the requested changes.")
        return list(dict.fromkeys(changes))[:8]

    def verification_summary(self, code_result):
        scorecard = code_result.get("code_quality_scorecard", {})
        review = code_result.get("self_review", {})
        after = review.get("after", {}) if isinstance(review, dict) else {}
        alignment = review.get("request_alignment", {}) if isinstance(review, dict) else {}
        metrics = code_result.get("code_metrics", {})
        items = []
        if isinstance(scorecard, dict) and scorecard:
            items.append(
                f"Quality score: {scorecard.get('overall_score', 0)}/100 "
                f"({scorecard.get('grade', 'ungraded')})."
            )
        if isinstance(metrics, dict) and metrics.get("syntax_valid") is not None:
            items.append("Python syntax: valid." if metrics.get("syntax_valid") else "Python syntax: invalid.")
        if isinstance(alignment, dict) and alignment.get("coverage") is not None:
            items.append(f"Request coverage: {alignment.get('coverage')}%.")
        if isinstance(after, dict) and after.get("warnings"):
            items.append(f"Remaining review warnings: {len(after.get('warnings', []))}.")
        elif after:
            items.append("No blocking self-review warning remains.")
        return items

    def render_code_suffix(self, code_result):
        sections = []
        delivery = code_result.get("delivery_explanation", {})
        delivery = delivery if isinstance(delivery, dict) else {}
        summary = str(delivery.get("summary") or self.code_summary(code_result)).strip()
        if summary:
            sections.append("Explanation\n" + summary)

        features = [
            str(item).strip()
            for item in delivery.get("implemented_features", [])
            if str(item).strip()
        ]
        if features:
            sections.append(
                "What the program includes\n"
                + "\n".join(f"- {item}" for item in features[:12])
            )

        structure = [
            str(item).strip()
            for item in delivery.get("structure", [])
            if str(item).strip()
        ]
        if structure:
            sections.append(
                "Structure\n" + "\n".join(f"- {item}" for item in structure[:12])
            )

        data_files = [
            str(item).strip()
            for item in delivery.get("data_files", [])
            if str(item).strip()
        ]
        if data_files:
            sections.append(
                "Data files\n" + "\n".join(f"- `{item}`" for item in data_files[:8])
            )

        changes = self.correction_summary(code_result)
        if changes:
            sections.append("What changed\n" + "\n".join(f"- {item}" for item in changes))

        verification = self.verification_summary(code_result)
        if verification:
            sections.append("Verification\n" + "\n".join(f"- {item}" for item in verification))

        run_instruction = str(delivery.get("run_instruction") or "").strip()
        if run_instruction:
            sections.append("Run\n" + run_instruction)
        elif code_result.get("generated_code") and code_result.get("language") == "python":
            sections.append("Run\nSave the code as a `.py` file and run `python filename.py`.")

        limitations = [
            str(item).strip()
            for item in delivery.get("limitations", [])
            if str(item).strip()
        ]
        if limitations:
            sections.append(
                "Remaining notes\n" + "\n".join(f"- {item}" for item in limitations[:6])
            )

        suggestions = self.code_improvement_suggestions(code_result, delivery)
        if suggestions:
            sections.append(
                "Useful next improvements\n"
                + "\n".join(f"- {item}" for item in suggestions)
            )
        return "\n\n".join(sections).strip()

    def code_improvement_suggestions(self, code_result, delivery):
        suggestions = []
        code = str(code_result.get("generated_code") or "").lower()
        project_files = code_result.get("project_files", {})
        if code and "def test_" not in code and not project_files:
            suggestions.append("Add focused tests for the main commands and invalid-input paths.")
        if any(name.endswith((".json", ".jsonl", ".db", ".sqlite")) for name in delivery.get("data_files", [])):
            suggestions.append("Add backup and recovery behavior before replacing persistent data.")
        if "input(" in code:
            suggestions.append("Add graceful handling for `Ctrl+C` and end-of-file input if the program will be used regularly.")
        if project_files and not any(str(path).lower().endswith("readme.md") for path in project_files):
            suggestions.append("Add a short README with setup, run, and test commands.")
        return list(dict.fromkeys(suggestions))[:3]

    def process(self, data):
        report = self.get_report(data)
        results = self.get_results(data)
        text = self.user_text(data, report)
        strict = self.strict_output(report, text)
        code_result = results.get("Code_brain", {})
        safety = results.get("Security_brain", {})
        blocked = isinstance(safety, dict) and bool(safety.get("blocked"))

        suffix = ""
        additions = []
        if strict:
            additions.append("No visible addition: the user requested a strict output format.")
        elif blocked:
            additions.append("No visible addition: the safety response must stay focused.")
        elif isinstance(code_result, dict) and (
            code_result.get("generated_code") or code_result.get("project_files")
        ):
            suffix = self.render_code_suffix(code_result)
            additions.extend([
                "explain the delivered code",
                "describe verified corrections when available",
                "show verification status",
                "include a practical run instruction",
            ])

        return {
            "brain": "Answer_Enrichment_brain",
            "internal_only": True,
            "strict_output": strict,
            "allowed": bool(suffix) and not strict and not blocked,
            "visible_suffix": suffix,
            "addition_decisions": additions,
            "confidence": 96 if strict or suffix else 80,
            "rules": [
                "Never replace the specialist answer.",
                "Never violate an explicit output constraint.",
                "Add only request-relevant information with concrete value.",
                "Do not expose internal plans, retries, or brain reports.",
            ],
        }


brain = AnswerEnrichmentBrain()
