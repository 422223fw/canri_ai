import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Code_brain import CodeBrain


brain = CodeBrain()

request = {
    "understanding": {
        "original_text": "Create Python code that loads JSON, validates it, then saves it safely",
        "main_topic": "code",
        "intent": "code_generation",
        "topics": {
            "code": 1,
            "python": 1,
            "json": 1,
            "file": 1
        },
        "possible_tasks": [
            "code_generation",
            "file_io",
            "validation"
        ],
        "words": [
            {
                "word": "python",
                "exists": True,
                "connections": ["code", "function", "script"]
            },
            {
                "word": "json",
                "exists": True,
                "connections": ["file", "load", "save", "data"]
            },
            {
                "word": "validate",
                "exists": True,
                "connections": ["safe", "check", "error handling"]
            }
        ]
    },
    "memory": {
        "memory_found": 2,
        "topic_matches": [
            {
                "topic": "json",
                "keywords": ["safe load", "file path", "error handling"]
            }
        ],
        "intent_matches": [
            {
                "intent": "code_generation",
                "task": "safe json tool"
            }
        ]
    },
    "existing_code": "import json\n\n# project already has setup code\n"
}

result = brain.process(request)

summary = {
    "language": result["language"],
    "task_type": result["task_type"],
    "confidence": result["confidence"],
    "used_memory_report": result["used_memory_report"],
    "existing_code_detected": result["existing_code_detected"],
    "matched_functions": result["matched_functions"],
    "dependencies_added": result["dependencies_added"],
    "composition_rules": len(result["composition_rules_used"]),
    "ordered_ids": result["assembly_plan"]["ordered_ids"][:10],
    "data_files_used": result["assembly_plan"]["data_files_used"]
}

print(json.dumps(summary, ensure_ascii=False, indent=2))
