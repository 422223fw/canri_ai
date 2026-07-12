"""
Fact_Check_brain.py
Canri AI

Checks whether information from Canri brains is reliable enough to present.
It does not invent facts. It scores evidence, source quality, contradictions,
claim risk, and whether stronger research is needed.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from Data_context import best_data_sources
except ImportError:
    best_data_sources = None


DATA_DIR = Path(__file__).parent / "data"
RULES_FILE = DATA_DIR / "Fact_check_rules.json"
STATS_FILE = DATA_DIR / "Fact_check_statistics.json"


HIGH_STAKES_TOPICS = {
    "health", "medical", "medicine", "security", "legal", "law",
    "finance", "money", "investment", "safety", "suicide", "weapon",
    "bomb", "malware", "phishing", "ransomware",
    "בריאות", "רפואה", "אבטחה", "חוק", "כסף", "השקעה", "התאבדות", "פצצה"
}

WEAK_LANGUAGE = {
    "maybe", "probably", "i think", "not sure", "unknown", "guess",
    "אולי", "נראה לי", "לא בטוח", "כנראה"
}

STRONG_SOURCE_TYPES = {
    "official_archive", "official_library", "academic_database",
    "medical_database", "public_health_authority", "official_science_agency",
    "standards_body", "government", "official"
}


class FactCheckBrain:

    def __init__(self):

        self.rules = self.load_json(RULES_FILE, [])
        self.statistics = self.load_json(STATS_FILE, {})

        print("Fact Check Brain Loaded")

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

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

    # ---------- input ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {}

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if "main_topic" in data or "intent" in data or "words" in data:
            return data

        return {}

    def get_results(self, data):

        if not isinstance(data, dict):
            return {}

        results = data.get("results")

        if isinstance(results, dict):
            return results

        return {}

    def extract_text(self, data):

        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            return str(data)

        parts = []

        for key in [
            "original_text", "corrected_text", "user_message", "question",
            "query", "text", "answer", "summary", "claim", "goal"
        ]:
            value = data.get(key)
            if value:
                parts.append(str(value))

        understanding = data.get("understanding")
        if isinstance(understanding, dict):
            for key in ["original_text", "corrected_text", "main_topic", "intent"]:
                value = understanding.get(key)
                if value:
                    parts.append(str(value))

        return " ".join(parts).strip()

    def collect_claims(self, data, results):

        claims = []

        if isinstance(data, dict):
            for fact in data.get("facts", []):
                claims.append(self.make_claim(fact, "input", "explicit_fact"))

            for claim in data.get("claims", []):
                claims.append(self.make_claim(claim, "input", "explicit_claim"))

        for brain_name, result in results.items():
            self.collect_claims_from_result(brain_name, result, claims)

        if not claims:
            text = self.extract_text(data)
            for sentence in self.extract_sentences(text)[:12]:
                if self.looks_like_claim(sentence):
                    claims.append(self.make_claim(sentence, "input_text", "sentence"))

        return self.dedupe_claims(claims)

    def collect_claims_from_result(self, brain_name, result, claims):

        if not isinstance(result, dict):
            return

        for key in ["facts", "verified_facts", "findings", "conclusions", "local_matches"]:
            value = result.get(key)
            if isinstance(value, list):
                for item in value[:20]:
                    claims.append(self.make_claim(item, brain_name, key))

        for key in ["answer", "summary", "best_answer", "result", "explanation"]:
            value = result.get(key)
            if isinstance(value, str):
                for sentence in self.extract_sentences(value)[:8]:
                    if self.looks_like_claim(sentence):
                        claims.append(self.make_claim(sentence, brain_name, key))

    def make_claim(self, value, source_brain, claim_type):

        if isinstance(value, dict):
            text = (
                value.get("claim")
                or value.get("fact")
                or value.get("definition")
                or value.get("summary")
                or value.get("text")
                or str(value)
            )
            confidence = value.get("confidence")
        else:
            text = str(value)
            confidence = None

        return {
            "text": re.sub(r"\s+", " ", text).strip(),
            "source_brain": source_brain,
            "type": claim_type,
            "confidence": confidence
        }

    def extract_sentences(self, text):

        text = re.sub(r"\s+", " ", str(text)).strip()
        if not text:
            return []

        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|[\n\r]+", text)
            if sentence.strip()
        ]

    def looks_like_claim(self, sentence):

        lowered = sentence.lower()

        if len(sentence) < 12:
            return False

        if "?" in sentence:
            return False

        claim_markers = [
            " is ", " are ", " was ", " were ", " has ", " have ",
            " can ", " causes ", " means ", " equals ", " contains ",
            " cures ", " prevents ", " proves ", " increases ", " reduces ",
            "הוא", "היא", "זה", "גורם", "כולל", "שווה", "נחשב"
        ]

        return any(marker in lowered for marker in claim_markers)

    def dedupe_claims(self, claims):

        seen = set()
        clean = []

        for claim in claims:
            text = claim.get("text", "").strip()
            key = text.lower()

            if not text or key in seen:
                continue

            seen.add(key)
            clean.append(claim)

        return clean[:80]

    def classify_claim(self, claim):

        text = str(claim.get("text", "") if isinstance(claim, dict) else claim).strip()
        lowered = f" {text.lower()} "
        opinion_markers = [
            " i think ", " i believe ", " in my opinion ", " seems ",
            " beautiful ", " boring ", " amazing ", " best ", " worst ",
            " should ", " ought to ", " prefer ", " feels "
        ]
        prediction_markers = [
            " will probably ", " may become ", " is expected to ",
            " likely to ", " forecast ", " predict "
        ]
        recommendation_markers = [
            " should ", " recommend ", " advice ", " better to ", " try to "
        ]

        if any(marker in lowered for marker in recommendation_markers):
            kind = "recommendation"
            verifiable = False
        elif any(marker in lowered for marker in opinion_markers):
            kind = "opinion"
            verifiable = False
        elif any(marker in lowered for marker in prediction_markers):
            kind = "prediction"
            verifiable = True
        else:
            kind = "factual_claim"
            verifiable = True

        return {
            "text": text,
            "kind": kind,
            "verifiable": verifiable,
            "reason": f"classified_as_{kind}"
        }

    def classify_claims(self, claims):

        classified = []
        counts = {
            "factual_claim": 0,
            "opinion": 0,
            "prediction": 0,
            "recommendation": 0
        }
        for claim in claims:
            classification = self.classify_claim(claim)
            enriched = dict(claim)
            enriched["classification"] = classification["kind"]
            enriched["verifiable"] = classification["verifiable"]
            enriched["classification_reason"] = classification["reason"]
            classified.append(enriched)
            counts[classification["kind"]] = counts.get(classification["kind"], 0) + 1
        return classified, counts

    # ---------- evidence ----------

    def collect_evidence(self, data, results):

        evidence = []

        if isinstance(data, dict):
            self.collect_evidence_from_result("input", data, evidence)

        for brain_name, result in results.items():
            if isinstance(result, dict):
                self.collect_evidence_from_result(brain_name, result, evidence)

        return evidence[:120]

    def collect_local_data_evidence(self, text, report, claims):

        if best_data_sources is None:
            return []

        query_parts = [text]

        for key in ["main_topic", "intent", "summary", "corrected_text", "original_text"]:
            value = report.get(key) if isinstance(report, dict) else None
            if value:
                query_parts.append(str(value))

        for claim in claims[:8]:
            claim_text = claim.get("text")
            if claim_text:
                query_parts.append(claim_text)

        query = " ".join(query_parts).strip()
        if not query:
            return []

        local_sources = []
        for source in best_data_sources(query, limit=8):
            trust_score = source.get("trust_score", 55)
            try:
                trust_score = float(trust_score)
            except (TypeError, ValueError):
                trust_score = 55

            local_sources.append({
                "source_brain": "Data_context",
                "name": source.get("name", "local data"),
                "url": "",
                "source_type": "local_data_json",
                "trust_score": max(0, min(round(trust_score, 2), 85)),
                "supports": source.get("supports", []),
                "notes": source.get("notes", ""),
                "sample": source.get("sample", [])[:5]
            })

        return local_sources

    def collect_context_evidence(self, data):

        if not isinstance(data, dict):
            return []

        evidence = []

        shared = data.get("shared_context", {})
        if not isinstance(shared, dict):
            shared = data.get("manager_context", {}).get("shared_context", {})
        if not isinstance(shared, dict):
            shared = {}

        data_context = data.get("data_context", {})
        if not isinstance(data_context, dict):
            data_context = data.get("manager_context", {}).get("data_context", {})
        if not isinstance(data_context, dict):
            data_context = {}

        knowledge = data.get("knowledge", {})
        if not isinstance(knowledge, dict):
            knowledge = data.get("manager_context", {}).get("knowledge", {})
        if not isinstance(knowledge, dict):
            knowledge = {}

        dictionary = data.get("dictionary", {})
        if not isinstance(dictionary, dict):
            dictionary = data.get("manager_context", {}).get("dictionary", {})
        if not isinstance(dictionary, dict):
            dictionary = {}

        local_data = shared.get("local_data", {}) if isinstance(shared.get("local_data"), dict) else {}
        data_sources = local_data.get("data_sources") or data_context.get("matches", [])
        for source in data_sources[:10]:
            if not isinstance(source, dict):
                continue
            score = source.get("score", 0) or 0
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 0
            evidence.append({
                "source_brain": "Data_context",
                "name": source.get("file", "local data"),
                "url": "",
                "source_type": "local_data_json",
                "trust_score": max(45, min(round(58 + score * 0.6, 2), 85)),
                "supports": source.get("matched_terms", [])[:10],
                "notes": f"Relevant Canri DATA file. Shape: {source.get('shape')}, items: {source.get('items')}",
                "sample": source.get("value_matches", [])[:4] or source.get("sample", [])[:6]
            })

        for item in knowledge.get("matches", [])[:8]:
            if not isinstance(item, dict):
                continue
            sources = item.get("sources", [])
            trust = 78
            if sources and isinstance(sources[0], dict):
                trust = sources[0].get("trust_score", sources[0].get("source_trust", trust))
            try:
                trust = float(trust)
            except (TypeError, ValueError):
                trust = 78
            evidence.append({
                "source_brain": "Knowledge_database",
                "name": item.get("title", "knowledge article"),
                "url": "",
                "source_type": "local_knowledge_article",
                "trust_score": max(50, min(round(trust, 2), 90)),
                "supports": item.get("terms", [])[:12],
                "notes": str(item.get("summary", ""))[:500]
            })

        for entry in dictionary.get("entries", [])[:10]:
            if not isinstance(entry, dict):
                continue
            meanings = entry.get("meanings", [])
            evidence.append({
                "source_brain": "UnderstandingDk",
                "name": entry.get("word", "dictionary entry"),
                "url": "",
                "source_type": "local_dictionary",
                "trust_score": 74,
                "supports": [entry.get("word"), entry.get("type")] + entry.get("connections", [])[:8],
                "notes": "; ".join(str(item) for item in meanings[:3])
            })

        return evidence[:30]

    def collect_evidence_from_result(self, brain_name, result, evidence):

        sources = []

        for key in [
            "fetched_sources", "approved_research_links", "sources",
            "citations", "evidence", "references"
        ]:
            value = result.get(key)
            if isinstance(value, list):
                sources.extend(value)

        for source in sources[:40]:
            if isinstance(source, dict):
                evidence.append(self.normalize_source(brain_name, source))

    def normalize_source(self, brain_name, source):

        trust_score = source.get("trust_score")
        reliability_score = source.get("reliability_score")
        score = trust_score if trust_score is not None else reliability_score

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 45

        source_type = str(source.get("source_type", "")).lower()

        if source_type in STRONG_SOURCE_TYPES:
            score += 5

        return {
            "source_brain": brain_name,
            "name": source.get("name", source.get("title", "unknown source")),
            "url": source.get("url", source.get("link", "")),
            "source_type": source.get("source_type", "unknown"),
            "trust_score": max(0, min(round(score, 2), 100)),
            "supports": source.get("supports", []),
            "notes": source.get("notes", "")
        }

    def evidence_score(self, evidence):

        if not evidence:
            return 0

        scores = [item.get("trust_score", 0) for item in evidence]
        average = sum(scores) / max(len(scores), 1)
        source_names = {item.get("name") for item in evidence if item.get("name")}
        source_types = {item.get("source_type") for item in evidence if item.get("source_type")}
        diversity_bonus = min(len(source_names) * 2 + len(source_types) * 3, 18)
        strong_count = sum(1 for score in scores if score >= 75)

        return min(100, round(average + diversity_bonus + strong_count * 3, 2))

    def claim_terms(self, text):

        stop_words = {
            "the", "and", "that", "this", "with", "from", "have", "has",
            "are", "was", "were", "can", "will", "would", "should", "about",
            "into", "what", "when", "where", "which", "there"
        }

        return {
            word
            for word in re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9\u0590-\u05FF-]{2,}", str(text).lower())
            if word not in stop_words
        }

    def evidence_terms(self, evidence_item):

        parts = [
            evidence_item.get("name", ""),
            evidence_item.get("source_type", ""),
            evidence_item.get("notes", ""),
            " ".join(map(str, evidence_item.get("supports", []))),
        ]

        sample = evidence_item.get("sample", [])
        if isinstance(sample, list):
            for item in sample[:6]:
                if isinstance(item, dict):
                    parts.append(str(item.get("text", "")))
                    parts.append(str(item.get("path", "")))
                else:
                    parts.append(str(item))

        return self.claim_terms(" ".join(parts))

    def link_claims_to_evidence(self, claims, evidence):

        links = []

        for claim in claims[:20]:
            claim_text = claim.get("text", "")
            terms = self.claim_terms(claim_text)
            matches = []

            for item in evidence[:40]:
                overlap = terms.intersection(self.evidence_terms(item))
                if not overlap:
                    continue

                trust = item.get("trust_score", 0)
                score = len(overlap) * 10 + trust * 0.4
                matches.append({
                    "source": item.get("name", "unknown source"),
                    "source_type": item.get("source_type", "unknown"),
                    "trust_score": trust,
                    "matched_terms": sorted(overlap)[:10],
                    "support_score": round(score, 2)
                })

            matches.sort(key=lambda value: value["support_score"], reverse=True)
            links.append({
                "claim": claim_text,
                "source_brain": claim.get("source_brain"),
                "matches": matches[:5],
                "best_support_score": matches[0]["support_score"] if matches else 0
            })

        return links

    def support_ratio(self, claims, claim_evidence_links):

        if not claims:
            return 0

        supported = sum(
            1
            for link in claim_evidence_links
            if link.get("best_support_score", 0) >= 35
        )
        return round(supported / max(len(claims[:20]), 1), 2)

    def build_fact_summary(self, verdict, confidence, claims, evidence, warnings, claim_evidence_links, coverage=None):

        lines = [
            f"Verdict: {verdict}",
            f"Confidence: {confidence}%",
            f"Claims checked: {len(claims)}",
            f"Evidence sources: {len(evidence)}"
        ]

        supported = sum(1 for link in claim_evidence_links if link.get("best_support_score", 0) >= 35)
        if claims:
            lines.append(f"Claims with local/source support: {supported}/{len(claims[:20])}")

        if isinstance(coverage, dict):
            lines.append(
                "Evidence coverage: "
                f"DATA={coverage.get('data_context', 0)}, "
                f"Knowledge={coverage.get('knowledge_database', 0)}, "
                f"Dictionary={coverage.get('dictionary', 0)}, "
                f"Research/external={coverage.get('research_or_external', 0)}, "
                f"Strong={coverage.get('strong_sources', 0)}"
            )

        if warnings:
            lines.append("Warnings: " + "; ".join(warnings[:4]))

        return "\n".join(lines)

    # ---------- risk and conflicts ----------

    def detect_topic_risk(self, text, report):

        lowered = f"{text} {report.get('main_topic', '')} {report.get('intent', '')}".lower()
        hits = [topic for topic in HIGH_STAKES_TOPICS if topic in lowered]

        if hits:
            return {
                "level": "high",
                "topics": sorted(hits)[:12],
                "requires_strong_sources": True
            }

        return {
            "level": "normal",
            "topics": [],
            "requires_strong_sources": False
        }

    def detect_conflicts(self, claims):

        conflicts = []
        normalized = {}

        for claim in claims:
            text = claim.get("text", "")
            key = self.claim_subject_key(text)

            if not key:
                continue

            polarity = self.claim_polarity(text)
            previous = normalized.get(key)

            if previous and previous["polarity"] != polarity:
                conflicts.append({
                    "subject": key,
                    "claim_a": previous["text"],
                    "claim_b": text,
                    "reason": "opposite polarity about the same subject"
                })
            else:
                normalized[key] = {
                    "text": text,
                    "polarity": polarity
                }

        return conflicts[:20]

    def claim_subject_key(self, text):

        text = re.sub(r"[^a-zA-Z0-9\u0590-\u05FF\s]", " ", text.lower())
        words = [
            word
            for word in text.split()
            if len(word) > 2 and word not in {"the", "and", "that", "this", "with", "from"}
        ]

        return " ".join(words[:4])

    def claim_polarity(self, text):

        lowered = text.lower()
        negative_markers = [" not ", " never ", " no ", "false", "cannot", "isn't", "doesn't", "לא ", "אינו", "שקר"]

        return "negative" if any(marker in f" {lowered} " for marker in negative_markers) else "positive"

    def detect_warnings(self, claims, evidence, conflicts, topic_risk, claim_evidence_links=None, coverage=None):

        warnings = []
        claim_evidence_links = claim_evidence_links or []
        coverage = coverage or {}

        if not claims:
            warnings.append("No clear factual claims found")

        if not evidence:
            warnings.append("No external or local source evidence found")

        if claims and self.support_ratio(claims, claim_evidence_links) < 0.45:
            warnings.append("Most claims have weak direct evidence support")

        if evidence and not coverage.get("strong_sources"):
            warnings.append("No strong evidence source found")

        if conflicts:
            warnings.append("Conflicting claims detected")

        if topic_risk.get("requires_strong_sources") and (
            self.evidence_score(evidence) < 90
            or not coverage.get("strong_sources")
        ):
            warnings.append("High-stakes topic requires stronger sources")

        for claim in claims:
            lowered = claim.get("text", "").lower()
            if any(marker in lowered for marker in WEAK_LANGUAGE):
                warnings.append("Uncertain wording detected")
                break

        return list(dict.fromkeys(warnings))

    # ---------- scoring ----------

    def calculate_confidence(
        self,
        claims,
        evidence,
        conflicts,
        warnings,
        data,
        results,
        topic_risk,
        claim_evidence_links=None,
        coverage=None
    ):

        score = 35
        claim_evidence_links = claim_evidence_links or []
        coverage = coverage or {}

        if claims:
            score += min(len(claims) * 2, 12)

        score += self.evidence_score(evidence) * 0.45
        score += self.support_ratio(claims, claim_evidence_links) * 18

        if coverage.get("strong_sources"):
            score += min(coverage.get("strong_sources", 0) * 4, 14)

        if coverage.get("has_local_support"):
            score += 5

        if coverage.get("has_external_or_research_support"):
            score += 7

        verified_brains = 0
        confidence_values = []

        for result in list(results.values()) + ([data] if isinstance(data, dict) else []):
            if isinstance(result, dict):
                if result.get("verified") is True:
                    verified_brains += 1
                if isinstance(result.get("confidence"), (int, float)):
                    confidence_values.append(float(result["confidence"]))

        score += min(verified_brains * 6, 18)

        if confidence_values:
            score += (sum(confidence_values) / len(confidence_values)) * 0.10

        score -= len(conflicts) * 18
        score -= len(warnings) * 5

        if topic_risk.get("requires_strong_sources") and (
            self.evidence_score(evidence) < 90
            or not coverage.get("strong_sources")
        ):
            score -= 18

        return max(0, min(round(score, 2), 100))

    def verdict_from_confidence(self, confidence, conflicts, topic_risk):

        if conflicts:
            return "conflicting"

        if confidence >= 85:
            return "verified"

        if confidence >= 68:
            return "likely_true"

        if confidence >= 45:
            return "uncertain"

        if topic_risk.get("requires_strong_sources"):
            return "needs_research"

        return "not_verified"

    def build_recommendations(self, verdict, warnings, topic_risk):

        recommendations = []

        if verdict in {"uncertain", "not_verified", "needs_research"}:
            recommendations.append("Ask Research_brain for stronger evidence from approved sources")

        if topic_risk.get("requires_strong_sources"):
            recommendations.append("Use official, academic, medical, legal, or standards sources before answering")

        if "Conflicting claims detected" in warnings:
            recommendations.append("Do not present final answer until contradictions are resolved")

        if "No clear factual claims found" in warnings:
            recommendations.append("Treat this as opinion, planning, or creative output instead of factual verification")

        return recommendations

    def evidence_coverage(self, evidence):

        coverage = {
            "data_context": 0,
            "knowledge_database": 0,
            "dictionary": 0,
            "research_or_external": 0,
            "source_types": {},
            "strong_sources": 0
        }

        for item in evidence:
            if not isinstance(item, dict):
                continue

            source_brain = str(item.get("source_brain", "")).lower()
            source_type = str(item.get("source_type", "")).lower()
            trust_score = item.get("trust_score", 0) or 0
            try:
                trust_score = float(trust_score)
            except (TypeError, ValueError):
                trust_score = 0

            coverage["source_types"][source_type or "unknown"] = (
                coverage["source_types"].get(source_type or "unknown", 0) + 1
            )

            if "data_context" in source_brain:
                coverage["data_context"] += 1
            elif "knowledge_database" in source_brain:
                coverage["knowledge_database"] += 1
            elif "understandingdk" in source_brain:
                coverage["dictionary"] += 1
            else:
                coverage["research_or_external"] += 1

            if trust_score >= 70:
                coverage["strong_sources"] += 1

        coverage["has_local_support"] = bool(
            coverage["data_context"]
            or coverage["knowledge_database"]
            or coverage["dictionary"]
        )
        coverage["has_external_or_research_support"] = bool(coverage["research_or_external"])
        return coverage

    def update_statistics(self, verdict, confidence):

        stats = self.statistics.get("Fact_Check_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_verdict"] = verdict
        stats["last_confidence"] = confidence
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("verdict_counts", {})
        stats["verdict_counts"][verdict] = stats["verdict_counts"].get(verdict, 0) + 1

        self.statistics["Fact_Check_brain"] = stats
        self.save_statistics()

    # ---------- public ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        results = self.get_results(data)
        text = self.extract_text(data)
        claims = self.collect_claims(data, results)
        claims, claim_type_counts = self.classify_claims(claims)
        verifiable_claims = [claim for claim in claims if claim.get("verifiable")]
        evidence = self.collect_evidence(data, results)
        evidence.extend(self.collect_context_evidence(data))
        local_data_evidence = self.collect_local_data_evidence(text, report, claims)
        evidence.extend(local_data_evidence)
        conflicts = self.detect_conflicts(claims)
        topic_risk = self.detect_topic_risk(text, report)
        claim_evidence_links = self.link_claims_to_evidence(verifiable_claims, evidence)
        coverage = self.evidence_coverage(evidence)
        warnings = self.detect_warnings(
            verifiable_claims,
            evidence,
            conflicts,
            topic_risk,
            claim_evidence_links,
            coverage
        )
        confidence = self.calculate_confidence(
            verifiable_claims,
            evidence,
            conflicts,
            warnings,
            data,
            results,
            topic_risk,
            claim_evidence_links,
            coverage
        )
        verdict = self.verdict_from_confidence(confidence, conflicts, topic_risk)
        if claims and not verifiable_claims:
            verdict = "opinion_not_fact_checkable"
            confidence = 100
        verified = verdict in {"verified", "likely_true"} and not conflicts
        recommendations = self.build_recommendations(verdict, warnings, topic_risk)
        final_output = self.build_fact_summary(
            verdict,
            confidence,
            claims,
            evidence,
            warnings,
            claim_evidence_links,
            coverage
        )

        self.update_statistics(verdict, confidence)

        return {
            "brain": "Fact_Check_brain",
            "verified": verified,
            "verdict": verdict,
            "confidence": confidence,
            "claim_count": len(claims),
            "verifiable_claim_count": len(verifiable_claims),
            "claim_type_counts": claim_type_counts,
            "claims_checked": claims[:20],
            "evidence_count": len(evidence),
            "evidence_score": self.evidence_score(evidence),
            "evidence_coverage": coverage,
            "local_data_evidence": local_data_evidence,
            "claim_evidence_links": claim_evidence_links,
            "strongest_sources": sorted(
                evidence,
                key=lambda item: item.get("trust_score", 0),
                reverse=True
            )[:8],
            "conflicts": conflicts,
            "warnings": warnings,
            "topic_risk": topic_risk,
            "needs_research": bool(verifiable_claims) and verdict in {"uncertain", "not_verified", "needs_research"},
            "reliability": {
                "level": (
                    "high" if confidence >= 85
                    else "medium" if confidence >= 65
                    else "low"
                ),
                "score": confidence,
                "verdict": verdict,
                "source_coverage": coverage,
                "opinion_separated": claim_type_counts.get("opinion", 0) + claim_type_counts.get("recommendation", 0)
            },
            "suggested_next_brains": [
                brain_name
                for brain_name in [
                    "Research_brain" if verdict in {"uncertain", "not_verified", "needs_research"} else None,
                    "Reasoning_brain" if conflicts else None,
                    "Security_brain" if topic_risk.get("level") == "high" else None,
                    "Response_brain"
                ]
                if brain_name
            ],
            "recommendations": recommendations,
            "answer": final_output,
            "final_output": final_output,
            "rules": [
                "Do not mark claims verified without evidence.",
                "High-stakes topics require stronger sources.",
                "Contradictions lower confidence sharply.",
                "Prefer official, academic, archive, medical, and standards sources.",
                "If evidence is weak, route to Research_brain before final response."
            ]
        }


brain = FactCheckBrain()
