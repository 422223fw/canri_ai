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

from Brain_storage import atomic_write_json


DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_FILE = DATA_DIR / "Planner_task_templates.json"
DEPENDENCY_FILE = DATA_DIR / "Planner_dependency_graph.json"
RISK_FILE = DATA_DIR / "Planner_risk_rules.json"
QUALITY_PATTERNS_FILE = DATA_DIR / "Planner_quality_patterns.json"
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
        self.quality_patterns = self.load_json(QUALITY_PATTERNS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        self.template_index = self.build_index(
            self.templates,
            ("domain", "intent", "scale", "output")
        )
        self.risk_index = self.build_index(
            self.risk_rules,
            ("domain", "intent", "scale")
        )
        self.quality_index = self.build_index(
            self.quality_patterns,
            ("domain", "intent")
        )

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

        atomic_write_json(STATS_FILE, self.statistics)

    def build_index(self, records, fields):

        index = {}
        values = records.values() if isinstance(records, dict) else records

        for record in values:
            if not isinstance(record, dict):
                continue
            key = tuple(str(record.get(field, "*")).lower() for field in fields)
            index.setdefault(key, []).append(record)

        return index

    def indexed_candidates(self, index, keys, fallback):

        candidates = []
        seen = set()

        for key in keys:
            for record in index.get(tuple(str(value).lower() for value in key), []):
                record_id = record.get("id") or id(record)
                if record_id in seen:
                    continue
                seen.add(record_id)
                candidates.append(record)

        return candidates or list(fallback)

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
        candidates = self.indexed_candidates(
            self.template_index,
            [
                (domain, intent, scale, output),
                (domain, intent, scale, "implementation_plan"),
                (domain, intent, "medium", output),
                (domain, "planning", scale, output),
            ],
            self.templates.values()
        )

        for template in candidates:
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
        candidates = self.indexed_candidates(
            self.risk_index,
            [
                (domain, intent, scale),
                (domain, intent, "medium"),
                (domain, "planning", scale),
            ],
            self.risk_rules.values()
        )

        for rule in candidates:
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

    def get_request_contract(self, report, data):

        for source in (report, data if isinstance(data, dict) else {}):
            contract = source.get("request_contract")
            if isinstance(contract, dict):
                return contract

        requirements = []
        for item in report.get("requirements", []):
            if isinstance(item, dict):
                requirements.append(item)
            elif item:
                requirements.append({
                    "id": f"requirement_{len(requirements) + 1}",
                    "text": str(item),
                    "kind": "explicit_constraint"
                })

        return {
            "requirements": requirements,
            "output_constraints": report.get("output_constraints", {}),
            "detail_inventory": report.get("detail_inventory", {}),
            "global_picture": report.get("global_picture", {})
        }

    def normalize_requirements(self, contract, text):

        requirements = []
        seen = set()

        for index, item in enumerate(contract.get("requirements", []), start=1):
            if isinstance(item, dict):
                requirement = dict(item)
                requirement_text = str(requirement.get("text", "")).strip()
            else:
                requirement = {}
                requirement_text = str(item).strip()

            key = re.sub(r"\s+", " ", requirement_text.lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            requirement["id"] = requirement.get("id") or f"requirement_{index}"
            requirement["text"] = requirement_text
            requirement.setdefault("kind", "explicit_constraint")
            requirements.append(requirement)

        if not requirements and text:
            requirements.append({
                "id": "primary_goal",
                "text": re.sub(r"\s+", " ", text).strip()[:500],
                "kind": "goal"
            })

        return requirements[:80]

    def requirement_brains(self, requirement, domain):

        lowered = requirement.get("text", "").lower()
        brains = []
        rules = {
            "Code_brain": ["code", "program", "function", "python", "json", "api"],
            "Security_brain": ["safe", "security", "password", "validate", "permission"],
            "Fact_Check_brain": ["fact", "source", "reliable", "verify", "current"],
            "Math_brain": ["calculate", "equation", "total", "percentage", "average"],
            "Story_brain": ["story", "character", "chapter", "plot"],
            "Memory_brain": ["continue", "same", "previous", "existing"],
        }
        domain_brain = {
            "code": "Code_brain",
            "math": "Math_brain",
            "story": "Story_brain",
            "security": "Security_brain",
        }.get(domain)
        if domain_brain:
            brains.append(domain_brain)
        for brain_name, markers in rules.items():
            if any(marker in lowered for marker in markers):
                brains.append(brain_name)
        return list(dict.fromkeys(brains or ["Reasoning_brain"]))

    def topological_order(self, steps):

        by_id = {step["id"]: step for step in steps if step.get("id")}
        indegree = {step_id: 0 for step_id in by_id}
        outgoing = {step_id: [] for step_id in by_id}
        missing_dependencies = []

        for step_id, step in by_id.items():
            valid_requires = []
            for required_id in step.get("requires", []):
                if required_id not in by_id:
                    missing_dependencies.append({
                        "step": step_id,
                        "missing": required_id
                    })
                    continue
                valid_requires.append(required_id)
                indegree[step_id] += 1
                outgoing[required_id].append(step_id)
            step["requires"] = valid_requires

        queue = sorted(
            (step_id for step_id, degree in indegree.items() if degree == 0),
            key=lambda step_id: (by_id[step_id].get("order", 9999), step_id)
        )
        ordered = []

        while queue:
            step_id = queue.pop(0)
            ordered.append(by_id[step_id])
            for next_id in outgoing[step_id]:
                indegree[next_id] -= 1
                if indegree[next_id] == 0:
                    queue.append(next_id)
                    queue.sort(key=lambda value: (by_id[value].get("order", 9999), value))

        cycle_nodes = [step_id for step_id, degree in indegree.items() if degree > 0]
        if cycle_nodes:
            for step_id in sorted(cycle_nodes):
                step = by_id[step_id]
                step["requires"] = [
                    required_id
                    for required_id in step.get("requires", [])
                    if required_id not in cycle_nodes
                ]
                ordered.append(step)

        for order, step in enumerate(ordered, start=1):
            step["order"] = order

        return ordered, {
            "valid": not cycle_nodes and not missing_dependencies,
            "cycle_detected": bool(cycle_nodes),
            "cycle_nodes": cycle_nodes,
            "missing_dependencies": missing_dependencies
        }

    def build_steps(self, template, dependency_data, memory_report, requirements, domain):

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

        if requirements:
            anchor_id = steps[0]["id"] if steps else None
            requirement_step_ids = []
            insert_at = 1 if steps else 0

            for index, requirement in enumerate(requirements[:24], start=1):
                step_id = f"requirement_coverage_{index}"
                requirement_step_ids.append(step_id)
                steps.insert(insert_at + index - 1, {
                    "id": step_id,
                    "order": insert_at + index,
                    "name": f"implement and verify: {requirement['text']}",
                    "requires": [anchor_id] if anchor_id else [],
                    "before": [],
                    "needed_brains": self.requirement_brains(requirement, domain),
                    "blocking": requirement.get("kind") == "output_constraint",
                    "status": "planned",
                    "requirement_ids": [requirement["id"]],
                    "acceptance_check": f"Evidence exists for requirement: {requirement['text']}"
                })

            verification_id = "verify_all_requirements"
            steps.append({
                "id": verification_id,
                "order": len(steps) + 1,
                "name": "verify every requested requirement and output constraint",
                "requires": requirement_step_ids,
                "before": [],
                "needed_brains": ["Quality_Control_brain"],
                "blocking": True,
                "status": "planned",
                "requirement_ids": [item["id"] for item in requirements],
                "acceptance_check": "All requirements have concrete evidence and no requested detail is missing"
            })

        return self.topological_order(steps)

    def choose_quality_pattern(self, domain, intent, terms):

        candidates = self.indexed_candidates(
            self.quality_index,
            [(domain, intent), (domain, "planning"), ("general", intent)],
            self.quality_patterns.values()
        )
        if not candidates:
            return {}

        terms_set = set(terms)
        return max(
            candidates,
            key=lambda item: (
                len(terms_set & set(item.get("trigger_terms", []))),
                item.get("quality_score", 0)
            )
        )

    def build_requirement_coverage(self, requirements, steps):

        coverage = []
        for requirement in requirements:
            step_ids = [
                step["id"]
                for step in steps
                if requirement["id"] in step.get("requirement_ids", [])
            ]
            coverage.append({
                "requirement_id": requirement["id"],
                "requirement": requirement["text"],
                "kind": requirement.get("kind", "constraint"),
                "covered": bool(step_ids),
                "planned_steps": step_ids,
                "verification": f"Check final evidence for {requirement['id']}"
            })
        return coverage

    def build_parallel_groups(self, steps):

        depths = {}
        for step in steps:
            depths[step["id"]] = 0 if not step.get("requires") else 1 + max(
                (depths.get(required_id, 0) for required_id in step["requires"]),
                default=0
            )

        groups = {}
        for step in steps:
            groups.setdefault(depths[step["id"]], []).append(step["id"])

        return [
            {"stage": stage + 1, "step_ids": step_ids, "parallel": len(step_ids) > 1}
            for stage, step_ids in sorted(groups.items())
        ]

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

    def build_plan(self, domain, intent, scale, output, terms, memory_report, contract):

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

        requirements = self.normalize_requirements(
            contract,
            contract.get("global_picture", {}).get("goal", "")
        )
        steps, graph_validation = self.build_steps(
            selected,
            dependency_data,
            memory_report,
            requirements,
            domain
        )
        quality_pattern = self.choose_quality_pattern(domain, intent, terms)
        requirement_coverage = self.build_requirement_coverage(requirements, steps)
        output_constraints = contract.get("output_constraints", {})
        detail_inventory = contract.get("detail_inventory", {})

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
            "goal": contract.get("global_picture", {}).get("goal") or selected.get("name"),
            "planning_strategy": selected.get("name"),
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
                + quality_pattern.get("quality_checks", []),
            "requirements": requirements,
            "requirement_coverage": requirement_coverage,
            "requirements_covered": sum(1 for item in requirement_coverage if item["covered"]),
            "requirements_total": len(requirement_coverage),
            "all_requirements_planned": all(item["covered"] for item in requirement_coverage),
            "output_constraints": output_constraints,
            "important_details": detail_inventory,
            "acceptance_criteria": [
                item.get("acceptance_check")
                for item in steps
                if item.get("acceptance_check")
            ] + quality_pattern.get("acceptance_criteria", []),
            "deliverables": quality_pattern.get("deliverables", [output]),
            "checkpoints": quality_pattern.get("checkpoints", [
                "requirements approved",
                "implementation assembled",
                "all acceptance checks passed"
            ]),
            "rollback_strategy": quality_pattern.get(
                "rollback_strategy",
                "Keep the last verified result and revert any step that fails its acceptance check."
            ),
            "parallel_groups": self.build_parallel_groups(steps),
            "critical_path": dependency_data.get("critical_path", [step["id"] for step in steps if step.get("blocking")]),
            "graph_validation": graph_validation,
            "quality_pattern_id": quality_pattern.get("id")
        }

    # ---------- statistics ----------

    def update_statistics(self, plan):

        stats = self.statistics.get("Planner_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_domain"] = plan.get("domain")
        stats["last_intent"] = plan.get("intent")
        stats["last_confidence"] = plan.get("confidence")
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats["templates"] = len(self.templates)
        stats["dependency_graphs"] = len(self.dependency_graph)
        stats["risk_rules"] = len(self.risk_rules)
        stats["quality_patterns"] = len(self.quality_patterns)
        stats["last_requirements_total"] = plan.get("requirements_total", 0)
        stats["last_requirements_covered"] = plan.get("requirements_covered", 0)

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

        contract = self.get_request_contract(report, data)
        if not contract.get("global_picture"):
            contract["global_picture"] = {"goal": text}

        plan = self.build_plan(
            domain,
            intent,
            scale,
            output,
            terms,
            memory_report,
            contract
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
                "Planner_quality_patterns.json",
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
