import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS attractions (
  id TEXT PRIMARY KEY,
  attraction_id TEXT NOT NULL UNIQUE,
  scenic_area TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  summary TEXT NOT NULL,
  description TEXT NOT NULL,
  location TEXT,
  parameters TEXT,
  core_function TEXT,
  opening_info TEXT,
  notes TEXT,
  tags_json TEXT NOT NULL,
  culture_points_json TEXT NOT NULL,
  visitor_tips_json TEXT NOT NULL,
  source_file TEXT NOT NULL,
  source_table INTEGER,
  source_row INTEGER,
  metadata_json TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id TEXT PRIMARY KEY,
  source_file TEXT NOT NULL,
  source_section TEXT NOT NULL,
  attraction_id TEXT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  chunk_type TEXT NOT NULL,
  priority INTEGER NOT NULL,
  metadata_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (attraction_id) REFERENCES attractions(id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_attraction_id
  ON knowledge_chunks(attraction_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_priority
  ON knowledge_chunks(priority DESC);

CREATE TABLE IF NOT EXISTS behavior_summary (
  id TEXT PRIMARY KEY,
  source_file TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  caveat TEXT NOT NULL,
  date_start TEXT,
  date_end TEXT,
  payload_json TEXT NOT NULL
);

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
  updated_at TEXT NOT NULL,
  FOREIGN KEY (attraction_id) REFERENCES attractions(id)
);

CREATE INDEX IF NOT EXISTS idx_operation_events_active_time
  ON operation_events(active, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_operation_events_attraction
  ON operation_events(attraction_id);

CREATE TABLE IF NOT EXISTS knowledge_gaps (
  id TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  matched_sources_json TEXT NOT NULL,
  confidence REAL,
  suggested_faq TEXT,
  status TEXT NOT NULL,
  eval_case_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status_created
  ON knowledge_gaps(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_query_status
  ON knowledge_gaps(query, status);
"""

DEMO_OPERATION_EVENTS = [
    {
        "id": "op-demo-crowd-jiulong",
        "attraction_id": "lingshan-ls-006",
        "event_type": "crowd",
        "severity": "warning",
        "message": "九龙灌浴广场演示拥挤，建议预留约 30 分钟等待或错峰进入。",
        "source": "mock_simulation",
        "created_by": "system-seed",
        "active": 1,
    },
    {
        "id": "op-demo-closed-manfeilong",
        "attraction_id": "lingshan-ls-015",
        "event_type": "closed",
        "severity": "critical",
        "message": "曼飞龙塔局部维护演示，非必去路线将自动避开该点。",
        "source": "mock_simulation",
        "created_by": "system-seed",
        "active": 1,
    },
    {
        "id": "op-demo-show-jiulong",
        "attraction_id": "lingshan-ls-006",
        "event_type": "show",
        "severity": "info",
        "message": "九龙灌浴演出即将开始，适合在附近游客提前就位。",
        "source": "mock_simulation",
        "created_by": "system-seed",
        "active": 1,
    },
    {
        "id": "op-demo-recommend-xiangyue",
        "attraction_id": "nianhuawan-nh-003",
        "event_type": "recommendation",
        "severity": "info",
        "message": "香月花街适合作为亲子与休闲游客的演示分流方向。",
        "source": "mock_simulation",
        "created_by": "system-seed",
        "active": 1,
    },
]


def connect() -> sqlite3.Connection:
    db_path = get_settings().sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _seed_operation_events(conn: sqlite3.Connection) -> int:
    now = "2026-05-08T00:00:00+00:00"
    end = "2026-12-31T23:59:59+00:00"
    rows = [
        {
            **event,
            "start_at": now,
            "end_at": end,
            "created_at": now,
            "updated_at": now,
        }
        for event in DEMO_OPERATION_EVENTS
    ]
    conn.executemany(
        """
        INSERT INTO operation_events (
          id, attraction_id, event_type, severity, message, start_at, end_at,
          source, created_by, active, created_at, updated_at
        )
        VALUES (
          :id, :attraction_id, :event_type, :severity, :message, :start_at, :end_at,
          :source, :created_by, :active, :created_at, :updated_at
        )
        ON CONFLICT(id) DO UPDATE SET
          attraction_id = excluded.attraction_id,
          event_type = excluded.event_type,
          severity = excluded.severity,
          message = excluded.message,
          start_at = excluded.start_at,
          end_at = excluded.end_at,
          source = excluded.source,
          created_by = excluded.created_by,
          active = excluded.active,
          updated_at = excluded.updated_at
        """,
        rows,
    )
    return len(rows)


def initialize_database(
    *,
    attractions_path: Path,
    chunks_path: Path,
    behavior_summary_path: Path,
    reset: bool = True,
) -> dict[str, int]:
    attractions = json.loads(attractions_path.read_text(encoding="utf-8"))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    behavior_summary = json.loads(behavior_summary_path.read_text(encoding="utf-8"))

    with connect() as conn:
        if reset:
            conn.executescript(
                """
                DROP TABLE IF EXISTS knowledge_chunks;
                DROP TABLE IF EXISTS behavior_summary;
                DROP TABLE IF EXISTS feedback_events;
                DROP TABLE IF EXISTS interaction_events;
                DROP TABLE IF EXISTS operation_events;
                DROP TABLE IF EXISTS knowledge_gaps;
                DROP TABLE IF EXISTS attractions;
                """
            )
        conn.executescript(SCHEMA)

        conn.executemany(
            """
            INSERT INTO attractions (
              id, attraction_id, scenic_area, name, category, summary,
              description, location, parameters, core_function, opening_info,
              notes, tags_json, culture_points_json, visitor_tips_json,
              source_file, source_table, source_row, metadata_json, payload_json
            )
            VALUES (
              :id, :attraction_id, :scenic_area, :name, :category, :summary,
              :description, :location, :parameters, :core_function, :opening_info,
              :notes, :tags_json, :culture_points_json, :visitor_tips_json,
              :source_file, :source_table, :source_row, :metadata_json, :payload_json
            )
            """,
            [
                {
                    **item,
                    "tags_json": _dump(item.get("tags", [])),
                    "culture_points_json": _dump(item.get("culture_points", [])),
                    "visitor_tips_json": _dump(item.get("visitor_tips", [])),
                    "metadata_json": _dump(item.get("metadata", {})),
                    "payload_json": _dump(item),
                }
                for item in attractions
            ],
        )

        conn.executemany(
            """
            INSERT INTO knowledge_chunks (
              id, source_file, source_section, attraction_id, title, content,
              tags_json, chunk_type, priority, metadata_json, payload_json
            )
            VALUES (
              :id, :source_file, :source_section, :attraction_id, :title, :content,
              :tags_json, :chunk_type, :priority, :metadata_json, :payload_json
            )
            """,
            [
                {
                    **item,
                    "tags_json": _dump(item.get("tags", [])),
                    "metadata_json": _dump(item.get("metadata", {})),
                    "payload_json": _dump(item),
                }
                for item in chunks
            ],
        )

        date_range = behavior_summary.get("date_range", {})
        conn.execute(
            """
            INSERT INTO behavior_summary (
              id, source_file, row_count, caveat, date_start, date_end, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "default",
                behavior_summary["source_file"],
                behavior_summary["row_count"],
                behavior_summary["caveat"],
                date_range.get("start"),
                date_range.get("end"),
                _dump(behavior_summary),
            ),
        )

        operation_events_count = _seed_operation_events(conn)

        conn.commit()

    return {
        "attractions": len(attractions),
        "knowledge_chunks": len(chunks),
        "behavior_summaries": 1,
        "interaction_events": 0,
        "feedback_events": 0,
        "operation_events": operation_events_count,
        "knowledge_gaps": 0,
    }
