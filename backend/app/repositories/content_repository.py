import json
import sqlite3
from typing import Any

from app.db import connect


def _payload(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return json.loads(row["payload_json"])


def list_attractions() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM attractions
            ORDER BY scenic_area, attraction_id
            """
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def get_attraction(attraction_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM attractions
            WHERE id = ? OR attraction_id = ?
            """,
            (attraction_id, attraction_id.upper()),
        ).fetchone()
    return _payload(row)


def list_knowledge_chunks(attraction_id: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT payload_json
        FROM knowledge_chunks
    """
    params: tuple[str, ...] = ()
    if attraction_id:
        query += " WHERE attraction_id = ?"
        params = (attraction_id,)
    query += " ORDER BY priority DESC, id LIMIT 500"

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def list_all_knowledge_chunks() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM knowledge_chunks
            ORDER BY priority DESC, id
            """
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def get_behavior_summary() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM behavior_summary
            WHERE id = 'default'
            """
        ).fetchone()
    return _payload(row)


def table_counts() -> dict[str, int]:
    with connect() as conn:
        return {
            "attractions": conn.execute("SELECT COUNT(*) FROM attractions").fetchone()[0],
            "knowledge_chunks": conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0],
            "behavior_summary": conn.execute("SELECT COUNT(*) FROM behavior_summary").fetchone()[0],
        }
