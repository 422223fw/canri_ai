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
        """Trust Understanding_brain's structured domain decision."""

        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        candidates = [
            report.get("main_topic"),
            contract.get("topic"),
            contract.get("global_picture", {}).get("topic")
            if isinstance(contract.get("global_picture"), dict) else None,
        ]
        for item in report.get("central_domains", []):
            candidates.append(item.get("domain") if isinstance(item, dict) else item)
        for item in contract.get("central_domains", []):
            candidates.append(item.get("domain") if isinstance(item, dict) else item)

        for candidate in candidates:
            domain = str(candidate or "").strip().lower()
            if domain not in {"", "unknown", "request"}:
                return domain
        return "general"

    def detect_intent(self, report, terms, text):
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        requested_action = report.get("requested_action", {})
        requested_action = requested_action if isinstance(requested_action, dict) else {}
        candidates = [
            report.get("intent"),
            requested_action.get("intent_override"),
            contract.get("intent"),
            contract.get("global_picture", {}).get("intent")
            if isinstance(contract.get("global_picture"), dict) else None,
        ]
        for candidate in candidates:
            intent = str(candidate or "").strip().lower()
            if intent not in {"", "unknown", "request"}:
                return intent
        return "planning"

    def detect_scale(self, report, contract):
        detail = contract.get("detail_inventory", {}) if isinstance(contract, dict) else {}
        coverage = detail.get("coverage", {}) if isinstance(detail, dict) else {}
        requirement_count = len(contract.get("requirements", [])) if isinstance(contract, dict) else 0
        detail_count = sum(
            int(value or 0)
            for value in coverage.values()
            if isinstance(value, (int, float))
        ) if isinstance(coverage, dict) else 0
        feature_count = len(report.get("features", [])) if isinstance(report, dict) else 0
        complexity = requirement_count + detail_count + feature_count
        if complexity >= 18:
            return "professional"
        if complexity >= 9:
            return "large"
        if complexity <= 2:
            return "small"
        return "medium"

    def detect_output(self, report, contract, intent):
        constraints = contract.get("output_constraints", {}) if isinstance(contract, dict) else {}
        requested = str(constraints.get("requested_format") or "").strip().lower()
        if requested:
            return requested
        intent_outputs = {
            "code_generation": "code",
            "code_analysis": "code_review",
            "translation": "translation",
            "comparison": "comparison_table",
            "learning": "lesson",
            "research": "report",
            "story_creation": "story",
            "image_generation": "image",
            "movie_creation": "movie_project",
        }
        return intent_outputs.get(intent, "implementation_plan")

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

            fragments = [requirement_text]
            if len(requirement_text) > 100:
                split_fragments = [
                    fragment.strip(" -\t")
                    for fragment in re.split(r"(?<=[.!?])\s+|\n+", requirement_text)
                    if fragment.strip(" -\t")
                ]
                if len(split_fragments) > 1:
                    fragments = split_fragments
            for fragment_index, fragment in enumerate(fragments, start=1):
                key = re.sub(r"\s+", " ", fragment.lower()).strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                normalized = dict(requirement)
                base_id = requirement.get("id") or f"requirement_{index}"
                normalized["id"] = (
                    f"{base_id}_{fragment_index}" if len(fragments) > 1 else base_id
                )
                normalized["text"] = fragment
                normalized.setdefault("kind", "explicit_constraint")
                requirements.append(normalized)

        if not requirements and text:
            requirements.append({
                "id": "primary_goal",
                "text": re.sub(r"\s+", " ", text).strip()[:500],
                "kind": "goal"
            })

        return requirements[:80]

    def understanding_brains(self, report, domain):
        routed = [
            str(item)
            for item in report.get("routing_hints", [])
            if str(item).endswith("_brain")
            and str(item) not in {"Planner_brain", "Response_brain", "Manager_brain"}
        ]
        domain_owner = {
            "code": "Code_brain",
            "science": "Science_brain",
            "technology": "Technology_brain",
            "math": "Math_brain",
            "game": "Game_brain",
            "story": "Story_brain",
            "creative": "Creative_brain",
            "history": "History_brain",
            "geography": "Geography_brain",
            "language": "Language_brain",
            "security": "Security_brain",
        }.get(domain)
        if domain_owner:
            routed.insert(0, domain_owner)
        return list(dict.fromkeys(routed or ["Reasoning_brain"]))

    def requirement_brains(self, requirement, domain, routed_brains):
        owners = list(routed_brains[:6])
        kind = str(requirement.get("kind", "")).lower()
        if kind == "output_constraint":
            owners.extend(["Quality_Control_brain", "Response_brain"])
        if "continuation" in kind:
            owners.insert(0, "Memory_brain")
        return list(dict.fromkeys(owners or ["Reasoning_brain"]))

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

    def build_steps(self, template, dependency_data, memory_report, requirements, domain, routed_brains):

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
                    "needed_brains": self.requirement_brains(requirement, domain, routed_brains),
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

    def identify_missing_information(self, domain, intent, report, contract):

        missing = []
        report = report if isinstance(report, dict) else {}
        contract = contract if isinstance(contract, dict) else {}
        coverage = contract.get("coverage", {})
        coverage = coverage if isinstance(coverage, dict) else {}
        if report and not coverage.get("whole_input_analyzed", True):
            missing.append("Understanding_brain did not confirm whole-request analysis")

        target = contract.get("target")
        topic = contract.get("topic") or report.get("main_topic")
        entities = contract.get("entities", [])
        if (
            intent in {"research", "question"}
            and domain == "general"
            and not target
            and str(topic or "").lower() in {"", "general", "unknown", "request"}
            and not entities
        ):
            missing.append("Understanding_brain did not identify a specific research target")

        for item in contract.get("unresolved_details", []):
            value = item.get("text") if isinstance(item, dict) else item
            if value:
                missing.append(str(value))

        return list(dict.fromkeys(missing))[:12]

    def build_plan(self, domain, intent, scale, output, terms, memory_report, contract, report):

        matches = self.find_templates(
            domain,
            intent,
            scale,
            output,
            terms
        )

        advisory = matches[0]["template"] if matches else {}
        match_score = matches[0]["score"] if matches else 45
        matched_terms = matches[0]["matched_terms"] if matches else []
        routed_brains = self.understanding_brains(report, domain)
        continuation = contract.get("continuation", {}) if isinstance(contract, dict) else {}
        default_steps = [
            "confirm the understood goal, requested result, and every explicit constraint",
        ]
        if isinstance(continuation, dict) and continuation.get("requested"):
            default_steps.append("load the active conversation artifact and preserve its working behavior")
        default_steps.extend([
            "gather only the project context, evidence, and specialist input required by this request",
            "produce the requested result from the requirement contract",
            "integrate specialist outputs and resolve conflicts against the user's goal",
            "validate every requirement and prepare the requested output format",
        ])
        selected = {
            "id": "request_contract_plan",
            "domain": domain,
            "intent": intent,
            "scale": scale,
            "output": output,
            "name": "request-driven plan synthesized from Understanding_brain",
            "default_steps": default_steps,
            "needed_brains": routed_brains,
            "difficulty": advisory.get("difficulty", 60),
            "estimated_minutes": advisory.get("estimated_minutes", 30),
            "confidence": max(70, advisory.get("confidence", 60)),
            "quality_checks": advisory.get("quality_checks", []),
        }

        # Prebuilt dependency graphs are advisory only. The executable plan is
        # synthesized from the current request contract and its requirements.
        dependency_data = {}

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
            domain,
            routed_brains,
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
        missing = self.identify_missing_information(domain, intent, report, contract)

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
            "advisory_template_id": advisory.get("id"),
            "template_role": "quality_and_risk_reference_only",
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
            "dependency_graph_used": False,
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

        contract = self.get_request_contract(report, data)
        if not contract.get("global_picture"):
            contract["global_picture"] = {"goal": text}

        scale = self.detect_scale(
            report,
            contract
        )

        output = self.detect_output(
            report,
            contract,
            intent,
        )

        plan = self.build_plan(
            domain,
            intent,
            scale,
            output,
            terms,
            memory_report,
            contract,
            report,
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
