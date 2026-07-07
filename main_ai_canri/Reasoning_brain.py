"""
Reasoning_brain.py
Canri AI

Reasoning_brain analyzes facts, memory, and previous brain results.
It does not invent facts. It builds:
- explicit premises
- connections
- contradictions
- conclusions
- solution paths
- uncertainty and next-brain recommendations
"""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
PATTERNS_FILE = DATA_DIR / "Reasoning_patterns.json"
RULES_FILE = DATA_DIR / "Reasoning_rules.json"
STATS_FILE = DATA_DIR / "Reasoning_statistics.json"

MAX_FACTS = 30
MAX_CONNECTIONS = 40

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "what", "where",
    "how", "why", "is", "are", "was", "were", "does", "did",
    "about", "from", "into", "make", "create", "build",
    "של", "את", "על", "מה", "איפה", "איך", "למה", "זה", "אני",
    "רוצה", "תעשה", "תכין", "לי"
}

NEGATION_TERMS = {
    "not", "no", "never", "cannot", "can't", "without",
    "לא", "אין", "אסור", "בלי"
}

CONSTRAINT_TERMS = {
    "must", "only", "do not", "dont", "don't", "without", "include",
    "needs", "need", "should", "final", "working", "runnable",
    "simple", "safe", "reliable", "accurate"
}


