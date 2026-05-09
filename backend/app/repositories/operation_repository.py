from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect


OPERATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS operation_events (
  id TEXT PRIMARY KEY,
  attraction_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  source TEXT NOT NULL,
  created_by TEXT NOT NULL,
  active INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_events_active_time
  ON operation_events(active, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_operation_events_attraction
  ON operation_events(attraction_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_operation_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(OPERATION_SCHEMA)


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "attraction_id": row["attraction_id"],
        "event_type": row["event_type"],
        "severity": row["severity"],
        "message": row["message"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "source": row["source"],
        "created_by": row["created_by"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_operation_events(
    *,
    active_only: bool = False,
    attraction_id: str | None = None,
    now: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM operation_events
        WHERE 1 = 1
    """
    params: list[Any] = []
    if attraction_id:
        query += " AND attraction_id = ?"
        params.append(attraction_id)
    if active_only:
        current = now or _now()
        query += " AND active = 1 AND start_at <= ? AND end_at >= ?"
        params.extend([current, current])
    query += " ORDER BY active DESC, severity DESC, start_at DESC, created_at DESC"

    with connect() as conn:
        ensure_operation_schema(conn)
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_row_to_event(row) for row in rows]


def get_operation_event(event_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_operation_schema(conn)
        row = conn.execute("SELECT * FROM operation_events WHERE id = ?", (event_id,)).fetchone()
    return _row_to_event(row) if row else None


def insert_operation_event(
    *,
    attraction_id: str,
    event_type: str,
    severity: str,
    message: str,
    start_at: str,
    end_at: str,
    source: str,
    created_by: str,
    active: bool = True,
) -> dict[str, Any]:
    event_id = f"op-{uuid.uuid4().hex[:12]}"
    created_at = _now()
    with connect() as conn:
        ensure_operation_schema(conn)
        conn.execute(
            """
            INSERT INTO operation_events (
              id, attraction_id, event_type, severity, message, start_at, end_at,
              source, created_by, active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                attraction_id,
                event_type,
                severity,
                message,
                start_at,
                end_at,
                source,
                created_by,
                1 if active else 0,
                created_at,
                created_at,
            ),
        )
        conn.commit()
    event = get_operation_event(event_id)
    if event is None:
        raise RuntimeError(f"Operation event {event_id} was inserted but not found.")
    return event


def update_operation_event(event_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_operation_event(event_id)
    allowed = {
        "attraction_id",
        "event_type",
        "severity",
        "message",
        "start_at",
        "end_at",
        "source",
        "created_by",
        "active",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if "active" in clean:
        clean["active"] = 1 if clean["active"] else 0
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), event_id]
    with connect() as conn:
        ensure_operation_schema(conn)
        cursor = conn.execute(
            f"UPDATE operation_events SET {assignments} WHERE id = ?",
            tuple(values),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_operation_event(event_id)
