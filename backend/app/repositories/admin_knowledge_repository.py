from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect


ADMIN_KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_knowledge_assets (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  scenic_area TEXT,
  attraction_id TEXT,
  status TEXT NOT NULL,
  chunk_count INTEGER NOT NULL,
  source_filename TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_knowledge_assets_status
  ON admin_knowledge_assets(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS admin_faqs (
  id TEXT PRIMARY KEY,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  scenic_area TEXT,
  attraction_id TEXT,
  tags_json TEXT NOT NULL,
  status TEXT NOT NULL,
  source_gap_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_faqs_status
  ON admin_faqs(status, updated_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dump_tags(tags: list[str] | None) -> str:
    return json.dumps(tags or [], ensure_ascii=False, separators=(",", ":"))


def ensure_admin_knowledge_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ADMIN_KNOWLEDGE_SCHEMA)


def _row_to_asset(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "asset_type": row["asset_type"],
        "scenic_area": row["scenic_area"],
        "attraction_id": row["attraction_id"],
        "status": row["status"],
        "chunk_count": int(row["chunk_count"]),
        "source_filename": row["source_filename"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_faq(row: sqlite3.Row) -> dict[str, Any]:
    try:
        tags = json.loads(row["tags_json"] or "[]")
    except json.JSONDecodeError:
        tags = []
    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "scenic_area": row["scenic_area"],
        "attraction_id": row["attraction_id"],
        "tags": tags if isinstance(tags, list) else [],
        "status": row["status"],
        "source_gap_id": row["source_gap_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def seed_admin_knowledge_if_empty(conn: sqlite3.Connection) -> None:
    ensure_admin_knowledge_schema(conn)
    asset_count = int(conn.execute("SELECT COUNT(*) FROM admin_knowledge_assets").fetchone()[0])
    faq_count = int(conn.execute("SELECT COUNT(*) FROM admin_faqs").fetchone()[0])
    now = _now()
    if asset_count == 0:
        conn.executemany(
            """
            INSERT INTO admin_knowledge_assets (
              id, title, asset_type, scenic_area, attraction_id, status,
              chunk_count, source_filename, note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "adm-asset-seed-lingshan-guide",
                    "灵山胜境导览讲解资料",
                    "guide_script",
                    "灵山胜境",
                    None,
                    "published",
                    0,
                    "processed:knowledge_chunks.json",
                    "本地后台演示资产，真实 RAG chunks 不在此处直接改写。",
                    now,
                    now,
                ),
                (
                    "adm-asset-seed-nianhuawan-faq",
                    "拈花湾常见问答整理",
                    "faq",
                    "拈花湾禅意小镇",
                    None,
                    "draft",
                    0,
                    "admin-seed",
                    "用于演示上传、草稿、发布和索引重建闭环。",
                    now,
                    now,
                ),
            ],
        )
    if faq_count == 0:
        conn.execute(
            """
            INSERT INTO admin_faqs (
              id, question, answer, scenic_area, attraction_id, tags_json,
              status, source_gap_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "adm-faq-seed-lingshan-buddha",
                "灵山大佛适合怎么游览？",
                "建议沿中轴线顺路游览，结合九龙灌浴、祥符禅寺等点位安排；发布前仍需管理员确认来源。",
                "灵山胜境",
                "lingshan-ls-011",
                _dump_tags(["导览", "路线", "讲解"]),
                "draft",
                None,
                now,
                now,
            ),
        )


def list_assets() -> list[dict[str, Any]]:
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        rows = conn.execute(
            "SELECT * FROM admin_knowledge_assets ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
        conn.commit()
    return [_row_to_asset(row) for row in rows]


def get_asset(asset_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        row = conn.execute("SELECT * FROM admin_knowledge_assets WHERE id = ?", (asset_id,)).fetchone()
    return _row_to_asset(row) if row else None


def insert_asset(
    *,
    title: str,
    asset_type: str,
    scenic_area: str | None = None,
    attraction_id: str | None = None,
    status: str = "draft",
    chunk_count: int = 0,
    source_filename: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    row_id = f"adm-asset-{uuid.uuid4().hex[:12]}"
    now = _now()
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        conn.execute(
            """
            INSERT INTO admin_knowledge_assets (
              id, title, asset_type, scenic_area, attraction_id, status,
              chunk_count, source_filename, note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                title,
                asset_type,
                scenic_area,
                attraction_id,
                status,
                chunk_count,
                source_filename,
                note,
                now,
                now,
            ),
        )
        conn.commit()
    asset = get_asset(row_id)
    if asset is None:
        raise RuntimeError(f"Admin knowledge asset {row_id} was inserted but not found.")
    return asset


def update_asset(asset_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_asset(asset_id)
    allowed = {
        "title",
        "asset_type",
        "scenic_area",
        "attraction_id",
        "status",
        "chunk_count",
        "source_filename",
        "note",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if not clean:
        return get_asset(asset_id)
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), asset_id]
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        cursor = conn.execute(f"UPDATE admin_knowledge_assets SET {assignments} WHERE id = ?", tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_asset(asset_id)


def list_faqs() -> list[dict[str, Any]]:
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        rows = conn.execute("SELECT * FROM admin_faqs ORDER BY updated_at DESC, created_at DESC").fetchall()
        conn.commit()
    return [_row_to_faq(row) for row in rows]


def get_faq(faq_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        row = conn.execute("SELECT * FROM admin_faqs WHERE id = ?", (faq_id,)).fetchone()
    return _row_to_faq(row) if row else None


def insert_faq(
    *,
    question: str,
    answer: str,
    scenic_area: str | None = None,
    attraction_id: str | None = None,
    tags: list[str] | None = None,
    status: str = "draft",
    source_gap_id: str | None = None,
) -> dict[str, Any]:
    row_id = f"adm-faq-{uuid.uuid4().hex[:12]}"
    now = _now()
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        conn.execute(
            """
            INSERT INTO admin_faqs (
              id, question, answer, scenic_area, attraction_id, tags_json,
              status, source_gap_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                question,
                answer,
                scenic_area,
                attraction_id,
                _dump_tags(tags),
                status,
                source_gap_id,
                now,
                now,
            ),
        )
        conn.commit()
    faq = get_faq(row_id)
    if faq is None:
        raise RuntimeError(f"Admin FAQ {row_id} was inserted but not found.")
    return faq


def update_faq(faq_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not updates:
        return get_faq(faq_id)
    allowed = {"question", "answer", "scenic_area", "attraction_id", "tags", "status", "source_gap_id"}
    clean = {key: value for key, value in updates.items() if key in allowed}
    if "tags" in clean:
        clean["tags_json"] = _dump_tags(clean.pop("tags") or [])
    if not clean:
        return get_faq(faq_id)
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), faq_id]
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        cursor = conn.execute(f"UPDATE admin_faqs SET {assignments} WHERE id = ?", tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_faq(faq_id)


def publish_admin_knowledge(
    *,
    asset_ids: list[str] | None = None,
    faq_ids: list[str] | None = None,
    publish_all_drafts: bool = False,
) -> dict[str, int]:
    now = _now()
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        asset_count = 0
        faq_count = 0
        if publish_all_drafts or not (asset_ids or faq_ids):
            asset_cursor = conn.execute(
                """
                UPDATE admin_knowledge_assets
                SET status = 'published', updated_at = ?
                WHERE status IN ('draft', 'pending_review')
                """,
                (now,),
            )
            faq_cursor = conn.execute(
                """
                UPDATE admin_faqs
                SET status = 'published', updated_at = ?
                WHERE status IN ('draft', 'pending_review')
                """,
                (now,),
            )
            asset_count = int(asset_cursor.rowcount)
            faq_count = int(faq_cursor.rowcount)
        else:
            for asset_id in asset_ids or []:
                cursor = conn.execute(
                    "UPDATE admin_knowledge_assets SET status = 'published', updated_at = ? WHERE id = ?",
                    (now, asset_id),
                )
                asset_count += int(cursor.rowcount)
            for faq_id in faq_ids or []:
                cursor = conn.execute(
                    "UPDATE admin_faqs SET status = 'published', updated_at = ? WHERE id = ?",
                    (now, faq_id),
                )
                faq_count += int(cursor.rowcount)
        conn.commit()
    return {"published_assets": asset_count, "published_faqs": faq_count}


def count_assets() -> int:
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        count = int(conn.execute("SELECT COUNT(*) FROM admin_knowledge_assets").fetchone()[0])
        conn.commit()
    return count
