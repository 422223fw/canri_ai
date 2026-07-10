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


DATA_DIR = Path(__file__).parent / "data"
MEMORY_FILE = DATA_DIR / "Memory_database.json"
MEMORY_STATS_FILE = DATA_DIR / "Memory_statistics.json"
LEGACY_MEMORY_FILE = Path("memory.json")

MAX_EPISODES = 5000
MAX_MATCHES = 12
DEFAULT_SESSION_ID = "default_session"

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "what", "where",
    "how", "why", "is", "are", "was", "were", "does", "did",
    "about", "from", "into", "code", "create", "make", "build",
    "של", "את", "על", "מה", "איפה", "איך", "למה", "זה", "אני",
    "רוצה", "תעשה", "תכין", "לי"
}


class MemoryBrain:

    def __init__(self):

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

        try:
            with source_file.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
        except (OSError, json.JSONDecodeError):
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

        try:
            with MEMORY_STATS_FILE.open("r", encoding="utf-8") as file:
                self.statistics = json.load(file)
        except (OSError, json.JSONDecodeError):
            self.statistics = {}

    def save_memory(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with MEMORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                self.database,
                file,
                indent=2,
                ensure_ascii=False
            )
            file.write("\n")

    def save_statistics(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with MEMORY_STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                self.statistics,
                file,
                indent=2,
                ensure_ascii=False
            )
            file.write("\n")

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

        for keyword in keywords:
            keyword = re.sub(r"\s+", " ", str(keyword).lower()).strip()
            keyword = re.sub(r"^[^\w\u0590-\u05FF]+|[^\w\u0590-\u05FF]+$", "", keyword)

            if (
                keyword
                and len(keyword) > 1
                and keyword not in STOP_WORDS
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

    def summarize_conversation(self, turns):

        recent = turns[-6:]
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

        for turn in turns[-20:]:
            text = f"{turn.get('user', '')} {turn.get('canri', '')}"
            for word in re.findall(r"[a-zA-Z\u0590-\u05FF][a-zA-Z0-9_\-\u0590-\u05FF]{2,}", text.lower()):
                if word not in STOP_WORDS:
                    counter[word] += 1

        return [word for word, _ in counter.most_common(30)]

    def add_user_turn(self, session_id, user_text, understanding_report, episode_id=None, data=None):

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
            "quality": {}
        }

        bucket.setdefault("turns", []).append(turn)
        bucket["turns"] = bucket["turns"][-300:]
        bucket["updated_utc"] = now
        bucket["summary"] = self.summarize_conversation(bucket["turns"])
        bucket["keywords"] = self.conversation_keywords(bucket["turns"])
        return turn

    def store_response(self, session_id, user_text, canri_text, response_result=None, manager_result=None):

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

        bucket["turns"] = turns[-300:]
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
            "מהקוד הקודם",
            "תמשיך",
            "תתקן",
            "תשפר"
        ]

        return any(marker in lowered for marker in markers)

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

        for turn in turns[-12:]:
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
                    "language": (match.group(1) or "text").strip().lower(),
                    "code": code[:12000],
                    "turn_user": str(turn.get("user", ""))[:300],
                    "created_utc": turn.get("created_utc")
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
        topic_shift = bool(
            current_topic
            and last_topic
            and current_topic not in {"unknown", "general"}
            and last_topic not in {"unknown", "general"}
            and current_topic != last_topic
            and len(overlap) < 3
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
                for turn in turns[-8:]
            ],
            "recent_code_blocks": code_blocks[-4:],
            "last_completed_turn": {
                "user": str(last_turn.get("user", ""))[:500],
                "canri": str(last_turn.get("canri", ""))[:900],
                "main_topic": last_topic,
                "intent": last_intent,
                "keywords": list(last_keywords)[:20],
                "created_utc": last_turn.get("created_utc")
            } if last_turn else {},
            "continuation_request": self.is_continuation_request(current_text),
            "topic_shift_from_previous": topic_shift,
            "keyword_overlap_with_previous": overlap,
            "usable_previous_code": code_blocks[-1] if code_blocks else None,
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
