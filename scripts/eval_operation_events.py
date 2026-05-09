"""Evaluate Task 06.12 operation events without leaking eval state."""

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
    admin_update_operation_event,
    operation_events,
    routes_recommend,
)
from app.db import connect  # noqa: E402
from app.repositories.operation_repository import ensure_operation_schema  # noqa: E402


CREATED_BY = "eval_operation_events"
LEGACY_CREATED_BY = "eval-operation-events"
EVAL_CREATED_BY_VALUES = (CREATED_BY, LEGACY_CREATED_BY)


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_window() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return (
        (now - timedelta(minutes=2)).isoformat(timespec="seconds"),
        (now + timedelta(hours=2)).isoformat(timespec="seconds"),
    )


def cleanup_eval_events() -> int:
    placeholders = ", ".join("?" for _ in EVAL_CREATED_BY_VALUES)
    with connect() as conn:
        ensure_operation_schema(conn)
        cursor = conn.execute(
            f"DELETE FROM operation_events WHERE created_by IN ({placeholders})",
            EVAL_CREATED_BY_VALUES,
        )
        conn.commit()
        return int(cursor.rowcount)


def trace_text(route: dict[str, Any]) -> str:
    return " ".join(str(item) for item in route.get("decision_trace", []))


def stop_by_id(route: dict[str, Any], attraction_id: str) -> dict[str, Any] | None:
    for stop in route.get("stops", []):
        if stop.get("attraction_id") == attraction_id:
            return stop
    return None


def stop_event_ids(stop: dict[str, Any] | None) -> set[str]:
    return {str(item.get("id")) for item in (stop or {}).get("operation_events", [])}


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


def result(case_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"id": case_id, "passed": passed, **details}


def check_public_active_events() -> dict[str, Any]:
    payload = operation_events()
    items = payload.get("items", [])
    passed = payload.get("count", 0) > 0 and all(item.get("active") for item in items)
    return result(
        "public_active_events",
        passed,
        count=payload.get("count"),
        event_types=[item.get("event_type") for item in items],
    )


def check_manual_crowd_affects_trace() -> dict[str, Any]:
    event = create_event(
        attraction_id="nianhuawan-nh-005",
        event_type="crowd",
        severity="warning",
        message="[eval_operation_events] crowd on Wudeng Lake, wait about 35 minutes.",
    )
    route = routes_recommend(
        RouteRecommendRequest(theme="nature", time_budget_minutes=240, avoid_crowd=True, crowd_tolerance="low")
    )
    text = trace_text(route)
    stop = stop_by_id(route, "nianhuawan-nh-005")
    event_ids = stop_event_ids(stop)
    passed = event["id"] in event_ids and "manual_admin" in text
    return result(
        "manual_crowd_affects_trace",
        passed,
        event_id=event["id"],
        active_event_ids=sorted(event_ids),
        stop_operation_note=stop.get("operation_note") if stop else None,
        trace=text,
    )


def check_closed_non_must_avoided() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-013",
        event_type="closed",
        severity="critical",
        message="[eval_operation_events] closed non-must stop should be avoided.",
    )
    route = routes_recommend(RouteRecommendRequest(theme="photo", time_budget_minutes=300, avoid_crowd=True))
    ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    text = trace_text(route)
    passed = "lingshan-ls-013" not in ids and "manual_admin" in text and event["message"] in text
    return result("closed_non_must_avoided", passed, event_id=event["id"], stop_ids=ids, trace=text)


def check_closed_must_kept_warning() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-013",
        event_type="closed",
        severity="critical",
        message="[eval_operation_events] closed must-visit stop should be kept with warning.",
    )
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
    event_ids = stop_event_ids(stop)
    passed = bool(
        stop
        and stop.get("constraint_type") == "must_visit"
        and event["id"] in event_ids
        and stop.get("operation_note")
        and "manual_admin" in text
    )
    return result(
        "closed_must_kept_warning",
        passed,
        event_id=event["id"],
        active_event_ids=sorted(event_ids),
        stop=stop,
        trace=text,
        warning=(route.get("constraint_summary") or {}).get("warning"),
    )


def check_show_event_visible() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-006",
        event_type="show",
        severity="info",
        message="[eval_operation_events] Jiulong show starts in 15 minutes.",
    )
    route = routes_recommend(RouteRecommendRequest(theme="family", time_budget_minutes=240))
    stop = stop_by_id(route, "lingshan-ls-006")
    text = trace_text(route)
    event_ids = stop_event_ids(stop)
    passed = event["id"] in event_ids and ("show" in text or event["message"] in text)
    return result(
        "show_event_visible",
        passed,
        event_id=event["id"],
        active_event_ids=sorted(event_ids),
        stop_operation_note=stop.get("operation_note") if stop else None,
    )


def check_patch_deactivate_event() -> dict[str, Any]:
    event = create_event(
        attraction_id="lingshan-ls-013",
        event_type="closed",
        severity="critical",
        message="[eval_operation_events] deactivated event should not affect the route.",
    )
    admin_update_operation_event(event["id"], OperationEventUpdateRequest(active=False))
    route = routes_recommend(RouteRecommendRequest(theme="photo", time_budget_minutes=300, avoid_crowd=True))
    stop = stop_by_id(route, "lingshan-ls-013")
    event_ids = stop_event_ids(stop)
    text = trace_text(route)
    passed = event["id"] not in event_ids and event["message"] not in text
    return result(
        "patch_deactivate_event",
        passed,
        event_id=event["id"],
        stop_found=bool(stop),
        active_event_ids=sorted(event_ids),
    )


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "public_active_events": check_public_active_events,
    "manual_crowd_affects_trace": check_manual_crowd_affects_trace,
    "closed_non_must_avoided": check_closed_non_must_avoided,
    "closed_must_kept_warning": check_closed_must_kept_warning,
    "show_event_visible": check_show_event_visible,
    "patch_deactivate_event": check_patch_deactivate_event,
}


def run_checks() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in load_cases():
        check = CHECKS.get(case["id"])
        if check is None:
            results.append(result(case["id"], False, error="No check registered for case id."))
            continue
        cleanup_eval_events()
        try:
            item = check()
        finally:
            cleanup_eval_events()
        item["description"] = case.get("description")
        results.append(item)
    return results


def write_report(results: list[dict[str, Any]]) -> dict[str, Any]:
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
    return report


def main() -> int:
    cleanup_eval_events()
    try:
        results = run_checks()
    except Exception as exc:  # pragma: no cover - eval runner guard
        results = [result("eval_runner_error", False, error=str(exc))]
    finally:
        cleanup_eval_events()

    report = write_report(results)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
