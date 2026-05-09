"""Validate the Task 03 SQLite database contents."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.repositories.content_repository import (  # noqa: E402
    get_behavior_summary,
    list_attractions,
    list_knowledge_chunks,
    table_counts,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    db_path = get_settings().sqlite_path()
    try:
        require(db_path.exists(), f"Database not found: {db_path}")
        counts = table_counts()
        require(counts["attractions"] == 22, f"Expected 22 attractions, got {counts['attractions']}")
        require(counts["knowledge_chunks"] >= 132, f"Expected at least 132 chunks, got {counts['knowledge_chunks']}")
        require(counts["behavior_summary"] == 1, f"Expected 1 behavior summary, got {counts['behavior_summary']}")
        require(counts["operation_events"] >= 4, f"Expected at least 4 demo operation events, got {counts['operation_events']}")
        require("knowledge_gaps" in counts, "knowledge_gaps table count missing")

        attractions = list_attractions()
        require(len(attractions) == 22, "Attraction repository returned wrong count")
        first_id = attractions[0]["id"]
        chunks = list_knowledge_chunks(first_id)
        require(chunks, f"No chunks found for first attraction {first_id}")
        require(all(chunk["attraction_id"] == first_id for chunk in chunks), "Chunk filter returned mixed attraction ids")

        behavior_summary = get_behavior_summary()
        require(behavior_summary is not None, "Behavior summary missing")
        require(behavior_summary["row_count"] >= 140000, "Behavior row_count is too small")
        require("不能声称" in behavior_summary["caveat"], "Behavior caveat is missing data limitation")
    except (AssertionError, sqlite3.Error) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("VALIDATION OK")
    print(json.dumps({"database": str(db_path), **counts}, ensure_ascii=False, sort_keys=True))
    print(f"Sample attraction: {first_id}, chunks: {len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
