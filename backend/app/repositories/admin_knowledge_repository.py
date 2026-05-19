from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import connect
from app.repositories.knowledge_gap_repository import ensure_knowledge_gap_schema


ADMIN_KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_knowledge_assets (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  scenic_area TEXT,
  attraction_id TEXT,
  status TEXT NOT NULL,
  chunk_count INTEGER NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  source_filename TEXT,
  note TEXT,
  published_chunk_ids_json TEXT NOT NULL DEFAULT '[]',
  published_at TEXT,
  last_publish_message TEXT,
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


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def ensure_admin_knowledge_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ADMIN_KNOWLEDGE_SCHEMA)
    _ensure_column(conn, "admin_knowledge_assets", "content", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "admin_knowledge_assets", "published_chunk_ids_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "admin_knowledge_assets", "published_at", "TEXT")
    _ensure_column(conn, "admin_knowledge_assets", "last_publish_message", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _row_to_asset(row: sqlite3.Row) -> dict[str, Any]:
    try:
        published_chunk_ids = json.loads(row["published_chunk_ids_json"] or "[]")
    except (IndexError, json.JSONDecodeError):
        published_chunk_ids = []
    return {
        "id": row["id"],
        "title": row["title"],
        "asset_type": row["asset_type"],
        "scenic_area": row["scenic_area"],
        "attraction_id": row["attraction_id"],
        "status": row["status"],
        "chunk_count": int(row["chunk_count"]),
        "content": row["content"] if "content" in row.keys() else "",
        "source_filename": row["source_filename"],
        "note": row["note"],
        "published_chunk_ids": published_chunk_ids if isinstance(published_chunk_ids, list) else [],
        "published_at": row["published_at"] if "published_at" in row.keys() else None,
        "last_publish_message": row["last_publish_message"] if "last_publish_message" in row.keys() else None,
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
              chunk_count, content, source_filename, note,
              published_chunk_ids_json, published_at, last_publish_message,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    "",
                    "processed:knowledge_chunks.json",
                    "本地后台演示资产，真实 RAG chunks 不在此处直接改写。",
                    _dump_json([]),
                    None,
                    None,
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
                    "",
                    "admin-seed",
                    "用于演示上传、草稿、发布和索引重建闭环。",
                    _dump_json([]),
                    None,
                    None,
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
    content: str = "",
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
              chunk_count, content, source_filename, note,
              published_chunk_ids_json, published_at, last_publish_message,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                title,
                asset_type,
                scenic_area,
                attraction_id,
                status,
                chunk_count,
                content,
                source_filename,
                note,
                _dump_json([]),
                None,
                None,
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
        "content",
        "source_filename",
        "note",
        "published_chunk_ids_json",
        "published_at",
        "last_publish_message",
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


def get_faq_by_source_gap_id(gap_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        ensure_admin_knowledge_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM admin_faqs
            WHERE source_gap_id = ?
            ORDER BY
              CASE status WHEN 'published' THEN 0 WHEN 'pending_review' THEN 1 WHEN 'draft' THEN 2 ELSE 3 END,
              updated_at DESC,
              created_at DESC
            LIMIT 1
            """,
            (gap_id,),
        ).fetchone()
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


def _clean_chunk_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _chunk_content(text: str, *, target_size: int = 420) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=[。！？；])", clean) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > target_size:
            if current:
                chunks.append(_clean_chunk_text(current))
                current = ""
            for index in range(0, len(paragraph), target_size):
                part = paragraph[index : index + target_size].strip()
                if part:
                    chunks.append(_clean_chunk_text(part))
            continue
        if current and len(current) + len(paragraph) > target_size:
            chunks.append(_clean_chunk_text(current))
            current = paragraph
        else:
            current = f"{current}{paragraph}" if current else paragraph
    if current:
        chunks.append(_clean_chunk_text(current))
    return [chunk for chunk in chunks if chunk]


def _normalize_attraction_id(conn: sqlite3.Connection, attraction_id: str | None) -> str | None:
    if not attraction_id:
        return None
    row = conn.execute(
        "SELECT id FROM attractions WHERE id = ? OR attraction_id = ?",
        (attraction_id, attraction_id.upper()),
    ).fetchone()
    return str(row["id"]) if row else None


def _insert_knowledge_chunk(
    conn: sqlite3.Connection,
    *,
    chunk_id: str,
    source_file: str,
    source_section: str,
    attraction_id: str | None,
    title: str,
    content: str,
    tags: list[str],
    chunk_type: str,
    priority: int,
    metadata: dict[str, Any],
) -> None:
    payload = {
        "id": chunk_id,
        "source_file": source_file,
        "source_section": source_section,
        "attraction_id": attraction_id,
        "title": title,
        "content": content,
        "tags": tags,
        "chunk_type": chunk_type,
        "priority": priority,
        "metadata": metadata,
    }
    conn.execute(
        """
        INSERT INTO knowledge_chunks (
          id, source_file, source_section, attraction_id, title, content,
          tags_json, chunk_type, priority, metadata_json, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chunk_id,
            source_file,
            source_section,
            attraction_id,
            title,
            content,
            _dump_json(tags),
            chunk_type,
            priority,
            _dump_json(metadata),
            _dump_json(payload),
        ),
    )


def _publish_asset(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    asset = _row_to_asset(row)
    asset_id = str(asset["id"])
    prefix = f"admin-asset-{asset_id}"
    conn.execute("DELETE FROM knowledge_chunks WHERE id LIKE ?", (f"{prefix}-%",))
    chunks = _chunk_content(str(asset.get("content") or ""))
    attraction_id = _normalize_attraction_id(conn, asset.get("attraction_id"))
    if asset.get("attraction_id") and not attraction_id:
        message = "发布失败：资产关联的景点 id 不存在，未写入 RAG。"
        conn.execute(
            """
            UPDATE admin_knowledge_assets
            SET last_publish_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (message, _now(), asset_id),
        )
        return {"id": asset_id, "chunk_ids": [], "message": message, "published": False}

    chunk_ids: list[str] = []
    source_file = f"admin:{asset.get('source_filename') or asset.get('title')}"
    tags = [
        "后台新增知识",
        str(asset.get("asset_type") or "other"),
        *( [str(asset["scenic_area"])] if asset.get("scenic_area") else [] ),
    ]
    for index, chunk_text in enumerate(chunks, start=1):
        chunk_id = f"{prefix}-{index:03d}"
        chunk_ids.append(chunk_id)
        _insert_knowledge_chunk(
            conn,
            chunk_id=chunk_id,
            source_file=source_file,
            source_section=f"后台知识资产/{asset.get('title')}/第 {index} 段",
            attraction_id=attraction_id,
            title=str(asset.get("title") or "后台新增知识"),
            content=chunk_text,
            tags=tags,
            chunk_type="admin_asset",
            priority=92,
            metadata={
                "admin_source": "asset",
                "asset_id": asset_id,
                "source_filename": asset.get("source_filename"),
                "scenic_area": asset.get("scenic_area"),
                "published_by": "admin_knowledge_publish",
            },
        )

    now = _now()
    if chunk_ids:
        message = f"已发布 {len(chunk_ids)} 个本地 RAG chunk。"
        status = "published"
    else:
        message = "该资产没有可发布正文，未写入 RAG chunk。"
        status = asset.get("status") or "draft"
    conn.execute(
        """
        UPDATE admin_knowledge_assets
        SET status = ?, chunk_count = ?, published_chunk_ids_json = ?,
            published_at = ?, last_publish_message = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, len(chunk_ids), _dump_json(chunk_ids), now if chunk_ids else asset.get("published_at"), message, now, asset_id),
    )
    return {"id": asset_id, "chunk_ids": chunk_ids, "message": message, "published": bool(chunk_ids)}


def _publish_faq(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    faq = _row_to_faq(row)
    faq_id = str(faq["id"])
    source_gap_id = str(faq.get("source_gap_id") or "") or None
    chunk_id = f"admin-faq-{faq_id}-001"
    conn.execute("DELETE FROM knowledge_chunks WHERE id = ?", (chunk_id,))
    attraction_id = _normalize_attraction_id(conn, faq.get("attraction_id"))
    if faq.get("attraction_id") and not attraction_id:
        return {
            "id": faq_id,
            "chunk_ids": [],
            "message": "FAQ 关联的景点 id 不存在，未写入 RAG。",
            "published": False,
        }
    content = _clean_chunk_text(f"问题：{faq.get('question')}\n回答：{faq.get('answer')}")
    if not content:
        return {"id": faq_id, "chunk_ids": [], "message": "FAQ 内容为空。", "published": False}
    tags = ["后台FAQ", *[str(tag) for tag in faq.get("tags", [])], *( [str(faq["scenic_area"])] if faq.get("scenic_area") else [] )]
    _insert_knowledge_chunk(
        conn,
        chunk_id=chunk_id,
        source_file=f"admin:faq:{faq_id}",
        source_section=f"后台 FAQ/{faq.get('question')}",
        attraction_id=attraction_id,
        title=str(faq.get("question") or "后台 FAQ"),
        content=content,
        tags=tags,
        chunk_type="admin_faq",
        priority=94,
        metadata={
            "admin_source": "faq",
            "source_type": "admin_faq",
            "faq_id": faq_id,
            "source_gap_id": source_gap_id,
            "scenic_area": faq.get("scenic_area"),
            "published_by": "admin_knowledge_publish",
        },
    )
    now = _now()
    conn.execute("UPDATE admin_faqs SET status = 'published', updated_at = ? WHERE id = ?", (now, faq_id))
    gap_status_after_publish = None
    if source_gap_id:
        ensure_knowledge_gap_schema(conn)
        resolution_note = "FAQ 已发布到本地知识库，知识缺口已自动标记为 resolved。"
        cursor = conn.execute(
            """
            UPDATE knowledge_gaps
            SET status = 'resolved',
                linked_faq_id = ?,
                resolved_at = ?,
                resolution_note = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (faq_id, now, resolution_note, now, source_gap_id),
        )
        if cursor.rowcount:
            gap_status_after_publish = "resolved"
    return {
        "id": faq_id,
        "faq_id": faq_id,
        "source_gap_id": source_gap_id,
        "published_chunks": 1,
        "gap_status_after_publish": gap_status_after_publish,
        "chunk_ids": [chunk_id],
        "message": "FAQ 已发布为 1 个本地 RAG chunk。",
        "published": True,
    }
    return {"id": faq_id, "chunk_ids": [chunk_id], "message": "FAQ 已发布为 1 个本地 RAG chunk。", "published": True}


def publish_admin_knowledge(
    *,
    asset_ids: list[str] | None = None,
    faq_ids: list[str] | None = None,
    publish_all_drafts: bool = False,
) -> dict[str, Any]:
    asset_results: list[dict[str, Any]] = []
    faq_results: list[dict[str, Any]] = []
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        if publish_all_drafts or not (asset_ids or faq_ids):
            asset_rows = conn.execute(
                """
                SELECT *
                FROM admin_knowledge_assets
                WHERE status IN ('draft', 'pending_review')
                   AND TRIM(COALESCE(content, '')) <> ''
                ORDER BY updated_at DESC, created_at DESC
                """,
            ).fetchall()
            faq_rows = conn.execute(
                """
                SELECT *
                FROM admin_faqs
                WHERE status IN ('draft', 'pending_review')
                ORDER BY updated_at DESC, created_at DESC
                """,
            ).fetchall()
        else:
            asset_rows = []
            for asset_id in asset_ids or []:
                row = conn.execute("SELECT * FROM admin_knowledge_assets WHERE id = ?", (asset_id,)).fetchone()
                if row:
                    asset_rows.append(row)
            faq_rows = []
            for faq_id in faq_ids or []:
                row = conn.execute("SELECT * FROM admin_faqs WHERE id = ?", (faq_id,)).fetchone()
                if row:
                    faq_rows.append(row)
        for row in asset_rows:
            asset_results.append(_publish_asset(conn, row))
        for row in faq_rows:
            faq_results.append(_publish_faq(conn, row))
        conn.commit()
    published_assets = sum(1 for item in asset_results if item.get("published"))
    published_faqs = sum(1 for item in faq_results if item.get("published"))
    published_chunks = sum(len(item.get("chunk_ids") or []) for item in [*asset_results, *faq_results])
    return {
        "published_assets": published_assets,
        "published_faqs": published_faqs,
        "published_chunks": published_chunks,
        "asset_results": asset_results,
        "faq_results": faq_results,
    }


def count_assets() -> int:
    with connect() as conn:
        seed_admin_knowledge_if_empty(conn)
        count = int(conn.execute("SELECT COUNT(*) FROM admin_knowledge_assets").fetchone()[0])
        conn.commit()
    return count
