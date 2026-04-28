from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.content_repository import get_attraction


CROWD_SOURCE = "mock_simulation"
MOCK_UPDATED_AT = datetime(2026, 4, 29, 9, 30, tzinfo=timezone.utc).isoformat(timespec="seconds")

MOCK_CROWD_RECORDS: dict[str, dict[str, Any]] = {
    "lingshan-ls-011": {"crowd_level": "high", "crowd_score": 86, "wait_minutes": 28},
    "lingshan-ls-006": {"crowd_level": "high", "crowd_score": 82, "wait_minutes": 24},
    "lingshan-ls-013": {"crowd_level": "medium", "crowd_score": 58, "wait_minutes": 12},
    "lingshan-ls-010": {"crowd_level": "medium", "crowd_score": 46, "wait_minutes": 8},
    "lingshan-ls-014": {"crowd_level": "low", "crowd_score": 28, "wait_minutes": 3},
    "nianhuawan-nh-002": {"crowd_level": "low", "crowd_score": 24, "wait_minutes": 2},
    "nianhuawan-nh-003": {"crowd_level": "medium", "crowd_score": 54, "wait_minutes": 10},
    "nianhuawan-nh-005": {"crowd_level": "low", "crowd_score": 31, "wait_minutes": 4},
}

LEVEL_LABELS = {
    "low": "舒适",
    "medium": "适中",
    "high": "拥挤",
}

LEVEL_NOTES = {
    "low": "当前模拟拥挤度较低，适合安排停留。",
    "medium": "当前模拟拥挤度适中，建议按计划游览并预留少量等待时间。",
    "high": "当前模拟拥挤度较高，建议错峰、缩短停留或稍后返回。",
}


def _record_for(attraction_id: str) -> dict[str, Any]:
    base = MOCK_CROWD_RECORDS.get(attraction_id, {"crowd_level": "low", "crowd_score": 20, "wait_minutes": 0})
    attraction = get_attraction(attraction_id)
    return {
        "attraction_id": attraction_id,
        "name": attraction.get("name") if attraction else attraction_id,
        "scenic_area": attraction.get("scenic_area") if attraction else None,
        "crowd_level": base["crowd_level"],
        "crowd_score": base["crowd_score"],
        "wait_minutes": base["wait_minutes"],
        "source": CROWD_SOURCE,
        "updated_at": MOCK_UPDATED_AT,
        "note": LEVEL_NOTES[base["crowd_level"]],
    }


def crowd_snapshot_items() -> list[dict[str, Any]]:
    return [_record_for(attraction_id) for attraction_id in sorted(MOCK_CROWD_RECORDS)]


def get_crowd_record(attraction_id: str) -> dict[str, Any]:
    return _record_for(attraction_id)


def get_crowd_snapshot() -> dict[str, Any]:
    items = crowd_snapshot_items()
    return {
        "items": items,
        "count": len(items),
        "source": CROWD_SOURCE,
        "updated_at": MOCK_UPDATED_AT,
        "caveat": "当前为模拟拥挤度/演示数据，不代表真实景区客流。",
    }


def crowd_label(level: str) -> str:
    return LEVEL_LABELS.get(level, level)
