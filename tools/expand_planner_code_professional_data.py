"""Add idempotent, structured planning and coding knowledge for Canri."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "main_ai_canri" / "data"


def load(name, default):
    path = DATA / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save(name, value):
    (DATA / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


PROJECTS = {
    "habit_tracker": {
        "aliases": ["habit tracker", "daily habits", "habit log"],
        "title": "Habit Tracker", "file": "habits.json",
        "fields": ["name", "frequency", "status", "description"],
        "search": ["name", "frequency", "status"], "numeric": []
    },
    "grade_book": {
        "aliases": ["grade book", "gradebook", "student grades"],
        "title": "Grade Book", "file": "grades.json",
        "fields": ["name", "subject", "grade", "description"],
        "search": ["name", "subject"], "numeric": ["grade"]
    },
    "recipe_manager": {
        "aliases": ["recipe manager", "cookbook", "recipe collection"],
        "title": "Recipe Manager", "file": "recipes.json",
        "fields": ["name", "category", "ingredients", "description"],
        "search": ["name", "category", "ingredients"], "numeric": []
    },
    "bookmark_manager": {
        "aliases": ["bookmark manager", "saved links", "web bookmarks"],
        "title": "Bookmark Manager", "file": "bookmarks.json",
        "fields": ["title", "url", "category", "description"],
        "search": ["title", "url", "category"], "numeric": []
    },
    "workout_log": {
        "aliases": ["workout log", "exercise tracker", "fitness log"],
        "title": "Workout Log", "file": "workouts.json",
        "fields": ["date", "name", "duration", "description"],
        "search": ["date", "name"], "numeric": ["duration"]
    },
    "time_tracker": {
        "aliases": ["time tracker", "time log", "hours worked"],
        "title": "Time Tracker", "file": "time_entries.json",
        "fields": ["date", "time", "name", "category", "hours", "description"],
        "search": ["date", "time", "name", "category"], "numeric": ["hours"]
    },
    "event_registration": {
        "aliases": ["event registration", "attendee list", "registrations"],
        "title": "Event Registration", "file": "registrations.json",
        "fields": ["name", "email", "date", "status"],
        "search": ["name", "email", "date", "status"], "numeric": []
    },
    "file_catalog": {
        "aliases": ["file catalog", "file organizer", "document catalog"],
        "title": "File Catalog", "file": "file_catalog.json",
        "fields": ["name", "category", "path", "description"],
        "search": ["name", "category", "path"], "numeric": []
    }
}

PROFILES = [
    "beginner", "compact", "validated", "fault_tolerant", "testable",
    "maintainable", "accessible", "portable", "auditable", "efficient",
    "extensible", "production_ready", "migration_safe", "search_optimized",
    "data_integrity", "error_resilient", "user_friendly", "modular",
    "documented", "quality_reviewed", "backup_ready", "unicode_safe",
    "deterministic", "boundary_tested", "release_ready"
]

FOCUSES = [
    "input_validation", "persistence", "error_handling", "search",
    "editing", "deletion", "reporting", "compatibility", "testing",
    "readability", "performance", "recovery", "requirements", "security",
    "usability"
]


def build_code_recipes():
    recipes = load("Code_project_recipes.json", {})
    for kind, spec in PROJECTS.items():
        for profile_index, profile in enumerate(PROFILES, start=1):
            for focus_index, focus in enumerate(FOCUSES[:5], start=1):
                recipe_id = f"recipe_{kind}_{profile}_{focus}"
                recipes[recipe_id] = {
                    "id": recipe_id,
                    "kind": kind,
                    "version": profile_index * 10 + focus_index,
                    "profile": profile,
                    "focus": focus,
                    "language": "python",
                    "architecture": "single_file_json_cli",
                    "generator": "json_record_cli",
                    "aliases": spec["aliases"],
                    "trigger_terms": spec["aliases"] + [profile, focus],
                    "title": spec["title"],
                    "file_name": spec["file"],
                    "fields": spec["fields"],
                    "search_fields": spec["search"],
                    "numeric_fields": spec["numeric"],
                    "total_expression": "1",
                    "total_label": "Records",
                    "components": [
                        "validated loader", "atomic saver", "record normalizer",
                        "add/list/search/delete commands", "number validation",
                        "help and command loop"
                    ],
                    "quality_gates": [
                        "Python syntax parses", "all requested fields are stored",
                        "invalid JSON is handled", "invalid numbers do not crash",
                        "save and load preserve records", f"review {focus}"
                    ],
                    "acceptance_criteria": [
                        f"The {spec['title']} starts without external libraries.",
                        f"Records persist in {spec['file']}.",
                        "Every advertised command has an implementation.",
                        "Malformed input produces a useful message instead of a crash."
                    ],
                    "quality_score": 80 + min(18, profile_index // 2 + focus_index)
                }
    save("Code_project_recipes.json", recipes)
    return len(recipes)


def build_planning_data():
    templates = load("Planner_task_templates.json", {})
    graphs = load("Planner_dependency_graph.json", {})
    risks = load("Planner_risk_rules.json", {})
    patterns = load("Planner_quality_patterns.json", {})

    domains = ["code", "math", "science", "story", "technology", "security", "language", "geography", "research", "general"]
    intents = ["code_generation", "planning", "debugging", "question", "research", "comparison", "learning", "analysis", "creation", "improvement"]
    scales = ["small", "medium", "large", "professional", "release"]
    outputs = ["code", "implementation_plan", "report", "answer", "roadmap"]

    count = 0
    for domain in domains:
        for intent in intents:
            for variant in range(10):
                scale = scales[variant % len(scales)]
                output = outputs[(variant + domains.index(domain)) % len(outputs)]
                focus = FOCUSES[variant % len(FOCUSES)]
                base_id = f"professional_{domain}_{intent}_{variant + 1:02d}"
                template_id = f"plan_{base_id}_{scale}_{output}"
                steps = [
                    "extract the complete request contract and exact constraints",
                    "map every requirement to an owner and acceptance check",
                    "choose architecture and interfaces before implementation",
                    "implement dependency-ready components",
                    "run focused validation and failure-path tests",
                    "verify every requirement and prepare the exact requested output"
                ]
                needed = ["Understanding_brain", "Reasoning_brain", "Quality_Control_brain"]
                specialist = {
                    "code": "Code_brain", "math": "Math_brain", "story": "Story_brain",
                    "security": "Security_brain", "science": "Science_brain",
                    "language": "Language_brain", "geography": "Geography_brain",
                    "research": "Research_brain", "technology": "Technology_brain"
                }.get(domain, "Manager_brain")
                needed.insert(2, specialist)
                templates[template_id] = {
                    "id": template_id, "domain": domain, "intent": intent,
                    "scale": scale, "output": output,
                    "name": f"{scale} {domain} {intent} plan focused on {focus}",
                    "trigger_terms": [domain, intent, scale, output, focus],
                    "default_steps": steps, "needed_brains": needed,
                    "quality_checks": [
                        "every explicit requirement has an implementation step",
                        "dependencies are acyclic and complete",
                        "failure paths and boundaries are tested",
                        "the final format matches the request exactly",
                        f"the {focus} quality focus is verified"
                    ],
                    "difficulty": 55 + variant * 3,
                    "estimated_minutes": 20 + variant * 10,
                    "confidence": 90
                }

                dependency_id = f"dependency_{template_id}"
                dependency_steps = {}
                ordered = []
                for step_index, step_name in enumerate(steps, start=1):
                    step_id = f"{template_id}_step_{step_index}"
                    ordered.append(step_id)
                    dependency_steps[step_id] = {
                        "name": step_name,
                        "requires": ordered[max(0, step_index - 3):step_index - 1],
                        "before": [], "needed_brains": needed,
                        "order": step_index, "blocking": step_index in {1, 2, 6}
                    }
                graphs[dependency_id] = {
                    "id": dependency_id, "template_id": template_id,
                    "domain": domain, "intent": intent,
                    "ordered_steps": ordered, "dependencies": dependency_steps,
                    "critical_path": ordered, "can_parallelize": ordered[2:5],
                    "confidence": 92
                }
                risk_id = f"risk_{base_id}_{scale}"
                risks[risk_id] = {
                    "id": risk_id, "domain": domain, "intent": intent, "scale": scale,
                    "risk_level": "high" if scale in {"professional", "release"} else "medium",
                    "risk_factors": [
                        "a small requirement is omitted", "a dependency is used before it is ready",
                        "happy-path-only validation", f"weak {focus}"
                    ],
                    "mitigations": [
                        "maintain a requirement coverage matrix", "topologically validate dependencies",
                        "test invalid and boundary inputs", "require evidence before final output"
                    ],
                    "requires_review_by": ["Quality_Control_brain", specialist],
                    "confidence": 92
                }
                pattern_id = f"quality_{base_id}"
                patterns[pattern_id] = {
                    "id": pattern_id, "domain": domain, "intent": intent,
                    "trigger_terms": [domain, intent, focus],
                    "quality_checks": [
                        "trace each requirement to a step and final evidence",
                        "validate interfaces, errors, boundaries, and persistence",
                        "compare the final result with the original request"
                    ],
                    "acceptance_criteria": [
                        "100 percent of extracted requirements are planned",
                        "the dependency graph contains no unresolved cycle",
                        "all blocking checks pass before response formatting"
                    ],
                    "deliverables": [output, "requirement coverage matrix", "validation evidence"],
                    "checkpoints": ["contract complete", "design validated", "implementation complete", "quality passed"],
                    "rollback_strategy": "Return to the last passed checkpoint and re-run only dependent steps.",
                    "quality_score": 90 + variant % 10
                }
                count += 1

    save("Planner_task_templates.json", templates)
    save("Planner_dependency_graph.json", graphs)
    save("Planner_risk_rules.json", risks)
    save("Planner_quality_patterns.json", patterns)
    return count, len(patterns)


if __name__ == "__main__":
    recipe_count = build_code_recipes()
    planning_count, quality_count = build_planning_data()
    print(json.dumps({
        "code_project_recipes": recipe_count,
        "professional_planning_records_added_or_updated": planning_count,
        "planner_quality_patterns": quality_count
    }, indent=2))
