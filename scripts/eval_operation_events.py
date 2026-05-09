"""Evaluate Task 06.12 operation event console and route response rules."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
CASE_PATH = ROOT / "evals" / "operation_events.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "operation_events_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import (  # noqa: E402
    OperationEventCreateRequest,
    OperationEventUpdateRequest,
    RouteRecommendRequest,
    admin_create_operation_event,
    admin_operation_events,
    admin_update_operation_event,
    operation_events,
    routes_recommend,
)


CREATED_BY = "eval-operation-events"


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_window() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return (
        (now - timedelta(minutes=2)).isoformat(timespec="seconds"),
        (now + timedelta(hours=2)).isoformat(timespec="seconds"),
    )


def trace_text(route: dict[str, Any]) -> str:
    return " ".join(str(item) for item in route.get("decision_trace", []))


def stop_by_id(route: dict[str, Any], attraction_id: str) -> dict[str, Any] | None:
    for stop in route.get("stops", []):
        if stop.get("attraction_id") == attraction_id:
            return stop
    return None


def create_event(
    *,
    attraction_id: str,
    event_type: str,
    severity: str,
    message: str,
) -> dict[str, Any]:
    start_at, end_at = now_window()
    return admin_create_operation_event(
        OperationEventCreateRequest(
            attraction_id=attraction_id,
            event_type=event_type,
            severity=severity,
            message=message,
            start_at=start_at,
            end_at=end_at,
            source="manual_admin",
            created_by=CREATED_BY,
            active=True,
        )
    )


def cleanup_old_eval_events() -> None:
    for event in admin_operation_events(active_only=False).get("items", []):
        if event.get("created_by") == CREATED_BY and event.get("active"):
            admin_update_operation_event(event["id"], OperationEventUpdateRequest(active=False))


def result(case_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"id": case_id, "passed": passed, **details}


def check_public_active_events() -> dict[str, Any]:
    payload = operation_events()
    items = payload.get("items", [])
    passed = payload.get("count", 0) > 0 and all(item.get("active") for item in items)
    return result("public_active_events", passed, count=payload.get("count"), event_types=[item.get("event_type") for item in items])


def check_manual_crowd_affects_trace() -> dict[str, Any]:
    event = create_event(
        attraction_id="nianhuawan-nh-005",
        event_type="crowd",
        severity="warning",
        message="eval operation crowd：五灯湖等待约 35 分钟，路线需提示错峰。",
    )
    route = routes_recommend(
        RouteRecommendRequest(theme="nature", time_budget_minutes=240, avoid_crowd=True, crowd_tolerance="low")
    )
    text = trace_text(route)
    stop = stop_by_id(route, "nianhuawan-nh-005")
    passed = bool("manual_admin" in text and stop and stop.get("operation_events"))
    return result(
        "manual_crowd_affects_trace",
        passed,
        event_id=event["id"],
        stop_operation_note=stop.get("operation_note") if stop else None,
        trace=text,
    )


def check_closed_non_must_avoided() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-013",
        event_type="closed",
        severity="critical",
        message="eval operation closed：灵山梵宫临时维护，非必去路线避开。",
    )
    route = routes_recommend(RouteRecommendRequest(theme="photo", time_budget_minutes=300, avoid_crowd=True))
    ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    text = trace_text(route)
    passed = "lingshan-ls-013" not in ids and "manual_admin" in text and "closed" in text
    return result("closed_non_must_avoided", passed, event_id=event["id"], stop_ids=ids, trace=text)


def check_closed_must_kept_warning() -> dict[str, Any]:
    route = routes_recommend(
        RouteRecommendRequest(
            theme="photo",
            time_budget_minutes=300,
            must_visit_attraction_ids=["lingshan-ls-013"],
            avoid_crowd=True,
        )
    )
    stop = stop_by_id(route, "lingshan-ls-013")
    text = trace_text(route)
    passed = bool(
        stop
        and stop.get("constraint_type") == "must_visit"
        and stop.get("operation_note")
        and "必去点" in text
        and "manual_admin" in text
    )
    return result(
        "closed_must_kept_warning",
        passed,
        stop=stop,
        trace=text,
        warning=(route.get("constraint_summary") or {}).get("warning"),
    )


def check_show_event_visible() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-006",
        event_type="show",
        severity="info",
        message="eval operation show：九龙灌浴演出 15 分钟后开始。",
    )
    route = routes_recommend(RouteRecommendRequest(theme="family", time_budget_minutes=240))
    stop = stop_by_id(route, "lingshan-ls-006")
    text = trace_text(route)
    passed = bool(stop and ("演出提醒" in str(stop.get("operation_note")) or "演出提醒" in text))
    return result("show_event_visible", passed, event_id=event["id"], stop_operation_note=stop.get("operation_note") if stop else None)


def check_patch_deactivate_event() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-013",
        event_type="closed",
        severity="critical",
        message="eval operation deactivate：停用后梵宫不应再被该事件影响。",
    )
    admin_update_operation_event(event["id"], OperationEventUpdateRequest(active=False))
    route = routes_recommend(RouteRecommendRequest(theme="photo", time_budget_minutes=300, avoid_crowd=True))
    stop = stop_by_id(route, "lingshan-ls-013")
    event_ids = {item.get("id") for item in (stop or {}).get("operation_events", [])}
    passed = event["id"] not in event_ids
    return result(
        "patch_deactivate_event",
        passed,
        event_id=event["id"],
        stop_found=bool(stop),
        active_event_ids=list(event_ids),
    )


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "public_active_events": check_public_active_events,
    "manual_crowd_affects_trace": check_manual_crowd_affects_trace,
    "closed_non_must_avoided": check_closed_non_must_avoided,
    "closed_must_kept_warning": check_closed_must_kept_warning,
    "show_event_visible": check_show_event_visible,
    "patch_deactivate_event": check_patch_deactivate_event,
}


def main() -> int:
    cleanup_old_eval_events()
    results: list[dict[str, Any]] = []
    for case in load_cases():
        check = CHECKS.get(case["id"])
        if check is None:
            results.append(result(case["id"], False, error="No check registered for case id."))
            continue
        item = check()
        item["description"] = case.get("description")
        results.append(item)

    passed = sum(1 for item in results if item["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "results": results,
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
