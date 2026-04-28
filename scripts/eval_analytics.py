"""Evaluate Task 06.7 analytics and feedback loop."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "evals" / "reports" / "analytics_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import (  # noqa: E402
    FeedbackRequest,
    QARequest,
    RouteRecommendRequest,
    analytics,
    feedback as feedback_endpoint,
    qa as qa_endpoint,
    route_share,
    routes_recommend,
)


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def main() -> int:
    before = analytics()
    qa = qa_endpoint(
        QARequest(
            question="灵山大佛适合怎么游览？",
            attraction_id="lingshan-ls-011",
            channel="mobile",
            visitor_profile={"group_type": "family", "time_budget_minutes": 120, "interests": ["佛教文化"]},
        )
    )
    route = routes_recommend(
        RouteRecommendRequest(
            theme="family",
            time_budget_minutes=240,
            group_type="family",
            intensity="easy",
            interests=["亲子轻松", "佛教文化"],
            start_attraction_id="lingshan-ls-011",
            avoid_crowd=True,
            crowd_tolerance="medium",
            channel="kiosk",
        )
    )
    share = route_share(route["id"], route["share"]["share_code"])
    feedback = feedback_endpoint(
        FeedbackRequest(
            channel="share",
            route_id=route["id"],
            rating=5,
            tags=["路线合理", "避开拥挤", "讲解清楚"],
            comment="演示反馈：路线清楚，避峰说明可信。",
        )
    )
    after = analytics()

    recent_types = {item["event_type"] for item in after.get("recent_events", [])}
    checks = [
        {
            "id": "qa-recorded",
            "passed": after["qa_count"] >= before["qa_count"] + 1 or "qa" in recent_types,
            "before": before["qa_count"],
            "after": after["qa_count"],
        },
        {
            "id": "route-recorded",
            "passed": after["route_count"] >= before["route_count"] + 1 or "route_recommend" in recent_types,
            "before": before["route_count"],
            "after": after["route_count"],
        },
        {
            "id": "share-open-recorded",
            "passed": after["share_open_count"] >= before["share_open_count"] + 1 or "route_share_open" in recent_types,
            "before": before["share_open_count"],
            "after": after["share_open_count"],
        },
        {
            "id": "feedback-recorded",
            "passed": after["feedback_count"] >= before["feedback_count"] + 1 and after["average_rating"] is not None and 1 <= after["average_rating"] <= 5,
            "feedback_id": feedback["id"],
            "average_rating": after["average_rating"],
        },
        {
            "id": "overview-fields",
            "passed": all(
                key in after
                for key in [
                    "popular_questions",
                    "route_theme_distribution",
                    "crowd_avoidance_count",
                    "recent_events",
                    "feedback_tags",
                ]
            ),
        },
        {
            "id": "no-session-id",
            "passed": not _contains_key(after, "session_id"),
        },
        {
            "id": "route-share-stable",
            "passed": share["id"] == route["id"] and len(share["stops"]) == len(route["stops"]),
        },
        {
            "id": "qa-response-valid",
            "passed": bool(qa.get("answer")) and "sources" in qa,
        },
    ]

    passed = sum(1 for check in checks if check["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "accuracy": round(passed / len(checks), 4) if checks else 0.0,
        "route_id": route["id"],
        "overview_after": {
            "service_count": after["service_count"],
            "qa_count": after["qa_count"],
            "route_count": after["route_count"],
            "share_open_count": after["share_open_count"],
            "feedback_count": after["feedback_count"],
            "average_rating": after["average_rating"],
            "crowd_avoidance_count": after["crowd_avoidance_count"],
        },
        "results": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "total", "passed", "failed", "accuracy"]}, ensure_ascii=False))
    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
