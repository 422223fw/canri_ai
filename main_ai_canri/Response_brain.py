"""
Response_brain.py
Canri AI

Turns many brain outputs into one clear answer for the user.
This brain does not invent new facts. It selects, filters, formats,
and presents the best available result from the Canri pipeline.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json
from Canri_identity import load_canri_identity, release_version


DATA_DIR = Path(__file__).parent / "data"
STATS_FILE = DATA_DIR / "Response_statistics.json"


BLOCKED_SAFETY_HINTS = {
    "self-harm": (
        "אני לא יכול לעזור עם הוראות לפגיעה עצמית. "
        "אם אתה או מישהו לידך בסכנה מיידית, כדאי לפנות עכשיו למוקד חירום מקומי "
        "או לאדם קרוב שאתה סומך עליו."
    ),
    "weapons": "אני לא יכול לעזור בהכנה או שימוש בנשק, חומרי נפץ, או פעולה מסוכנת.",
    "illegal": "אני לא יכול לעזור בפעולה לא חוקית או מזיקה. אפשר לעזור בכיוון בטוח וחוקי.",
    "medical": "בנושא רפואי רגיש אני לא אציג דבר כאמת בלי מקור חזק. כדאי להתייעץ עם גורם רפואי מוסמך.",
    "general": "אני לא יכול לעזור בחלק המסוכן של הבקשה, אבל אפשר להמשיך בכיוון בטוח."
}

INTERNAL_ONLY_BRAINS = {
    "Manager_brain",
    "Planner_brain",
    "Reasoning_brain",
    "Quality_Control_brain",
    "Fact_Check_brain",
    "Learning_brain",
    "Memory_brain",
    "Collaboration_brain",
    "Nervous_system_brain",
    "LLM_bridge_brain",
}


class ResponseBrain:

    def __init__(self):

        self.statistics = self.load_json(STATS_FILE, {})

        print("Response Brain Loaded")

    # ---------- loading ----------

    def load_json(self, path, default):

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):

        atomic_write_json(STATS_FILE, self.statistics)

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "general",
                "intent": "question"
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if "main_topic" in data or "intent" in data:
            return data

        return {}

    def get_results(self, data):

        if not isinstance(data, dict):
            return {}

        results = data.get("results")

        if isinstance(results, dict):
            return results

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            previous = manager_context.get("previous_results")
            if isinstance(previous, dict):
                return previous

        return {}

    def get_cognitive_workspace(self, data):

        if not isinstance(data, dict):
            return {}
        workspace = data.get("cognitive_workspace", {})
        if isinstance(workspace, dict):
            return workspace
        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            workspace = manager_context.get("cognitive_workspace", {})
            return workspace if isinstance(workspace, dict) else {}
        return {}

    def get_dictionary_context(self, data):

        if not isinstance(data, dict):
            return {}

        dictionary = data.get("dictionary")
        if isinstance(dictionary, dict):
            return dictionary

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            dictionary = manager_context.get("dictionary")
            if isinstance(dictionary, dict):
                return dictionary

        return {}

    def extract_user_text(self, data, report):

        if isinstance(data, str):
            return data

        candidates = []
        if isinstance(data, dict):
            for key in ["original_text", "user_message", "question", "text", "goal", "corrected_text"]:
                value = data.get(key)
                if value:
                    candidates.append(str(value).strip())

        for key in ["original_text", "corrected_text", "text"]:
            value = report.get(key)
            if value:
                candidates.append(str(value).strip())

        # The same request is present in several shared-context fields. Joining
        # them made short greetings look like long research prompts and inflated
        # keyword scores. Preserve one complete user message instead.
        return next((value for value in candidates if value), "")

    def complete_understanding_report(self, report, user_text):
        """Upgrade legacy partial reports through the central understanding brain."""

        current = report if isinstance(report, dict) else {}
        if not str(user_text or "").strip():
            return current
        contract = current.get("request_contract")
        if isinstance(contract, dict) and contract and current.get("routing_hints"):
            return current
        try:
            from Understanding_brain import brain as understanding_brain

            parsed = understanding_brain.process(str(user_text))
        except Exception:
            return current
        if not isinstance(parsed, dict):
            return current
        merged = dict(parsed)
        for key, value in current.items():
            if key == "request_contract" and not value:
                continue
            if value is not None:
                merged[key] = value
        return merged

    def user_focus_terms(self, text):

        stop_words = {
            "the", "and", "for", "with", "what", "how", "why", "when",
            "where", "who", "is", "are", "was", "were", "this", "that",
            "explain", "check", "reliable", "information", "local",
            "knowledge", "available", "use", "used", "if", "you", "your"
        }

        terms = []

        for word in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", str(text).lower()):
            if word not in stop_words and word not in terms:
                terms.append(word)

        return terms[:12]

    def rank_items_by_focus(self, items, focus_terms):

        if not focus_terms:
            return items

        def score(item):
            if isinstance(item, dict):
                text = " ".join(str(value) for value in item.values())
            else:
                text = str(item)
            lowered = text.lower()
            total = 0
            for term in focus_terms:
                total += lowered.count(term)
                if lowered.startswith(term):
                    total += 6
                if term in lowered[:120]:
                    total += 2
            return total

        return sorted(items, key=score, reverse=True)

    def is_capability_question(self, text, report=None):

        report = report if isinstance(report, dict) else {}
        return str(report.get("intent", "")).casefold() == "capability_question"

    def capability_answer(self):

        identity = load_canri_identity()
        capabilities = identity.get("capabilities", {}) if isinstance(identity, dict) else {}
        core = capabilities.get("core", []) if isinstance(capabilities, dict) else []
        feature_lines = [str(item) for item in core[:6] if str(item).strip()]
        feature_text = "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(feature_lines, start=1)
        )
        if not feature_text:
            feature_text = (
                "1. Answer questions and explain topics.\n"
                "2. Plan projects and generate code.\n"
                "3. Use specialist brains and local knowledge."
            )

        return (
            f"Canri AI {release_version()} can help with several things inside this project:\n\n"
            f"{feature_text}\n\n"
            "A good test prompt is: Create a simple Python inventory system."
        )

    def dictionary_answer(self, text, dictionary):

        if not isinstance(dictionary, dict) or not dictionary.get("available"):
            return None

        lowered = str(text).lower()
        product_matches = dictionary.get("product_matches", [])
        company_matches = dictionary.get("company_matches", [])
        entries = dictionary.get("entries", [])

        if product_matches and any(
            phrase in lowered
            for phrase in ["who makes", "what is", "who made", "company", "product"]
        ):
            product = product_matches[0]
            name = product.get("name") or product.get("id")
            company = product.get("company")
            category = product.get("category")
            description = product.get("description")

            answer = f"{name} is"
            if category:
                answer += f" a {category}"
            if company:
                answer += f" made by {company}"
            answer += "."

            if description:
                answer += f" {description}"

            return answer

        if company_matches and any(
            phrase in lowered
            for phrase in ["what is", "who is", "company", "products"]
        ):
            company = company_matches[0]
            name = company.get("name") or company.get("id")
            description = company.get("description") or f"{name} is a company."
            products = company.get("products", [])[:6]

            if products:
                description += " Known products include " + ", ".join(products) + "."

            return description

        weak_words = {
            "general",
            "question",
            "language",
            "request",
            "what",
            "who",
            "how",
            "why"
        }
        strong_entries = [
            entry
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("word")
            and entry.get("word") not in weak_words
            and entry.get("meanings")
        ]

        if strong_entries and any(
            phrase in lowered
            for phrase in ["what is", "what are", "explain", "define", "מה זה"]
        ):
            entry = strong_entries[0]
            word = entry.get("word")
            meaning = entry.get("meanings", [""])[0]
            connections = entry.get("connections", [])[:5]
            answer = f"{word.capitalize()} means: {meaning}"

            if connections:
                answer += " Related ideas: " + ", ".join(connections) + "."

            return answer

        return None

    def is_action_request(self, report):

        if not isinstance(report, dict):
            return False

        requested_action = report.get(
            "requested_action",
            {}
        )

        if isinstance(requested_action, dict) and requested_action.get("is_action_request"):
            return True

        contract = report.get("request_contract", {})
        return bool(
            isinstance(contract, dict)
            and (contract.get("action") or contract.get("action_kind"))
        )

    def is_definition_or_explanation_request(self, text, report):

        intent = str(report.get("intent", "")).lower()
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        action = str(contract.get("action") or "").casefold()
        action_kind = str(contract.get("action_kind") or "").casefold()
        return intent in {"question", "research"} or action in {
            "explain", "define", "research", "verify"
        } or action_kind in {"explain", "research", "question"}

    def is_greeting(self, text, report=None):

        report = report if isinstance(report, dict) else {}
        if str(report.get("intent", "")).casefold() != "greeting":
            return False
        if self.is_action_request(report):
            return False

        # A one-word greeting must remain conversational even if an upstream
        # retrieval match accidentally added a specialist route.
        normalized = re.sub(r"[^a-z\u0590-\u05FF]+", " ", str(text or "").casefold()).strip()
        if normalized in {"hello", "hi", "hey", "shalom", "שלום", "היי", "הי"}:
            return True

        substantive_routes = set(self.routed_brains(report)).difference({
            "Response_brain", "Language_brain", "Emotion_brain",
            "Memory_brain", "Understanding_brain",
        })
        return not substantive_routes

    def greeting_answer(self, text=""):

        if re.search(r"[\u0590-\u05FF]", str(text or "")):
            return "שלום, אני Canri. כן, אשמח לעזור. מה תרצה לעשות?"

        return "Hello, I am Canri. Yes, I would be glad to help. What would you like to do?"

    # ---------- safety ----------

    def safety_status(self, results):

        security = results.get("Security_brain", {})
        fact_check = results.get("Fact_Check_brain", {})

        blocked = False
        warnings = []
        reason = "general"
        risk_level = 0

        if isinstance(security, dict):
            risk_level = security.get("risk_level", 0) or 0
            warnings.extend(security.get("warnings", []))

            if security.get("safe") is False or risk_level >= 70:
                blocked = True

            warning_text = " ".join(str(item).lower() for item in warnings)
            blocked_items = " ".join(str(item).lower() for item in security.get("blocked_items", []))
            combined = f"{warning_text} {blocked_items}"

            if "self" in combined or "suicide" in combined or "להתאבד" in combined:
                reason = "self-harm"
            elif "weapon" in combined or "explosive" in combined or "bomb" in combined:
                reason = "weapons"
            elif "illegal" in combined or "malware" in combined or "phishing" in combined:
                reason = "illegal"
            elif "medical" in combined or "medicine" in combined:
                reason = "medical"

        if isinstance(fact_check, dict):
            if fact_check.get("needs_research") and fact_check.get("topic_risk", {}).get("level") == "high":
                warnings.append("High-risk factual answer needs stronger verification")

        return {
            "blocked": blocked,
            "reason": reason,
            "risk_level": risk_level,
            "warnings": list(dict.fromkeys(warnings))
        }

    def quality_status(self, results):

        quality = results.get("Quality_Control_brain", {})

        if not isinstance(quality, dict):
            return {
                "available": False,
                "passed": None,
                "score": None,
                "issues": []
            }

        return {
            "available": True,
            "passed": quality.get("passed"),
            "score": quality.get("quality_score"),
            "needs_retry": quality.get("needs_retry"),
            "issues": quality.get("issues", [])[:5],
            "retry_requests": quality.get("retry_requests", [])[:5]
        }

    # ---------- selection ----------

    def routed_brains(self, report):

        if not isinstance(report, dict):
            return []
        central_domains = {
            str(item.get("domain") if isinstance(item, dict) else item).casefold()
            for item in report.get("central_domains", [])
            if str(item.get("domain") if isinstance(item, dict) else item).strip()
        }
        routes = []
        for item in report.get("semantic_domain_profiles", []):
            if not isinstance(item, dict):
                continue
            domain = str(item.get("domain") or "").casefold()
            if central_domains and domain not in central_domains:
                continue
            routes.append(str(item.get("brain") or ""))
            routes.extend(str(brain) for brain in item.get("supporting_brains", []) if brain)
        routes.extend(str(brain) for brain in report.get("routing_hints", []) if brain)
        return list(dict.fromkeys(
            brain for brain in routes if brain.endswith("_brain")
        ))

    def result_score(self, brain_name, result, route_rank=None):

        if not isinstance(result, dict):
            return 0

        if result.get("error") or result.get("skipped"):
            return -20

        score = 20

        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            score += confidence * 0.45

        if result.get("verified") is True:
            score += 12

        if result.get("needs_research") is True:
            score -= 18

        if result.get("safe") is False:
            score -= 40

        useful_keys = [
            "answer", "summary", "best_answer", "result", "generated_code",
            "plan", "steps", "best_idea", "facts", "articles", "local_matches",
            "game_design", "response", "translated_text", "story", "draft",
            "final_output", "image_file", "generated_image_prompt"
            , "project_files", "movie_project", "render_status"
        ]

        score += sum(5 for key in useful_keys if result.get(key))

        if brain_name == "Code_brain" and (
            result.get("generated_code") or result.get("project_files")
        ):
            score += 35

        if brain_name == "Story_brain" and (
            result.get("story")
            or result.get("final_output")
            or result.get("draft")
        ):
            score += 55

        if brain_name == "Image_brain" and (
            result.get("image_file")
            or result.get("generated_image_prompt")
        ):
            score += 45

        if brain_name == "Movie_brain" and result.get("movie_project"):
            score += 65

        if result.get("generated_code"):
            score += 15

        if brain_name == "Local_LLM_brain" and result.get("final_output"):
            score += 28

        if brain_name != "Code_brain" and result.get("local_matches") and not result.get("answer"):
            score -= 12

        if isinstance(route_rank, int):
            score += max(4, 24 - route_rank * 2)

        return score

    @staticmethod
    def llm_candidate_approved(results):

        if not isinstance(results, dict):
            return False
        bridge = results.get("LLM_bridge_brain", {})
        return bool(
            isinstance(bridge, dict)
            and bridge.get("candidate_accepted") is True
            and bridge.get("candidate_role") == "general_conversation"
        )

    def choose_primary_result(self, results, report=None):

        candidates = []
        report = report or {}
        routed = self.routed_brains(report)
        route_rank = {brain: index for index, brain in enumerate(routed)}
        allow_creative = not routed or "Creative_brain" in route_rank
        allow_code = not routed or "Code_brain" in route_rank

        for brain_name, result in results.items():
            if brain_name in {
                "Response_brain",
                "Security_brain",
                "Fact_Check_brain",
                "Learning_brain",
                "Emotion_brain",
                "Collaboration_brain"
            } or brain_name in INTERNAL_ONLY_BRAINS:
                continue
            if brain_name == "Creative_brain" and not allow_creative:
                continue
            if brain_name == "Code_brain" and not allow_code:
                continue
            if brain_name == "Local_LLM_brain" and not self.llm_candidate_approved(results):
                continue
            if not self.has_user_facing_output(brain_name, result):
                continue

            candidates.append((
                self.result_score(brain_name, result, route_rank.get(brain_name)),
                brain_name,
                result
            ))

        candidates.sort(key=lambda item: item[0], reverse=True)

        if not candidates:
            return None, {}

        return candidates[0][1], candidates[0][2]

    def choose_workspace_result(self, workspace, results, report, user_text):

        if not isinstance(workspace, dict):
            return None, {}
        permitted = {
            brain for brain in self.routed_brains(report)
            if brain not in INTERNAL_ONLY_BRAINS and brain != "Response_brain"
        }
        if not permitted:
            permitted = None

        ranked = []
        selected = workspace.get("selected_candidate")
        if isinstance(selected, dict):
            ranked.append(selected)
        ranked.extend(
            item for item in workspace.get("candidates", [])
            if isinstance(item, dict) and item not in ranked
        )
        for candidate in ranked:
            brain_name = candidate.get("brain")
            if not brain_name or candidate.get("usable") is False:
                continue
            if permitted is not None and brain_name not in permitted:
                continue
            if brain_name == "Local_LLM_brain" and not self.llm_candidate_approved(results):
                continue
            result = results.get(brain_name)
            if self.has_user_facing_output(brain_name, result):
                return brain_name, result
        return None, {}

    def choose_domain_result(self, report, results, user_text):

        preferred = self.routed_brains(report)
        local_result = results.get("Local_LLM_brain", {})
        reviewed_code_available = (
            "Code_brain" in preferred
            and self.has_user_facing_output(
                "Code_brain",
                results.get("Code_brain", {}),
            )
        )
        if (
            isinstance(local_result, dict)
            and local_result.get("status") == "completed"
            and local_result.get("final_output")
            and self.llm_candidate_approved(results)
            and not reviewed_code_available
        ):
            preferred.insert(0, "Local_LLM_brain")

        for brain_name in list(dict.fromkeys(preferred)):
            result = results.get(brain_name)
            if not isinstance(result, dict):
                continue
            if result.get("error") or result.get("skipped"):
                continue
            if self.has_user_facing_output(brain_name, result):
                return brain_name, result

        return None, {}

    def has_user_facing_output(self, brain_name, result):

        if brain_name in INTERNAL_ONLY_BRAINS or not isinstance(result, dict):
            return False
        text = self.text_from_result(brain_name, result)
        return bool(text and not self.looks_like_internal_report(text))

    def is_pure_emotional_conversation(self, report, results, user_text):

        emotion = results.get("Emotion_brain", {})
        if not isinstance(emotion, dict):
            return False

        conversation_intent = str(
            emotion.get("conversation_intent", "none")
        ).lower()
        if conversation_intent in {"", "none"}:
            return False
        if not str(emotion.get("support_response") or "").strip():
            return False

        non_emotional_results = {
            "Emotion_brain", "Creative_brain", "Language_brain",
            "Response_brain", "Memory_brain", "Understanding_brain",
            "Manager_brain", "Reasoning_brain", "Planner_brain",
            "Security_brain", "Quality_Control_brain", "Learning_brain",
            "Nervous_system_brain", "Collaboration_brain",
            "Fact_Check_brain", "Answer_Enrichment_brain",
        }
        if any(
            brain_name not in non_emotional_results
            and self.has_user_facing_output(brain_name, result)
            for brain_name, result in results.items()
        ):
            return False

        substantive_routes = set(self.routed_brains(report)).difference({
            "Emotion_brain", "Creative_brain", "Language_brain",
            "Response_brain", "Memory_brain", "Understanding_brain",
            "Manager_brain", "Reasoning_brain", "Planner_brain",
            "Security_brain", "Quality_Control_brain", "Learning_brain",
            "Nervous_system_brain", "Collaboration_brain",
        })
        return not substantive_routes

    # ---------- formatting ----------

    def clean_text(self, text):

        text = re.sub(r"\s+", " ", str(text)).strip()
        return text

    def as_list(self, value):

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return [
                {
                    "key": key,
                    "value": item
                }
                for key, item in value.items()
            ]

        if value in [None, "", [], {}]:
            return []

        return [value]

    def detect_code_language(self, code, fallback="text"):

        code_text = str(code)

        if "def " in code_text or "class " in code_text or "import " in code_text:
            return "python"

        if "function " in code_text or "module.exports" in code_text or "const " in code_text:
            return "javascript"

        if "public class " in code_text:
            return "java"

        if "<!doctype html>" in code_text.lower() or "<html" in code_text.lower():
            return "html"

        return fallback or "text"

    def format_code_block(self, code, language=None):

        language = language or self.detect_code_language(code)
        code = str(code).strip()

        if code.startswith("```"):
            return code

        return f"```{language}\n{code}\n```"

    def project_file_language(self, path):

        suffix = str(path).lower().rsplit(".", 1)[-1] if "." in str(path) else ""
        return {
            "py": "python",
            "toml": "toml",
            "json": "json",
            "md": "markdown",
            "yaml": "yaml",
            "yml": "yaml",
            "txt": "text",
        }.get(suffix, "text")

    def format_project_files(self, project_files):

        if isinstance(project_files, list):
            normalized = {
                str(item.get("path") or item.get("name")): str(item.get("content", ""))
                for item in project_files
                if isinstance(item, dict) and (item.get("path") or item.get("name"))
            }
        elif isinstance(project_files, dict):
            normalized = {
                str(path): str(content)
                for path, content in project_files.items()
            }
        else:
            normalized = {}

        sections = []
        for path in sorted(normalized):
            sections.append(f"### `{path}`")
            sections.append(
                self.format_code_block(
                    normalized[path],
                    self.project_file_language(path)
                )
            )
        return "\n\n".join(sections).strip()

    def format_code_result(self, result):

        if result.get("mode") == "code_analysis":
            return str(
                result.get("answer")
                or result.get("summary")
                or "I analyzed the code."
            ).strip()

        project_files = result.get("project_files")
        if project_files:
            return self.format_project_files(project_files)

        code = result.get("generated_code", "")

        if not code and result.get("answer"):
            return str(result.get("answer")).strip()

        if result.get("output_mode") == "code_only" and code:
            return self.format_code_block(
                code,
                result.get("language")
            )

        parts = []

        assembly_plan = result.get("assembly_plan", {})
        steps = assembly_plan.get("steps", []) if isinstance(assembly_plan, dict) else []
        selected = self.code_piece_names(result, steps)

        parts.append("Here is a first code structure draft.")

        if selected:
            parts.append(
                "\nMain pieces:\n"
                + "\n".join(
                    f"- {self.clean_text(item)}"
                    for item in selected[:8]
                )
            )

        if steps:
            parts.append(
                "\nPlan:\n"
                + self.format_code_steps(steps[:8])
            )

        if result.get("dependencies_added"):
            dependencies = self.as_list(result.get("dependencies_added"))[:8]
            parts.append(
                "\nDependencies added:\n"
                + "\n".join(
                    f"- {self.clean_text(item)}"
                    for item in dependencies
                )
            )

        if code:
            parts.append(
                "\nCode:\n"
                + self.format_code_block(
                    code,
                    result.get("language")
                )
            )

        if result.get("needs_creative_brain") and isinstance(result.get("creative_fallback"), dict):
            fallback_code = result["creative_fallback"].get("generated_code")
            if fallback_code and fallback_code != code:
                parts.append(
                    "\nCreative fallback draft:\n"
                    + self.format_code_block(
                        fallback_code,
                        result["creative_fallback"].get("language")
                    )
                )

        parts.append("\nNote: this is a draft structure, not executed code. Review it before running.")

        return "\n".join(parts)

    def code_piece_names(self, result, steps):

        names = []

        if steps:
            for step in steps:
                if not isinstance(step, dict):
                    continue

                category = str(step.get("category", "")).lower()
                name = step.get("name") or step.get("id")

                if category in {"css", "style", "theme"}:
                    continue

                if name and name not in names:
                    names.append(name)

        if not names:
            for name in result.get("selected", []):
                if name not in names:
                    names.append(name)

        return names[:8]

    def format_code_steps(self, steps):

        lines = []
        seen = set()

        for index, step in enumerate(steps, start=1):
            if isinstance(step, dict):
                category = str(step.get("category", "module")).replace("_", " ")
                name = str(step.get("name") or step.get("id") or "code piece")
                glue = str(step.get("glue_strategy", "")).replace("_", " ")

                if category in {"css", "style", "theme"}:
                    continue

                if name in seen:
                    continue
                seen.add(name)

                detail = f"Add {category} module: {name}"
                if glue:
                    detail += f" ({glue})"
            else:
                detail = self.clean_text(step)

            lines.append(f"{len(lines) + 1}. {detail}")

        return "\n".join(lines) if lines else "1. Build the core code structure."

    def format_creative_result(self, result):

        nested_answer = result.get("answer_for_source_brain")
        if isinstance(nested_answer, dict):
            for key in ["generated_code", "final_output", "story", "answer", "concept"]:
                value = nested_answer.get(key)
                if isinstance(value, str) and value.strip():
                    if key == "generated_code":
                        return self.format_code_block(
                            value,
                            nested_answer.get("language")
                        )
                    if not self.looks_like_internal_report(value):
                        return value

        for key in ["final_output", "story", "answer", "result"]:
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                if not self.looks_like_internal_report(value):
                    return value

        evolution = result.get("evolution", {})
        quality = result.get("quality", {})
        best = result.get("best_idea", {})
        top_ideas = result.get("top_ideas", [])

        if isinstance(best, dict):
            for key in ["final_output", "story", "concept", "summary"]:
                value = best.get(key)
                if isinstance(value, str) and value.strip():
                    return self.clean_text(value)

        lines = ["Simulation results:"]

        if isinstance(evolution, dict):
            lines.append(
                f"- Rounds completed: {evolution.get('rounds_completed', 0)}"
            )
            lines.append(
                f"- Stop reason: {evolution.get('stop_reason', 'unknown')}"
            )

        if isinstance(quality, dict):
            lines.append(
                f"- Best score: {quality.get('best_score', result.get('confidence', 0))}"
            )
            lines.append(
                "- Quality checks: "
                + ", ".join(
                    name
                    for name, passed in [
                        ("good enough", quality.get("good_enough")),
                        ("creative enough", quality.get("creative_enough")),
                        ("coherent enough", quality.get("coherent_enough")),
                        ("safe enough", quality.get("safe_enough")),
                    ]
                    if passed
                )
            )

        if isinstance(best, dict):
            title = best.get("title") or best.get("id") or "selected result"
            concept = best.get("concept") or best.get("summary") or ""
            lines.append(f"- Selected result: {self.clean_text(title)}")
            if concept:
                lines.append(f"- Result summary: {self.clean_text(concept)}")

        if isinstance(top_ideas, list) and top_ideas:
            lines.append("\nTop candidates:")
            for index, idea in enumerate(top_ideas[:5], start=1):
                if not isinstance(idea, dict):
                    continue
                title = idea.get("title") or idea.get("id") or "candidate"
                score = idea.get("scores", {}).get("total", idea.get("confidence", ""))
                suffix = f" ({score})" if score != "" else ""
                lines.append(f"{index}. {self.clean_text(title)}{suffix}")

        return (
            "Creative_brain completed a simulation, but it did not return a clean final answer yet. "
            "Quality_Control_brain should ask the specialist to convert the selected idea into the final user-facing result."
        )

    def format_image_result(self, result):

        if result.get("safe") is False:
            return str(
                result.get("answer")
                or "I cannot create that image request because it is unsafe."
            )

        lines = []

        image_file = result.get("image_file")
        if image_file:
            lines.append("Created an image preview:")
            lines.append(str(image_file))

        prompt = result.get("generated_image_prompt")
        if prompt:
            lines.append("")
            lines.append("Image prompt:")
            lines.append(str(prompt))

        negative_prompt = result.get("negative_prompt")
        if negative_prompt:
            lines.append("")
            lines.append("Negative prompt:")
            lines.append(str(negative_prompt))

        style = result.get("style", {})
        if isinstance(style, dict) and style.get("name"):
            lines.append("")
            lines.append(f"Style: {style['name']}")

        return "\n".join(lines).strip() or str(result.get("answer", "")).strip()

    def text_from_result(self, brain_name, result):

        if not isinstance(result, dict):
            return self.clean_text(result)

        if brain_name in INTERNAL_ONLY_BRAINS:
            return ""

        if brain_name == "Code_brain":
            return self.format_code_result(result)

        if brain_name == "Creative_brain":
            return self.format_creative_result(result)

        if brain_name == "Image_brain":
            return self.format_image_result(result)

        if brain_name == "Movie_brain":
            return str(result.get("answer") or result.get("final_output") or "")

        if brain_name == "Story_brain":
            for key in ["story", "final_output", "draft"]:
                value = result.get(key)
                if value:
                    return str(value)

        if brain_name == "Math_brain":
            value = result.get("final_output")
            if value:
                return str(value)

        if result.get("generated_code"):
            return self.format_code_block(
                result.get("generated_code"),
                result.get("language")
            )

        for key in [
            "answer", "best_answer", "response", "final_output", "summary",
            "explanation", "translated_text"
        ]:
            value = result.get(key)
            if value:
                return str(value)

        creative_fallback = result.get("creative_fallback") or result.get("creative_help")
        if isinstance(creative_fallback, dict):
            code = creative_fallback.get("generated_code")
            if not code and isinstance(creative_fallback.get("code_assembly"), dict):
                code = creative_fallback["code_assembly"].get("generated_code")
            if not code and isinstance(creative_fallback.get("answer_for_source_brain"), dict):
                answer = creative_fallback["answer_for_source_brain"]
                code = answer.get("generated_code") or answer.get("concept") or answer.get("title")
            if code:
                if "generated_code" in creative_fallback or "def " in str(code) or "class " in str(code):
                    return self.format_code_block(
                        code,
                        creative_fallback.get("language")
                    )
                return str(code)

        if result.get("best_idea"):
            idea = result["best_idea"]
            if isinstance(idea, dict):
                title = idea.get("title", "רעיון")
                concept = idea.get("concept", "")
                return f"{title}\n{concept}".strip()

        if result.get("plan"):
            return self.format_plan(result["plan"])

        if result.get("steps"):
            return self.format_steps(result["steps"])

        if result.get("facts"):
            facts = self.rank_items_by_focus(
                self.as_list(result["facts"])[:8],
                getattr(self, "_active_focus_terms", [])
            )
            return self.format_list(
                "מצאתי את העובדות האלה:",
                facts
            )

        if result.get("local_matches"):
            return self.format_list(
                "מצאתי התאמות מקומיות:",
                self.as_list(result["local_matches"])[:6]
            )

        if result.get("game_design"):
            return self.format_structured(result["game_design"])

        return ""

    def looks_like_internal_report(self, text):

        lowered = str(text).lower()
        markers = [
            "goal:",
            "core idea:",
            "novel twist:",
            "constraint:",
            "validation:",
            "tradeoff:",
            "implementation:",
            "direction:"
        ]
        process_markers = [
            "review relevant memory before",
            "extract the complete request contract",
            "map every requirement to an owner",
            "implement and verify:",
            "verify every requirement",
            "quality correction requirements",
            "here is the useful conclusion:",
            "the current draft did not pass canri's quality check",
            "problem: requested feature is missing",
            "fix needed: implement this exact requirement"
        ]
        return (
            sum(1 for marker in markers if marker in lowered) >= 2
            or any(marker in lowered for marker in process_markers)
        )

    def safe_alternative_result(self, results, report, user_text, current_brain=None):

        preferred_brain, preferred_result = self.choose_domain_result(
            report,
            results,
            user_text
        )

        candidates = []
        if preferred_brain and preferred_brain != current_brain:
            candidates.append((preferred_brain, preferred_result))

        for brain_name, result in results.items():
            if brain_name in {
                current_brain,
                "Response_brain",
                "Security_brain",
                "Quality_Control_brain",
                "Learning_brain",
                "Collaboration_brain",
                "Planner_brain",
                "Reasoning_brain",
                "Memory_brain",
                "Fact_Check_brain"
            }:
                continue
            candidates.append((brain_name, result))

        for brain_name, result in candidates:
            text = self.text_from_result(brain_name, result)
            if text and not self.looks_like_internal_report(text):
                return brain_name, result, text

        return None, {}, ""

    def user_facing_fallback(self, report):

        topic = str(report.get("main_topic", "general")).lower()
        messages = {
            "story": "I could not produce the story cleanly yet. Please send the story request again.",
            "math": "I could not produce a verified math answer yet. Please send the expression again.",
            "science": "I could not produce a clear science explanation yet. Please ask the question again."
        }
        return messages.get(
            topic,
            "I could not produce a useful final answer yet. Please send the request again in one sentence."
        )

    def source_citations(self, results, limit=5):

        citations = []
        seen = set()
        fact_check = results.get("Fact_Check_brain", {})
        research = results.get("Research_brain", {})
        candidates = []
        if isinstance(fact_check, dict):
            candidates.extend(fact_check.get("strongest_sources", []))
        if isinstance(research, dict):
            candidates.extend(research.get("fetched_sources", []))
            candidates.extend(research.get("approved_research_links", []))
            for evidence in research.get("scanner_evidence", []):
                if not isinstance(evidence, dict):
                    continue
                candidates.extend(evidence.get("sources", []))
                if evidence.get("url"):
                    candidates.append(evidence)

        for source in candidates:
            if not isinstance(source, dict):
                continue
            name = str(source.get("name") or source.get("title") or "").strip()
            url = str(
                source.get("url")
                or source.get("link")
                or source.get("search_url")
                or ""
            ).strip()
            if not name or not url or not url.startswith(("https://", "http://")):
                continue
            identity = (name.lower(), url.lower())
            if identity in seen:
                continue
            seen.add(identity)
            citations.append({
                "name": name,
                "url": url,
                "trust_score": source.get("trust_score") or source.get("reliability_score"),
                "source_type": source.get("source_type"),
            })
            if len(citations) >= max(1, int(limit)):
                break
        return citations

    def add_source_footer(self, text, citations):

        if not citations:
            return text
        lines = ["Sources:"]
        for source in citations:
            score = source.get("trust_score")
            suffix = f" (trust {score}/100)" if isinstance(score, (int, float)) else ""
            lines.append(f"- {source['name']}: {source['url']}{suffix}")
        return f"{text}\n\n" + "\n".join(lines)

    def format_plan(self, plan):

        if isinstance(plan, list):
            return self.format_steps(plan)

        if isinstance(plan, dict):
            if isinstance(plan.get("steps"), list):
                return self.format_steps(plan["steps"])
            return self.format_structured(plan)

        return str(plan)

    def format_steps(self, steps):

        lines = []

        for index, step in enumerate(steps[:12], start=1):
            if isinstance(step, dict):
                text = step.get("title") or step.get("step") or step.get("name") or step.get("action") or str(step)
            else:
                text = str(step)
            lines.append(f"{index}. {self.clean_text(text)}")

        return "\n".join(lines)

    def format_list(self, title, items):

        lines = [title]

        for item in items:
            if isinstance(item, dict):
                text = item.get("text") or item.get("fact") or item.get("summary") or item.get("title") or str(item)
            else:
                text = str(item)
            lines.append(f"- {self.clean_text(text)}")

        return "\n".join(lines)

    def format_structured(self, value, depth=0):

        if depth > 2:
            return self.clean_text(value)

        if isinstance(value, list):
            return self.format_steps(value)

        if not isinstance(value, dict):
            return self.clean_text(value)

        preferred = [
            "summary", "answer", "result", "recommendations",
            "conclusions", "solutions", "verdict"
        ]
        keys = [key for key in preferred if key in value]
        safe_extra_keys = [
            "generated_code", "plan", "steps", "best_idea",
            "translated_text", "facts", "code_explanation"
        ]
        keys.extend(key for key in safe_extra_keys if key in value and key not in keys)

        lines = []

        for key in keys[:10]:
            item = value.get(key)
            if item in [None, "", [], {}]:
                continue

            label = str(key).replace("_", " ")

            if isinstance(item, (dict, list)):
                rendered = self.format_structured(item, depth + 1)
                lines.append(f"{label}: {rendered}")
            elif key == "generated_code":
                lines.append(self.format_code_block(item))
            else:
                lines.append(f"{label}: {self.clean_text(item)}")

        return "\n".join(lines)

    def should_skip_verification_note(self, report, primary_brain):

        _ = primary_brain
        routes = set(self.routed_brains(report))
        return "Fact_Check_brain" not in routes

    def add_verification_note(self, text, results, report=None, primary_brain=None):

        report = report or {}

        if self.should_skip_verification_note(report, primary_brain):
            return text

        fact_check = results.get("Fact_Check_brain", {})

        if not isinstance(fact_check, dict):
            return text

        verdict = fact_check.get("verdict")
        confidence = fact_check.get("confidence")

        if verdict in {"uncertain", "not_verified", "needs_research"}:
            note = "שים לב: לא אימתתי את זה מספיק חזק עדיין."
            if confidence is not None:
                note += f" רמת ביטחון: {confidence}%."
            return f"{text}\n\n{note}"

        if verdict == "conflicting":
            return f"{text}\n\nיש סתירות בין חלק מהמקורות או המוחות, אז לא כדאי להתייחס לזה כתשובה סופית."

        return text

    def add_quality_note(self, text, results):

        quality = self.quality_status(results)

        if not quality["available"]:
            return text

        if quality.get("passed") is True:
            return text

        issues = quality.get("issues", [])
        if not issues:
            return text

        main_issue = issues[0]
        problem = main_issue.get("problem", "Quality check found a possible issue.")
        score = quality.get("score")
        note = f"Quality note: {problem}"
        if score is not None:
            note += f" Score: {score}/100."

        return f"{text}\n\n{note}"

    def blocking_quality_issue(self, results, primary_brain=None):

        quality = self.quality_status(results)
        if not quality["available"] or quality.get("passed") is True:
            return None

        for issue in quality.get("issues", []):
            if not isinstance(issue, dict):
                continue
            if issue.get("severity") not in {"critical", "high"}:
                continue
            if primary_brain and issue.get("target_brain") not in {primary_brain, "Manager_brain"}:
                continue
            return issue

        return None

    def adapt_tone(self, text, results):

        emotion = results.get("Emotion_brain", {})

        if not isinstance(emotion, dict):
            return text

        style = emotion.get("response_style", {})
        detected = str(emotion.get("dominant_emotion", "")).lower()

        # Emotion_brain returns a style name, while older versions returned a
        # dictionary. Emotional conversations are handled as a direct domain
        # result; technical answers should stay concise instead of receiving a
        # hard-coded language prefix.
        if detected in {"stress", "sadness", "fear", "anger"}:
            return text

        if detected in {"stress", "sadness", "fear", "anger"}:
            return f"אני אענה בזהירות וברור.\n\n{text}"

        if isinstance(style, dict) and style.get("prefix"):
            return f"{style['prefix']}\n\n{text}"

        return text

    def final_polish(self, text):

        text = str(text).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

        if not text:
            return "אין לי עדיין מספיק מידע כדי לענות טוב. כדאי להריץ Research_brain או מוח מומחה נוסף."

        return text

    def strict_output_request(self, report, user_text):

        contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
        constraints = contract.get("output_constraints", {}) if isinstance(contract, dict) else {}
        return bool(constraints.get("only_output"))

    def requests_verification_status(self, user_text, report=None):

        _ = user_text
        report = report if isinstance(report, dict) else {}
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        action = str(contract.get("action") or "").casefold()
        action_kind = str(contract.get("action_kind") or "").casefold()
        return (
            "Fact_Check_brain" in set(self.routed_brains(report))
            or action in {"verify", "fact_check", "research"}
            or action_kind in {"verify", "fact_check", "research"}
        )

    def strip_internal_output(self, text):

        value = str(text or "").strip()
        value = re.sub(
            r"\n\s*(?:Quality note|Internal note|Simulation summary):.*$",
            "",
            value,
            flags=re.IGNORECASE | re.DOTALL
        ).strip()
        return value

    def collect_follow_up_tasks(self, results, limit=4):

        tasks = []
        seen = set()
        for result in results.values():
            if not isinstance(result, dict):
                continue
            for task in result.get("suggested_follow_up_tasks", []):
                if not isinstance(task, dict):
                    continue
                identity = str(task.get("id") or task.get("title") or "").strip().lower()
                if not identity or identity in seen:
                    continue
                seen.add(identity)
                tasks.append({
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "goal": task.get("goal"),
                    "owner_brains": task.get("owner_brains", [])[:6],
                    "acceptance_checks": task.get("acceptance_checks", [])[:6],
                })
                if len(tasks) >= max(1, int(limit)):
                    return tasks
        return tasks

    def apply_answer_enrichment(self, text, results, strict_output=False):

        if strict_output:
            return text
        enrichment = results.get("Answer_Enrichment_brain", {})
        if not isinstance(enrichment, dict) or not enrichment.get("allowed"):
            return text
        suffix = str(enrichment.get("visible_suffix") or "").strip()
        if not suffix or suffix in str(text):
            return text
        return f"{str(text).rstrip()}\n\n{suffix}"

    # ---------- statistics ----------

    def update_statistics(self, primary_brain, confidence, blocked):

        stats = self.statistics.get("Response_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_primary_brain"] = primary_brain
        stats["last_confidence"] = confidence
        stats["last_blocked"] = blocked
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()

        self.statistics["Response_brain"] = stats
        self.save_statistics()

    # ---------- public ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        results = self.get_results(data)
        cognitive_workspace = self.get_cognitive_workspace(data)
        dictionary = self.get_dictionary_context(data)
        user_text = self.extract_user_text(data, report)
        report = self.complete_understanding_report(report, user_text)
        self._active_focus_terms = self.user_focus_terms(user_text)
        routed_brains = set(self.routed_brains(report))
        infrastructure_brains = {
            "Memory_brain",
            "Understanding_brain",
            "Response_brain",
            "Language_brain",
            "Reasoning_brain",
            "Emotion_brain",
            "Security_brain",
            "Learning_brain",
            "Fact_Check_brain",
        }
        domain_specialists = routed_brains.difference(infrastructure_brains)
        safety = self.safety_status(results)
        strict_output = self.strict_output_request(report, user_text)
        citations = self.source_citations(results)
        agent_result = results.get("Agent_brain", {})
        agent_status = str(agent_result.get("status", "")) if isinstance(agent_result, dict) else ""
        agent_user_visible = bool(
            isinstance(agent_result, dict)
            and agent_result.get("user_visible")
            and agent_result.get("display_text")
            and agent_status in {
                "completed", "partially_completed", "blocked", "approval_required",
                "configuration_required", "rejected", "not_found", "no_changes"
            }
        )

        if safety["blocked"]:
            display_text = BLOCKED_SAFETY_HINTS.get(
                safety["reason"],
                BLOCKED_SAFETY_HINTS["general"]
            )
            primary_brain = "Security_brain"
            confidence = 100
        elif agent_user_visible:
            display_text = str(agent_result.get("display_text", "")).strip()
            primary_brain = "Agent_brain"
            confidence = agent_result.get("confidence", 85)
        elif self.is_greeting(user_text, report):
            display_text = self.greeting_answer(user_text)
            primary_brain = "Response_brain"
            confidence = 95
        elif self.is_capability_question(user_text, report):
            display_text = self.capability_answer()
            primary_brain = "Response_brain"
            confidence = 95
        elif self.is_pure_emotional_conversation(report, results, user_text):
            emotion_result = results.get("Emotion_brain", {})
            display_text = str(
                emotion_result.get("support_response")
                or emotion_result.get("final_output")
                or emotion_result.get("answer")
            ).strip()
            primary_brain = "Emotion_brain"
            confidence = emotion_result.get("confidence", 80)
        elif (
            not self.is_action_request(report)
            and self.is_definition_or_explanation_request(user_text, report)
            and not domain_specialists
            and not self.requests_verification_status(user_text, report)
            and self.dictionary_answer(user_text, dictionary)
        ):
            display_text = self.dictionary_answer(user_text, dictionary)
            primary_brain = "Dictionary_context"
            confidence = 88
        else:
            code_result = results.get("Code_brain", {})
            is_code_request = (
                "Code_brain" in routed_brains
                and self.is_action_request(report)
            )

            if (
                is_code_request
                and isinstance(code_result, dict)
                and (
                    code_result.get("generated_code")
                    or code_result.get("project_files")
                )
            ):
                primary_brain, primary_result = "Code_brain", code_result
            else:
                primary_brain, primary_result = self.choose_workspace_result(
                    cognitive_workspace,
                    results,
                    report,
                    user_text
                )
                if not primary_brain:
                    primary_brain, primary_result = self.choose_domain_result(
                        report,
                        results,
                        user_text
                    )
                if not primary_brain:
                    primary_brain, primary_result = self.choose_primary_result(results, report)

            if primary_brain:
                display_text = self.text_from_result(primary_brain, primary_result)
                if self.looks_like_internal_report(display_text):
                    alt_brain, alt_result, alt_text = self.safe_alternative_result(
                        results,
                        report,
                        user_text,
                        primary_brain
                    )
                    if alt_text:
                        primary_brain = alt_brain
                        primary_result = alt_result
                        display_text = alt_text
                    else:
                        display_text = self.user_facing_fallback(report)
                # Quality feedback is internal coordination data. After all
                # correction rounds, always return the strongest usable result
                # instead of exposing a quality-control report to the user.
                blocking_issue = self.blocking_quality_issue(results, primary_brain)
            elif user_text:
                display_text = "קיבלתי את ההודעה, אבל עדיין אין לי פלט מומחה מספיק טוב להציג."
            else:
                display_text = "אין לי עדיין מידע מספיק כדי לבנות תשובה."

            if not primary_brain:
                display_text = (
                    "קיבלתי את הבקשה, אך עדיין אין תוצאה מקצועית מספיק להצגה."
                    if user_text
                    else "אין עדיין מספיק מידע כדי לבנות תשובה מדויקת."
                )

            if not display_text or self.looks_like_internal_report(display_text):
                display_text = self.user_facing_fallback(report)

            if not strict_output:
                if self.requests_verification_status(user_text, report):
                    display_text = self.add_verification_note(
                        display_text,
                        results,
                        report,
                        primary_brain
                    )
                    display_text = self.add_source_footer(display_text, citations)
                display_text = self.apply_answer_enrichment(
                    display_text,
                    results,
                    strict_output=False
                )
                display_text = self.adapt_tone(display_text, results)

            confidence_values = [
                result.get("confidence")
                for result in results.values()
                if isinstance(result, dict)
                and isinstance(result.get("confidence"), (int, float))
            ]
            confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 55

        display_text = self.strip_internal_output(display_text)
        display_text = self.final_polish(display_text)
        follow_up_tasks = self.collect_follow_up_tasks(results)

        self.update_statistics(
            primary_brain,
            confidence,
            safety["blocked"]
        )

        return {
            "brain": "Response_brain",
            "display_text": display_text,
            "answer": display_text,
            "primary_brain": primary_brain,
            "confidence": confidence,
            "blocked": safety["blocked"],
            "safety": safety,
            "quality": self.quality_status(results),
            "used_results": sorted(results.keys()),
            "screen_ready": True,
            "strict_output": strict_output,
            "suggested_follow_up_tasks": follow_up_tasks,
            "follow_up_tasks_visible": False,
            "source_citations": citations,
            "cognitive_selection": {
                "selected_candidate": cognitive_workspace.get("selected_candidate"),
                "coverage": cognitive_workspace.get("coverage", {}),
                "unresolved_count": len(
                    cognitive_workspace.get("unresolved_requirements", [])
                ),
                "evidence_summary": cognitive_workspace.get("evidence_summary", {}),
            },
            "rules": [
                "Return one clear answer for the screen.",
                "Do not invent facts that no brain provided.",
                "Respect Security_brain blocks.",
                "Show uncertainty when Fact_Check_brain is not confident.",
                "Prefer the strongest domain expert result."
            ]
        }


brain = ResponseBrain()
