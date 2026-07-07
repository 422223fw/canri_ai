"""
Planner_brain.py
Canri AI

Planner_brain turns a user goal into an ordered, dependency-aware plan.
It does not execute the task and does not generate final content. It decides:
- what needs to happen
- in what order
- which brains should be involved
- what risks and missing information must be handled
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_FILE = DATA_DIR / "Planner_task_templates.json"
DEPENDENCY_FILE = DATA_DIR / "Planner_dependency_graph.json"
RISK_FILE = DATA_DIR / "Planner_risk_rules.json"
STATS_FILE = DATA_DIR / "Planner_statistics.json"

MAX_MATCHES = 8

GENERIC_TERMS = {
    "the", "and", "for", "with", "that", "this", "what", "how",
    "why", "make", "create", "build", "do", "task", "plan",
    "תעשה", "תכין", "לי", "של", "את", "מה", "איך", "זה"
}


class PlannerBrain:

    def __init__(self):

        self.templates = self.load_json(TEMPLATES_FILE, {})
        self.dependency_graph = self.load_json(DEPENDENCY_FILE, {})
        self.risk_rules = self.load_json(RISK_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        print("Planner Brain Loaded")

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

    # ---------- input extraction ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "unknown",
                "intent": "planning",
                "words": []
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if (
            "main_topic" in data
            or "intent" in data
            or "words" in data
        ):
            return data

        return {}

    def get_memory_report(self, data):

        if not isinstance(data, dict):
            return {}

        memory = data.get("memory")

        if isinstance(memory, dict):
            return memory

        return {}

    def extract_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "query",
                "text",
                "goal",
                "task"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_terms(self, report, memory_report, text):

        terms = []

        for key in [
            "main_topic",
            "intent",
            "language",
            "target_language"
        ]:
            value = report.get(key)
            if value and value != "unknown":
                terms.append(str(value))

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            terms.extend(str(topic) for topic in topics)

        for task in report.get("possible_tasks", []):
            terms.append(str(task).replace("_", " "))

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            word = word_data.get("word")
            if word:
                terms.append(str(word))

            for connection in word_data.get("connections", [])[:8]:
                terms.append(str(connection))

        for keyword in memory_report.get("current_keywords", [])[:25]:
            terms.append(str(keyword))

        for match in memory_report.get("ranked_matches", [])[:5]:
            if isinstance(match, dict):
                terms.extend(str(keyword) for keyword in match.get("keywords", [])[:8])

        terms.extend(
            re.findall(
                r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
                text
            )
        )

        clean_terms = []

        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip()
            term = term.replace("_", " ")

            if (
                term
                and len(term) > 1
                and term not in GENERIC_TERMS
                and term not in clean_terms
            ):
                clean_terms.append(term)

        return clean_terms[:100]

    # ---------- classification ----------

    def detect_domain(self, report, terms, text):

        topic = str(report.get("main_topic", "")).lower()
        lowered = f"{text.lower()} {' '.join(terms)}"

        domain_rules = {
            "code": ["code", "python", "javascript", "java", "function", "api", "debug"],
            "science": ["science", "physics", "chemistry", "biology", "experiment", "article"],
            "language": ["language", "translation", "translate", "grammar", "synonym", "antonym"],
            "geography": ["geography", "country", "city", "capital", "map", "gps", "river"],
            "technology": ["technology", "hardware", "software", "cpu", "gpu", "robot", "server"],
            "history": ["history", "empire", "war", "ancient", "timeline"],
            "math": ["math", "equation", "calculate", "algebra", "geometry"],
            "game": ["game", "player", "enemy", "level", "inventory"],
            "story": ["story", "character", "plot", "world", "creative"],
            "security": ["security", "password", "token", "encrypt", "danger", "safe"]
        }

        for domain, keywords in domain_rules.items():
            if topic == domain or any(keyword in lowered for keyword in keywords):
                return domain

        return topic if topic and topic != "unknown" else "code" if "program" in lowered else "general"

    def detect_intent(self, report, terms, text):

        intent = str(report.get("intent", "")).lower()
        lowered = f"{text.lower()} {' '.join(terms)}"

        if intent and intent != "unknown":
            return intent

        intent_rules = {
            "code_generation": ["write code", "generate code", "program", "function", "script"],
            "debugging": ["debug", "fix", "error", "bug"],
            "research": ["research", "find information", "source", "article"],
            "translation": ["translate", "translation"],
            "comparison": ["compare", "versus", "vs"],
            "learning": ["learn", "lesson", "teach"],
            "planning": ["plan", "roadmap", "steps"],
            "question": ["what", "why", "how", "where"]
        }

        for detected_intent, keywords in intent_rules.items():
            if any(keyword in lowered for keyword in keywords):
                return detected_intent

        return "planning"

    def detect_scale(self, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        if any(word in lowered for word in ["production", "professional", "advanced"]):
            return "professional"

        if any(word in lowered for word in ["big", "large", "huge", "full", "complete"]):
            return "large"

        if any(word in lowered for word in ["simple", "basic", "small", "quick"]):
            return "small"

        return "medium"

    def detect_output(self, intent, terms, text):

        lowered = f"{text.lower()} {' '.join(terms)}"

        if "code" in lowered or intent == "code_generation":
            return "code"
        if "table" in lowered:
            return "comparison_table"
        if "roadmap" in lowered:
            return "roadmap"
        if "lesson" in lowered or intent == "learning":
            return "lesson"
        if "report" in lowered or intent == "research":
            return "report"

        return "implementation_plan"

    # ---------- template search ----------

    def score_template(self, template, domain, intent, scale, output, terms):

        score = 0
        matched = []

        if template.get("domain") == domain:
            score += 30
            matched.append(domain)

        if template.get("intent") == intent:
            score += 25
            matched.append(intent)

        if template.get("scale") == scale:
            score += 12
            matched.append(scale)

        if template.get("output") == output:
            score += 12
            matched.append(output)

        searchable = " ".join([
            template.get("id", ""),
            template.get("name", ""),
            template.get("domain", ""),
            template.get("intent", ""),
            template.get("scale", ""),
            template.get("output", ""),
            " ".join(template.get("trigger_terms", [])),
            " ".join(template.get("default_steps", []))
        ]).lower()

        for term in terms:
            if term in searchable:
                score += 2
                matched.append(term)

        score += template.get("confidence", 60) / 20

        return round(score, 2), list(dict.fromkeys(matched))

    def find_templates(self, domain, intent, scale, output, terms):

        matches = []

        for template in self.templates.values():
            score, matched = self.score_template(
                template,
                domain,
                intent,
                scale,
                output,
                terms
            )

            if score <= 10:
                continue

            matches.append({
                "score": score,
                "matched_terms": matched,
                "template": template
            })

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return matches[:MAX_MATCHES]

    # ---------- planning ----------

    def get_dependency_data(self, template_id):

        return self.dependency_graph.get(
            f"dependency_{template_id}",
            {}
        )

    def get_risk_rule(self, domain, intent, scale):

        best_rule = None
        best_score = -1

        for rule in self.risk_rules.values():
            score = 0

            if rule.get("domain") == domain:
                score += 4
            if rule.get("intent") == intent:
                score += 3
            if rule.get("scale") == scale:
                score += 2

            if score > best_score:
                best_score = score
                best_rule = rule

        return best_rule or {}

    def build_steps(self, template, dependency_data, memory_report):

        steps = []
        dependencies = dependency_data.get("dependencies", {})

        if dependencies:
            ordered_ids = dependency_data.get("ordered_steps", [])

            for step_id in ordered_ids:
                step_data = dependencies.get(step_id, {})
                steps.append({
                    "id": step_id,
                    "order": step_data.get("order", len(steps) + 1),
                    "name": step_data.get("name", "planned step"),
                    "requires": step_data.get("requires", []),
                    "before": step_data.get("before", []),
                    "needed_brains": step_data.get(
                        "needed_brains",
                        template.get("needed_brains", [])
                    ),
                    "blocking": step_data.get("blocking", False),
                    "status": "planned"
                })

        if not steps:
            for index, step_name in enumerate(template.get("default_steps", []), start=1):
                steps.append({
                    "id": f"{template.get('id', 'fallback')}_step_{index}",
                    "order": index,
                    "name": step_name,
                    "requires": [],
                    "before": [],
                    "needed_brains": template.get("needed_brains", []),
                    "blocking": index <= 2,
                    "status": "planned"
                })

        if memory_report.get("memory_found", 0):
            steps.insert(0, {
                "id": "memory_context_review",
                "order": 0,
                "name": "review relevant memory before executing the plan",
                "requires": [],
                "before": [steps[0]["id"]] if steps else [],
                "needed_brains": ["Memory_brain"],
                "blocking": True,
                "status": "planned"
            })

        return steps

    def identify_missing_information(self, domain, intent, terms):

        missing = []

        if not terms:
            missing.append("No clear terms were extracted from the request")

        if domain == "code" and not any(term in terms for term in ["python", "javascript", "java", "html", "css", "sql"]):
            missing.append("Programming language is not clear")

        if intent in ["research", "question"] and domain == "general":
            missing.append("Topic is too broad")

        if domain == "geography" and any(term in terms for term in ["weather", "population", "current", "today"]):
            missing.append("Current geographic data may require Research_brain")

        return missing

    def build_plan(self, domain, intent, scale, output, terms, memory_report):

        matches = self.find_templates(
            domain,
            intent,
            scale,
            output,
            terms
        )

        if matches:
            selected = matches[0]["template"]
            match_score = matches[0]["score"]
            matched_terms = matches[0]["matched_terms"]
        else:
            selected = {
                "id": "fallback_general_plan",
                "domain": domain,
                "intent": intent,
                "scale": scale,
                "output": output,
                "name": "fallback general planning template",
                "default_steps": [
                    "clarify goal",
                    "collect information",
                    "choose strategy",
                    "execute with specialist brains",
                    "verify result"
                ],
                "needed_brains": [
                    "Reasoning_brain",
                    "Research_brain",
                    "Fact_Check_brain",
                    "Response_brain"
                ],
                "difficulty": 60,
                "estimated_minutes": 40,
                "confidence": 55
            }
            match_score = 35
            matched_terms = []

        dependency_data = self.get_dependency_data(
            selected["id"]
        )

        risk_rule = self.get_risk_rule(
            domain,
            intent,
            scale
        )

        steps = self.build_steps(
            selected,
            dependency_data,
            memory_report
        )

        needed_brains = []

        for step in steps:
            needed_brains.extend(step.get("needed_brains", []))

        needed_brains.extend(selected.get("needed_brains", []))

        risk_level = risk_rule.get("risk_level", "medium")
        missing = self.identify_missing_information(domain, intent, terms)

        confidence = min(
            100,
            match_score + selected.get("confidence", 60) * 0.25
        )

        if missing:
            confidence = max(20, confidence - len(missing) * 10)

        return {
            "goal": selected.get("name"),
            "template_id": selected.get("id"),
            "domain": domain,
            "intent": intent,
            "scale": scale,
            "output": output,
            "steps": steps,
            "estimated_steps": len(steps),
            "needed_brains": list(dict.fromkeys(needed_brains)),
            "difficulty": selected.get("difficulty", 60),
            "estimated_minutes": selected.get("estimated_minutes", 30),
            "risk_level": risk_level,
            "risk_factors": risk_rule.get("risk_factors", []),
            "mitigations": risk_rule.get("mitigations", []),
            "requires_review_by": risk_rule.get("requires_review_by", []),
            "missing_information": missing,
            "matched_terms": matched_terms[:30],
            "confidence": round(confidence, 2),
            "dependency_graph_used": bool(dependency_data),
            "memory_context_used": bool(memory_report.get("memory_found", 0)),
            "quality_checks": selected.get("quality_checks", [])
        }

    # ---------- statistics ----------

    def update_statistics(self, plan):

        stats = self.statistics.get("Planner_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_domain"] = plan.get("domain")
        stats["last_intent"] = plan.get("intent")
        stats["last_confidence"] = plan.get("confidence")
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("templates", len(self.templates))
        stats.setdefault("dependency_graphs", len(self.dependency_graph))
        stats.setdefault("risk_rules", len(self.risk_rules))

        self.statistics["Planner_brain"] = stats
        self.save_statistics()

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        text = self.extract_text(data, report)

        terms = self.collect_terms(
            report,
            memory_report,
            text
        )

        domain = self.detect_domain(
            report,
            terms,
            text
        )

        intent = self.detect_intent(
            report,
            terms,
            text
        )

        scale = self.detect_scale(
            terms,
            text
        )

        output = self.detect_output(
            intent,
            terms,
            text
        )

        plan = self.build_plan(
            domain,
            intent,
            scale,
            output,
            terms,
            memory_report
        )

        self.update_statistics(plan)

        return {
            "brain": "Planner_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "terms_used": terms,
            "plan": plan,
            "confidence": plan["confidence"],
            "suggested_next_brains": [
                brain_name
                for brain_name in (
                    plan["needed_brains"]
                    + [
                        "Creative_brain"
                        if plan.get("missing_information") or plan.get("confidence", 0) < 55
                        else None
                    ]
                )
                if brain_name and brain_name != "Planner_brain"
            ],
            "data_files_used": [
                "Planner_task_templates.json",
                "Planner_dependency_graph.json",
                "Planner_risk_rules.json",
                "Planner_statistics.json"
            ],
            "rules": [
                "Use Understanding_brain and Memory_brain reports as planning input.",
                "Do not execute the task; only create an ordered plan.",
                "Prefer dependency-aware templates before fallback planning.",
                "Mark missing information instead of guessing.",
                "Route risky plans through Security_brain or Fact_Check_brain."
            ]
        }


brain = PlannerBrain()
