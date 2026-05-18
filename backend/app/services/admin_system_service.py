from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db import connect
from app.repositories import admin_system_repository as repo
from app.services.avatar_speaker import get_avatar_status


SOURCE_NOTE = "系统设置为本地演示配置，mock 模式无 API Key 可运行；不代表真实 GPS、真实客流或硬件接入。"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(value: Any, *, fallback: str = "", max_length: int = 240) -> str:
    text = str(value if value is not None else fallback).strip()
    return text[:max_length]


def _clean_bool(value: Any, *, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "开启"}
    return fallback


def _with_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "mode": "mock", "source_note": SOURCE_NOTE}


def get_admin_system_settings() -> dict[str, Any]:
    return _with_meta(repo.get_system_settings())


def update_admin_system_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = repo.get_system_settings()
    updates: dict[str, Any] = {}
    for field, max_length in {
        "scenic_area_name": 80,
        "default_provider_mode": 40,
        "avatar_mode": 40,
        "data_boundary_notice": 240,
    }.items():
        if field in payload:
            updates[field] = _clean_text(payload.get(field), fallback=str(current.get(field) or ""), max_length=max_length)
    if "mock_crowd_enabled" in payload:
        updates["mock_crowd_enabled"] = 1 if _clean_bool(payload.get("mock_crowd_enabled"), fallback=bool(current.get("mock_crowd_enabled"))) else 0
    if "route_topology_enabled" in payload:
        updates["route_topology_enabled"] = 1 if _clean_bool(payload.get("route_topology_enabled"), fallback=bool(current.get("route_topology_enabled"))) else 0
    return _with_meta(repo.update_system_settings(updates))


def _database_status() -> dict[str, Any]:
    settings = get_settings()
    try:
        db_path = settings.sqlite_path()
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
            attractions = conn.execute("SELECT COUNT(*) AS count FROM attractions").fetchone()["count"]
            chunks = conn.execute("SELECT COUNT(*) AS count FROM knowledge_chunks").fetchone()["count"]
        relative_path = str(Path(db_path).resolve().relative_to(Path(__file__).resolve().parents[3]))
        return {
            "status": "ok",
            "database_url": settings.database_url,
            "path": relative_path,
            "attraction_count": int(attractions),
            "knowledge_chunk_count": int(chunks),
        }
    except Exception as exc:  # pragma: no cover - surfaced in healthcheck payload
        return {
            "status": "warning",
            "database_url": settings.database_url,
            "path": "",
            "attraction_count": 0,
            "knowledge_chunk_count": 0,
            "message": str(exc),
        }


def run_admin_system_healthcheck() -> dict[str, Any]:
    settings = get_settings()
    database = _database_status()
    try:
        avatar_status = get_avatar_status()
    except Exception as exc:  # pragma: no cover - sidecar failures should not break admin healthcheck
        avatar_status = {
            "mode": settings.avatar_speaker_mode,
            "sidecar_ready": False,
            "fallback_available": True,
            "fallback_reason": str(exc),
        }
    knowledge_status = "ok" if database.get("attraction_count", 0) > 0 and database.get("knowledge_chunk_count", 0) > 0 else "warning"
    return {
        "backend": {
            "status": "ok",
            "service": settings.service_name,
            "mode": settings.mode,
        },
        "database": database,
        "avatar_mock": {
            "status": "ok",
            "mode": settings.avatar_speaker_mode or "mock",
            "message": "数字人表现层不可用时会降级到 mock accepted，不影响主流程。",
        },
        "sidecar_status": {
            "status": "ready" if avatar_status.get("sidecar_ready") else "mock_fallback",
            "sidecar_ready": bool(avatar_status.get("sidecar_ready")),
            "active_session_id": avatar_status.get("active_session_id"),
            "fallback_available": bool(avatar_status.get("fallback_available", True)),
            "fallback_reason": avatar_status.get("fallback_reason"),
        },
        "knowledge_local": {
            "status": knowledge_status,
            "attraction_count": database.get("attraction_count", 0),
            "knowledge_chunk_count": database.get("knowledge_chunk_count", 0),
            "message": "本地 SQLite 知识库用于演示 RAG 与管理后台，不代表线上发布系统。",
        },
        "settings": get_admin_system_settings(),
        "checked_at": _now(),
        "mode": "mock",
        "source_note": SOURCE_NOTE,
    }