class ReasoningBrain:

    def __init__(self):

        self.patterns = self.load_json(PATTERNS_FILE, {})
        self.rules = self.load_json(RULES_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})

        print("Reasoning Brain Loaded")

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
            return {
                "original_text": str(data),
                "main_topic": "unknown",
                "intent": "question",
                "words": []
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        if (
            "main_topic" in data
            or "intent" in data
            or "words" in data
        ):
            return data

        return {}

    def get_memory_report(self, data):

        if not isinstance(data, dict):
            return {}

        memory = data.get("memory")

        if isinstance(memory, dict):
            return memory

        return {}

    def get_previous_results(self, data):

        if not isinstance(data, dict):
            return {}

        manager_context = data.get("manager_context", {})

        if isinstance(manager_context, dict):
            results = manager_context.get("previous_results", {})
            if isinstance(results, dict):
                return results

        results = data.get("results", {})

        if isinstance(results, dict):
            return results

        return {}

    def get_context_block(self, data, key):

        if not isinstance(data, dict):
            return {}

        value = data.get(key)
        if isinstance(value, dict):
            return value

        manager_context = data.get("manager_context", {})
        if isinstance(manager_context, dict):
            value = manager_context.get(key)
            if isinstance(value, dict):
                return value

        return {}

    def extract_text(self, data, report):

        parts = []

        if isinstance(data, str):
            parts.append(data)

        if isinstance(data, dict):
            for key in [
                "original_text",
                "corrected_text",
                "user_message",
                "question",
                "query",
                "text",
                "goal",
                "task"
            ]:
                value = data.get(key)
                if value:
                    parts.append(str(value))

        for key in [
            "original_text",
            "corrected_text",
            "main_topic",
            "intent"
        ]:
            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def collect_terms(self, report, memory_report, text):

        terms = []

        for key in ["main_topic", "intent", "language", "target_language"]:
            value = report.get(key)
            if value and value != "unknown":
                terms.append(str(value))

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            terms.extend(str(topic) for topic in topics)

        for task in report.get("possible_tasks", []):
            terms.append(str(task).replace("_", " "))

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            word = word_data.get("word")
            if word:
                terms.append(str(word))

            for connection in word_data.get("connections", [])[:8]:
                terms.append(str(connection))

        for keyword in memory_report.get("current_keywords", [])[:30]:
            terms.append(str(keyword))

        for match in memory_report.get("ranked_matches", [])[:5]:
            if isinstance(match, dict):
                terms.extend(str(keyword) for keyword in match.get("keywords", [])[:8])

        meaning_frame = report.get("meaning_frame", {})
        if isinstance(meaning_frame, dict):
            for key in ["subject", "action", "object", "question_focus"]:
                value = meaning_frame.get(key)
                if value:
                    terms.append(str(value))
            terms.extend(str(term) for term in meaning_frame.get("content_terms", [])[:30])

        sentence_graph = report.get("sentence_graph", {})
        if isinstance(sentence_graph, dict):
            for edge in sentence_graph.get("edges", [])[:40]:
                if not isinstance(edge, dict):
                    continue
                for key in ["from_word", "relation", "to_word"]:
                    value = edge.get(key)
                    if value:
                        terms.append(str(value).replace("_", " "))

        terms.extend(
            re.findall(
                r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
                text
            )
        )

        clean = []

        for term in terms:
            term = re.sub(r"\s+", " ", str(term).lower()).strip()
            term = term.replace("_", " ")

            if (
                term
                and len(term) > 1
                and term not in STOP_WORDS
                and term not in clean
            ):
                clean.append(term)

        return clean[:100]

    def graph_facts(self, report):

        facts = []
        meaning_frame = report.get("meaning_frame", {})

        if isinstance(meaning_frame, dict):
            subject = meaning_frame.get("subject")
            action = meaning_frame.get("action")
            obj = meaning_frame.get("object")

            if subject and action and obj:
                facts.append({
                    "text": f"Sentence meaning: {subject} performs {action} on {obj}.",
                    "source": "Understanding_brain.sentence_graph",
                    "confidence": report.get("graph_confidence", 78)
                })
            elif action and obj:
                facts.append({
                    "text": f"Sentence goal/action: {action} targets {obj}.",
                    "source": "Understanding_brain.sentence_graph",
                    "confidence": report.get("graph_confidence", 70)
                })

        sentence_graph = report.get("sentence_graph", {})
        if not isinstance(sentence_graph, dict):
            return facts

        for edge in sentence_graph.get("edges", [])[:35]:
            if not isinstance(edge, dict):
                continue

            left = edge.get("from_word")
            relation = edge.get("relation")
            right = edge.get("to_word")

            if left and relation and right:
                facts.append({
                    "text": f"Graph relation: {left} --{relation}--> {right}.",
                    "source": "Understanding_brain.sentence_graph",
                    "confidence": edge.get("confidence", 65)
                })

        return facts

    def context_facts(self, data):

        facts = []

        dictionary = self.get_context_block(data, "dictionary")
        if isinstance(dictionary, dict):
            for entry in dictionary.get("entries", [])[:8]:
                if not isinstance(entry, dict):
                    continue
                word = entry.get("word")
                meanings = entry.get("meanings", [])
                if word and meanings:
                    facts.append({
                        "text": f"Dictionary definition for {word}: {meanings[0]}",
                        "source": "Data_context.dictionary",
                        "confidence": 78
                    })

            for product in dictionary.get("product_matches", [])[:5]:
                if not isinstance(product, dict):
                    continue
                name = product.get("name") or product.get("id")
                company = product.get("company")
                description = product.get("description")
                if name:
                    text = f"Product context: {name}"
                    if company:
                        text += f" is associated with {company}"
                    if description:
                        text += f"; {description}"
                    facts.append({
                        "text": text,
                        "source": "Data_context.company_products",
                        "confidence": 78
                    })

        for context_key, source_name in [
            ("data_context", "Data_context"),
            ("knowledge", "Knowledge_database"),
            ("knowledge_context", "Knowledge_database")
        ]:
            context = self.get_context_block(data, context_key)
            matches = context.get("matches", []) if isinstance(context, dict) else []
            for match in matches[:8]:
                if not isinstance(match, dict):
                    continue
                summary = (
                    match.get("summary")
                    or match.get("text")
                    or match.get("title")
                    or match.get("description")
                )
                if summary:
                    facts.append({
                        "text": str(summary),
                        "source": source_name,
                        "confidence": match.get("trust_score", match.get("confidence", 72))
                    })

        return facts

    # ---------- facts ----------

    def normalize_fact(self, fact, source="input", confidence=70):

        if isinstance(fact, dict):
            text = (
                fact.get("fact")
                or fact.get("summary")
                or fact.get("text")
                or fact.get("definition")
                or fact.get("description")
                or fact.get("name")
                or ""
            )
            confidence = fact.get("confidence", confidence)
            source = fact.get("source", source)
        else:
            text = str(fact)

        text = re.sub(r"\s+", " ", str(text)).strip()

        if not text:
            return None

        tokens = self.tokenize(text)

        return {
            "text": text,
            "source": source,
            "confidence": confidence,
            "tokens": tokens,
            "negated": bool(set(tokens) & NEGATION_TERMS)
        }

    def tokenize(self, text):

        tokens = re.findall(
            r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
            text.lower()
        )

        return [
            token
            for token in tokens
            if token not in STOP_WORDS
        ]

    def extract_facts(self, data, report, memory_report, previous_results, text):

        facts = []

        if isinstance(data, dict):
            for fact in data.get("facts", []):
                normalized = self.normalize_fact(fact, "input", 75)
                if normalized:
                    facts.append(normalized)

        for fact in self.graph_facts(report):
            normalized = self.normalize_fact(fact, fact.get("source", "Understanding_brain"), fact.get("confidence", 70))
            if normalized:
                facts.append(normalized)

        for fact in self.context_facts(data):
            normalized = self.normalize_fact(fact, fact.get("source", "context"), fact.get("confidence", 72))
            if normalized:
                facts.append(normalized)

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            word = word_data.get("word")
            connections = word_data.get("connections", [])

            if word:
                text_fact = f"{word} is connected to {', '.join(str(x) for x in connections[:5])}"
                normalized = self.normalize_fact(text_fact, "Understanding_brain", 65)
                if normalized:
                    facts.append(normalized)

        for match in memory_report.get("ranked_matches", [])[:8]:
            if not isinstance(match, dict):
                continue

            normalized = self.normalize_fact(
                match.get("summary", ""),
                "Memory_brain",
                min(match.get("score", 50), 90)
            )
            if normalized:
                facts.append(normalized)

        for brain_name, result in previous_results.items():
            if not isinstance(result, dict):
                continue

            for key in ["facts", "conclusions", "solutions"]:
                values = result.get(key, [])
                if not isinstance(values, list):
                    continue

                for value in values[:5]:
                    normalized = self.normalize_fact(value, brain_name, result.get("confidence", 65))
                    if normalized:
                        facts.append(normalized)

            if result.get("summary"):
                normalized = self.normalize_fact(result["summary"], brain_name, result.get("confidence", 65))
                if normalized:
                    facts.append(normalized)

        if not facts and text:
            normalized = self.normalize_fact(text, "request_text", 55)
            if normalized:
                facts.append(normalized)

        unique = []
        seen = set()

        for fact in facts:
            key = fact["text"].lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(fact)

        return unique[:MAX_FACTS]

    # ---------- classification ----------

    def detect_domain(self, report, terms, text):

        topic = str(report.get("main_topic", "")).lower()
        lowered = f"{text.lower()} {' '.join(terms)}"

        domain_rules = {
            "code": ["code", "python", "javascript", "java", "function", "api", "debug"],
            "science": ["science", "physics", "chemistry", "biology", "evidence", "experiment"],
            "language": ["language", "translation", "grammar", "synonym", "antonym"],
            "geography": ["geography", "country", "city", "capital", "map", "gps"],
            "technology": ["technology", "hardware", "software", "cpu", "gpu", "robot"],
            "history": ["history", "empire", "war", "ancient", "timeline"],
            "math": ["math", "equation", "calculate", "algebra", "geometry"],
            "game": ["game", "player", "enemy", "level", "inventory"],
            "story": ["story", "character", "plot", "world"],
            "security": ["security", "password", "token", "encrypt", "danger", "safe"]
        }

        for domain, keywords in domain_rules.items():
            if topic == domain or any(keyword in lowered for keyword in keywords):
                return domain

        return topic if topic and topic != "unknown" else "general"

    def detect_intent(self, report, terms, text):

        intent = str(report.get("intent", "")).lower()

        if intent and intent != "unknown":
            return intent

        lowered = f"{text.lower()} {' '.join(terms)}"

        if any(word in lowered for word in ["debug", "fix", "error", "bug"]):
            return "debugging"
        if any(word in lowered for word in ["compare", "versus", "vs"]):
            return "comparison"
        if any(word in lowered for word in ["research", "source", "evidence"]):
            return "research"
        if any(word in lowered for word in ["plan", "steps", "roadmap"]):
            return "planning"
        if any(word in lowered for word in ["why", "how", "what"]):
            return "question"

        return "explanation"

    def choose_reasoning_mode(self, domain, intent, facts, terms):

        term_text = " ".join(terms)

        if intent == "debugging":
            return "diagnostic"
        if intent == "comparison":
            return "comparative"
        if domain in ["science", "history"] or intent == "research":
            return "evidence_based"
        if domain in ["security"] or "risk" in term_text or "safe" in term_text:
            return "risk_based"
        if domain in ["math", "code"] or intent in ["code_generation", "planning"]:
            return "step_by_step"
        if len(facts) >= 4:
            return "inductive"

        return "deductive"

    # ---------- pattern/rule matching ----------

    def select_pattern(self, domain, intent, mode, terms):

        best = None
        best_score = -1

        for pattern in self.patterns.values():
            score = 0

            if pattern.get("domain") == domain:
                score += 30
            if pattern.get("intent") == intent:
                score += 25
            if pattern.get("mode") == mode:
                score += 25

            triggers = " ".join(pattern.get("trigger_terms", []))
            score += sum(1 for term in terms[:20] if term in triggers)
            score += pattern.get("confidence", 60) / 25

            if score > best_score:
                best_score = score
                best = pattern

        return best or {}

    def select_rule(self, domain, intent, mode):

        best = None
        best_score = -1

        for rule in self.rules.values():
            score = 0
            if rule.get("domain") == domain:
                score += 4
            if rule.get("intent") == intent:
                score += 3
            if rule.get("mode") == mode:
                score += 3

            if score > best_score:
                best_score = score
                best = rule

        return best or {}

    # ---------- reasoning ----------

    def find_connections(self, facts):

        connections = []

        for index, left in enumerate(facts):
            left_tokens = set(left["tokens"])

            for right in facts[index + 1:]:
                right_tokens = set(right["tokens"])
                shared = sorted(left_tokens & right_tokens)

                if not shared:
                    continue

                strength = min(100, len(shared) * 20)

                connections.append({
                    "from": left["text"],
                    "to": right["text"],
                    "shared_terms": shared[:10],
                    "strength": strength,
                    "type": "semantic_overlap"
                })

        connections.sort(
            key=lambda item: item["strength"],
            reverse=True
        )

        return connections[:MAX_CONNECTIONS]

    def find_graph_connections(self, report):

        sentence_graph = report.get("sentence_graph", {})
        if not isinstance(sentence_graph, dict):
            return []

        connections = []
        for edge in sentence_graph.get("edges", [])[:50]:
            if not isinstance(edge, dict):
                continue
            left = edge.get("from_word")
            relation = edge.get("relation")
            right = edge.get("to_word")
            if not left or not relation or not right:
                continue

            relation_type = "sentence_graph"
            if relation in {"does_action", "acts_on"}:
                relation_type = "core_meaning"
            elif relation.startswith("preposition_"):
                relation_type = "context_relation"
            elif relation in {"describes", "compound_modifier", "modifies_action"}:
                relation_type = "modifier_relation"

            connections.append({
                "from": left,
                "to": right,
                "relation": relation,
                "strength": edge.get("confidence", 65),
                "type": relation_type,
                "evidence": edge.get("evidence", "sentence_graph")
            })

        return connections

    def detect_contradictions(self, facts):

        contradictions = []

        for index, left in enumerate(facts):
            left_tokens = set(left["tokens"]) - NEGATION_TERMS

            for right in facts[index + 1:]:
                right_tokens = set(right["tokens"]) - NEGATION_TERMS
                shared = sorted(left_tokens & right_tokens)

                if not shared:
                    continue

                if left["negated"] != right["negated"]:
                    contradictions.append({
                        "claim_a": left["text"],
                        "claim_b": right["text"],
                        "shared_terms": shared[:10],
                        "severity": "medium",
                        "resolution": "Needs verification before using either claim as certain."
                    })

        return contradictions[:12]

    def evaluate_evidence(self, facts, contradictions):

        if not facts:
            return {
                "evidence_level": "none",
                "average_confidence": 0,
                "source_count": 0
            }

        average = sum(fact.get("confidence", 50) for fact in facts) / len(facts)
        sources = sorted(set(fact.get("source", "unknown") for fact in facts))

        if contradictions:
            level = "conflicted"
        elif average >= 75 and len(sources) >= 2:
            level = "strong"
        elif average >= 60:
            level = "moderate"
        else:
            level = "weak"

        return {
            "evidence_level": level,
            "average_confidence": round(average, 2),
            "source_count": len(sources),
            "sources": sources
        }

    def extract_constraints(self, text, report, terms):

        constraints = []
        lowered = str(text).lower()

        for term in sorted(CONSTRAINT_TERMS, key=len, reverse=True):
            if term in lowered:
                constraints.append({
                    "constraint": term,
                    "source": "request_text",
                    "importance": "high" if term in {"must", "only", "do not", "don't", "working", "runnable"} else "medium"
                })

        output_type = report.get("desired_output")
        if output_type:
            constraints.append({
                "constraint": f"desired output is {output_type}",
                "source": "Understanding_brain",
                "importance": "high"
            })

        if report.get("intent") == "code_generation":
            constraints.append({
                "constraint": "code requests should produce real runnable code unless the user asks for a plan",
                "source": "Reasoning_brain",
                "importance": "high"
            })

        if report.get("intent") == "story_creation":
            constraints.append({
                "constraint": "story requests should output the final story, not the creative process",
                "source": "Reasoning_brain",
                "importance": "high"
            })

        return constraints[:20]

    def build_reasoning_chain(self, domain, intent, mode, facts, graph_connections, contradictions, constraints, evidence):

        chain = []

        chain.append({
            "step": "understand_request",
            "result": f"Detected domain={domain}, intent={intent}, mode={mode}."
        })

        if graph_connections:
            core = [
                item
                for item in graph_connections
                if item.get("type") == "core_meaning"
            ][:4]
            chain.append({
                "step": "connect_sentence_graph",
                "result": "Used sentence graph relations to preserve meaning.",
                "evidence": core or graph_connections[:4]
            })

        if constraints:
            chain.append({
                "step": "apply_constraints",
                "result": "Important user constraints were detected and should control the answer.",
                "constraints": constraints[:8]
            })

        if facts:
            strongest = sorted(
                facts,
                key=lambda fact: fact.get("confidence", 0),
                reverse=True
            )[:5]
            chain.append({
                "step": "rank_evidence",
                "result": f"Evidence level is {evidence.get('evidence_level')} with {evidence.get('source_count', 0)} sources.",
                "support": [
                    {
                        "text": fact["text"],
                        "source": fact["source"],
                        "confidence": fact["confidence"]
                    }
                    for fact in strongest
                ]
            })

        if contradictions:
            chain.append({
                "step": "handle_conflicts",
                "result": "Contradictions exist, so the final response should stay cautious.",
                "conflicts": contradictions[:4]
            })

        chain.append({
            "step": "handoff",
            "result": "Send a concise conclusion and any constraints to the specialist or Response_brain."
        })

        return chain

    def generate_conclusions(self, facts, connections, contradictions, evidence):

        conclusions = []

        if not facts:
            return [
                {
                    "claim": "There is not enough information to reason reliably.",
                    "confidence": 10,
                    "support": []
                }
            ]

        if contradictions:
            conclusions.append({
                "claim": "Some available claims may conflict, so the answer should stay cautious.",
                "confidence": 45,
                "support": [item["claim_a"] for item in contradictions[:3]]
            })

        if connections:
            top = connections[0]
            conclusions.append({
                "claim": f"The strongest connection is around: {', '.join(top['shared_terms'][:5])}.",
                "confidence": min(90, top["strength"]),
                "support": [top["from"], top["to"]]
            })

        if evidence["evidence_level"] == "strong":
            conclusions.append({
                "claim": "The available evidence is strong enough to support a direct answer.",
                "confidence": 85,
                "support": [fact["text"] for fact in facts[:3]]
            })
        elif evidence["evidence_level"] == "moderate":
            conclusions.append({
                "claim": "The available evidence supports a useful answer, but important details should remain explicit.",
                "confidence": 70,
                "support": [fact["text"] for fact in facts[:3]]
            })
        elif evidence["evidence_level"] == "weak":
            conclusions.append({
                "claim": "The available evidence is weak, so another specialist or Research_brain should help.",
                "confidence": 40,
                "support": [fact["text"] for fact in facts[:2]]
            })

        return conclusions[:8]

    def build_decision_summary(self, domain, intent, mode, conclusions, constraints, missing_information):

        if missing_information:
            recommendation = "Ask for or infer the missing information before giving a confident final answer."
            best_conclusion = "Important information is missing, so the answer should stay cautious."
        elif intent == "code_generation":
            recommendation = "Generate the final runnable code and avoid module lists, placeholders, or draft-only structures."
            best_conclusion = "The user wants final runnable code, so the system should output the implementation directly."
        elif intent == "story_creation":
            recommendation = "Return the final story text directly, not the creative reasoning report."
            best_conclusion = "The user wants the final creative result, not the internal evolution report."
        elif intent == "planning":
            recommendation = "Return ordered steps with dependencies and risks."
            best_conclusion = "The user wants a structured plan with ordered steps."
        elif domain in {"science", "history", "geography"}:
            recommendation = "Answer with sourced, cautious facts and mark uncertainty."
            best_conclusion = "The answer should be factual, source-aware, and careful with uncertainty."
        else:
            recommendation = "Return a direct, clear answer based on the strongest available evidence."
            best_conclusion = conclusions[0]["claim"] if conclusions else "No reliable conclusion was produced."

        return {
            "best_conclusion": best_conclusion,
            "recommended_response_strategy": recommendation,
            "must_follow": [
                item["constraint"]
                for item in constraints
                if item.get("importance") == "high"
            ][:8],
            "mode": mode,
            "domain": domain,
            "intent": intent
        }

    def generate_solutions(self, domain, intent, mode, missing_information, contradictions):

        solutions = []

        if missing_information:
            solutions.append({
                "action": "Clarify missing information",
                "reason": "; ".join(missing_information),
                "priority": "high"
            })

        if contradictions:
            solutions.append({
                "action": "Verify conflicting claims before final answer",
                "reason": "Contradictions were detected",
                "priority": "high"
            })

        domain_actions = {
            "code": "Create a step-by-step implementation path and route code to Code_brain.",
            "science": "Compare evidence and route factual claims to Science_brain and Fact_Check_brain.",
            "language": "Use Language_brain for translation, grammar, tone, and examples.",
            "geography": "Use Geography_brain for local knowledge and Research_brain for current data.",
            "technology": "Use Technology_brain to analyze tools, hardware, software, and constraints.",
            "history": "Build a timeline and verify dates with History_brain or Research_brain.",
            "math": "Solve step by step and verify each transformation.",
            "game": "Use Planner_brain to split gameplay systems before Code_brain.",
            "story": "Use Creative_brain and Story_brain to build coherent narrative structure.",
            "security": "Use Security_brain before giving operational details."
        }

        solutions.append({
            "action": domain_actions.get(domain, "Gather more information and reason step by step."),
            "reason": f"Detected {domain} domain with {mode} reasoning.",
            "priority": "medium"
        })

        if intent == "planning":
            solutions.append({
                "action": "Route to Planner_brain for dependency-aware steps.",
                "reason": "The request is planning-oriented.",
                "priority": "medium"
            })

        return solutions

    def identify_missing_information(self, domain, intent, terms, facts):

        missing = []

        if not terms:
            missing.append("No clear terms were extracted.")

        if not facts:
            missing.append("No facts were provided.")

        if domain == "code" and not any(term in terms for term in ["python", "javascript", "java", "html", "css", "sql"]):
            missing.append("Programming language is unclear.")

        if intent in ["research", "question"] and len(facts) < 2:
            missing.append("More evidence is needed for a reliable answer.")

        return missing

    def calculate_confidence(self, facts, connections, contradictions, evidence, pattern):

        confidence = 35

        confidence += min(len(facts) * 4, 25)
        confidence += min(len(connections) * 2, 20)
        confidence += evidence.get("average_confidence", 0) * 0.2
        confidence += pattern.get("confidence", 60) * 0.1
        confidence -= len(contradictions) * 8

        if evidence.get("evidence_level") == "conflicted":
            confidence -= 15
        elif evidence.get("evidence_level") == "strong":
            confidence += 10

        return round(max(0, min(confidence, 100)), 2)

    def suggested_next_brains(self, domain, intent, confidence, contradictions, missing_information):

        next_brains = []

        if intent == "planning" or domain in ["code", "game"]:
            next_brains.append("Planner_brain")

        domain_map = {
            "code": ["Code_brain", "Security_brain"],
            "science": ["Science_brain", "Fact_Check_brain"],
            "language": ["Language_brain"],
            "geography": ["Geography_brain", "Research_brain"],
            "technology": ["Technology_brain", "Research_brain"],
            "history": ["History_brain", "Research_brain"],
            "math": ["Math_brain"],
            "security": ["Security_brain"],
            "story": ["Creative_brain", "Story_brain"],
            "game": ["Game_brain", "Code_brain"]
        }

        next_brains.extend(domain_map.get(domain, []))

        if confidence < 55 or missing_information:
            next_brains.append("Research_brain")
            next_brains.append("Creative_brain")

        if contradictions:
            next_brains.append("Fact_Check_brain")

        next_brains.append("Response_brain")

        return list(dict.fromkeys(next_brains))

    # ---------- statistics ----------

    def update_statistics(self, domain, intent, mode, confidence):

        stats = self.statistics.get("Reasoning_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_domain"] = domain
        stats["last_intent"] = intent
        stats["last_mode"] = mode
        stats["last_confidence"] = confidence
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()
        stats.setdefault("patterns", len(self.patterns))
        stats.setdefault("rules", len(self.rules))

        self.statistics["Reasoning_brain"] = stats
        self.save_statistics()

    # ---------- process ----------

    def process(self, data):

        report = self.get_understanding_report(data)
        memory_report = self.get_memory_report(data)
        previous_results = self.get_previous_results(data)
        text = self.extract_text(data, report)

        terms = self.collect_terms(
            report,
            memory_report,
            text
        )

        facts = self.extract_facts(
            data,
            report,
            memory_report,
            previous_results,
            text
        )

        domain = self.detect_domain(
            report,
            terms,
            text
        )

        intent = self.detect_intent(
            report,
            terms,
            text
        )

        mode = self.choose_reasoning_mode(
            domain,
            intent,
            facts,
            terms
        )

        pattern = self.select_pattern(
            domain,
            intent,
            mode,
            terms
        )

        rule = self.select_rule(
            domain,
            intent,
            mode
        )

        connections = self.find_connections(
            facts
        )

        graph_connections = self.find_graph_connections(
            report
        )

        contradictions = self.detect_contradictions(
            facts
        )

        evidence = self.evaluate_evidence(
            facts,
            contradictions
        )

        missing_information = self.identify_missing_information(
            domain,
            intent,
            terms,
            facts
        )

        constraints = self.extract_constraints(
            text,
            report,
            terms
        )

        conclusions = self.generate_conclusions(
            facts,
            connections + graph_connections,
            contradictions,
            evidence
        )

        reasoning_chain = self.build_reasoning_chain(
            domain,
            intent,
            mode,
            facts,
            graph_connections,
            contradictions,
            constraints,
            evidence
        )

        solutions = self.generate_solutions(
            domain,
            intent,
            mode,
            missing_information,
            contradictions
        )

        decision_summary = self.build_decision_summary(
            domain,
            intent,
            mode,
            conclusions,
            constraints,
            missing_information
        )

        confidence = self.calculate_confidence(
            facts,
            connections,
            contradictions,
            evidence,
            pattern
        )

        self.update_statistics(
            domain,
            intent,
            mode,
            confidence
        )

        return {
            "brain": "Reasoning_brain",
            "used_understanding_report": bool(report),
            "used_memory_report": bool(memory_report),
            "used_previous_results": bool(previous_results),
            "main_topic": domain,
            "intent": intent,
            "reasoning_mode": mode,
            "terms_used": terms,
            "graph_used": bool(graph_connections),
            "facts_used": [
                {
                    "text": fact["text"],
                    "source": fact["source"],
                    "confidence": fact["confidence"],
                    "negated": fact["negated"]
                }
                for fact in facts
            ],
            "connections": connections,
            "graph_connections": graph_connections,
            "contradictions": contradictions,
            "constraints": constraints,
            "evidence": evidence,
            "reasoning_chain": reasoning_chain,
            "conclusions": conclusions,
            "decision_summary": decision_summary,
            "solutions": solutions,
            "missing_information": missing_information,
            "pattern_used": {
                "id": pattern.get("id"),
                "mode": pattern.get("mode"),
                "steps": pattern.get("steps", []),
                "quality_checks": pattern.get("quality_checks", [])
            },
            "rule_used": {
                "id": rule.get("id"),
                "then": rule.get("then", []),
                "avoid": rule.get("avoid", [])
            },
            "confidence": confidence,
            "suggested_next_brains": self.suggested_next_brains(
                domain,
                intent,
                confidence,
                contradictions,
                missing_information
            ),
            "data_files_used": [
                "Reasoning_patterns.json",
                "Reasoning_rules.json",
                "Reasoning_statistics.json"
            ],
            "rules": [
                "Use explicit facts and memory instead of guessing.",
                "Show contradictions instead of hiding them.",
                "Use specialist brains when evidence is weak or risky.",
                "Conclusions must follow from facts, not from confidence alone."
            ]
        }


brain = ReasoningBrain()
