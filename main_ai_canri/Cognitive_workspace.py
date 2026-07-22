"""Request-scoped cognitive workspace shared by Canri brains.

The workspace is an internal blackboard.  It turns the Understanding report,
conversation memory, retrieved evidence, and specialist results into one
decision state.  It deliberately rewards requirement coverage and evidence
instead of response length.
"""

from collections import defaultdict
import re


INTERNAL_BRAINS = {
    "Manager_brain",
    "Memory_brain",
    "Planner_brain",
    "Reasoning_brain",
    "Quality_Control_brain",
    "Learning_brain",
    "Collaboration_brain",
    "Nervous_system_brain",
    "Response_brain",
    "Security_brain",
}

DOMAIN_OWNERS = {
    "code": ["Code_brain", "Technology_brain"],
    "math": ["Math_brain"],
    "story": ["Story_brain", "Creative_brain", "Character_brain", "World_brain"],
    "science": ["Science_brain", "Research_brain", "Fact_Check_brain"],
    "knowledge": ["Research_brain", "Fact_Check_brain"],
    "technology": ["Technology_brain", "Research_brain", "Fact_Check_brain"],
    "geography": ["Geography_brain", "Research_brain", "Fact_Check_brain"],
    "history": ["History_brain", "Research_brain", "Fact_Check_brain"],
    "emotion": ["Emotion_brain"],
    "language": ["Language_brain", "Spelling_brain"],
    "image_generation": ["Image_brain", "Creative_brain"],
    "vision": ["Vision_brain"],
    "voice": ["Voice_brain"],
    "game": ["Game_brain", "Code_brain", "Creative_brain"],
    "planning": ["Planner_brain", "Reasoning_brain"],
    "general": ["Research_brain", "Fact_Check_brain"],
}

OUTPUT_FIELDS = (
    "final_output",
    "generated_code",
    "answer",
    "support_response",
    "story",
    "draft",
    "result",
    "response",
    "summary",
    "explanation",
    "solution",
    "translated_text",
    "game_design",
    "facts",
    "local_matches",
    "image_file",
    "generated_image_prompt",
)

FACTUAL_DOMAINS = {
    "science", "knowledge", "technology", "geography", "history", "health",
}

INTERNAL_REPORT_MARKERS = (
    "goal:",
    "core idea:",
    "novel twist:",
    "quality correction requirements:",
    "here is the useful conclusion:",
    "extract the complete request contract",
    "map every requirement to an owner",
    "the current draft did not pass canri's quality check",
)


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _confidence(value):
    if not isinstance(value, (int, float)):
        return 0.0
    value = float(value)
    if 0 <= value <= 1:
        value *= 100
    return max(0.0, min(100.0, value))


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _tokens(value):
    ignored = {
        "the", "and", "for", "with", "from", "into", "only", "must",
        "should", "this", "that", "user", "output", "final", "working",
        "program", "code", "result", "return", "using", "use",
    }
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9_+-]{2,}", str(value).lower())
        if token not in ignored
    }


