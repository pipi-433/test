from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect


ANALYTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS interaction_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  channel TEXT NOT NULL,
  question TEXT,
  answer_preview TEXT,
  attraction_id TEXT,
  route_id TEXT,
  share_code TEXT,
  confidence REAL,
  success INTEGER NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_events_type_created
  ON interaction_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_events_route_id
  ON interaction_events(route_id);

CREATE TABLE IF NOT EXISTS feedback_events (
  id TEXT PRIMARY KEY,
  channel TEXT NOT NULL,
  route_id TEXT,
  attraction_id TEXT,
  rating INTEGER NOT NULL,
  tags_json TEXT NOT NULL,
  comment TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_events_created
  ON feedback_events(created_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dump(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def ensure_analytics_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ANALYTICS_SCHEMA)


def insert_interaction_event(
    *,
    event_type: str,
    channel: str,
    question: str | None = None,
    answer_preview: str | None = None,
    attraction_id: str | None = None,
    route_id: str | None = None,
    share_code: str | None = None,
    confidence: float | None = None,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    created_at = _now()
    with connect() as conn:
        ensure_analytics_schema(conn)
        conn.execute(
            """
            INSERT INTO interaction_events (
              id, event_type, channel, question, answer_preview, attraction_id,
              route_id, share_code, confidence, success, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                channel,
                question,
                answer_preview,
                attraction_id,
                route_id,
                share_code,
                confidence,
                1 if success else 0,
                _dump(metadata),
                created_at,
            ),
        )
        conn.commit()
    return {"id": event_id, "created_at": created_at}


def insert_feedback_event(
    *,
    channel: str,
    rating: int,
    tags: list[str],
    route_id: str | None = None,
    attraction_id: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
    created_at = _now()
    with connect() as conn:
        ensure_analytics_schema(conn)
        conn.execute(
            """
            INSERT INTO feedback_events (
              id, channel, route_id, attraction_id, rating, tags_json, comment, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                channel,
                route_id,
                attraction_id,
                rating,
                json.dumps(tags, ensure_ascii=False, separators=(",", ":")),
                comment,
                created_at,
            ),
        )
        conn.commit()
    return {"id": feedback_id, "created_at": created_at}


def _rows(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        ensure_analytics_schema(conn)
        return conn.execute(query, params).fetchall()


def _one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with connect() as conn:
        ensure_analytics_schema(conn)
        return conn.execute(query, params).fetchone()


def count_events(event_type: str | None = None) -> int:
    if event_type:
        row = _one("SELECT COUNT(*) AS count FROM interaction_events WHERE event_type = ?", (event_type,))
    else:
        row = _one("SELECT COUNT(*) AS count FROM interaction_events")
    return int(row["count"] if row else 0)


def feedback_count() -> int:
    row = _one("SELECT COUNT(*) AS count FROM feedback_events")
    return int(row["count"] if row else 0)


def average_rating() -> float | None:
    row = _one("SELECT AVG(rating) AS average_rating FROM feedback_events")
    value = row["average_rating"] if row else None
    return round(float(value), 2) if value is not None else None


def popular_questions(limit: int = 6) -> list[dict[str, Any]]:
    rows = _rows(
        """
        SELECT question, COUNT(*) AS count
        FROM interaction_events
        WHERE event_type = 'qa' AND question IS NOT NULL AND TRIM(question) != ''
        GROUP BY question
        ORDER BY count DESC, MAX(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [{"question": row["question"], "count": int(row["count"])} for row in rows]


def low_confidence_questions(limit: int = 6) -> list[dict[str, Any]]:
    rows = _rows(
        """
        SELECT question, answer_preview, confidence, created_at
        FROM interaction_events
        WHERE event_type = 'qa'
          AND question IS NOT NULL
          AND (confidence IS NULL OR confidence < 0.55 OR json_extract(metadata_json, '$.fallback') = 1)
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "question": row["question"],
            "answer_preview": row["answer_preview"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def route_theme_distribution() -> list[dict[str, Any]]:
    rows = _rows(
        """
        SELECT json_extract(metadata_json, '$.theme') AS theme,
               json_extract(metadata_json, '$.theme_label') AS theme_label,
               COUNT(*) AS count
        FROM interaction_events
        WHERE event_type = 'route_recommend'
        GROUP BY theme, theme_label
        ORDER BY count DESC, theme
        """
    )
    return [
        {"theme": row["theme"] or "unknown", "theme_label": row["theme_label"] or row["theme"] or "unknown", "count": int(row["count"])}
        for row in rows
    ]


def feedback_tags() -> list[dict[str, Any]]:
    rows = _rows("SELECT tags_json FROM feedback_events")
    counts: dict[str, int] = {}
    for row in rows:
        try:
            tags = json.loads(row["tags_json"])
        except json.JSONDecodeError:
            tags = []
        for tag in tags:
            value = str(tag).strip()
            if value:
                counts[value] = counts.get(value, 0) + 1
    return [{"tag": tag, "count": count} for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def feedback_rating_distribution() -> dict[str, int]:
    rows = _rows("SELECT rating FROM feedback_events")
    distribution = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
    for row in rows:
        rating = int(row["rating"])
        distribution["total"] += 1
        if rating >= 4:
            distribution["positive"] += 1
        elif rating == 3:
            distribution["neutral"] += 1
        else:
            distribution["negative"] += 1
    return distribution


def feedback_rows(limit: int = 12) -> list[dict[str, Any]]:
    rows = _rows(
        """
        SELECT id, channel, route_id, attraction_id, rating, tags_json, comment, created_at
        FROM feedback_events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (max(1, min(limit, 100)),),
    )
    items = []
    for row in rows:
        try:
            tags = json.loads(row["tags_json"])
        except json.JSONDecodeError:
            tags = []
        rating = int(row["rating"])
        if rating >= 4:
            sentiment = "positive"
            status = "已处理"
        elif rating == 3:
            sentiment = "neutral"
            status = "处理中"
        else:
            sentiment = "negative"
            status = "待跟进"
        topic = row["attraction_id"] or row["route_id"] or "游客反馈"
        items.append(
            {
                "id": row["id"],
                "time": row["created_at"],
                "channel": row["channel"],
                "topic": topic,
                "rating": rating,
                "tags": tags,
                "comment": row["comment"] or "游客未填写文字备注。",
                "sentiment": sentiment,
                "status": status,
            }
        )
    return items


def recent_events(limit: int = 12) -> list[dict[str, Any]]:
    rows = _rows(
        """
        SELECT id, event_type, channel, question, answer_preview, attraction_id,
               route_id, share_code, confidence, success, metadata_json, created_at
        FROM interaction_events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    items = []
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"])
        except json.JSONDecodeError:
            metadata = {}
        items.append(
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "channel": row["channel"],
                "question": row["question"],
                "answer_preview": row["answer_preview"],
                "attraction_id": row["attraction_id"],
                "route_id": row["route_id"],
                "share_code": row["share_code"],
                "confidence": row["confidence"],
                "success": bool(row["success"]),
                "metadata": metadata,
                "created_at": row["created_at"],
            }
        )
    return items
