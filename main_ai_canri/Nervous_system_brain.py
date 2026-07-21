"""Cross-brain state integration for Canri.

This brain never writes the user-facing answer. It builds a compact neural
state from the request contract and current specialist results so Manager_brain
can target corrections without loading every project data file.
"""

import json
import re
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
PROFILE_FILE = DATA_DIR / "Nervous_system_profiles.json"


class NervousSystemBrain:

    def __init__(self):
        self.profile = self.load_profile()
        print("Nervous System Brain Loaded")

    def load_profile(self):
        try:
            with PROFILE_FILE.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def understanding(self, data):
        if not isinstance(data, dict):
            return {}
        report = data.get("understanding")
        return report if isinstance(report, dict) else {}

    def results(self, data):
        if not isinstance(data, dict):
            return {}
        results = data.get("results")
        return results if isinstance(results, dict) else {}

    def result_text(self, result):
        if not isinstance(result, dict):
            return ""
        project_files = result.get("project_files")
        if isinstance(project_files, dict) and project_files:
            return "\n".join(str(value) for value in project_files.values())
        for field in self.profile.get("candidate_fields", []):
            value = result.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def owner_brains(self, report):
        topic = str(report.get("main_topic", "general")).lower()
        domains = report.get("domains", [])
        requested = [topic]
        if isinstance(domains, list):
            requested.extend(str(item).lower() for item in domains)

        owners = []
        table = self.profile.get("domain_owners", {})
        for domain in requested:
            for brain_name in table.get(domain, []):
                if brain_name not in owners:
                    owners.append(brain_name)
        return owners or list(table.get("general", []))

    def active_brain_states(self, results):
        states = []
        for brain_name, result in results.items():
            if not isinstance(result, dict):
                continue
            text = self.result_text(result)
            states.append({
                "brain": brain_name,
                "confidence": result.get("confidence"),
                "has_output": bool(text),
                "output_characters": len(text),
                "error": bool(result.get("error")),
                "skipped": bool(result.get("skipped")),
                "self_review_ready": result.get("self_review", {}).get("ready"),
                "scanner_received": result.get("scanner_context", {}).get("received", False),
            })
        return states

    def candidate_score(self, brain_name, result, owners):
        if not isinstance(result, dict) or result.get("error") or result.get("skipped"):
            return -1000
        text = self.result_text(result)
        if not text:
            return -1000
        score = min(len(text) / 120.0, 25.0)
        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            score += float(confidence) * 0.55
        if brain_name in owners:
            score += 35 - owners.index(brain_name) * 4
        if brain_name in set(self.profile.get("internal_brains", [])):
            score -= 50
        if result.get("self_review", {}).get("ready") is True:
            score += 20
        elif result.get("self_review", {}).get("ready") is False:
            score -= 35
        alignment = result.get("self_review", {}).get("request_alignment", {})
        if isinstance(alignment.get("coverage"), (int, float)):
            score += float(alignment["coverage"]) * 0.15
        return round(score, 3)

    def best_candidate(self, results, owners):
        ranked = []
        for brain_name, result in results.items():
            score = self.candidate_score(brain_name, result, owners)
            if score <= -1000:
                continue
            ranked.append({
                "brain": brain_name,
                "score": score,
                "confidence": result.get("confidence"),
                "output_characters": len(self.result_text(result)),
            })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[0] if ranked else None, ranked[:8]

    def requirement_terms(self, requirement):
        ignored = {
            "the", "and", "for", "with", "from", "into", "only", "output",
            "final", "working", "program", "code", "user", "must", "should",
        }
        return [
            term for term in re.findall(r"[a-z][a-z0-9_]{2,}", str(requirement).lower())
            if term not in ignored
        ][:12]

    def requirement_check_index(self, results):

        index = {}
        quality = results.get("Quality_Control_brain", {})
        if isinstance(quality, dict):
            for check in quality.get("requirement_checks", []):
                if not isinstance(check, dict) or not check.get("requirement"):
                    continue
                index[str(check["requirement"])] = {
                    "passed": bool(check.get("passed")),
                    "source": "Quality_Control_brain",
                    "evidence": check.get("evidence"),
                }

        code_result = results.get("Code_brain", {})
        if isinstance(code_result, dict):
            alignment = code_result.get("self_review", {}).get("request_alignment", {})
            for check in alignment.get("checks", []) if isinstance(alignment, dict) else []:
                if not isinstance(check, dict) or not check.get("requirement"):
                    continue
                index.setdefault(str(check["requirement"]), {
                    "passed": bool(check.get("passed")),
                    "source": "CodeSelfReviewer",
                    "evidence": check.get("evidence"),
                })
            generation = code_result.get("generation_basis", {})
            for requirement_id in generation.get("verified_requirement_ids", []):
                index.setdefault(str(requirement_id), {
                    "passed": True,
                    "source": "Code_brain_generation_contract",
                    "evidence": "verified during request-driven assembly",
                })
            for requirement_id in generation.get("failed_requirement_ids", []):
                index.setdefault(str(requirement_id), {
                    "passed": False,
                    "source": "Code_brain_generation_contract",
                    "evidence": "not verified during request-driven assembly",
                })
        return index

    def requirement_state(self, report, results, owners):
        contract = report.get("request_contract", {})
        requirements = contract.get("requirements", []) if isinstance(contract, dict) else []
        check_index = self.requirement_check_index(results)
        specialist_text = " ".join(
            self.result_text(result).lower()
            for brain_name, result in results.items()
            if brain_name not in set(self.profile.get("internal_brains", []))
        )
        states = []
        for item in requirements[:100]:
            if isinstance(item, dict):
                requirement_id = item.get("id")
                text = item.get("text", "")
                kind = item.get("kind", "explicit_constraint")
            else:
                requirement_id = None
                text = str(item)
                kind = "explicit_constraint"
                feature = None
            if isinstance(item, dict):
                feature = item.get("feature")
            terms = self.requirement_terms(text)
            matches = [term for term in terms if term in specialist_text]
            checkable = kind in {"feature", "output_constraint"} or bool(terms)
            possible_ids = [
                str(value)
                for value in [
                    requirement_id,
                    feature,
                    f"feature_{feature}" if feature else None,
                ]
                if value
            ]
            exact_check = next(
                (check_index[key] for key in possible_ids if key in check_index),
                None,
            )
            if exact_check:
                covered = bool(exact_check["passed"])
                coverage_source = exact_check["source"]
                evidence = exact_check.get("evidence")
            else:
                threshold = max(1, min(3, (len(terms) + 2) // 3))
                covered = len(matches) >= threshold if terms else bool(specialist_text)
                coverage_source = "semantic_term_estimate"
                evidence = matches[:8]
            states.append({
                "id": requirement_id,
                "text": str(text)[:300],
                "kind": kind,
                "checkable": checkable,
                "covered": covered,
                "matched_terms": matches[:8],
                "coverage_source": coverage_source,
                "evidence": evidence,
                "suggested_owners": owners[:4],
            })
        return states

    def build_connections(self, active_states, owners):

        connections = []
        for state in active_states:
            source = state.get("brain")
            if not source or state.get("error") or state.get("skipped"):
                continue
            for target in owners[:4]:
                if source == target:
                    continue
                connections.append({
                    "from": source,
                    "to": target,
                    "signal": "specialist_result_available",
                    "strength": "high" if state.get("has_output") else "low",
                })
        return connections[:40]

    def improvement_opportunities(self, report, unresolved, best):

        contract = report.get("request_contract", {})
        policy = contract.get("enhancement_policy", {}) if isinstance(contract, dict) else {}
        opportunities = []
        for item in unresolved[:8]:
            opportunities.append({
                "type": "missing_requirement",
                "requirement_id": item.get("id"),
                "instruction": f"Complete and verify: {item.get('text', '')}",
                "owners": item.get("suggested_owners", [])[:4],
            })
        if policy.get("always_consider_improvements") and best:
            opportunities.extend([
                {
                    "type": "robustness",
                    "instruction": "Check realistic invalid input and failure paths without changing scope.",
                    "owners": [best.get("brain")],
                },
                {
                    "type": "precision",
                    "instruction": "Verify exact counts, names, files, literals, and output restrictions.",
                    "owners": [best.get("brain"), "Quality_Control_brain"],
                },
            ])
        return opportunities[:12]

    def compact_data_sources(self, data):
        if not isinstance(data, dict):
            return []
        sources = []
        for context_name in ["knowledge", "dictionary", "data_context", "memory"]:
            context = data.get(context_name)
            if isinstance(context, dict) and context.get("available", True):
                sources.append({
                    "context": context_name,
                    "matches": len(context.get("matches", [])) if isinstance(context.get("matches"), list) else 0,
                })
        return sources

    def process(self, data):
        report = self.understanding(data)
        results = self.results(data)
        owners = self.owner_brains(report)
        best, ranked = self.best_candidate(results, owners)
        requirement_states = self.requirement_state(report, results, owners)
        unresolved = [item for item in requirement_states if item.get("checkable") and not item.get("covered")]
        active_states = self.active_brain_states(results)
        manager_context = data.get("manager_context", {}) if isinstance(data, dict) else {}
        exact_coverage = sum(
            1 for item in requirement_states
            if item.get("coverage_source") != "semantic_term_estimate" and item.get("covered")
        )
        total_covered = sum(1 for item in requirement_states if item.get("covered"))

        return {
            "brain": "Nervous_system_brain",
            "internal_only": True,
            "confidence": 90 if best else 55,
            "request_topic": report.get("main_topic", "general"),
            "owner_brains": owners,
            "integration_stage": manager_context.get("phase", "neural_integration"),
            "active_brains": active_states,
            "brain_connections": self.build_connections(active_states, owners),
            "best_candidate": best,
            "ranked_candidates": ranked,
            "requirements": requirement_states,
            "unresolved_requirements": unresolved[:20],
            "coverage": {
                "total_requirements": len(requirement_states),
                "covered_requirements": total_covered,
                "exactly_verified_requirements": exact_coverage,
                "coverage_percent": round(
                    total_covered / max(len(requirement_states), 1) * 100,
                    2,
                ),
            },
            "improvement_opportunities": self.improvement_opportunities(
                report,
                unresolved,
                best,
            ),
            "correction_cycle": int(data.get("quality_retry_attempt", 0)) if isinstance(data, dict) else 0,
            "max_correction_cycles": int(self.profile.get("max_correction_cycles", 20)),
            "data_sources_used": self.compact_data_sources(data),
            "scanner_evidence_available": bool(
                isinstance(data, dict)
                and data.get("scanner_knowledge", {}).get("available")
            ),
            "suggested_next_brains": list(dict.fromkeys(
                brain_name
                for item in unresolved[:5]
                for brain_name in item.get("suggested_owners", [])
            )),
        }


brain = NervousSystemBrain()
