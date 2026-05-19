from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect


KNOWLEDGE_GAP_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_gaps (
  id TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  matched_sources_json TEXT NOT NULL,
  confidence REAL,
  suggested_faq TEXT,
  status TEXT NOT NULL,
  eval_case_id TEXT,
  linked_faq_id TEXT,
  resolved_at TEXT,
  resolution_note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status_created
  ON knowledge_gaps(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_query_status
  ON knowledge_gaps(query, status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def ensure_knowledge_gap_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(KNOWLEDGE_GAP_SCHEMA)
    _ensure_column(conn, "knowledge_gaps", "linked_faq_id", "TEXT")
    _ensure_column(conn, "knowledge_gaps", "resolved_at", "TEXT")
    _ensure_column(conn, "knowledge_gaps", "resolution_note", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _row_to_gap(row: sqlite3.Row) -> dict[str, Any]:
    try:
        matched_sources = json.loads(row["matched_sources_json"] or "[]")
    except json.JSONDecodeError:
        matched_sources = []
    return {
        "id": row["id"],
        "query": row["query"],
        "trigger_type": row["trigger_type"],
        "matched_sources": matched_sources,
        "confidence": row["confidence"],
        "suggested_faq": row["suggested_faq"],
        "status": row["status"],
        "eval_case_id": row["eval_case_id"],
        "linked_faq_id": row["linked_faq_id"] if "linked_faq_id" in row.keys() else None,
        "linked_faq_status": None,
        "resolved_at": row["resolved_at"] if "resolved_at" in row.keys() else None,
        "resolution_note": row["resolution_note"] if "resolution_note" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _attach_linked_faq(conn: sqlite3.Connection, gap: dict[str, Any]) -> dict[str, Any]:
    row = None
    linked_faq_id = gap.get("linked_faq_id")
    try:
        if linked_faq_id:
            row = conn.execute("SELECT id, status FROM admin_faqs WHERE id = ?", (linked_faq_id,)).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT id, status
                FROM admin_faqs
                WHERE source_gap_id = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                (gap["id"],),
            ).fetchone()
    except sqlite3.OperationalError:
        row = None
    if row is not None:
        gap["linked_faq_id"] = row["id"]
        gap["linked_faq_status"] = row["status"]
    return gap


def list_knowledge_gaps(*, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    query = "SELECT * FROM knowledge_gaps"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        rows = conn.execute(query, tuple(params)).fetchall()
        gaps = [_attach_linked_faq(conn, _row_to_gap(row)) for row in rows]
    return gaps


def get_knowledge_gap(gap_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        row = conn.execute("SELECT * FROM knowledge_gaps WHERE id = ?", (gap_id,)).fetchone()
        return _attach_linked_faq(conn, _row_to_gap(row)) if row else None


def find_existing_gap(query: str, *, statuses: tuple[str, ...] = ("open", "drafted")) -> dict[str, Any] | None:
    clean_query = query.strip()
    if not clean_query:
        return None
    placeholders = ", ".join("?" for _ in statuses)
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        row = conn.execute(
            f"""
            SELECT *
            FROM knowledge_gaps
            WHERE query = ? AND status IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (clean_query, *statuses),
        ).fetchone()
        return _attach_linked_faq(conn, _row_to_gap(row)) if row else None


def insert_knowledge_gap(
    *,
    query: str,
    trigger_type: str,
    matched_sources: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
    suggested_faq: str | None = None,
    status: str = "open",
    eval_case_id: str | None = None,
    gap_id: str | None = None,
) -> dict[str, Any]:
    created_at = _now()
    row_id = gap_id or f"kgap-{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO knowledge_gaps (
              id, query, trigger_type, matched_sources_json, confidence,
              suggested_faq, status, eval_case_id, linked_faq_id,
              resolved_at, resolution_note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                query.strip(),
                trigger_type,
                _dump(matched_sources or []),
                confidence,
                suggested_faq,
                status,
                eval_case_id,
                None,
                None,
                None,
                created_at,
                created_at,
            ),
        )
        conn.commit()
    gap = get_knowledge_gap(row_id)
    if gap is None:
        raise RuntimeError(f"Knowledge gap {row_id} was inserted but not found.")
    return gap


def update_knowledge_gap(gap_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_knowledge_gap(gap_id)
    allowed = {
        "query",
        "trigger_type",
        "matched_sources",
        "confidence",
        "suggested_faq",
        "status",
        "eval_case_id",
        "linked_faq_id",
        "resolved_at",
        "resolution_note",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if "matched_sources" in clean:
        clean["matched_sources_json"] = _dump(clean.pop("matched_sources") or [])
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), gap_id]
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        cursor = conn.execute(
            f"UPDATE knowledge_gaps SET {assignments} WHERE id = ?",
            tuple(values),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_knowledge_gap(gap_id)


def count_knowledge_gaps(status: str | None = None) -> int:
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        if status:
            return int(conn.execute("SELECT COUNT(*) FROM knowledge_gaps WHERE status = ?", (status,)).fetchone()[0])
        return int(conn.execute("SELECT COUNT(*) FROM knowledge_gaps").fetchone()[0])


def delete_eval_gaps(*, query_prefix: str) -> int:
    with connect() as conn:
        ensure_knowledge_gap_schema(conn)
        cursor = conn.execute("DELETE FROM knowledge_gaps WHERE query LIKE ?", (f"{query_prefix}%",))
        conn.commit()
        return int(cursor.rowcount)
