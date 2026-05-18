from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db import connect


ADMIN_SYSTEM_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_system_settings (
  id TEXT PRIMARY KEY,
  scenic_area_name TEXT NOT NULL,
  default_provider_mode TEXT NOT NULL,
  avatar_mode TEXT NOT NULL,
  mock_crowd_enabled INTEGER NOT NULL,
  route_topology_enabled INTEGER NOT NULL,
  data_boundary_notice TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

DEFAULT_SETTINGS_ID = "default"
DEFAULT_SETTINGS = {
    "id": DEFAULT_SETTINGS_ID,
    "scenic_area_name": "灵山胜境",
    "default_provider_mode": "mock",
    "avatar_mode": "mock",
    "mock_crowd_enabled": True,
    "route_topology_enabled": True,
    "data_boundary_notice": "本地演示日志、公开样例与 mock 数据，不代表真实全园运营数据。",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_admin_system_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(ADMIN_SYSTEM_SCHEMA)


def _row_to_settings(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "scenic_area_name": row["scenic_area_name"],
        "default_provider_mode": row["default_provider_mode"],
        "avatar_mode": row["avatar_mode"],
        "mock_crowd_enabled": bool(row["mock_crowd_enabled"]),
        "route_topology_enabled": bool(row["route_topology_enabled"]),
        "data_boundary_notice": row["data_boundary_notice"],
        "updated_at": row["updated_at"],
    }


def seed_system_settings_if_missing(conn: sqlite3.Connection) -> None:
    ensure_admin_system_schema(conn)
    row = conn.execute("SELECT id FROM admin_system_settings WHERE id = ?", (DEFAULT_SETTINGS_ID,)).fetchone()
    if row:
        return
    now = _now()
    conn.execute(
        """
        INSERT INTO admin_system_settings (
          id, scenic_area_name, default_provider_mode, avatar_mode,
          mock_crowd_enabled, route_topology_enabled, data_boundary_notice, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_SETTINGS["id"],
            DEFAULT_SETTINGS["scenic_area_name"],
            DEFAULT_SETTINGS["default_provider_mode"],
            DEFAULT_SETTINGS["avatar_mode"],
            1 if DEFAULT_SETTINGS["mock_crowd_enabled"] else 0,
            1 if DEFAULT_SETTINGS["route_topology_enabled"] else 0,
            DEFAULT_SETTINGS["data_boundary_notice"],
            now,
        ),
    )


def get_system_settings() -> dict[str, Any]:
    with connect() as conn:
        seed_system_settings_if_missing(conn)
        row = conn.execute("SELECT * FROM admin_system_settings WHERE id = ?", (DEFAULT_SETTINGS_ID,)).fetchone()
        conn.commit()
    if row is None:
        return {**DEFAULT_SETTINGS, "updated_at": _now()}
    return _row_to_settings(row)


def update_system_settings(updates: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "scenic_area_name",
        "default_provider_mode",
        "avatar_mode",
        "mock_crowd_enabled",
        "route_topology_enabled",
        "data_boundary_notice",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if not clean:
        return get_system_settings()
    clean["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [*clean.values(), DEFAULT_SETTINGS_ID]
    with connect() as conn:
        seed_system_settings_if_missing(conn)
        conn.execute(f"UPDATE admin_system_settings SET {assignments} WHERE id = ?", tuple(values))
        conn.commit()
    return get_system_settings()
