"""
Security_brain.py
Canri AI
"""

import re


class SecurityBrain:

    def __init__(self):

        self.danger_patterns = [
            {
                "name": "recursive_delete",
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
                "level": 70,
                "patterns": [
                    r"password",
                    r"secret",
                    r"token",
                    r"\.env",
                    r"id_rsa",
                    r"credentials"
                ],
                "warning": "Potential sensitive data access detected"
            },
            {
                "name": "network_download",
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
                "level": 50,
                "patterns": [
                    r"while\s+true\s*:",
                    r"while\s+1\s*:"
                ],
                "warning": "Potential infinite loop detected"
            },
            {
                "name": "prompt_injection",
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

    def scan_text(
        self,
        text
    ):

        warnings = []
        blocked_items = []
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

                    risk_level = max(
                        risk_level,
                        danger["level"]
                    )

                    break

        return {
            "risk_level": risk_level,
            "warnings": list(dict.fromkeys(warnings)),
            "blocked_items": list(dict.fromkeys(blocked_items))
        }

    def calculate_safe(
        self,
        risk_level
    ):

        return risk_level < 70

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

        return {
            "brain": "Security_brain",
            "safe": safe,
            "risk_level": scan["risk_level"],
            "warnings": scan["warnings"],
            "blocked_items": scan["blocked_items"],
            "checked_text_length": len(text)
        }


brain = SecurityBrain()
