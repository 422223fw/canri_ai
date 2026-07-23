"""Cross-brain state integration for Canri.

This brain never writes the user-facing answer. It builds a compact neural
state from the request contract and current specialist results so Manager_brain
can target corrections without loading every project data file.
"""

import json
import re
from pathlib import Path

try:
    from Cognitive_workspace import CognitiveWorkspace
except Exception:
    CognitiveWorkspace = None


DATA_DIR = Path(__file__).parent / "data"
PROFILE_FILE = DATA_DIR / "Nervous_system_profiles.json"


class NervousSystemBrain:

    def __init__(self):
        self.profile = self.load_profile()
        self.workspace_builder = CognitiveWorkspace() if CognitiveWorkspace is not None else None
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
        if not domains:
            domains = report.get("central_domains", [])
        requested = [topic]
        if isinstance(domains, list):
            requested.extend(
                str(item.get("domain") if isinstance(item, dict) else item).lower()
                for item in domains
            )

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
                "source_evidence": bool(
                    result.get("source_citations")
                    or result.get("strongest_sources")
                    or result.get("scanner_evidence")
                    or result.get("scanner_knowledge_used")
                ),
                "needs_help": bool(result.get("needs_help")),
            })
        return states

    def candidate_score(self, brain_name, result, owners):
        if not isinstance(result, dict) or result.get("error") or result.get("skipped"):
            return -1000
        text = self.result_text(result)
        if not text:
            return -1000
        # Length is not intelligence. A usable output receives a small fixed
        # score; most points come from ownership, verification, and evidence.
        score = 10.0
        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            normalized = float(confidence) * (100 if 0 <= confidence <= 1 else 1)
            score += max(0.0, min(100.0, normalized)) * 0.10
        if brain_name in owners:
            score += 30 - owners.index(brain_name) * 4
        if brain_name in set(self.profile.get("internal_brains", [])):
            score -= 100
        if result.get("self_review", {}).get("ready") is True:
            score += 15
        elif result.get("self_review", {}).get("ready") is False:
            score -= 30
        alignment = result.get("self_review", {}).get("request_alignment", {})
        if isinstance(alignment.get("coverage"), (int, float)):
            coverage = float(alignment["coverage"])
            coverage = coverage * 100 if 0 <= coverage <= 1 else coverage
            score += max(0.0, min(100.0, coverage)) * 0.30
        scanner_context = result.get("scanner_context", {})
        if isinstance(scanner_context, dict) and scanner_context.get("received"):
            score += 4
        if result.get("source_citations") or result.get("strongest_sources"):
            score += 10
        lowered = text.lower()
        if any(marker in lowered for marker in [
            "no visual or file attachments were found",
            "no image attachment was found",
            "no audio attachment was found",
            "nothing was attached to inspect",
        ]):
            score -= 120
        if "the current draft did not pass canri's quality check" in lowered:
            score -= 100
        if "here is the useful conclusion:" in lowered:
            score -= 80
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

        active_by_name = {
            state.get("brain"): state
            for state in active_states
            if state.get("brain") and state.get("has_output")
        }
        active_owners = [name for name in owners if name in active_by_name]
        for index, source in enumerate(active_owners):
            for target in active_owners[index + 1:]:
                connections.append({
                    "from": source,
                    "to": target,
                    "signal": "cross_domain_consultation",
                    "strength": "high",
                })
                connections.append({
                    "from": target,
                    "to": source,
                    "signal": "cross_domain_consultation",
                    "strength": "high",
                })
        return connections[:40]

    def specialist_handoffs(self, results, owners, unresolved):
        handoffs = []
        for owner in owners[:6]:
            result = results.get(owner, {})
            if not isinstance(result, dict):
                result = {}
            handoffs.append({
                "brain": owner,
                "output_ready": bool(self.result_text(result)),
                "confidence": result.get("confidence"),
                "evidence_ready": bool(
                    result.get("source_citations")
                    or result.get("strongest_sources")
                    or result.get("scanner_evidence")
                    or result.get("scanner_knowledge_used")
                ),
                "needs_help": bool(result.get("needs_help") or result.get("error")),
                "unresolved_requirements": [
                    item.get("id") or item.get("text")
                    for item in unresolved
                    if owner in item.get("suggested_owners", [])
                ][:10],
            })
        return handoffs

    def synthesis_brief(self, report, best, owners, unresolved, scanner_state):
        contract = report.get("request_contract", {}) if isinstance(report, dict) else {}
        constraints = contract.get("output_constraints", {}) if isinstance(contract, dict) else {}
        return {
            "selected_brain": best.get("brain") if isinstance(best, dict) else None,
            "consulted_owners": owners[:6],
            "unresolved_count": len(unresolved),
            "trusted_evidence_available": bool(scanner_state.get("available")),
            "strict_output": bool(constraints.get("only_output")),
            "instructions": [
                "Use the selected specialist output as the base answer.",
                "Merge only evidence or corrections that improve an explicit requirement.",
                "Do not select a media brain's missing-attachment notice for a text-only request.",
                "Preserve strict output constraints and keep internal coordination hidden.",
            ],
        }

    def scanner_state(self, data):

        scanner = data.get("scanner_knowledge", {}) if isinstance(data, dict) else {}
        matches = scanner.get("matches", []) if isinstance(scanner, dict) else []
        matches = [item for item in matches if isinstance(item, dict)]
        trust_scores = [
            float(item.get("trust_score") or 0)
            for item in matches
            if isinstance(item.get("trust_score"), (int, float))
        ]
        source_ids = list(dict.fromkeys(
            source.get("source_id")
            for item in matches
            for source in item.get("sources", [])
            if isinstance(source, dict) and source.get("source_id")
        ))
        return {
            "available": bool(matches),
            "matches": len(matches),
            "collections": sorted({item.get("collection", "trusted_knowledge") for item in matches}),
            "source_ids": source_ids[:20],
            "average_trust": round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0,
            "maximum_trust": max(trust_scores, default=0),
            "retrieval": scanner.get("retrieval"),
        }

    def memory_state(self, data):

        memory = data.get("memory", {}) if isinstance(data, dict) else {}
        conversation = memory.get("conversation", {}) if isinstance(memory, dict) else {}
        return {
            "session_id": memory.get("session_id") if isinstance(memory, dict) else None,
            "session_isolation": memory.get("session_isolation") is True if isinstance(memory, dict) else False,
            "continuation": bool(conversation.get("continuation_request")),
            "continuation_kind": conversation.get("continuation_kind", "none"),
            "continuation_turn_id": (
                conversation.get("continuation_source", {}).get("turn_id")
                if isinstance(conversation.get("continuation_source"), dict)
                else None
            ),
            "thread_state": conversation.get("thread_state", {}),
        }

    def correction_packets(self, results, unresolved, owners):

        quality = results.get("Quality_Control_brain", {})
        requests = quality.get("retry_requests", []) if isinstance(quality, dict) else []
        packets = []
        for request in requests[:8]:
            if not isinstance(request, dict) or not request.get("target_brain"):
                continue
            packets.append({
                "target_brain": request.get("target_brain"),
                "problem": request.get("problem"),
                "instruction": request.get("instruction"),
                "expected_program_kind": request.get("expected_program_kind"),
                "failed_requirements": request.get("failed_requirement_checks") or request.get("failed_requirements", []),
                "required_features": request.get("required_features", []),
                "force_regeneration": bool(request.get("force_regeneration")),
                "preserve_passed_requirements": True,
            })
        if not packets:
            for item in unresolved[:8]:
                packets.append({
                    "target_brain": (item.get("suggested_owners") or owners or ["Reasoning_brain"])[0],
                    "problem": f"Unresolved requirement: {item.get('text', '')}",
                    "instruction": f"Complete and verify: {item.get('text', '')}",
                    "failed_requirements": [item.get("id") or item.get("text")],
                    "preserve_passed_requirements": True,
                })
        return packets[:10]

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
        workspace = data.get("cognitive_workspace", {}) if isinstance(data, dict) else {}
        if self.workspace_builder is not None:
            workspace = self.workspace_builder.refresh(
                workspace,
                report,
                data.get("memory", {}) if isinstance(data, dict) else {},
                results,
                {
                    "knowledge": data.get("knowledge", {}),
                    "scanner_knowledge": data.get("scanner_knowledge", {}),
                    "dictionary": data.get("dictionary", {}),
                    "data_context": data.get("full_data_context") or data.get("data_context", {}),
                } if isinstance(data, dict) else {},
                request_id=workspace.get("request_id") if isinstance(workspace, dict) else None,
            )
        owners = workspace.get("owner_brains", []) or self.owner_brains(report)
        workspace_ranked = workspace.get("candidates", []) if isinstance(workspace, dict) else []
        if workspace_ranked:
            ranked = workspace_ranked[:8]
            best = workspace.get("selected_candidate") or ranked[0]
        else:
            best, ranked = self.best_candidate(results, owners)
        if isinstance(workspace, dict) and workspace.get("requirements") is not None:
            requirement_states = [
                {
                    **item,
                    "covered": item.get("status") == "passed",
                    "coverage_source": item.get("verification_source") or "unverified",
                    "suggested_owners": item.get("owners", owners[:4]),
                }
                for item in workspace.get("requirements", [])
                if isinstance(item, dict)
            ]
        else:
            requirement_states = self.requirement_state(report, results, owners)
        unresolved = [item for item in requirement_states if item.get("checkable") and not item.get("covered")]
        active_states = self.active_brain_states(results)
        manager_context = data.get("manager_context", {}) if isinstance(data, dict) else {}
        exact_coverage = sum(
            1 for item in requirement_states
            if item.get("coverage_source") != "semantic_term_estimate" and item.get("covered")
        )
        total_covered = sum(1 for item in requirement_states if item.get("covered"))
        scanner_state = self.scanner_state(data)
        memory_state = self.memory_state(data)
        brain_connections = self.build_connections(active_states, owners)
        if scanner_state["available"]:
            for owner in owners[:4]:
                brain_connections.append({
                    "from": "Scanner_knowledge",
                    "to": owner,
                    "signal": "indexed_source_evidence",
                    "strength": "high" if scanner_state["maximum_trust"] >= 80 else "medium",
                })
        if memory_state["continuation"]:
            for owner in owners[:4]:
                brain_connections.append({
                    "from": "Memory_brain",
                    "to": owner,
                    "signal": f"continuation_{memory_state['continuation_kind']}",
                    "strength": "high",
                })

        specialist_handoffs = self.specialist_handoffs(
            results,
            owners,
            unresolved,
        )
        synthesis_brief = self.synthesis_brief(
            report,
            best,
            owners,
            unresolved,
            scanner_state,
        )

        return {
            "brain": "Nervous_system_brain",
            "internal_only": True,
            "confidence": 90 if best else 55,
            "request_topic": report.get("main_topic", "general"),
            "owner_brains": owners,
            "integration_stage": manager_context.get("phase", "neural_integration"),
            "active_brains": active_states,
            "brain_connections": brain_connections[:50],
            "specialist_handoffs": specialist_handoffs,
            "synthesis_brief": synthesis_brief,
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
            "correction_packets": (
                workspace.get("correction_packets", [])
                if isinstance(workspace, dict) and workspace.get("correction_packets") is not None
                else self.correction_packets(results, unresolved, owners)
            ),
            "memory_state": memory_state,
            "scanner_state": scanner_state,
            "correction_cycle": int(data.get("quality_retry_attempt", 0)) if isinstance(data, dict) else 0,
            "max_correction_cycles": int(self.profile.get("max_correction_cycles", 20)),
            "data_sources_used": self.compact_data_sources(data),
            "scanner_evidence_available": scanner_state["available"],
            "cognitive_workspace": {
                "summary": workspace.get("summary", {}) if isinstance(workspace, dict) else {},
                "decision": workspace.get("decision", {}) if isinstance(workspace, dict) else {},
                "evidence_summary": workspace.get("evidence_summary", {}) if isinstance(workspace, dict) else {},
            },
            "suggested_next_brains": list(dict.fromkeys(
                brain_name
                for item in unresolved[:5]
                for brain_name in item.get("suggested_owners", [])
            )),
        }


brain = NervousSystemBrain()
