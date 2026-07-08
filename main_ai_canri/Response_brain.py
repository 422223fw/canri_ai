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

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

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

    def is_capability_question(self, text):

        lowered = str(text).lower()

        patterns = [
            "what can you do",
            "what are you able to do",
            "what can canri do",
            "what can u do",
            "tell me what you can do",
            "מה אתה יכול לעשות",
            "מה אתה יודע לעשות"
        ]

        return any(pattern in lowered for pattern in patterns)

    def capability_answer(self):

        return (
            "Right now I can help with several things inside this Canri project:\n\n"
            "1. Answer simple questions and explain topics.\n"
            "2. Plan projects, games, systems, and learning paths.\n"
            "3. Generate and assemble code drafts, especially Python-style code.\n"
            "4. Check whether information looks reliable before presenting it.\n"
            "5. Use specialist brains for science, technology, geography, history, language, games, stories, vision, voice, memory, and creativity.\n"
            "6. Use Creative_brain when another brain is stuck or missing an idea.\n"
            "7. Summarize all brain outputs into one clean answer on the screen.\n\n"
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

        intent = str(
            report.get(
                "intent",
                ""
            )
        ).lower()

        return intent in {
            "code_generation",
            "code_analysis",
            "story_creation",
            "creative_generation",
            "game_design",
            "planning",
            "math",
            "translation",
            "correction",
            "request"
        }

    def is_definition_or_explanation_request(self, text, report):

        lowered = str(text).lower()
        intent = str(report.get("intent", "")).lower()

        if intent in {"question", "research"}:
            return True

        markers = [
            "what is",
            "what are",
            "explain what",
            "explain",
            "define",
            "meaning of",
            "check if",
            "reliable"
        ]

        return any(marker in lowered for marker in markers)

    def is_greeting(self, text):

        lowered = str(text).strip().lower()

        if not lowered:
            return False

        greetings = {
            "hello",
            "hi",
            "hey",
            "shalom",
            "שלום",
            "היי",
            "הי"
        }

        cleaned = re.sub(r"[^\w\u0590-\u05FF\s]", "", lowered).strip()
        words = cleaned.split()

        return cleaned in greetings or (
            len(words) <= 3
            and any(word in greetings for word in words)
        )

    def greeting_answer(self):

        return (
            "שלום, אני Canri. אני מוכן לעזור.\n\n"
            "אפשר לבקש ממני לתכנן פרויקט, לבנות קוד, להסביר נושא, "
            "לבדוק מידע, או לעבוד עם אחד מהמוחות המומחים."
        )

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

    # ---------- selection ----------

    def result_score(self, brain_name, result):

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
            "final_output"
        ]

        score += sum(5 for key in useful_keys if result.get(key))

        if brain_name == "Code_brain" and result.get("generated_code"):
            score += 35

        if brain_name == "Story_brain" and (
            result.get("story")
            or result.get("final_output")
            or result.get("draft")
        ):
            score += 55

        if result.get("generated_code"):
            score += 15

        if brain_name != "Code_brain" and result.get("local_matches") and not result.get("answer"):
            score -= 12

        priority = {
            "Code_brain": 24,
            "Game_brain": 13,
            "Science_brain": 12,
            "Technology_brain": 12,
            "Geography_brain": 12,
            "History_brain": 12,
            "Language_brain": 12,
            "Math_brain": 12,
            "Story_brain": 12,
            "Creative_brain": 10,
            "Research_brain": 9,
            "Reasoning_brain": 8,
            "Planner_brain": 7,
            "Memory_brain": 4
        }

        score += priority.get(brain_name, 0)

        return score

    def choose_primary_result(self, results, report=None):

        candidates = []
        report = report or {}
        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()
        allow_creative = topic in {"story", "creative", "game"} or intent in {
            "story_creation",
            "creative_generation",
            "game_design"
        }
        allow_code = intent in {"code_generation", "code_analysis"} or (
            topic == "code"
            and intent not in {"question", "research"}
        )

        for brain_name, result in results.items():
            if brain_name in {
                "Response_brain",
                "Security_brain",
                "Fact_Check_brain",
                "Learning_brain",
                "Emotion_brain"
            }:
                continue
            if brain_name == "Creative_brain" and not allow_creative:
                continue
            if brain_name == "Code_brain" and not allow_code:
                continue

            candidates.append((
                self.result_score(brain_name, result),
                brain_name,
                result
            ))

        candidates.sort(key=lambda item: item[0], reverse=True)

        if not candidates:
            return None, {}

        return candidates[0][1], candidates[0][2]

    def choose_domain_result(self, report, results, user_text):

        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()
        lowered = str(user_text).lower()

        preferred = []

        if topic == "math" or intent == "math" or (
            re.search(r"\d|\bx\b", lowered)
            and (
                "=" in lowered
                or "^" in lowered
                or "**" in lowered
                or any(term in lowered for term in ["solve", "calculate", "step by step"])
            )
        ):
            preferred.append("Math_brain")

        if intent in {"question", "research"}:
            preferred.extend(["Research_brain", "Reasoning_brain"])

        if intent in {"code_generation", "code_analysis"} or (
            topic == "code"
            and intent not in {"question", "research"}
        ):
            preferred.append("Code_brain")

        if topic == "story" or intent == "story_creation":
            preferred.extend(["Story_brain", "Creative_brain"])

        if topic == "language" or intent in {"translation", "correction"}:
            preferred.append("Language_brain")

        domain_map = {
            "science": "Science_brain",
            "technology": "Technology_brain",
            "geography": "Geography_brain",
            "history": "History_brain",
            "game": "Game_brain",
            "vision": "Vision_brain",
            "voice": "Voice_brain",
        }

        if topic in domain_map:
            preferred.append(domain_map[topic])

        for brain_name in list(dict.fromkeys(preferred)):
            result = results.get(brain_name)
            if not isinstance(result, dict):
                continue
            if result.get("error") or result.get("skipped"):
                continue
            if self.text_from_result(brain_name, result):
                return brain_name, result

        return None, {}

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

    def format_code_result(self, result):

        if result.get("mode") == "code_analysis":
            return str(
                result.get("answer")
                or result.get("summary")
                or "I analyzed the code."
            ).strip()

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

        for key in ["final_output", "story", "answer", "result"]:
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value

        evolution = result.get("evolution", {})
        quality = result.get("quality", {})
        best = result.get("best_idea", {})
        top_ideas = result.get("top_ideas", [])

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

        return "\n".join(line for line in lines if line.strip())

    def text_from_result(self, brain_name, result):

        if not isinstance(result, dict):
            return self.clean_text(result)

        if brain_name == "Code_brain":
            return self.format_code_result(result)

        if brain_name == "Creative_brain":
            return self.format_creative_result(result)

        if brain_name == "Story_brain":
            for key in ["story", "final_output", "draft"]:
                value = result.get(key)
                if value:
                    return str(value)

        if brain_name == "Math_brain":
            value = result.get("final_output")
            if value:
                return str(value)

        if brain_name == "Reasoning_brain":
            for key in ["solutions", "conclusions"]:
                value = result.get(key)
                if isinstance(value, list) and value:
                    return self.format_list("Here is the useful conclusion:", value[:5])

        if result.get("generated_code"):
            return self.format_code_block(
                result.get("generated_code"),
                result.get("language")
            )

        for key in ["answer", "best_answer", "response", "summary", "explanation", "translated_text"]:
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

        return self.format_structured(result)

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

        topic = str(report.get("main_topic", "")).lower()
        intent = str(report.get("intent", "")).lower()

        creative_or_build_request = (
            topic in {"code", "game", "story", "creative"}
            or intent in {
                "code_generation",
                "code_analysis",
                "game_design",
                "story_creation",
                "creative_generation",
                "request"
            }
            or primary_brain in {
                "Code_brain",
                "Game_brain",
                "Creative_brain",
                "Story_brain",
                "Planner_brain"
            }
        )

        return creative_or_build_request

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

    def adapt_tone(self, text, results):

        emotion = results.get("Emotion_brain", {})

        if not isinstance(emotion, dict):
            return text

        style = emotion.get("response_style", {})
        detected = str(emotion.get("dominant_emotion", "")).lower()

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
        dictionary = self.get_dictionary_context(data)
        user_text = self.extract_user_text(data, report)
        self._active_focus_terms = self.user_focus_terms(user_text)
        safety = self.safety_status(results)

        if safety["blocked"]:
            display_text = BLOCKED_SAFETY_HINTS.get(
                safety["reason"],
                BLOCKED_SAFETY_HINTS["general"]
            )
            primary_brain = "Security_brain"
            confidence = 100
        elif self.is_greeting(user_text):
            display_text = self.greeting_answer()
            primary_brain = "Response_brain"
            confidence = 95
        elif self.is_capability_question(user_text):
            display_text = self.capability_answer()
            primary_brain = "Response_brain"
            confidence = 95
        elif (
            (
                not self.is_action_request(report)
                or self.is_definition_or_explanation_request(user_text, report)
            )
            and not any(
                marker in user_text.lower()
                for marker in ["reliable", "fact check", "check if", "local knowledge", "use local knowledge"]
            )
            and self.dictionary_answer(user_text, dictionary)
        ):
            display_text = self.dictionary_answer(user_text, dictionary)
            primary_brain = "Dictionary_context"
            confidence = 88
        else:
            code_result = results.get("Code_brain", {})
            is_code_request = (
                str(report.get("intent", "")).lower() in {"code_generation", "code_analysis"}
                or (
                    str(report.get("main_topic", "")).lower() == "code"
                    and str(report.get("intent", "")).lower() not in {"question", "research"}
                )
            )

            if (
                is_code_request
                and isinstance(code_result, dict)
                and code_result.get("generated_code")
            ):
                primary_brain, primary_result = "Code_brain", code_result
            else:
                primary_brain, primary_result = self.choose_domain_result(
                    report,
                    results,
                    user_text
                )
                if not primary_brain:
                    primary_brain, primary_result = self.choose_primary_result(results, report)

            if primary_brain:
                display_text = self.text_from_result(primary_brain, primary_result)
            elif user_text:
                display_text = "קיבלתי את ההודעה, אבל עדיין אין לי פלט מומחה מספיק טוב להציג."
            else:
                display_text = "אין לי עדיין מידע מספיק כדי לבנות תשובה."

            display_text = self.add_verification_note(
                display_text,
                results,
                report,
                primary_brain
            )
            display_text = self.adapt_tone(display_text, results)

            confidence_values = [
                result.get("confidence")
                for result in results.values()
                if isinstance(result, dict)
                and isinstance(result.get("confidence"), (int, float))
            ]
            confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 55

        display_text = self.final_polish(display_text)

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
            "used_results": sorted(results.keys()),
            "screen_ready": True,
            "rules": [
                "Return one clear answer for the screen.",
                "Do not invent facts that no brain provided.",
                "Respect Security_brain blocks.",
                "Show uncertainty when Fact_Check_brain is not confident.",
                "Prefer the strongest domain expert result."
            ]
        }


brain = ResponseBrain()
