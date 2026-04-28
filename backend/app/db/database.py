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
"""


def connect() -> sqlite3.Connection:
    db_path = get_settings().sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


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

        conn.commit()

    return {
        "attractions": len(attractions),
        "knowledge_chunks": len(chunks),
        "behavior_summaries": 1,
        "interaction_events": 0,
        "feedback_events": 0,
    }
