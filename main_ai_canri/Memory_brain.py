"""
Memory_brain.py
Canri AI

Deep memory system for Canri:
- stores every Understanding_brain report as an episodic memory
- builds semantic profiles for topics, intents, words, and tasks
- searches by topic, intent, keywords, text similarity, and recency
- returns a compact memory report that other brains can use
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from Brain_storage import atomic_write_json, load_json_resilient
from domain_packages.understanding.context import stop_terms as understanding_stop_terms


DATA_DIR = Path(__file__).parent / "data"
MEMORY_FILE = DATA_DIR / "Memory_database.json"
MEMORY_STATS_FILE = DATA_DIR / "Memory_statistics.json"
LEGACY_MEMORY_FILE = Path("memory.json")

MAX_EPISODES = 20000
MAX_MATCHES = 12
MAX_TURNS_PER_SESSION = 2000
RECENT_CONTEXT_TURNS = 16
DEFAULT_SESSION_ID = "default_session"

class MemoryBrain:

    def __init__(self):

        self.deleted_sessions = set()

        self.database = {
            "episodes": [],
            "conversations": {},
            "semantic_memory": {
                "topics": {},
                "intents": {},
                "keywords": {},
                "tasks": {}
            },
            "metadata": {
                "version": "2.0.0",
                "created_utc": datetime.now(timezone.utc).isoformat()
            }
        }

        self.statistics = {}

        self.load_memory()
        self.load_statistics()

        print("Memory Brain Loaded")

    # ---------- file handling ----------

    def load_memory(self):

        source_file = MEMORY_FILE

        if not source_file.exists() and LEGACY_MEMORY_FILE.exists():
            source_file = LEGACY_MEMORY_FILE

        if not source_file.exists():
            return

        loaded = load_json_resilient(source_file, None)
        if loaded is None:
            return

        if isinstance(loaded, list):
            self.database["episodes"] = [
                self.normalize_old_memory(item)
                for item in loaded
                if isinstance(item, dict)
            ]
            self.rebuild_semantic_memory()
            return

        if isinstance(loaded, dict):
            self.database.update(loaded)
            self.database.setdefault("episodes", [])
            self.database.setdefault("conversations", {})
            self.database.setdefault("semantic_memory", {})
            for key in ["topics", "intents", "keywords", "tasks"]:
                self.database["semantic_memory"].setdefault(key, {})

    def load_statistics(self):

        if not MEMORY_STATS_FILE.exists():
            return

        self.statistics = load_json_resilient(MEMORY_STATS_FILE, {})

    def save_memory(self):

        atomic_write_json(MEMORY_FILE, self.database)

    def save_statistics(self):

        atomic_write_json(MEMORY_STATS_FILE, self.statistics)

    # ---------- extraction ----------

    def get_understanding_report(self, data):

        if not isinstance(data, dict):
            return {
                "original_text": str(data),
                "main_topic": "unknown",
                "intent": "unknown",
                "words": []
            }

        understanding = data.get("understanding")

        if isinstance(understanding, dict):
            return understanding

        return data

    def get_session_id(self, data):

        if isinstance(data, dict):
            session_id = data.get("session_id")

            if not session_id and isinstance(data.get("memory"), dict):
                session_id = data["memory"].get("session_id")

            if session_id:
                return str(session_id)

        return DEFAULT_SESSION_ID

    def get_chat_title(self, data, text=None):

        if isinstance(data, dict):
            for key in ["chat_title", "conversation_title", "title"]:
                value = data.get(key)
                if value:
                    return str(value)[:80]

        text = str(text or "").strip()
        if text:
            return text[:60]

        return "Canri chat"

    def extract_text(self, report):

        parts = []

        for key in [
            "original_text",
            "corrected_text",
            "user_message",
            "question",
            "query",
            "text",
            "main_topic",
            "intent"
        ]:

            value = report.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip()

    def extract_user_turn_text(self, report):

        for key in [
            "original_text",
            "corrected_text",
            "user_message",
            "question",
            "query",
            "text"
        ]:
            value = report.get(key)
            if value:
                return str(value).strip()

        return self.extract_text(report)

    def extract_keywords(self, report, text):

        keywords = []

        for key in ["main_topic", "intent", "language", "target_language"]:
            value = report.get(key)
            if value and value != "unknown":
                keywords.append(str(value))

        topics = report.get("topics", {})
        if isinstance(topics, dict):
            keywords.extend(str(topic) for topic in topics)

        for task in report.get("possible_tasks", []):
            keywords.append(str(task).replace("_", " "))

        for word_data in report.get("words", []):
            if not isinstance(word_data, dict):
                continue

            word = str(word_data.get("word", "")).strip()
            if word and word_data.get("exists", True):
                keywords.append(word)

            for connection in word_data.get("connections", [])[:8]:
                keywords.append(str(connection))

        keywords.extend(
            re.findall(
                r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{1,}",
                text
            )
        )

        clean = []
        blocked = understanding_stop_terms(report)

        for keyword in keywords:
            keyword = re.sub(r"\s+", " ", str(keyword).lower()).strip()
            keyword = re.sub(r"^[^\w\u0590-\u05FF]+|[^\w\u0590-\u05FF]+$", "", keyword)

            if (
                keyword
                and len(keyword) > 1
                and keyword not in blocked
                and keyword not in clean
            ):
                clean.append(keyword)

        return clean[:80]

    def normalize_old_memory(self, item):

        text = self.extract_text(item)
        keywords = self.extract_keywords(item, text)

        return {
            "id": self.make_memory_id(
                item,
                text,
                item.get("session_id", "legacy_session")
            ),
            "session_id": item.get("session_id", "legacy_session"),
            "created_utc": item.get(
                "created_utc",
                datetime.now(timezone.utc).isoformat()
            ),
            "main_topic": item.get("main_topic", "unknown"),
            "intent": item.get("intent", "unknown"),
            "summary": self.make_summary(item, text),
            "text": text,
            "keywords": keywords,
            "possible_tasks": item.get("possible_tasks", []),
            "importance": self.estimate_importance(item, keywords),
            "source": "legacy_memory",
            "raw_report": item
        }

    def make_memory_id(self, report, text, session_id=DEFAULT_SESSION_ID):

        base = "|".join([
            str(session_id),
            str(report.get("main_topic", "unknown")),
            str(report.get("intent", "unknown")),
            text[:80]
        ])

        return "mem_" + str(abs(hash(base)))

    def make_summary(self, report, text):

        topic = report.get("main_topic", "unknown")
        intent = report.get("intent", "unknown")

        if text:
            return f"{intent} about {topic}: {text[:140]}"

        return f"{intent} about {topic}"

    def estimate_importance(self, report, keywords):

        score = 35

        if report.get("intent") in [
            "code_generation",
            "translation",
            "question",
            "research"
        ]:
            score += 15

        if report.get("main_topic") in [
            "code",
            "language",
            "science",
            "geography",
            "technology"
        ]:
            score += 15

        score += min(len(keywords), 20)

        return min(score, 100)

    # ---------- semantic memory ----------

    def update_semantic_bucket(self, bucket_name, key, episode):

        if not key:
            return

        bucket = self.database["semantic_memory"].setdefault(bucket_name, {})

        item = bucket.get(key, {
            "count": 0,
            "last_seen_utc": None,
            "related_keywords": {},
            "episode_ids": []
        })

        item["count"] += 1
        item["last_seen_utc"] = episode["created_utc"]

        for keyword in episode.get("keywords", [])[:20]:
            item["related_keywords"][keyword] = item["related_keywords"].get(keyword, 0) + 1

        if episode["id"] not in item["episode_ids"]:
            item["episode_ids"].append(episode["id"])
            item["episode_ids"] = item["episode_ids"][-30:]

        bucket[key] = item

    def rebuild_semantic_memory(self):

        self.database["semantic_memory"] = {
            "topics": {},
            "intents": {},
            "keywords": {},
            "tasks": {}
        }

        for episode in self.database["episodes"]:
            self.index_episode(episode)

    def index_episode(self, episode):

        self.update_semantic_bucket(
            "topics",
            episode.get("main_topic", "unknown"),
            episode
        )

        self.update_semantic_bucket(
            "intents",
            episode.get("intent", "unknown"),
            episode
        )

        for keyword in episode.get("keywords", [])[:40]:
            self.update_semantic_bucket("keywords", keyword, episode)

        for task in episode.get("possible_tasks", [])[:20]:
            self.update_semantic_bucket(
                "tasks",
                str(task).replace("_", " ").lower(),
                episode
            )

    # ---------- storing ----------

    def add_memory(self, understanding_report, session_id=DEFAULT_SESSION_ID):

        text = self.extract_text(understanding_report)
        keywords = self.extract_keywords(understanding_report, text)

        episode = {
            "id": self.make_memory_id(understanding_report, text, session_id),
            "session_id": session_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "main_topic": understanding_report.get("main_topic", "unknown"),
            "intent": understanding_report.get("intent", "unknown"),
            "summary": self.make_summary(understanding_report, text),
            "text": text,
            "keywords": keywords,
            "possible_tasks": understanding_report.get("possible_tasks", []),
            "importance": self.estimate_importance(understanding_report, keywords),
            "source": "Understanding_brain",
            "raw_report": understanding_report
        }

        if session_id in self.deleted_sessions:
            episode["not_stored"] = "session_deleted"
            return episode

        existing_ids = {
            item.get("id")
            for item in self.database["episodes"]
        }

        if episode["id"] in existing_ids:
            return episode

        self.database["episodes"].append(episode)
        self.database["episodes"] = self.database["episodes"][-MAX_EPISODES:]

        self.index_episode(episode)
        self.save_memory()

        return episode

    # ---------- conversation memory ----------

    def conversation_bucket(self, session_id, title=None):

        if session_id in self.deleted_sessions:
            return {
                "session_id": session_id,
                "title": title or "Deleted chat",
                "created_utc": None,
                "updated_utc": None,
                "turns": [],
                "summary": "",
                "keywords": [],
                "open_threads": [],
                "deleted": True
            }

        conversations = self.database.setdefault("conversations", {})
        bucket = conversations.get(session_id)

        if not isinstance(bucket, dict):
            now = datetime.now(timezone.utc).isoformat()
            bucket = {
                "session_id": session_id,
                "title": title or "Canri chat",
                "created_utc": now,
                "updated_utc": now,
                "turns": [],
                "summary": "",
                "keywords": [],
                "open_threads": []
            }
            conversations[session_id] = bucket

        if title and (not bucket.get("title") or bucket.get("title") == "Canri chat"):
            bucket["title"] = title

        return bucket

    def rename_session(self, session_id, title):

        session_id = str(session_id or "").strip()
        title = str(title or "").strip()[:80]
        if not session_id or not title:
            return False

        bucket = self.database.setdefault("conversations", {}).get(session_id)
        if not isinstance(bucket, dict):
            return False

        bucket["title"] = title
        bucket["updated_utc"] = datetime.now(timezone.utc).isoformat()
        self.save_memory()
        return True

    def create_session(self, session_id, title=None):

        session_id = str(session_id or "").strip()
        if not session_id:
            return False
        self.deleted_sessions.discard(session_id)
        self.conversation_bucket(session_id, str(title or "Canri chat")[:80])
        self.save_memory()
        return True

    def delete_session(self, session_id):

        session_id = str(session_id or "").strip()
        if not session_id:
            return False

        self.deleted_sessions.add(session_id)

        conversations = self.database.setdefault("conversations", {})
        existed = conversations.pop(session_id, None) is not None
        episodes = self.database.setdefault("episodes", [])
        remaining = [
            episode
            for episode in episodes
            if str(episode.get("session_id", "")) != session_id
        ]
        removed_episodes = len(episodes) - len(remaining)
        if removed_episodes:
            self.database["episodes"] = remaining
            self.rebuild_semantic_memory()

        if existed or removed_episodes:
            self.save_memory()
            return True
        return False

    def clear_conversation_memory(self):

        self.deleted_sessions.update(
            str(session_id)
            for session_id in self.database.get("conversations", {})
        )
        removed_sessions = len(self.database.get("conversations", {}))
        removed_episodes = len(self.database.get("episodes", []))
        self.database["conversations"] = {}
        self.database["episodes"] = []
        self.rebuild_semantic_memory()
        self.save_memory()
        return {
            "cleared": True,
            "removed_sessions": removed_sessions,
            "removed_episodes": removed_episodes
        }

    def summarize_conversation(self, turns):

        recent = turns[-12:]
        parts = []

        for turn in recent:
            user_text = str(turn.get("user", "")).strip()
            canri_text = str(turn.get("canri", "")).strip()
            if user_text:
                parts.append("User: " + user_text[:140])
            if canri_text:
                parts.append("Canri: " + canri_text[:140])

        return " | ".join(parts)[-1400:]

    def conversation_keywords(self, turns):

        counter = Counter()

        for turn in turns[-80:]:
            for word in turn.get("keywords", []):
                clean = str(word or "").casefold().strip()
                if clean:
                    counter[clean] += 1

        return [word for word, _ in counter.most_common(30)]

    def add_user_turn(self, session_id, user_text, understanding_report, episode_id=None, data=None):

        if session_id in self.deleted_sessions:
            return {
                "id": None,
                "session_id": session_id,
                "not_stored": "session_deleted"
            }

        title = self.get_chat_title(data, user_text)
        bucket = self.conversation_bucket(session_id, title)
        now = datetime.now(timezone.utc).isoformat()
        turn_id = "turn_" + str(abs(hash(f"{session_id}|{user_text[:120]}|{episode_id}")))

        for turn in bucket.get("turns", []):
            if turn.get("id") == turn_id:
                return turn

        turn = {
            "id": turn_id,
            "created_utc": now,
            "updated_utc": now,
            "episode_id": episode_id,
            "user": user_text,
            "canri": "",
            "main_topic": understanding_report.get("main_topic", "unknown"),
            "intent": understanding_report.get("intent", "unknown"),
            "keywords": self.extract_keywords(understanding_report, user_text)[:30],
            "request_contract": understanding_report.get("request_contract", {}),
            "entities": understanding_report.get("entities", [])[:30],
            "artifacts": [],
            "quality": {}
        }

        bucket.setdefault("turns", []).append(turn)
        bucket["turns"] = bucket["turns"][-MAX_TURNS_PER_SESSION:]
        bucket["updated_utc"] = now
        bucket["summary"] = self.summarize_conversation(bucket["turns"])
        bucket["keywords"] = self.conversation_keywords(bucket["turns"])
        return turn

    def response_artifacts(self, canri_text, response_result=None, manager_result=None):

        artifacts = []
        response_result = response_result if isinstance(response_result, dict) else {}
        manager_result = manager_result if isinstance(manager_result, dict) else {}
        results = manager_result.get("results", {})
        results = results if isinstance(results, dict) else {}
        code_result = results.get("Code_brain", {})
        if isinstance(code_result, dict):
            generated = str(code_result.get("generated_code") or "").strip()
            if generated:
                artifacts.append({
                    "type": "code",
                    "language": code_result.get("language", "python"),
                    "program_kind": code_result.get("program_kind"),
                    "content": generated[:50000],
                    "selected_functions": code_result.get("function_selection", {}).get(
                        "selected_functions", []
                    )[:30],
                })
            project_files = code_result.get("project_files", {})
            if isinstance(project_files, dict) and project_files:
                artifacts.append({
                    "type": "code_project",
                    "program_kind": code_result.get("program_kind"),
                    "files": {
                        str(path): str(content)[:30000]
                        for path, content in list(project_files.items())[:30]
                    },
                })

        agent_result = results.get("Agent_brain", {})
        if isinstance(agent_result, dict):
            changed_files = [
                {
                    "path": item.get("path"),
                    "added_lines": item.get("added_lines", 0),
                    "removed_lines": item.get("removed_lines", 0),
                    "line_count": item.get("after_line_count", 0),
                }
                for item in agent_result.get("action_results", [])
                if isinstance(item, dict)
                and item.get("type") == "write_file"
                and item.get("ok")
            ]
            if changed_files:
                artifacts.append({
                    "type": "agent_project",
                    "workspace": agent_result.get("workspace"),
                    "status": agent_result.get("status"),
                    "files": changed_files[:50],
                })

        for language, content in re.findall(
            r"```([a-zA-Z0-9_+\-.#]*)\s*(.*?)```",
            str(canri_text or ""),
            re.DOTALL,
        ):
            content = content.strip()
            if content and not any(
                item.get("type") == "code" and item.get("content") == content
                for item in artifacts
            ):
                artifacts.append({
                    "type": "code",
                    "language": (language or "text").lower(),
                    "content": content[:50000],
                })

        primary_brain = response_result.get("primary_brain")
        if primary_brain in {"Story_brain", "Creative_brain"} and canri_text:
            artifacts.append({"type": "story", "content": str(canri_text)[:20000]})

        source_refs = []
        for result in results.values():
            if not isinstance(result, dict):
                continue
            candidates = [
                *result.get("strongest_sources", [])[:8],
                *result.get("fetched_sources", [])[:8],
                *result.get("approved_research_links", [])[:8],
            ]
            for source in candidates:
                if not isinstance(source, dict):
                    continue
                reference = {
                    "name": source.get("name") or source.get("title"),
                    "url": source.get("url") or source.get("search_url"),
                    "trust_score": source.get("trust_score") or source.get("reliability_score"),
                    "source_type": source.get("source_type"),
                }
                if reference["name"] and reference not in source_refs:
                    source_refs.append(reference)
        if source_refs:
            artifacts.append({"type": "sources", "items": source_refs[:20]})

        return artifacts[:12]

    def store_response(self, session_id, user_text, canri_text, response_result=None, manager_result=None):

        if session_id in self.deleted_sessions:
            return None

        bucket = self.conversation_bucket(session_id)
        turns = bucket.setdefault("turns", [])
        now = datetime.now(timezone.utc).isoformat()
        target = None

        for turn in reversed(turns):
            if str(turn.get("user", "")).strip() == str(user_text).strip() and not turn.get("canri"):
                target = turn
                break

        if target is None:
            target = {
                "id": "turn_" + str(abs(hash(f"{session_id}|{user_text[:120]}|response"))),
                "created_utc": now,
                "episode_id": None,
                "user": user_text,
                "main_topic": "unknown",
                "intent": "unknown",
                "keywords": [],
                "quality": {}
            }
            turns.append(target)

        target["canri"] = str(canri_text or "")
        target["updated_utc"] = now
        target["artifacts"] = self.response_artifacts(
            canri_text,
            response_result,
            manager_result,
        )

        if isinstance(response_result, dict):
            target["response"] = {
                "primary_brain": response_result.get("primary_brain"),
                "confidence": response_result.get("confidence"),
                "blocked": response_result.get("blocked")
            }

        if isinstance(manager_result, dict):
            quality = manager_result.get("results", {}).get("Quality_Control_brain", {})
            if isinstance(quality, dict):
                target["quality"] = {
                    "passed": quality.get("passed"),
                    "quality_score": quality.get("quality_score"),
                    "needs_retry": quality.get("needs_retry")
                }
                target["failed_requirements"] = [
                    check.get("requirement")
                    for check in quality.get("requirement_checks", [])
                    if isinstance(check, dict) and check.get("passed") is False
                ][:30]
            cognitive = manager_result.get("cognitive_workspace", {})
            if isinstance(cognitive, dict):
                target["cognitive_state"] = {
                    "summary": cognitive.get("summary", {}),
                    "decision": cognitive.get("decision", {}),
                    "passed_requirement_ids": cognitive.get(
                        "passed_requirement_ids",
                        [],
                    )[:80],
                    "unresolved_requirements": cognitive.get(
                        "unresolved_requirements",
                        [],
                    )[:30],
                    "correction_packets": cognitive.get("correction_packets", [])[:8],
                }
                unresolved = cognitive.get("unresolved_requirements", [])
                if isinstance(unresolved, list) and unresolved:
                    target["failed_requirements"] = list(dict.fromkeys([
                        *target.get("failed_requirements", []),
                        *[
                            item.get("id") or item.get("text")
                            for item in unresolved
                            if isinstance(item, dict)
                            and item.get("status") == "failed"
                            and (item.get("id") or item.get("text"))
                        ],
                    ]))[:30]

        bucket["turns"] = turns[-MAX_TURNS_PER_SESSION:]
        bucket["updated_utc"] = now
        bucket["summary"] = self.summarize_conversation(bucket["turns"])
        bucket["keywords"] = self.conversation_keywords(bucket["turns"])
        self.save_memory()
        return target

    def is_continuation_request(self, text):

        lowered = str(text).lower()
        markers = [
            "continue",
            "same program",
            "same code",
            "same story",
            "you just wrote",
            "previous code",
            "previous answer",
            "fix the program",
            "fix it",
            "improve it",
            "improve the same",
            "add these features",
            "from the code",
            "continue the code",
            "continue the story",
            "continue the answer",
            "use the previous",
            "based on the previous",
            "המשך",
            "תמשיך",
            "תתקן",
            "תשפר",
            "אותו קוד",
            "אותה תוכנה",
            "אותו סיפור",
            "התשובה הקודמת",
            "מהקוד הקודם"
        ]

        return any(marker in lowered for marker in markers)

    def continuation_kind(self, text):

        lowered = str(text or "").lower()
        if any(marker in lowered for marker in [
            "code", "program", "function", "python", "app", "project",
            "קוד", "תוכנה", "פונקציה", "פרויקט",
        ]):
            return "code"
        if any(marker in lowered for marker in [
            "story", "chapter", "character", "plot",
            "סיפור", "פרק", "דמות", "עלילה",
        ]):
            return "story"
        if any(marker in lowered for marker in [
            "source", "fact", "explanation", "answer",
            "מקור", "עובדה", "הסבר", "תשובה",
        ]):
            return "answer"
        return "general"

    def turn_matches_continuation_kind(self, turn, kind):

        artifacts = turn.get("artifacts", []) if isinstance(turn, dict) else []
        artifact_types = {
            item.get("type")
            for item in artifacts
            if isinstance(item, dict)
        }
        topic = str(turn.get("main_topic", "")).lower()
        if kind == "code":
            return bool(
                artifact_types.intersection({"code", "code_project", "agent_project"})
                or topic == "code"
            )
        if kind == "story":
            return "story" in artifact_types or topic in {"story", "creative"}
        if kind == "answer":
            return bool(str(turn.get("canri", "")).strip())
        return True

    def select_continuation_turn(self, turns, current_text):

        if not turns:
            return {}, "none"
        kind = self.continuation_kind(current_text)
        for turn in reversed(turns):
            if self.turn_matches_continuation_kind(turn, kind):
                return turn, kind
        return turns[-1], kind

    def relevant_conversation_turns(
        self,
        turns,
        current_topic,
        current_intent,
        current_keywords,
        continuation=False,
        limit=12
    ):

        ranked = []
        for position, turn in enumerate(turns):
            if not str(turn.get("canri", "")).strip():
                continue
            score = 0
            reasons = []
            turn_keywords = set(turn.get("keywords", []))
            overlap = sorted(current_keywords & turn_keywords)
            if current_topic not in {"", "unknown", "general"} and turn.get("main_topic") == current_topic:
                score += 35
                reasons.append("same_topic")
            if current_intent not in {"", "unknown", "request"} and turn.get("intent") == current_intent:
                score += 20
                reasons.append("same_intent")
            if overlap:
                score += min(30, len(overlap) * 6)
                reasons.append("keyword_overlap")
            recency = max(0, 15 - (len(turns) - position - 1))
            score += recency
            if continuation and position == len(turns) - 1:
                score += 100
                reasons.append("explicit_continuation_source")
            if score <= 10 and not continuation:
                continue
            ranked.append({
                "id": turn.get("id"),
                "user": str(turn.get("user", ""))[:1000],
                "canri": str(turn.get("canri", ""))[:12000],
                "main_topic": turn.get("main_topic"),
                "intent": turn.get("intent"),
                "keywords": list(turn_keywords)[:30],
                "score": score,
                "reasons": reasons,
                "quality": turn.get("quality", {})
            })

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    def build_conversation_report(self, session_id, current_report=None, current_text=""):

        bucket = self.conversation_bucket(session_id)
        turns = bucket.get("turns", [])
        code_blocks = []
        current_report = current_report if isinstance(current_report, dict) else {}
        current_topic = current_report.get("main_topic", "unknown")
        current_intent = current_report.get("intent", "unknown")
        current_keywords = set(
            self.extract_keywords(current_report, current_text)
            if current_report
            else []
        )

        for turn in turns[-40:]:
            canri_text = str(turn.get("canri", ""))
            for match in re.finditer(
                r"```([a-zA-Z0-9_+\-.#]*)\s*(.*?)```",
                canri_text,
                re.DOTALL
            ):
                code = match.group(2).strip()
                if not code:
                    continue
                code_blocks.append({
                    "turn_id": turn.get("id"),
                    "language": (match.group(1) or "text").strip().lower(),
                    "code": code[:30000],
                    "turn_user": str(turn.get("user", ""))[:300],
                    "created_utc": turn.get("created_utc")
                })
            for artifact in turn.get("artifacts", []):
                if not isinstance(artifact, dict) or artifact.get("type") != "code":
                    continue
                code = str(artifact.get("content", "")).strip()
                if not code or any(
                    item.get("turn_id") == turn.get("id") and item.get("code") == code[:30000]
                    for item in code_blocks
                ):
                    continue
                code_blocks.append({
                    "turn_id": turn.get("id"),
                    "language": artifact.get("language", "python"),
                    "code": code[:30000],
                    "program_kind": artifact.get("program_kind"),
                    "turn_user": str(turn.get("user", ""))[:300],
                    "created_utc": turn.get("created_utc"),
                })

        completed_turns = [
            turn
            for turn in turns
            if str(turn.get("canri", "")).strip()
        ]
        last_turn = completed_turns[-1] if completed_turns else {}
        last_topic = last_turn.get("main_topic", "unknown")
        last_intent = last_turn.get("intent", "unknown")
        last_keywords = set(last_turn.get("keywords", []))
        overlap = sorted(current_keywords & last_keywords)[:12]
        continuation = self.is_continuation_request(current_text)
        continuation_turn, continuation_kind = self.select_continuation_turn(
            completed_turns,
            current_text,
        ) if continuation else ({}, "none")
        relevant_turns = self.relevant_conversation_turns(
            completed_turns,
            current_topic,
            current_intent,
            current_keywords,
            continuation
        )
        topic_shift = bool(
            current_topic
            and last_topic
            and current_topic not in {"unknown", "general"}
            and last_topic not in {"unknown", "general"}
            and current_topic != last_topic
            and len(overlap) < 3
        )
        topic_stack = []
        for turn in completed_turns[-30:]:
            cognitive_state = turn.get("cognitive_state", {})
            cognitive_summary = (
                cognitive_state.get("summary", {})
                if isinstance(cognitive_state, dict)
                else {}
            )
            contract = turn.get("request_contract", {})
            global_picture = (
                contract.get("global_picture", {})
                if isinstance(contract, dict)
                else {}
            )
            topic_item = {
                "topic": turn.get("main_topic", "unknown"),
                "intent": turn.get("intent", "unknown"),
                "goal": cognitive_summary.get("goal") or global_picture.get("goal"),
                "turn_id": turn.get("id"),
                "open_requirements": turn.get("failed_requirements", [])[:12],
                "status": "open" if turn.get("failed_requirements") else "completed",
            }
            if topic_stack and (
                topic_stack[-1].get("topic") == topic_item["topic"]
                and topic_stack[-1].get("intent") == topic_item["intent"]
            ):
                topic_stack[-1] = topic_item
            else:
                topic_stack.append(topic_item)
        active_turn = continuation_turn or last_turn
        active_cognitive = active_turn.get("cognitive_state", {}) if active_turn else {}
        active_summary = (
            active_cognitive.get("summary", {})
            if isinstance(active_cognitive, dict)
            else {}
        )
        active_contract = active_turn.get("request_contract", {}) if active_turn else {}
        active_global = (
            active_contract.get("global_picture", {})
            if isinstance(active_contract, dict)
            else {}
        )

        return {
            "session_id": session_id,
            "title": bucket.get("title"),
            "turn_count": len(turns),
            "summary": bucket.get("summary", ""),
            "keywords": bucket.get("keywords", [])[:30],
            "recent_turns": [
                {
                    "user": turn.get("user", "")[:500],
                    "canri": turn.get("canri", "")[:700],
                    "main_topic": turn.get("main_topic"),
                    "intent": turn.get("intent"),
                    "quality": turn.get("quality", {})
                }
                for turn in turns[-RECENT_CONTEXT_TURNS:]
            ],
            "recent_code_blocks": code_blocks[-8:],
            "last_completed_turn": {
                "user": str(last_turn.get("user", ""))[:500],
                "canri": str(last_turn.get("canri", ""))[:900],
                "main_topic": last_topic,
                "intent": last_intent,
                "keywords": list(last_keywords)[:20],
                "created_utc": last_turn.get("created_utc")
            } if last_turn else {},
            "continuation_request": continuation,
            "continuation_kind": continuation_kind,
            "continuation_source": (
                {
                    "turn_id": continuation_turn.get("id"),
                    "user": str(continuation_turn.get("user", ""))[:1000],
                    "canri": str(continuation_turn.get("canri", ""))[:12000],
                    "main_topic": continuation_turn.get("main_topic"),
                    "intent": continuation_turn.get("intent"),
                    "quality": continuation_turn.get("quality", {}),
                    "request_contract": continuation_turn.get("request_contract", {}),
                    "artifacts": continuation_turn.get("artifacts", [])[:8],
                    "failed_requirements": continuation_turn.get("failed_requirements", [])[:20],
                    "cognitive_state": continuation_turn.get("cognitive_state", {}),
                }
                if continuation and continuation_turn
                else None
            ),
            "relevant_turns": relevant_turns,
            "relevant_turn_ids": [turn.get("id") for turn in relevant_turns],
            "topic_shift_from_previous": topic_shift,
            "keyword_overlap_with_previous": overlap,
            "usable_previous_code": next(
                (
                    item
                    for item in reversed(code_blocks)
                    if not continuation_turn or item.get("turn_id") == continuation_turn.get("id")
                ),
                code_blocks[-1] if code_blocks else None,
            ),
            "agent_continuation": next(
                (
                    artifact
                    for artifact in reversed((continuation_turn or last_turn).get("artifacts", []))
                    if isinstance(artifact, dict) and artifact.get("type") == "agent_project"
                ),
                None,
            ),
            "thread_state": {
                "active_topic": continuation_turn.get("main_topic") if continuation_turn else last_topic,
                "active_intent": continuation_turn.get("intent") if continuation_turn else last_intent,
                "active_turn_id": continuation_turn.get("id") if continuation_turn else last_turn.get("id"),
                "artifact_types": list(dict.fromkeys(
                    item.get("type")
                    for item in (continuation_turn or last_turn).get("artifacts", [])
                    if isinstance(item, dict) and item.get("type")
                )),
                "open_requirements": (continuation_turn or last_turn).get("failed_requirements", [])[:20],
                "active_goal": active_summary.get("goal") or active_global.get("goal"),
                "selected_brain": active_summary.get("selected_brain"),
                "topic_stack": topic_stack[-12:],
                "completed_requirement_ids": (
                    active_cognitive.get("passed_requirement_ids", [])
                    if isinstance(active_cognitive, dict)
                    else []
                ),
            },
            "session_isolation": True
        }

    # ---------- search ----------

    def same_session(self, episode, session_id):

        return episode.get("session_id", "legacy_session") == session_id

    def session_episodes(self, session_id):

        return [
            episode
            for episode in self.database.get("episodes", [])
            if self.same_session(episode, session_id)
        ]

    def score_episode(self, episode, topic, intent, keywords, text):

        score = 0
        reasons = []

        if topic and episode.get("main_topic") == topic:
            score += 25
            reasons.append("same_topic")

        if intent and episode.get("intent") == intent:
            score += 20
            reasons.append("same_intent")

        episode_keywords = set(episode.get("keywords", []))
        keyword_overlap = sorted(set(keywords) & episode_keywords)

        if keyword_overlap:
            score += len(keyword_overlap) * 6
            reasons.append("keyword_overlap")

        lowered_text = text.lower()
        episode_text = episode.get("text", "").lower()

        shared_text_tokens = set(
            token
            for token in re.findall(r"[a-zA-Z\u0590-\u05FF]{3,}", lowered_text)
            if token in episode_text
        )

        if shared_text_tokens:
            score += min(len(shared_text_tokens) * 2, 16)
            reasons.append("text_similarity")

        score += min(episode.get("importance", 0) / 10, 10)

        return {
            "score": round(score, 2),
            "reasons": reasons,
            "keyword_overlap": keyword_overlap
        }

    def search_memory(self, topic, intent, keywords, text, session_id):

        matches = []

        for episode in self.database.get("episodes", []):
            if not self.same_session(episode, session_id):
                continue

            scored = self.score_episode(
                episode,
                topic,
                intent,
                keywords,
                text
            )

            if scored["score"] <= 0:
                continue

            matches.append({
                "id": episode.get("id"),
                "score": scored["score"],
                "reasons": scored["reasons"],
                "keyword_overlap": scored["keyword_overlap"],
                "topic": episode.get("main_topic"),
                "intent": episode.get("intent"),
                "summary": episode.get("summary"),
                "keywords": episode.get("keywords", [])[:20],
                "created_utc": episode.get("created_utc"),
                "session_id": episode.get("session_id", "legacy_session"),
                "importance": episode.get("importance", 0)
            })

        matches.sort(
            key=lambda item: (
                item["score"],
                item.get("importance", 0),
                item.get("created_utc", "")
            ),
            reverse=True
        )

        return matches[:MAX_MATCHES]

    def search_topic(self, topic, session_id):

        return [
            episode
            for episode in self.database.get("episodes", [])
            if self.same_session(episode, session_id)
            if episode.get("main_topic") == topic
        ][-MAX_MATCHES:]

    def search_intent(self, intent, session_id):

        return [
            episode
            for episode in self.database.get("episodes", [])
            if self.same_session(episode, session_id)
            if episode.get("intent") == intent
        ][-MAX_MATCHES:]

    def search_keywords(self, keywords, session_id):

        keyword_set = set(keywords)
        results = []

        for episode in self.database.get("episodes", []):
            if not self.same_session(episode, session_id):
                continue

            if keyword_set & set(episode.get("keywords", [])):
                results.append(episode)

        return results[-MAX_MATCHES:]

    # ---------- reports ----------

    def build_semantic_summary(self, keywords, session_id):

        topic_counter = Counter()
        intent_counter = Counter()
        keyword_profiles = defaultdict(Counter)
        related_counter = Counter()
        known_keywords = set()

        for episode in self.session_episodes(session_id):
            topic_counter.update([episode.get("main_topic", "unknown")])
            intent_counter.update([episode.get("intent", "unknown")])

            episode_keywords = episode.get("keywords", [])[:40]
            episode_keyword_set = set(episode_keywords)

            for keyword in keywords[:20]:
                if keyword not in episode_keyword_set:
                    continue

                known_keywords.add(keyword)
                keyword_profiles[keyword].update(episode_keywords[:20])

        for keyword in keywords[:20]:
            related_counter.update(keyword_profiles.get(keyword, {}))

        return {
            "session_id": session_id,
            "known_keywords": [
                keyword
                for keyword in keywords
                if keyword in known_keywords
            ],
            "related_keywords": [
                keyword
                for keyword, _ in related_counter.most_common(20)
                if keyword not in keywords
            ],
            "topic_profiles": dict(topic_counter.most_common(20)),
            "intent_profiles": dict(intent_counter.most_common(20))
        }

    def update_statistics(self, memory_report):

        stats = self.statistics.get("Memory_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["episodes"] = len(self.database.get("episodes", []))
        stats["last_memory_found"] = memory_report.get("memory_found", 0)
        stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()

        self.statistics["Memory_brain"] = stats
        self.save_statistics()

    def process(self, data):

        understanding_report = self.get_understanding_report(data)
        session_id = self.get_session_id(data)
        text = self.extract_text(understanding_report)
        user_turn_text = self.extract_user_turn_text(understanding_report)
        keywords = self.extract_keywords(understanding_report, text)

        topic = understanding_report.get("main_topic", "unknown")
        intent = understanding_report.get("intent", "unknown")

        ranked_matches = self.search_memory(
            topic,
            intent,
            keywords,
            text,
            session_id
        )

        topic_matches = self.search_topic(topic, session_id)
        intent_matches = self.search_intent(intent, session_id)
        keyword_matches = self.search_keywords(keywords, session_id)

        semantic_summary = self.build_semantic_summary(keywords, session_id)

        memory_report = {
            "memory_found": len(ranked_matches),
            "session_id": session_id,
            "session_isolation": True,
            "conversation": self.build_conversation_report(
                session_id,
                understanding_report,
                user_turn_text
            ),
            "ranked_matches": ranked_matches,
            "topic_matches": topic_matches,
            "intent_matches": intent_matches,
            "keyword_matches": keyword_matches,
            "semantic_summary": semantic_summary,
            "current_keywords": keywords,
            "memory_depth": {
                "episodes": len(self.database.get("episodes", [])),
                "session_episodes": len(self.session_episodes(session_id)),
                "topics": len(self.database["semantic_memory"].get("topics", {})),
                "intents": len(self.database["semantic_memory"].get("intents", {})),
                "keywords": len(self.database["semantic_memory"].get("keywords", {})),
                "tasks": len(self.database["semantic_memory"].get("tasks", {}))
            }
        }

        stored_episode = self.add_memory(understanding_report, session_id)
        user_turn = self.add_user_turn(
            session_id,
            user_turn_text,
            understanding_report,
            stored_episode.get("id"),
            data
        )

        memory_report["stored_episode_id"] = stored_episode["id"]
        memory_report["stored_turn_id"] = user_turn.get("id")
        memory_report["conversation"] = self.build_conversation_report(
            session_id,
            understanding_report,
            user_turn_text
        )
        memory_report["memory_depth"] = {
            "episodes": len(self.database.get("episodes", [])),
            "session_episodes": len(self.session_episodes(session_id)),
            "topics": len(self.database["semantic_memory"].get("topics", {})),
            "intents": len(self.database["semantic_memory"].get("intents", {})),
            "keywords": len(self.database["semantic_memory"].get("keywords", {})),
            "tasks": len(self.database["semantic_memory"].get("tasks", {}))
        }

        self.update_statistics(memory_report)

        return {
            "brain": "Memory_brain",
            "understanding": understanding_report,
            "memory": memory_report,
            "rules": [
                "Store Understanding_brain reports as episodic memories.",
                "Keep memory search isolated by session_id.",
                "Build semantic memory from topics, intents, keywords, and tasks.",
                "Return ranked memory matches for other brains.",
                "Keep memory compact enough for other brains to use safely."
            ]
        }


brain = MemoryBrain()
