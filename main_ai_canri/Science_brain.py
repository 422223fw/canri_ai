"""
Science_brain.py
Canri AI

תפקיד: פיזיקה, כימיה, ביולוגיה ומדע כללי.

זרימת עבודה (תואם לארכיטקטורת Canri):

    Manager_brain
        ↓ (report מ-UnderstandingBrain)
    Science_brain
        Load data (Articles.json)
            ↓
        Load statistics (Articles_statistics.json)
            ↓
        Analyze report (כל words/connections, לא רק main_topic)
            ↓
        Search local database
            ↓
        Rank by statistics (trust / success_rate / uses)
            ↓
        Fact_Check hook (לא ממומש כרגע - רק flag)
            ↓
        Update statistics
            ↓
        Return report -> Manager_brain
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
ARTICLES_PATH = DATA_DIR / "Articles.json"
STATISTICS_PATH = DATA_DIR / "Articles_statistics.json"

# ניקוד טקסטואלי (title*3 + content*1) שנחשב "התאמה מלאה" - 100% ביטחון לפני שקלול סטטיסטיקה
MAX_MATCH_SCORE_FOR_FULL_CONFIDENCE = 6

# מתחת לסף הזה - ה-brain ינסה חיפוש חיצוני (placeholder כרגע)
LOCAL_CONFIDENCE_THRESHOLD = 40

# מתחת לסף הזה (אחרי הכל) - ה-brain מסמן needs_help / needs_fact_check
MIN_USABLE_CONFIDENCE = 15

# כמה statistics.trust משפיע על הדירוג הסופי (0-1, 0 = רק טקסט, 1 = רק אמינות)
STATISTICS_WEIGHT = 0.25
QUALITY_WEIGHT = 0.2

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "what", "how", "why",
    "are", "is", "was", "were", "does", "did", "can", "could", "should",
    "about", "into", "from", "של", "את", "על", "מה", "איך", "למה"
}

GENERIC_SCIENCE_TERMS = {
    "science", "scientific", "evidence", "model", "models", "measurement",
    "measurements", "application", "applications", "concept", "concepts",
    "research", "study", "studies", "system", "systems", "field", "fields",
    "method", "methods", "quality", "source", "sources", "data", "information",
    "general", "knowledge", "process", "processes"
}


class ScienceBrain:

    def __init__(self):
        self.articles = self._load_articles()
        self.statistics = self._load_statistics()
        self.cache = {}
        print("Science Brain Loaded")

    # ---------- טעינה ----------

    def _load_json(self, path, default):
        if not path.exists():
            print(f"[Science_brain] WARNING: {path} not found, using default")
            return default

        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Science_brain] ERROR loading {path}: {e}")
            return default

    def _load_articles(self):
        data = self._load_json(ARTICLES_PATH, [])
        return data if isinstance(data, list) else []

    def _load_statistics(self):
        data = self._load_json(STATISTICS_PATH, {})
        return data if isinstance(data, dict) else {}

    def _save_statistics(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with STATISTICS_PATH.open("w", encoding="utf-8") as f:
                json.dump(self.statistics, f, ensure_ascii=False, indent=4)
        except OSError as e:
            print(f"[Science_brain] ERROR saving statistics: {e}")

    # ---------- ניתוח ה-report ----------

    def _collect_keywords(self, report):
        """
        משתמש בכל המידע מ-UnderstandingBrain:
        main_topic, topics, וגם connections של כל מילה ב-words.
        לא מתבסס רק על main_topic.
        """
        keywords = set()

        main_topic = report.get("main_topic")
        if main_topic and main_topic != "unknown":
            keywords.add(main_topic.lower())

        for topic in report.get("topics", {}):
            keywords.add(topic.lower())

        for word_data in report.get("words", []):

            if not word_data.get("exists"):
                continue

            keywords.add(word_data["word"].lower())

            for connection in word_data.get("connections", []):
                keywords.add(connection.lower())

        original_text = report.get("original_text", "")
        for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", original_text.lower()):
            if token not in STOP_WORDS:
                keywords.add(token)

        return {
            keyword
            for keyword in keywords
            if keyword not in STOP_WORDS
            and keyword not in GENERIC_SCIENCE_TERMS
            and len(keyword) > 2
        }

    # ---------- חיפוש מקומי ----------

    def _field_text(self, value):
        if isinstance(value, list):
            return " ".join(str(item) for item in value)
        if isinstance(value, dict):
            return " ".join(str(item) for item in value.values())
        return str(value or "")

    def _text_match_score(self, article, keywords):
        fields = {
            "title": (article.get("title", ""), 4),
            "abstract": (article.get("abstract", ""), 3),
            "keywords": (self._field_text(article.get("keywords", [])), 3),
            "field": (article.get("field", ""), 2),
            "subfield": (article.get("subfield", ""), 2),
            "concepts": (self._field_text(article.get("concepts", [])), 2),
            "content": (article.get("content", ""), 1)
        }

        score = 0
        matched_by_field = {}

        for field_name, (text, weight) in fields.items():
            text_lower = str(text).lower()
            matches = {
                kw
                for kw in keywords
                if kw
                and kw not in GENERIC_SCIENCE_TERMS
                and kw in text_lower
            }

            if matches:
                matched_by_field[field_name] = sorted(matches)
                score += len(matches) * weight

        return score, matched_by_field

    def _article_quality_score(self, article):
        quality = 50

        content_length = len(article.get("content", ""))
        if content_length >= 2500:
            quality += 15
        elif content_length >= 1200:
            quality += 8

        if article.get("abstract"):
            quality += 8
        if article.get("key_points"):
            quality += 8
        if article.get("source_recommendations"):
            quality += 8
        if article.get("field") and article.get("subfield"):
            quality += 6
        if article.get("difficulty"):
            quality += 5

        return min(quality, 100)

    def _get_article_stats(self, article_id):
        """
        מחזיר את הסטטיסטיקה של מאמר, או ברירת מחדל ניטרלית אם אין עדיין.
        """
        return self.statistics.get(
            article_id,
            {"uses": 0, "success_rate": 50, "trust": 50}
        )

    def search_local_articles(self, keywords):
        """
        מחפש לפי התאמת טקסט גנרית (title/content), ואז מדרג מחדש
        לפי statistics (trust) - מאמר עם אמינות גבוהה יותר עולה בדירוג.
        """
        matches = []

        for article in self.articles:

            article_id = article.get("id", article.get("title", "untitled"))

            text_score, matched_by_field = self._text_match_score(
                article,
                keywords
            )

            if text_score == 0:
                continue

            stats = self._get_article_stats(article_id)
            trust_score = stats.get("trust", 50) / 100  # 0-1
            quality_score = self._article_quality_score(article) / 100

            # ניקוד סופי: שקלול בין התאמת טקסט לבין אמינות סטטיסטית
            final_score = (
                (1 - STATISTICS_WEIGHT - QUALITY_WEIGHT) * text_score
                +
                STATISTICS_WEIGHT * trust_score * MAX_MATCH_SCORE_FOR_FULL_CONFIDENCE
                +
                QUALITY_WEIGHT * quality_score * MAX_MATCH_SCORE_FOR_FULL_CONFIDENCE
            )

            matches.append({
                "article_id": article_id,
                "title": article.get("title", "untitled"),
                "field": article.get("field", "science"),
                "subfield": article.get("subfield", "general"),
                "difficulty": article.get("difficulty", "intermediate"),
                "abstract": article.get("abstract", ""),
                "content": article.get("content", ""),
                "keywords": article.get("keywords", []),
                "key_points": article.get("key_points", []),
                "source_recommendations": article.get("source_recommendations", []),
                "matched_by_field": matched_by_field,
                "text_score": text_score,
                "trust": stats.get("trust", 50),
                "quality": self._article_quality_score(article),
                "final_score": round(final_score, 2)
            })

        matches.sort(key=lambda x: x["final_score"], reverse=True)

        return matches

    def search_external(self, keywords):
        """
        Placeholder לחיפוש חיצוני - לא ממומש כרגע.
        """
        print("[Science_brain] external search not implemented yet")
        return []

    # ---------- סיכום ----------

    def summarize(self, matches, max_articles=3, max_chars_per_article=300):
        summary_parts = []

        for article in matches[:max_articles]:
            content = article["content"]

            if len(content) > max_chars_per_article:
                content = content[:max_chars_per_article].rsplit(" ", 1)[0] + "..."

            summary_parts.append({
                "article_id": article["article_id"],
                "title": article["title"],
                "field": article.get("field"),
                "subfield": article.get("subfield"),
                "difficulty": article.get("difficulty"),
                "abstract": article.get("abstract"),
                "excerpt": content,
                "key_points": article.get("key_points", [])[:4],
                "source_recommendations": article.get("source_recommendations", [])[:4],
                "trust": article["trust"],
                "quality": article.get("quality"),
                "matched_by_field": article.get("matched_by_field", {})
            })

        return summary_parts

    # ---------- ביטחון ----------

    def calculate_confidence(self, matches):
        if not matches:
            return 0

        top_score = matches[0]["final_score"]

        confidence = min(
            (top_score / MAX_MATCH_SCORE_FOR_FULL_CONFIDENCE) * 100,
            100
        )

        if len(matches) > 1:
            confidence = min(confidence + 10, 100)

        return round(confidence, 2)

    # ---------- עדכון סטטיסטיקה (Learning) ----------

    def update_statistics(self, matches, confidence):
        """
        מעדכן uses לכל מאמר שנעשה בו שימוש בתשובה הזו.
        success_rate/trust כרגע לא משתנים אוטומטית (דורש feedback
        אמיתי מהמשתמש/Fact_Check בעתיד) - רק uses גדל.
        """
        for article in matches[:3]:

            article_id = article["article_id"]
            stats = self._get_article_stats(article_id)

            stats["uses"] = stats.get("uses", 0) + 1
            stats["last_confidence"] = confidence
            stats["last_used_utc"] = datetime.now(timezone.utc).isoformat()

            self.statistics[article_id] = stats

        self._save_statistics()

    # ---------- process ----------

    def process(self, data):
        """
        data = ה-report שמועבר מ-Manager_brain (שמקורו ב-UnderstandingBrain).
        מחזיר report סטרוקטורי בחזרה ל-Manager_brain.
        """
        original_text = data.get("original_text", "")

        # Cache - אם אותה שאלה כבר נענתה
        if original_text in self.cache:
            return self.cache[original_text]

        keywords = self._collect_keywords(data)

        # שלב 1: חיפוש מקומי (כולל דירוג לפי statistics)
        matches = self.search_local_articles(keywords)
        confidence = self.calculate_confidence(matches)
        source = "local"

        # שלב 2: fallback לחיפוש חיצוני אם הביטחון נמוך
        if confidence < LOCAL_CONFIDENCE_THRESHOLD:

            external_matches = self.search_external(keywords)

            if external_matches:
                matches = external_matches + matches
                confidence = self.calculate_confidence(matches)
                source = "external"

        # שלב 3: סיכום
        summary = self.summarize(matches)

        # שלב 4: needs_fact_check - flag בלבד, Fact_Check_brain מופעל ע"י Manager
        needs_fact_check = confidence < MIN_USABLE_CONFIDENCE or len(matches) > 1

        # שלב 5: עדכון סטטיסטיקה (Learning)
        if matches:
            self.update_statistics(matches, confidence)

        result = {
            "topic": data.get("main_topic", "unknown"),
            "keywords_used": list(keywords),
            "source": source,
            "confidence": confidence,
            "summary": summary,
            "articles_found": len(matches),
            "top_article_ids": [
                article["article_id"]
                for article in matches[:5]
            ],
            "needs_fact_check": needs_fact_check
        }

        self.cache[original_text] = result

        return result


brain = ScienceBrain()
