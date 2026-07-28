"""Top-level Canri application brain and runtime health facade."""

from datetime import datetime, timezone

from Brain_runtime import brain_runtime
from Canri_identity import release_version


class MainBrain:

    VERSION = release_version()

    def __init__(self):
        print("Main Brain Started")

    def process(self, data):
        """Return application status without exposing private request content."""

        request = data if isinstance(data, dict) else {"command": str(data or "status")}
        health = brain_runtime.health_snapshot()
        totals = health.get("totals", {})
        calls = int(totals.get("calls", 0) or 0)
        successes = int(totals.get("success", 0) or 0)
        return {
            "brain": "Main_brain",
            "version": self.VERSION,
            "status": "ready",
            "command": request.get("command", "status"),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_contract": brain_runtime.CONTRACT_VERSION,
            "health": {
                "recorded_calls": calls,
                "successful_calls": successes,
                "success_rate_percent": round(successes / max(calls, 1) * 100, 2),
                "brains_observed": len(health.get("brains", {})),
            },
            "confidence": 100,
        }


brain = MainBrain()
