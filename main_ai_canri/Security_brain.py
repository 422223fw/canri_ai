"""
Security_brain.py
Canri AI
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
STATS_FILE = DATA_DIR / "Security_statistics.json"


class SecurityBrain:

    def __init__(self):

        self.statistics = self.load_json(
            STATS_FILE,
            {}
        )

        self.danger_patterns = [
            {
                "name": "recursive_delete",
                "category": "destructive_code",
                "level": 100,
                "patterns": [
                    r"rm\s+-rf\s+/",
                    r"del\s+/f\s+/s\s+/q",
                    r"rmdir\s+/s\s+/q",
                    r"shutil\.rmtree",
                    r"os\.remove",
                    r"os\.unlink"
                ],
                "warning": "Potential file deletion detected"
            },
            {
                "name": "shell_execution",
                "category": "code_execution",
                "level": 80,
                "patterns": [
                    r"os\.system",
                    r"subprocess\.",
                    r"eval\s*\(",
                    r"exec\s*\("
                ],
                "warning": "Potential command or code execution detected"
            },
            {
                "name": "sensitive_file_access",
                "category": "privacy",
                "level": 45,
                "patterns": [
                    r"\bread\s+password",
                    r"\bdump\s+password",
                    r"\bextract\s+password",
                    r"\bsteal\s+password",
                    r"\bread\s+token",
                    r"\bdump\s+token",
                    r"\bextract\s+token",
                    r"\bsteal\s+token",
                    r"\bsecret\s+file\b",
                    r"\.env",
                    r"id_rsa",
                    r"\bcredentials\s+file\b",
                    r"\bdump\s+credentials\b",
                    r"\bextract\s+credentials\b"
                ],
                "warning": "Potential sensitive data access detected"
            },
            {
                "name": "network_download",
                "category": "network",
                "level": 60,
                "patterns": [
                    r"curl\s+",
                    r"wget\s+",
                    r"requests\.get",
                    r"urllib\.request"
                ],
                "warning": "Potential network download detected"
            },
            {
                "name": "infinite_loop",
                "category": "resource_abuse",
                "level": 50,
                "patterns": [
                    r"while\s+true\s*:",
                    r"while\s+1\s*:"
                ],
                "warning": "Potential infinite loop detected"
            },
            {
                "name": "prompt_injection",
                "category": "prompt_attack",
                "level": 75,
                "patterns": [
                    r"ignore\s+previous\s+instructions",
                    r"ignore\s+all\s+previous",
                    r"jailbreak",
                    r"developer\s+mode",
                    r"system\s+prompt"
                ],
                "warning": "Potential prompt injection detected"
            },
            {
                "name": "self_harm",
                "category": "self_harm",
                "level": 100,
                "patterns": [
                    r"\bsuicide\b",
                    r"\bkill\s+myself\b",
                    r"\bend\s+my\s+life\b",
                    r"\bhurt\s+myself\b",
                    r"\bself\s*harm\b",
                    r"\bwant\s+to\s+die\b",
                    r"\bhow\s+to\s+die\b",
                    r"\bhang\s+myself\b",
                    r"\boverdose\b",
                    r"להתאבד",
                    r"התאבדות",
                    r"למות",
                    r"לפגוע\s+בעצמי"
                ],
                "warning": "Self-harm related request detected"
            },
            {
                "name": "weapons_or_explosives",
                "category": "weapons",
                "level": 100,
                "patterns": [
                    r"\bmake\s+(a\s+)?bomb\b",
                    r"\bbuild\s+(a\s+)?bomb\b",
                    r"\bbomb\s+recipe\b",
                    r"\bexplosive\b",
                    r"\bdetonator\b",
                    r"\bnapalm\b",
                    r"\bmolotov\b",
                    r"\bgunpowder\b",
                    r"\bweapon\s+instructions\b",
                    r"לבנות\s+פצצה",
                    r"להכין\s+פצצה",
                    r"חומר\s+נפץ",
                    r"נפצים",
                    r"נשק"
                ],
                "warning": "Weapon or explosive instruction request detected"
            },
            {
                "name": "illegal_activity",
                "category": "illegal_abuse",
                "level": 90,
                "patterns": [
                    r"\bhack\s+into\b",
                    r"\bsteal\s+password",
                    r"\bcredit\s+card\s+steal",
                    r"\bphishing\b",
                    r"\bmalware\b",
                    r"\bransomware\b",
                    r"\bkeylogger\b",
                    r"\bbypass\s+security\b",
                    r"\bhide\s+from\s+police\b",
                    r"לפרוץ\s+ל",
                    r"לגנוב\s+סיסמא",
                    r"פישינג",
                    r"תוכנה\s+זדונית"
                ],
                "warning": "Illegal or abusive activity request detected"
            },
            {
                "name": "dangerous_medical_or_false_claim",
                "category": "medical_safety",
                "level": 80,
                "patterns": [
                    r"\bstop\s+taking\s+medicine\b",
                    r"\bignore\s+doctor\b",
                    r"\bdrink\s+bleach\b",
                    r"\bcure\s+cancer\s+with\b",
                    r"\bguaranteed\s+cure\b",
                    r"להפסיק\s+תרופות",
                    r"להתעלם\s+מהרופא",
                    r"תרופת\s+פלא",
                    r"ריפוי\s+מובטח"
                ],
                "warning": "Potential dangerous or unreliable medical claim detected"
            }
        ]

        print("Security Brain Loaded")

    def load_json(
        self,
        path,
        default
    ):

        if not path.exists():
            return default

        try:
            with path.open(
                "r",
                encoding="utf-8"
            ) as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self):

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with STATS_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                self.statistics,
                file,
                ensure_ascii=False,
                indent=2
            )
            file.write("\n")

    def extract_text(
        self,
        data
    ):

        if isinstance(
            data,
            str
        ):

            return data

        if not isinstance(
            data,
            dict
        ):

            return str(data)

        text_parts = []

        keys = [
            "user_message",
            "original_text",
            "corrected_text",
            "generated_code",
            "command",
            "code",
            "text"
        ]

        for key in keys:

            value = data.get(
                key
            )

            if value:

                text_parts.append(
                    str(value)
                )

        results = data.get(
            "results",
            {}
        )

        if (
            results
            and isinstance(
                results,
                dict
            )
        ):

            for result in results.values():

                text_parts.append(
                    self.extract_text(result)
                )

        understanding = data.get(
            "understanding",
            {}
        )

        if (
            understanding
            and isinstance(
                understanding,
                dict
            )
        ):

            text_parts.append(
                self.extract_text(understanding)
            )

        return "\n".join(text_parts)

    def safe_security_project_intent(self, text):

        lowered = str(text).lower()

        safe_project_markers = [
            "password manager",
            "password generator",
            "save/load all data from a json file",
            "terminal",
            "local",
            "do not use external libraries",
            "build a real runnable python"
        ]

        harmful_markers = [
            "steal",
            "phishing",
            "keylogger",
            "malware",
            "dump passwords",
            "extract passwords",
            "bypass security",
            "hack into",
            "read browser passwords",
            "browser cookies",
            "token grabber"
        ]

        return (
            any(marker in lowered for marker in safe_project_markers)
            and not any(marker in lowered for marker in harmful_markers)
        )

    def scan_text(
        self,
        text
    ):

        warnings = []
        blocked_items = []
        categories = []
        matches = []
        risk_level = 0

        lowered = text.lower()

        for danger in self.danger_patterns:

            for pattern in danger["patterns"]:

                if re.search(
                    pattern,
                    lowered
                ):

                    warnings.append(
                        danger["warning"]
                    )

                    blocked_items.append(
                        danger["name"]
                    )

                    categories.append(
                        danger.get(
                            "category",
                            "general"
                        )
                    )

                    matches.append({
                        "name": danger["name"],
                        "category": danger.get(
                            "category",
                            "general"
                        ),
                        "risk": danger["level"],
                        "warning": danger["warning"],
                        "matched_pattern": pattern
                    })

                    risk_level = max(
                        risk_level,
                        danger["level"]
                    )

                    break

        if self.safe_security_project_intent(text):
            safe_categories = {
                "privacy",
                "network",
                "resource_abuse"
            }
            filtered_matches = [
                match
                for match in matches
                if match.get("category") not in safe_categories
            ]
            if len(filtered_matches) != len(matches):
                matches = filtered_matches
                warnings = [
                    match["warning"]
                    for match in matches
                ]
                blocked_items = [
                    match["name"]
                    for match in matches
                ]
                categories = [
                    match["category"]
                    for match in matches
                ]
                risk_level = max(
                    [match["risk"] for match in matches],
                    default=25
                )

        return {
            "risk_level": risk_level,
            "warnings": list(dict.fromkeys(warnings)),
            "blocked_items": list(dict.fromkeys(blocked_items)),
            "categories": list(dict.fromkeys(categories)),
            "matches": matches
        }

    def calculate_safe(
        self,
        risk_level
    ):

        return risk_level < 70

    def risk_label(
        self,
        risk_level
    ):

        if risk_level >= 90:
            return "critical"
        if risk_level >= 70:
            return "high"
        if risk_level >= 40:
            return "medium"
        if risk_level > 0:
            return "low"
        return "none"

    def recommended_action(
        self,
        safe,
        scan
    ):

        categories = set(
            scan.get(
                "categories",
                []
            )
        )

        if "self_harm" in categories:
            return "block_harmful_details_and_provide_crisis_support"
        if categories & {"weapons", "illegal_abuse"}:
            return "block_operational_instructions_and_offer_safe_alternative"
        if categories & {"destructive_code", "code_execution"}:
            return "require_review_before_execution"
        if categories & {"medical_safety"}:
            return "avoid_medical_certainty_and_recommend_professional_help"
        if not safe:
            return "block_or_rewrite_safely"
        if scan.get("risk_level", 0) > 0:
            return "answer_with_caution"
        return "allow"

    def calculate_confidence(
        self,
        text,
        scan
    ):

        if not text.strip():
            return 40

        if scan.get("matches"):
            return min(
                98,
                72 + len(scan["matches"]) * 6 + scan.get("risk_level", 0) * 0.15
            )

        return 82

    def update_statistics(
        self,
        safe,
        risk_level,
        confidence
    ):

        stats = self.statistics.get(
            "Security_brain",
            {}
        )

        uses = stats.get(
            "uses",
            0
        )

        stats["uses"] = uses + 1
        stats["blocked"] = stats.get(
            "blocked",
            0
        ) + (0 if safe else 1)
        stats["last_risk_level"] = risk_level
        stats["last_confidence"] = round(
            confidence,
            2
        )
        stats["average_confidence"] = round(
            (
                stats.get("average_confidence", 0) * uses
                + confidence
            ) / max(stats["uses"], 1),
            2
        )
        stats["last_used_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

        self.statistics["Security_brain"] = stats
        self.save_statistics()

    def process(
        self,
        data
    ):

        text = self.extract_text(
            data
        )

        scan = self.scan_text(
            text
        )

        safe = self.calculate_safe(
            scan["risk_level"]
        )

        confidence = self.calculate_confidence(
            text,
            scan
        )

        risk_label = self.risk_label(
            scan["risk_level"]
        )

        action = self.recommended_action(
            safe,
            scan
        )

        self.update_statistics(
            safe,
            scan["risk_level"],
            confidence
        )

        return {
            "brain": "Security_brain",
            "safe": safe,
            "risk_level": scan["risk_level"],
            "risk_label": risk_label,
            "warnings": scan["warnings"],
            "blocked_items": scan["blocked_items"],
            "risk_categories": scan["categories"],
            "matches": scan["matches"][:20],
            "recommended_action": action,
            "checked_text_length": len(text),
            "confidence": round(confidence, 2),
            "suggested_next_brains": [
                brain_name
                for brain_name, enabled in [
                    ("Response_brain", True),
                    ("Fact_Check_brain", "medical_safety" in scan["categories"])
                ]
                if enabled
            ],
            "rules": [
                "Block self-harm, weapon, illegal, and destructive operational details.",
                "Allow safe technical and educational content with caution when risk is low.",
                "Return confidence so Learning_brain can measure security reliability.",
                "Prefer safe alternatives instead of only refusing."
            ]
        }


brain = SecurityBrain()
