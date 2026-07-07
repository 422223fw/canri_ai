import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

TEMPLATES_FILE = DATA_DIR / "Planner_task_templates.json"
DEPENDENCY_FILE = DATA_DIR / "Planner_dependency_graph.json"
RISK_FILE = DATA_DIR / "Planner_risk_rules.json"
STATS_FILE = DATA_DIR / "Planner_statistics.json"


DOMAINS = {
    "code": {
        "brains": ["Technology_brain", "Code_brain", "Security_brain"],
        "steps": ["understand requirements", "choose architecture", "select functions", "assemble code", "test behavior"],
        "risks": ["missing requirements", "unsafe code", "integration mismatch"]
    },
    "science": {
        "brains": ["Science_brain", "Research_brain", "Fact_Check_brain"],
        "steps": ["define question", "collect evidence", "compare sources", "explain findings", "check uncertainty"],
        "risks": ["outdated evidence", "weak source", "overclaiming"]
    },
    "language": {
        "brains": ["Language_brain", "Memory_brain", "Response_brain"],
        "steps": ["detect language", "identify intent", "apply rules", "translate or explain", "check style"],
        "risks": ["lost meaning", "wrong tone", "grammar mismatch"]
    },
    "geography": {
        "brains": ["Geography_brain", "Research_brain", "Fact_Check_brain"],
        "steps": ["identify place", "classify geography type", "find local facts", "check current data", "format answer"],
        "risks": ["old population", "ambiguous place", "requires GPS"]
    },
    "technology": {
        "brains": ["Technology_brain", "Research_brain", "Security_brain"],
        "steps": ["detect technology domain", "check local knowledge", "compare options", "identify constraints", "recommend path"],
        "risks": ["obsolete tool", "hardware mismatch", "security issue"]
    },
    "history": {
        "brains": ["History_brain", "Research_brain", "Fact_Check_brain"],
        "steps": ["define period", "identify actors", "build timeline", "compare interpretations", "explain context"],
        "risks": ["source bias", "date confusion", "anachronism"]
    },
    "math": {
        "brains": ["Math_brain", "Reasoning_brain", "Fact_Check_brain"],
        "steps": ["parse problem", "identify formula", "solve step by step", "verify result", "explain method"],
        "risks": ["wrong formula", "unit mismatch", "calculation error"]
    },
    "game": {
        "brains": ["Game_brain", "Creative_brain", "Technology_brain", "Code_brain"],
        "steps": ["define gameplay loop", "design entities", "plan systems", "implement mechanics", "test balance"],
        "risks": ["scope creep", "unbalanced mechanic", "missing save system"]
    },
    "story": {
        "brains": ["Creative_brain", "Story_brain", "Character_brain", "World_brain"],
        "steps": ["define premise", "build characters", "create conflict", "outline scenes", "revise tone"],
        "risks": ["weak conflict", "flat character", "tone mismatch"]
    },
    "security": {
        "brains": ["Security_brain", "Technology_brain", "Response_brain"],
        "steps": ["classify safety level", "identify harmful parts", "block unsafe details", "offer safe alternative", "verify final response"],
        "risks": ["harmful instruction", "private data exposure", "unsafe execution"]
    }
}


INTENTS = [
    "question", "code_generation", "research", "translation", "explanation",
    "debugging", "learning", "comparison", "planning", "creative_creation"
]


SCALES = [
    "tiny", "small", "medium", "large", "professional",
    "production", "beginner", "advanced", "fast", "detailed"
]


OUTPUTS = [
    "answer", "code", "report", "checklist", "roadmap",
    "lesson", "comparison_table", "implementation_plan", "safe_response", "summary"
]


def difficulty_for(domain, intent, scale):
    score = 35

    if domain in ["code", "science", "technology", "security"]:
        score += 15
    if intent in ["code_generation", "research", "debugging", "planning"]:
        score += 12
    if scale in ["large", "professional", "production", "advanced", "detailed"]:
        score += 18

    return min(score, 100)


def make_template(index, domain, intent, scale, output):
    profile = DOMAINS[domain]
    difficulty = difficulty_for(domain, intent, scale)

    return {
        "id": f"plan_template_{index:04d}_{domain}_{intent}_{scale}_{output}",
        "domain": domain,
        "intent": intent,
        "scale": scale,
        "output": output,
        "name": f"{scale} {domain} {intent} plan for {output}",
        "trigger_terms": [domain, intent, scale, output],
        "default_steps": profile["steps"],
        "needed_brains": profile["brains"],
        "quality_checks": [
            "requirements are clear",
            "steps are ordered by dependency",
            "risky steps are reviewed before execution",
            "final answer matches the requested output"
        ],
        "difficulty": difficulty,
        "estimated_minutes": max(5, int(difficulty * 1.4)),
        "confidence": 82 if difficulty < 80 else 74
    }


def make_dependency(template):
    step_ids = []
    dependencies = {}

    for index, step in enumerate(template["default_steps"], start=1):
        step_id = f"{template['id']}_step_{index}"
        step_ids.append(step_id)
        dependencies[step_id] = {
            "name": step,
            "requires": step_ids[:-1][-2:],
            "before": step_ids[index:index + 2],
            "needed_brains": template["needed_brains"][:2],
            "order": index,
            "blocking": index <= 2
        }

    return {
        "id": f"dependency_{template['id']}",
        "template_id": template["id"],
        "domain": template["domain"],
        "intent": template["intent"],
        "ordered_steps": step_ids,
        "dependencies": dependencies,
        "critical_path": step_ids,
        "can_parallelize": step_ids[2:4],
        "confidence": template["confidence"]
    }


def make_risk_rule(index, template):
    profile = DOMAINS[template["domain"]]
    return {
        "id": f"risk_rule_{index:04d}_{template['domain']}_{template['intent']}",
        "domain": template["domain"],
        "intent": template["intent"],
        "scale": template["scale"],
        "risk_level": "high" if template["difficulty"] >= 80 else "medium" if template["difficulty"] >= 60 else "low",
        "risk_factors": profile["risks"],
        "mitigations": [
            "ask for clarification when requirements are incomplete",
            "use specialist brains before final response",
            "run Fact_Check_brain or Security_brain when risk is non-trivial",
            "keep uncertain claims marked as uncertain"
        ],
        "requires_review_by": [
            "Security_brain" if template["domain"] in ["code", "security", "technology"] else "Fact_Check_brain"
        ],
        "confidence": template["confidence"]
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    templates = {}
    dependencies = {}
    risks = {}

    index = 1
    for domain, intent, scale, output in product(DOMAINS, INTENTS, SCALES, OUTPUTS):
        template = make_template(index, domain, intent, scale, output)
        templates[template["id"]] = template
        dependencies[f"dependency_{template['id']}"] = make_dependency(template)
        risks[f"risk_rule_{index:04d}_{domain}_{intent}"] = make_risk_rule(index, template)
        index += 1

    statistics = {
        "Planner_brain": {
            "templates": len(templates),
            "dependency_graphs": len(dependencies),
            "risk_rules": len(risks),
            "last_build": "generated"
        }
    }

    write_json(TEMPLATES_FILE, templates)
    write_json(DEPENDENCY_FILE, dependencies)
    write_json(RISK_FILE, risks)
    write_json(STATS_FILE, statistics)

    print(json.dumps({
        "templates": len(templates),
        "dependency_graphs": len(dependencies),
        "risk_rules": len(risks)
    }, indent=2))


if __name__ == "__main__":
    main()