class CognitiveWorkspace:
    """Build and update one compact decision state for a single request."""

    SCHEMA_VERSION = 1

    def create(self, request_id, report, memory=None, contexts=None):
        return self.refresh(
            {},
            report,
            memory or {},
            {},
            contexts or {},
            request_id=request_id,
        )

    def refresh(
        self,
        workspace,
        report,
        memory,
        results,
        contexts=None,
        request_id=None,
    ):
        previous = _as_dict(workspace)
        report = _as_dict(report)
        memory = _as_dict(memory)
        results = _as_dict(results)
        contexts = _as_dict(contexts)
        contract = _as_dict(report.get("request_contract"))
        domains = self._domains(report, contract)
        owners = self._owners(domains)
        requirements = self._requirements(contract, previous, owners)
        checks = self._requirement_checks(results)
        requirements = self._apply_checks(requirements, checks)
        evidence = self._evidence(contexts, results, previous)
        candidates = self._candidates(
            results,
            domains,
            owners,
            requirements,
            checks,
            evidence,
            contract,
        )
        selected = candidates[0] if candidates else None
        conflicts = self._conflicts(results, candidates)
        unresolved = [
            item for item in requirements
            if item.get("checkable", True) and item.get("status") != "passed"
        ]
        corrections = self._correction_packets(
            unresolved,
            requirements,
            checks,
            owners,
            results,
        )
        conversation = _as_dict(memory.get("conversation"))
        memory_state = self._memory_state(conversation, memory)
        coverage = self._coverage(requirements)
        goal = self._goal(contract, report)
        improvements = self._improvements(contract, unresolved, selected)

        return {
            "schema_version": self.SCHEMA_VERSION,
            "request_id": request_id or previous.get("request_id"),
            "internal_only": True,
            "goal": goal,
            "domains": domains,
            "primary_domain": domains[0] if domains else "general",
            "owner_brains": owners,
            "requirements": requirements,
            "non_negotiables": [
                {
                    "id": item.get("id"),
                    "text": item.get("text"),
                    "kind": item.get("kind"),
                    "quantity": item.get("quantity"),
                    "target": item.get("target"),
                    "values": item.get("values", []),
                }
                for item in requirements
                if item.get("kind") in {
                    "negative_constraint",
                    "quantified_constraint",
                    "interaction_constraint",
                    "output_constraint",
                }
            ],
            "coverage": coverage,
            "unresolved_requirements": unresolved[:40],
            "passed_requirement_ids": [
                item.get("id") for item in requirements if item.get("status") == "passed"
            ],
            "evidence": evidence[:60],
            "evidence_summary": self._evidence_summary(evidence),
            "candidates": candidates[:12],
            "selected_candidate": selected,
            "conflicts": conflicts[:30],
            "correction_packets": corrections[:12],
            "memory_state": memory_state,
            "improvement_opportunities": improvements,
            "decision": {
                "selected_brain": selected.get("brain") if selected else None,
                "selection_reason": (
                    "highest requirement, domain, evidence, and verification score"
                    if selected else "no usable specialist output yet"
                ),
                "ready_for_response": bool(
                    selected
                    and selected.get("usable")
                    and not any(
                        item.get("kind") in {
                            "quantified_constraint", "interaction_constraint", "output_constraint"
                        }
                        for item in unresolved
                    )
                ),
                "needs_correction": bool(unresolved and candidates),
            },
            "summary": {
                "goal": goal.get("goal"),
                "selected_brain": selected.get("brain") if selected else None,
                "coverage_percent": coverage.get("percent", 0),
                "unresolved_count": len(unresolved),
                "evidence_count": len(evidence),
                "conflict_count": len(conflicts),
                "continuation": memory_state.get("continuation", False),
            },
        }

    def view_for_brain(self, workspace, brain_name):
        workspace = _as_dict(workspace)
        requirements = _as_list(workspace.get("requirements"))
        owned = [
            item for item in requirements
            if brain_name in _as_list(item.get("owners"))
            or item.get("kind") in {
                "negative_constraint",
                "quantified_constraint",
                "interaction_constraint",
                "output_constraint",
            }
        ]
        if not owned:
            owned = requirements

        evidence = _as_list(workspace.get("evidence"))
        domain = str(workspace.get("primary_domain", "general"))
        if domain not in FACTUAL_DOMAINS and brain_name not in {
            "Research_brain", "Fact_Check_brain", "Science_brain",
            "Technology_brain", "Geography_brain", "History_brain",
        }:
            evidence = evidence[:8]

        packets = [
            item for item in _as_list(workspace.get("correction_packets"))
            if item.get("target_brain") == brain_name
        ]
        return {
            "internal_only": True,
            "request_id": workspace.get("request_id"),
            "target_brain": brain_name,
            "goal": workspace.get("goal", {}),
            "primary_domain": workspace.get("primary_domain"),
            "requirements": owned[:80],
            "non_negotiables": workspace.get("non_negotiables", [])[:40],
            "passed_requirement_ids": workspace.get("passed_requirement_ids", [])[:80],
            "unresolved_requirements": [
                item for item in owned if item.get("status") != "passed"
            ][:40],
            "evidence": evidence[:20],
            "evidence_summary": workspace.get("evidence_summary", {}),
            "memory_state": workspace.get("memory_state", {}),
            "selected_candidate": workspace.get("selected_candidate"),
            "peer_candidates": workspace.get("candidates", [])[:6],
            "conflicts": workspace.get("conflicts", [])[:12],
            "correction_packets": packets,
            "instruction": (
                "Work toward the shared goal, preserve every passed requirement, "
                "resolve the requirements assigned to this brain, and cite available "
                "evidence when making factual claims. Do not expose this workspace."
            ),
        }

    def receipt(self, workspace, brain_name):
        view = self.view_for_brain(workspace, brain_name)
        return {
            "received": True,
            "request_id": view.get("request_id"),
            "assigned_requirements": len(view.get("requirements", [])),
            "unresolved_assigned": len(view.get("unresolved_requirements", [])),
            "evidence_items": len(view.get("evidence", [])),
            "must_preserve": len(view.get("passed_requirement_ids", [])),
        }

    def _goal(self, contract, report):
        global_picture = _as_dict(contract.get("global_picture"))
        return {
            "goal": global_picture.get("goal") or report.get("original_text", ""),
            "action": global_picture.get("action") or contract.get("action"),
            "target": global_picture.get("target") or contract.get("target"),
            "topic": global_picture.get("topic") or report.get("main_topic", "general"),
            "intent": global_picture.get("intent") or report.get("intent", "unknown"),
            "requested_format": global_picture.get("requested_format"),
            "strict_output": bool(
                _as_dict(contract.get("enhancement_policy")).get("strict_output")
                or _as_dict(contract.get("output_constraints")).get("only_output")
            ),
        }

    def _domains(self, report, contract):
        values = []
        for value in [
            report.get("main_topic"),
            contract.get("topic"),
            *(_as_list(contract.get("central_domains"))),
            *(_as_list(report.get("domains"))),
        ]:
            clean = str(value or "").strip().lower()
            if clean and clean not in {"unknown", "request", "memory_context"}:
                values.append(clean)
        return list(dict.fromkeys(values))[:4] or ["general"]

    def _owners(self, domains):
        owners = []
        for domain in domains:
            for brain_name in DOMAIN_OWNERS.get(domain, []):
                if brain_name not in owners:
                    owners.append(brain_name)
        return owners or list(DOMAIN_OWNERS["general"])

    def _requirement_owner(self, item, owners):
        text = str(item.get("text", "")).lower()
        feature = str(item.get("feature", "")).lower()
        if any(term in f"{text} {feature}" for term in [
            "python", "function", "class", "json", "api", "database", "runnable",
        ]):
            return ["Code_brain"]
        if any(term in text for term in ["equation", "calculate", "math", "percent"]):
            return ["Math_brain"]
        if any(term in text for term in ["story", "character", "chapter", "sentence"]):
            return ["Story_brain", "Creative_brain"]
        return owners[:4]

    def _requirements(self, contract, previous, owners):
        old = {
            str(item.get("id")): item
            for item in _as_list(previous.get("requirements"))
            if isinstance(item, dict) and item.get("id")
        }
        output = []
        for index, value in enumerate(_as_list(contract.get("requirements"))[:120], start=1):
            item = dict(value) if isinstance(value, dict) else {
                "id": f"requirement_{index}",
                "text": str(value),
                "kind": "explicit_constraint",
            }
            item["id"] = str(item.get("id") or f"requirement_{index}")
            item["text"] = str(item.get("text") or item["id"])
            item.setdefault("kind", "explicit_constraint")
            item["owners"] = self._requirement_owner(item, owners)
            item["checkable"] = True
            previous_item = old.get(item["id"], {})
            item["status"] = previous_item.get("status", "unverified")
            item["verification_source"] = previous_item.get("verification_source")
            item["evidence"] = previous_item.get("evidence")
            item["attempts"] = int(previous_item.get("attempts", 0))
            output.append(item)
        return output

    def _requirement_checks(self, results):
        checks = defaultdict(list)

        def add(key, passed, source, evidence=None, target=None):
            clean = str(key or "").strip()
            if not clean:
                return
            checks[clean].append({
                "passed": bool(passed),
                "source": source,
                "evidence": evidence,
                "target_brain": target,
            })

        quality = _as_dict(results.get("Quality_Control_brain"))
        for check in _as_list(quality.get("requirement_checks")):
            if not isinstance(check, dict):
                continue
            add(
                check.get("requirement_id") or check.get("requirement"),
                check.get("passed"),
                "Quality_Control_brain",
                check.get("evidence") or check.get("reason"),
                check.get("target_brain"),
            )

        for brain_name, result in results.items():
            if not isinstance(result, dict):
                continue
            alignment = _as_dict(_as_dict(result.get("self_review")).get("request_alignment"))
            for check in _as_list(alignment.get("checks")):
                if not isinstance(check, dict):
                    continue
                add(
                    check.get("requirement_id") or check.get("requirement"),
                    check.get("passed"),
                    f"{brain_name}_self_review",
                    check.get("evidence"),
                    brain_name,
                )
            generation = _as_dict(result.get("generation_basis"))
            for requirement_id in _as_list(generation.get("verified_requirement_ids")):
                add(requirement_id, True, f"{brain_name}_generation", target=brain_name)
            for requirement_id in _as_list(generation.get("failed_requirement_ids")):
                add(requirement_id, False, f"{brain_name}_generation", target=brain_name)
        return dict(checks)

    def _apply_checks(self, requirements, checks):
        for item in requirements:
            possible = [item.get("id"), item.get("feature"), item.get("text")]
            matches = []
            for key in possible:
                matches.extend(_as_list(checks.get(str(key or ""))))
            if not matches:
                continue
            exact = next(
                (check for check in reversed(matches) if check.get("source") == "Quality_Control_brain"),
                matches[-1],
            )
            item["status"] = "passed" if exact.get("passed") else "failed"
            item["verification_source"] = exact.get("source")
            item["evidence"] = exact.get("evidence")
            item["attempts"] = int(item.get("attempts", 0)) + 1
        return requirements

    def _result_output(self, result):
        project_files = result.get("project_files")
        if isinstance(project_files, dict) and project_files:
            return "project_files", "\n".join(str(value) for value in project_files.values())
        for field in OUTPUT_FIELDS:
            value = result.get(field)
            if isinstance(value, str) and value.strip():
                return field, value.strip()
            if isinstance(value, (list, dict)) and value:
                return field, str(value)
            if isinstance(value, (int, float)):
                return field, str(value)
        return None, ""

    def _looks_internal(self, text):
        lowered = str(text).lower()
        return (
            sum(marker in lowered for marker in INTERNAL_REPORT_MARKERS[:3]) >= 2
            or any(marker in lowered for marker in INTERNAL_REPORT_MARKERS[3:])
        )

    def _candidate_checks(self, brain_name, requirements, checks, text):
        passed = 0
        failed = 0
        exact = 0
        semantic = 0
        lowered = str(text).lower()
        for item in requirements:
            possible = [item.get("id"), item.get("feature"), item.get("text")]
            matching = [
                check
                for key in possible
                for check in _as_list(checks.get(str(key or "")))
                if check.get("target_brain") in {None, brain_name}
            ]
            if matching:
                exact += 1
                if matching[-1].get("passed"):
                    passed += 1
                else:
                    failed += 1
                continue
            terms = _tokens(item.get("text"))
            if terms and len(terms & _tokens(lowered)) >= max(1, min(3, len(terms) // 2)):
                semantic += 1
        return {
            "exact_passed": passed,
            "exact_failed": failed,
            "exact_checked": exact,
            "semantic_matches": semantic,
            "total": len(requirements),
        }

    def _candidate_evidence_score(self, result, evidence, factual):
        sources = []
        for key in ["source_citations", "strongest_sources", "fetched_sources"]:
            sources.extend(item for item in _as_list(result.get(key)) if isinstance(item, dict))
        scanner = _as_dict(result.get("scanner_context"))
        if scanner.get("received"):
            sources.append({"trust_score": scanner.get("maximum_trust_score", 0)})
        trusted = [
            source for source in sources
            if _number(source.get("trust_score") or source.get("reliability_score")) >= 70
        ]
        if factual:
            if trusted:
                return min(15.0, 6.0 + len(trusted) * 2.0)
            if sources or evidence:
                return 5.0
            return -10.0
        return 5.0 if sources else 2.0

    def _candidates(self, results, domains, owners, requirements, checks, evidence, contract):
        candidates = []
        factual = any(domain in FACTUAL_DOMAINS for domain in domains)
        continuation = bool(_as_dict(contract.get("continuation")).get("requested"))
        quality = _as_dict(results.get("Quality_Control_brain"))
        retry_targets = {
            item.get("target_brain")
            for item in _as_list(quality.get("retry_requests"))
            if isinstance(item, dict) and item.get("target_brain")
        }

        for brain_name, result in results.items():
            if brain_name in INTERNAL_BRAINS or not isinstance(result, dict):
                continue
            field, text = self._result_output(result)
            if result.get("error") or result.get("skipped") or not text:
                continue
            score = 10.0
            reasons = ["usable specialist output"]
            if brain_name in owners:
                domain_score = max(12.0, 30.0 - owners.index(brain_name) * 4.0)
                score += domain_score
                reasons.append("matches the requested domain")
            else:
                domain_score = 2.0
                score += domain_score

            coverage = self._candidate_checks(brain_name, requirements, checks, text)
            total = max(coverage["total"], 1)
            exact_ratio = coverage["exact_passed"] / total
            semantic_ratio = coverage["semantic_matches"] / total
            coverage_score = min(35.0, exact_ratio * 35.0 + semantic_ratio * 9.0)
            score += coverage_score
            score -= coverage["exact_failed"] * 12.0
            if coverage["exact_passed"]:
                reasons.append(f"{coverage['exact_passed']} requirements verified")
            if coverage["exact_failed"]:
                reasons.append(f"{coverage['exact_failed']} requirements failed")

            self_review = _as_dict(result.get("self_review"))
            if self_review.get("ready") is True:
                score += 12.0
                reasons.append("self-review passed")
            elif self_review.get("ready") is False:
                score -= 25.0
                reasons.append("self-review failed")

            score += _confidence(result.get("confidence")) * 0.10
            score += self._candidate_evidence_score(result, evidence, factual)

            preservation = _as_dict(result.get("continuation_preservation"))
            generation = _as_dict(result.get("generation_basis"))
            if continuation:
                preserved = bool(
                    preservation.get("preserved")
                    or generation.get("continuation_preserved")
                    or result.get("continued_from_memory")
                )
                score += 10.0 if preserved else -8.0
                reasons.append("previous artifact preserved" if preserved else "continuation not verified")

            if brain_name in retry_targets:
                score -= 18.0
                reasons.append("quality control requested correction")
            if result.get("safe") is False:
                score -= 80.0
                reasons.append("unsafe result")
            if self._looks_internal(text):
                score -= 100.0
                reasons.append("contains internal process report")

            candidates.append({
                "brain": brain_name,
                "score": round(score, 3),
                "usable": score > 0 and not self._looks_internal(text),
                "output_field": field,
                "output_characters": len(text),
                "confidence": result.get("confidence"),
                "domain_score": domain_score,
                "requirement_score": round(coverage_score, 3),
                "coverage": coverage,
                "program_kind": result.get("program_kind"),
                "reasons": reasons[:10],
            })
        candidates.sort(key=lambda item: item.get("score", -1000), reverse=True)
        return candidates

    def _normalize_evidence(self, item, source_name):
        if not isinstance(item, dict):
            return None
        sources = _as_list(item.get("sources"))
        first_source = next((source for source in sources if isinstance(source, dict)), {})
        meanings = _as_list(item.get("meanings"))
        first_meaning = next((meaning for meaning in meanings if isinstance(meaning, dict)), {})
        title = (
            item.get("title")
            or item.get("name")
            or item.get("word")
            or item.get("file")
            or item.get("product")
            or item.get("company")
            or first_source.get("source_name")
        )
        excerpt = (
            item.get("summary")
            or item.get("excerpt")
            or item.get("definition")
            or first_meaning.get("definition")
            or item.get("description")
            or item.get("notes")
        )
        if not excerpt:
            sample = item.get("value_matches") or item.get("sample") or item.get("matched_terms")
            if isinstance(sample, (list, dict)) and sample:
                excerpt = str(sample)
        url = item.get("url") or first_source.get("url")
        trust = item.get("trust_score") or item.get("reliability_score") or first_source.get("trust_score")
        identity = item.get("article_id") or item.get("file") or url or title
        if not identity and not excerpt:
            return None
        return {
            "id": str(identity or excerpt)[:300],
            "title": str(title or identity or source_name)[:300],
            "excerpt": str(excerpt or "")[:1200],
            "url": url,
            "trust_score": trust,
            "source": source_name,
            "collection": item.get("collection"),
        }

    def _evidence(self, contexts, results, previous):
        evidence = []
        seen = set()

        def add(item, source):
            normalized = self._normalize_evidence(item, source)
            if not normalized:
                return
            identity = normalized["id"].lower()
            if identity in seen:
                return
            seen.add(identity)
            evidence.append(normalized)

        for item in _as_list(previous.get("evidence")):
            add(item, item.get("source", "previous_workspace") if isinstance(item, dict) else "previous_workspace")

        for context_name in ["scanner_knowledge", "knowledge", "data_context", "dictionary"]:
            context = _as_dict(contexts.get(context_name))
            for item in [
                *_as_list(context.get("matches")),
                *_as_list(context.get("entries")),
                *_as_list(context.get("company_matches")),
                *_as_list(context.get("product_matches")),
            ]:
                add(item, context_name)

        for brain_name, result in results.items():
            if not isinstance(result, dict):
                continue
            for key in ["strongest_sources", "fetched_sources", "source_citations", "facts"]:
                for item in _as_list(result.get(key)):
                    if isinstance(item, str):
                        item = {"title": item, "excerpt": item}
                    add(item, brain_name)
        evidence.sort(
            key=lambda item: _number(item.get("trust_score")),
            reverse=True,
        )
        return evidence[:60]

    def _evidence_summary(self, evidence):
        scores = [
            _number(item.get("trust_score"))
            for item in evidence
            if item.get("trust_score") is not None
        ]
        return {
            "count": len(evidence),
            "trusted_count": sum(score >= 70 for score in scores),
            "maximum_trust": max(scores, default=0),
            "sources": list(dict.fromkeys(
                str(item.get("source")) for item in evidence if item.get("source")
            ))[:20],
        }

    def _conflicts(self, results, candidates):
        conflicts = []
        reasoning = _as_dict(results.get("Reasoning_brain"))
        for item in _as_list(reasoning.get("contradictions")):
            conflicts.append({"type": "reasoning_contradiction", "detail": item})
        fact_check = _as_dict(results.get("Fact_Check_brain"))
        for key in ["conflicts", "contradictions", "unsupported_claims"]:
            for item in _as_list(fact_check.get(key)):
                conflicts.append({"type": key, "detail": item})
        quality = _as_dict(results.get("Quality_Control_brain"))
        for item in _as_list(quality.get("issues")):
            conflicts.append({"type": "quality_issue", "detail": item})
        program_kinds = {
            item.get("program_kind") for item in candidates[:5] if item.get("program_kind")
        }
        if len(program_kinds) > 1:
            conflicts.append({
                "type": "candidate_program_kind_disagreement",
                "detail": sorted(program_kinds),
            })
        return conflicts[:30]

    def _correction_packets(self, unresolved, requirements, checks, owners, results):
        grouped = defaultdict(list)
        for item in unresolved:
            target = (_as_list(item.get("owners")) or owners or ["Research_brain"])[0]
            grouped[target].append(item)

        quality = _as_dict(results.get("Quality_Control_brain"))
        existing = {
            item.get("target_brain"): item
            for item in _as_list(quality.get("retry_requests"))
            if isinstance(item, dict) and item.get("target_brain")
        }
        passed = [item.get("id") for item in requirements if item.get("status") == "passed"]
        packets = []
        for target, items in grouped.items():
            quality_request = _as_dict(existing.get(target))
            packets.append({
                "target_brain": target,
                "problem": quality_request.get("problem") or "Unresolved request requirements",
                "instruction": quality_request.get("instruction") or (
                    "Produce a corrected result that completes every listed requirement and "
                    "preserves all requirements that already passed."
                ),
                "failed_requirement_ids": [item.get("id") for item in items][:40],
                "failed_requirements": [item.get("text") for item in items][:40],
                "preserve_requirement_ids": passed[:80],
                "force_regeneration": bool(quality_request.get("force_regeneration")),
                "expected_program_kind": quality_request.get("expected_program_kind"),
            })
        return packets

    def _memory_state(self, conversation, memory):
        source = _as_dict(conversation.get("continuation_source"))
        thread = _as_dict(conversation.get("thread_state"))
        return {
            "session_id": memory.get("session_id"),
            "session_isolation": memory.get("session_isolation") is True,
            "continuation": bool(conversation.get("continuation_request")),
            "continuation_kind": conversation.get("continuation_kind", "none"),
            "source_turn_id": source.get("turn_id"),
            "active_topic": thread.get("active_topic"),
            "active_intent": thread.get("active_intent"),
            "active_goal": thread.get("active_goal"),
            "topic_stack": thread.get("topic_stack", []),
            "open_requirements": thread.get("open_requirements", []),
            "artifact_types": thread.get("artifact_types", []),
            "has_previous_code": bool(conversation.get("usable_previous_code")),
        }

    def _coverage(self, requirements):
        passed = sum(item.get("status") == "passed" for item in requirements)
        failed = sum(item.get("status") == "failed" for item in requirements)
        unverified = max(0, len(requirements) - passed - failed)
        return {
            "total": len(requirements),
            "passed": passed,
            "failed": failed,
            "unverified": unverified,
            "percent": round(passed / max(len(requirements), 1) * 100, 2),
            "exact_verification_only": True,
        }

    def _improvements(self, contract, unresolved, selected):
        policy = _as_dict(contract.get("enhancement_policy"))
        if unresolved or not selected or not policy.get("always_consider_improvements"):
            return []
        if policy.get("strict_output"):
            return []
        return [
            {
                "type": "robustness",
                "owner": selected.get("brain"),
                "instruction": "Improve realistic invalid-input and failure paths inside the requested scope.",
            },
            {
                "type": "precision",
                "owner": selected.get("brain"),
                "instruction": "Recheck exact names, counts, files, literals, and continuation behavior.",
            },
        ]
