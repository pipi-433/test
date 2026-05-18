from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect


ADMIN_AVATAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_avatar_profile (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  outfit_style TEXT NOT NULL,
  voice_name TEXT NOT NULL,
  speech_rate REAL NOT NULL,
  volume REAL NOT NULL,
  default_emotion TEXT NOT NULL,
  background_style TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_avatar_clip_jobs (
  id TEXT PRIMARY KEY,
  clip_id TEXT,
  title TEXT NOT NULL,
  attraction_id TEXT,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_avatar_clip_jobs_created
  ON admin_avatar_clip_jobs(created_at DESC);
"""


DEFAULT_PROFILE_ID = "default"
DEFAULT_PROFILE = {
    "id": DEFAULT_PROFILE_ID,
    "name": "小灵",
    "outfit_style": "宋韵青绿",
    "voice_name": "温柔女声",
    "speech_rate": 1.0,
    "volume": 0.9,
    "default_emotion": "happy",
    "background_style": "灵山山水",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_admin_avatar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ADMIN_AVATAR_SCHEMA)


def _row_to_profile(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "outfit_style": row["outfit_style"],
        "voice_name": row["voice_name"],
        "speech_rate": float(row["speech_rate"]),
        "volume": float(row["volume"]),
        "default_emotion": row["default_emotion"],
        "background_style": row["background_style"],
        "updated_at": row["updated_at"],
    }


def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "clip_id": row["clip_id"],
        "title": row["title"],
        "attraction_id": row["attraction_id"],
        "status": row["status"],
        "message": row["message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def seed_avatar_profile_if_missing(conn: sqlite3.Connection) -> None:
    ensure_admin_avatar_schema(conn)
    row = conn.execute("SELECT id FROM admin_avatar_profile WHERE id = ?", (DEFAULT_PROFILE_ID,)).fetchone()
    if row:
        return
    now = _now()
    conn.execute(
        """
        INSERT INTO admin_avatar_profile (
          id, name, outfit_style, voice_name, speech_rate, volume,
          default_emotion, background_style, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_PROFILE["id"],
            DEFAULT_PROFILE["name"],
            DEFAULT_PROFILE["outfit_style"],
            DEFAULT_PROFILE["voice_name"],
            DEFAULT_PROFILE["speech_rate"],
            DEFAULT_PROFILE["volume"],
            DEFAULT_PROFILE["default_emotion"],
            DEFAULT_PROFILE["background_style"],
            now,
        ),
    )


def get_avatar_profile() -> dict[str, Any]:
    with connect() as conn:
        seed_avatar_profile_if_missing(conn)
        row = conn.execute("SELECT * FROM admin_avatar_profile WHERE id = ?", (DEFAULT_PROFILE_ID,)).fetchone()
        conn.commit()
    if row is None:
        return {**DEFAULT_PROFILE, "updated_at": _now()}
    return _row_to_profile(row)


def update_avatar_profile(updates: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name",
        "outfit_style",
        "voice_name",
        "speech_rate",
        "volume",
        "default_emotion",
        "background_style",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if not clean:
        return get_avatar_profile()
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), DEFAULT_PROFILE_ID]
    with connect() as conn:
        seed_avatar_profile_if_missing(conn)
        conn.execute(f"UPDATE admin_avatar_profile SET {assignments} WHERE id = ?", tuple(values))
        conn.commit()
    return get_avatar_profile()


def insert_clip_job(
    *,
    title: str,
    clip_id: str | None = None,
    attraction_id: str | None = None,
    status: str = "mock_created",
    message: str,
) -> dict[str, Any]:
    row_id = f"avatar-job-{uuid.uuid4().hex[:12]}"
    now = _now()
    with connect() as conn:
        ensure_admin_avatar_schema(conn)
        conn.execute(
            """
            INSERT INTO admin_avatar_clip_jobs (
              id, clip_id, title, attraction_id, status, message, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, clip_id, title, attraction_id, status, message, now, now),
        )
        conn.commit()
    job = get_clip_job(row_id)
    if job is None:
        raise RuntimeError(f"Avatar clip job {row_id} was inserted but not found.")
    return job


def get_clip_job(job_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_admin_avatar_schema(conn)
        row = conn.execute("SELECT * FROM admin_avatar_clip_jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def list_clip_jobs(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        ensure_admin_avatar_schema(conn)
        rows = conn.execute(
            "SELECT * FROM admin_avatar_clip_jobs ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    return [_row_to_job(row) for row in rows]
