"""Validate Task 02 processed JSON artifacts."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"

ATTRACTION_FIELDS = {
    "id",
    "attraction_id",
    "scenic_area",
    "name",
    "category",
    "summary",
    "description",
    "culture_points",
    "visitor_tips",
    "tags",
    "source_file",
}

CHUNK_FIELDS = {
    "id",
    "source_file",
    "source_section",
    "attraction_id",
    "title",
    "content",
    "tags",
    "chunk_type",
    "priority",
    "metadata",
}


def load_json(name: str) -> Any:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise AssertionError(f"Missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path} is not valid JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_attractions(attractions: list[dict[str, Any]]) -> set[str]:
    require(isinstance(attractions, list), "attractions.json must be a list")
    require(len(attractions) == 22, f"Expected 22 attractions, got {len(attractions)}")
    ids = [item.get("id") for item in attractions]
    require(len(set(ids)) == len(ids), "Attraction ids must be unique")
    scenic_counts = Counter(item.get("scenic_area") for item in attractions)
    require(scenic_counts["灵山胜境"] == 16, f"Expected 16 灵山胜境 attractions, got {scenic_counts['灵山胜境']}")
    require(scenic_counts["拈花湾禅意小镇"] == 6, f"Expected 6 拈花湾 attractions, got {scenic_counts['拈花湾禅意小镇']}")

    for item in attractions:
        missing = ATTRACTION_FIELDS - item.keys()
        require(not missing, f"Attraction {item.get('id')} missing fields: {sorted(missing)}")
        require(item["source_file"].endswith(".docx"), f"Attraction {item['id']} has invalid source_file")
        require(item["tags"], f"Attraction {item['id']} must have tags")
        require(item["summary"], f"Attraction {item['id']} must have summary")
    return set(ids)


def validate_chunks(chunks: list[dict[str, Any]], attraction_ids: set[str]) -> None:
    require(isinstance(chunks, list), "knowledge_chunks.json must be a list")
    require(len(chunks) >= 90, f"Expected at least 90 knowledge chunks, got {len(chunks)}")
    ids = [item.get("id") for item in chunks]
    require(len(set(ids)) == len(ids), "Knowledge chunk ids must be unique")

    linked = 0
    source_files = set()
    for item in chunks:
        missing = CHUNK_FIELDS - item.keys()
        require(not missing, f"Chunk {item.get('id')} missing fields: {sorted(missing)}")
        require(item["source_file"].endswith(".docx"), f"Chunk {item['id']} has invalid source_file")
        require(item["source_section"], f"Chunk {item['id']} missing source_section")
        require(len(item["content"]) >= 20, f"Chunk {item['id']} content too short")
        require(isinstance(item["tags"], list), f"Chunk {item['id']} tags must be a list")
        require(isinstance(item["metadata"], dict), f"Chunk {item['id']} metadata must be an object")
        if item["attraction_id"] is not None:
            require(item["attraction_id"] in attraction_ids, f"Chunk {item['id']} references unknown attraction_id {item['attraction_id']}")
            linked += 1
        source_files.add(item["source_file"])
    require(linked >= 66, f"Expected at least 66 attraction-linked chunks, got {linked}")
    require(len(source_files) == 2, f"Expected chunks from 2 docx files, got {sorted(source_files)}")


def validate_behavior(summary: dict[str, Any]) -> None:
    require(isinstance(summary, dict), "behavior_summary.json must be an object")
    for field in ["source_file", "source_sha256", "caveat", "row_count", "fields", "date_range", "distributions", "averages"]:
        require(field in summary, f"behavior_summary missing {field}")
    require(summary["source_file"].endswith(".xlsx"), "behavior source_file must be xlsx")
    require("样例" in summary["caveat"] and "不能声称" in summary["caveat"], "behavior caveat must clarify sample-data limitation")
    require(summary["row_count"] >= 140000, f"Expected at least 140000 behavior rows, got {summary['row_count']}")
    require(summary["date_range"]["start"] <= summary["date_range"]["end"], "Invalid behavior date range")
    for key in ["attraction_type", "satisfaction", "gender", "age_group"]:
        require(key in summary["distributions"], f"Missing distribution {key}")
        require(summary["distributions"][key], f"Distribution {key} must not be empty")


def main() -> int:
    try:
        attractions = load_json("attractions.json")
        chunks = load_json("knowledge_chunks.json")
        behavior = load_json("behavior_summary.json")
        attraction_ids = validate_attractions(attractions)
        validate_chunks(chunks, attraction_ids)
        validate_behavior(behavior)
    except AssertionError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    scenic_counts = Counter(item["scenic_area"] for item in attractions)
    linked_chunks = sum(1 for item in chunks if item["attraction_id"])
    print("VALIDATION OK")
    print(f"Attractions: {len(attractions)} ({dict(scenic_counts)})")
    print(f"Knowledge chunks: {len(chunks)} ({linked_chunks} linked to attractions)")
    print(f"Behavior rows: {behavior['row_count']} ({behavior['date_range']['start']} to {behavior['date_range']['end']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
