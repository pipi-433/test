"""Evaluate Task 06.9 route constraint guardrails and edge cases."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
CASE_PATH = ROOT / "evals" / "route_constraints.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_constraints_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import RouteConversationRequest, RouteIntentRequest, routes_conversation, routes_intent  # noqa: E402
from app.services.route_memory_service import ROUTE_MEMORY_STORE  # noqa: E402
from app.services.route_service import recommend_route  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def stop_by_id(route: dict[str, Any], attraction_id: str) -> dict[str, Any] | None:
    for stop in route.get("stops", []):
        if stop.get("attraction_id") == attraction_id:
            return stop
    return None


def trace_text(route: dict[str, Any]) -> str:
    return " ".join(str(item) for item in route.get("decision_trace", []))


def contains_key(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in value for key in keys) or any(contains_key(item, keys) for item in value.values())
    if isinstance(value, list):
        return any(contains_key(item, keys) for item in value)
    return False


def result(case_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"id": case_id, "passed": passed, **details}


def check_must_high_lingshan() -> dict[str, Any]:
    route = recommend_route(
        theme="blessing",
        time_budget_minutes=240,
        must_visit_attraction_ids=["lingshan-ls-011"],
        avoid_crowd=True,
        crowd_tolerance="low",
    )
    stop = stop_by_id(route, "lingshan-ls-011")
    passed = bool(
        stop
        and stop.get("constraint_type") == "must_visit"
        and stop.get("crowd_level") == "high"
        and stop.get("crowd_action") in {"delay", "keep_with_warning"}
        and "必去" in trace_text(route)
    )
    return result(
        "must_high_lingshan",
        passed,
        crowd_action=stop.get("crowd_action") if stop else None,
        constraint_type=stop.get("constraint_type") if stop else None,
    )


def check_must_high_jiulong() -> dict[str, Any]:
    route = recommend_route(
        theme="family",
        time_budget_minutes=240,
        must_visit_attraction_ids=["lingshan-ls-006"],
        avoid_crowd=True,
        crowd_tolerance="low",
    )
    stop = stop_by_id(route, "lingshan-ls-006")
    passed = bool(
        stop
        and stop.get("constraint_type") == "must_visit"
        and stop.get("crowd_level") == "high"
        and stop.get("crowd_action") in {"delay", "keep_with_warning"}
    )
    return result("must_high_jiulong", passed, crowd_action=stop.get("crowd_action") if stop else None)


def check_avoid_template_stop() -> dict[str, Any]:
    route = recommend_route(theme="family", avoid_attraction_ids=["lingshan-ls-006"])
    stop_ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    summary = route.get("constraint_summary") or {}
    passed = "lingshan-ls-006" not in stop_ids and "lingshan-ls-006" in summary.get("skipped_avoid_attraction_ids", [])
    return result("avoid_template_stop", passed, stop_ids=stop_ids, summary=summary)


def check_optional_fangong() -> dict[str, Any]:
    route = recommend_route(theme="family", optional_attraction_ids=["lingshan-ls-013"])
    stop = stop_by_id(route, "lingshan-ls-013")
    summary = route.get("constraint_summary") or {}
    passed = bool(
        (stop and stop.get("constraint_type") == "optional")
        or "lingshan-ls-013" in summary.get("optional_not_selected_attraction_ids", [])
        or "梵宫" in trace_text(route)
    )
    return result(
        "optional_fangong",
        passed,
        selected=bool(stop),
        constraint_type=stop.get("constraint_type") if stop else None,
        optional_not_selected=summary.get("optional_not_selected_attraction_ids", []),
    )


def check_must_avoid_conflict_conversation() -> dict[str, Any]:
    response = routes_conversation(
        RouteConversationRequest(
            message="灵山大佛必须去但又不想去灵山大佛",
            session_id="mock-eval-constraint-conflict",
            selected_attraction_id="lingshan-ls-011",
        )
    )
    options = response.get("clarification_options") or []
    passed = bool(
        response.get("needs_clarification")
        and response.get("route") is None
        and all(option in options for option in ["保留为必去", "取消必去并避开", "重新规划不包含该点"])
    )
    return result("must_avoid_conflict_conversation", passed, options=options)


def check_many_must_short_budget() -> dict[str, Any]:
    must_ids = ["lingshan-ls-011", "lingshan-ls-006", "lingshan-ls-013", "lingshan-ls-014"]
    route = recommend_route(
        theme="family",
        time_budget_minutes=120,
        must_visit_attraction_ids=must_ids,
        avoid_crowd=True,
        crowd_tolerance="low",
    )
    stop_ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    summary = route.get("constraint_summary") or {}
    passed = all(attraction_id in stop_ids for attraction_id in must_ids) and bool(summary.get("warning") or "超过" in trace_text(route))
    return result("many_must_short_budget", passed, stop_ids=stop_ids, warning=summary.get("warning"))


def check_invalid_attraction_id() -> dict[str, Any]:
    route = recommend_route(theme="family", must_visit_attraction_ids=["bad-attraction-id"])
    stop_ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    summary = route.get("constraint_summary") or {}
    passed = "bad-attraction-id" not in stop_ids and "bad-attraction-id" in summary.get("invalid_attraction_ids", [])
    return result("invalid_attraction_id", passed, stop_ids=stop_ids, invalid=summary.get("invalid_attraction_ids", []))


def check_session_isolation() -> dict[str, Any]:
    first = routes_conversation(
        RouteConversationRequest(
            message="灵山大佛一定要去",
            session_id="mock-eval-session-a",
            selected_attraction_id="lingshan-ls-011",
        )
    )
    second = routes_conversation(
        RouteConversationRequest(
            message="我带老人孩子，三小时，别太挤",
            session_id="mock-eval-session-b",
            selected_attraction_id="lingshan-ls-006",
        )
    )
    first_must = first["memory"]["constraints"].get("must_visit_attraction_ids", [])
    second_must = second["memory"]["constraints"].get("must_visit_attraction_ids", [])
    passed = "lingshan-ls-011" in first_must and "lingshan-ls-011" not in second_must
    return result("session_isolation", passed, first_must=first_must, second_must=second_must)


def check_remove_must_same_session() -> dict[str, Any]:
    session_id = "mock-eval-remove-must"
    first = routes_conversation(
        RouteConversationRequest(message="灵山大佛一定要去", session_id=session_id, selected_attraction_id="lingshan-ls-011")
    )
    second = routes_conversation(
        RouteConversationRequest(
            message="算了，不去灵山大佛",
            session_id=first["session_id"],
            current_route_id=(first.get("route") or {}).get("id"),
            selected_attraction_id="lingshan-ls-011",
        )
    )
    must_ids = second["memory"]["constraints"].get("must_visit_attraction_ids", [])
    avoid_ids = second["memory"]["constraints"].get("avoid_attraction_ids", [])
    route = second.get("route") or {}
    stop = stop_by_id(route, "lingshan-ls-011")
    passed = "lingshan-ls-011" not in must_ids and "lingshan-ls-011" in avoid_ids and stop is None
    return result("remove_must_same_session", passed, must_ids=must_ids, avoid_ids=avoid_ids, stop=stop)


def check_start_in_avoid() -> dict[str, Any]:
    route = recommend_route(theme="blessing", start_attraction_id="lingshan-ls-011", avoid_attraction_ids=["lingshan-ls-011"])
    stop_ids = [stop.get("attraction_id") for stop in route.get("stops", [])]
    summary = route.get("constraint_summary") or {}
    passed = "lingshan-ls-011" not in stop_ids and bool(summary.get("start_context_only"))
    return result("start_in_avoid", passed, stop_ids=stop_ids, start_context_only=summary.get("start_context_only"))


def check_intent_direct_conflict() -> dict[str, Any]:
    response = routes_intent(
        RouteIntentRequest(message="灵山大佛必须去但又不想去灵山大佛", selected_attraction_id="lingshan-ls-011")
    )
    options = response.get("clarification_options") or []
    passed = bool(response.get("needs_clarification") and all(option in options for option in ["保留为必去", "取消必去并避开"]))
    return result("intent_direct_conflict", passed, intent=response.get("intent"), options=options)


def check_normal_route_regression() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240)
    passed = bool(
        len(route.get("stops", [])) >= 3
        and 0 <= int(route.get("recommendation_score", -1)) <= 100
        and "crowd_comfort" in (route.get("score_breakdown") or {})
        and all("decision_reason" in stop and "constraint_type" in stop for stop in route.get("stops", []))
        and not route.get("constraint_conflicts")
        and not contains_key(route, {"user_id", "phone", "openid"})
    )
    return result(
        "normal_route_regression",
        passed,
        stop_count=len(route.get("stops", [])),
        score=route.get("recommendation_score"),
    )


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "must_high_lingshan": check_must_high_lingshan,
    "must_high_jiulong": check_must_high_jiulong,
    "avoid_template_stop": check_avoid_template_stop,
    "optional_fangong": check_optional_fangong,
    "must_avoid_conflict_conversation": check_must_avoid_conflict_conversation,
    "many_must_short_budget": check_many_must_short_budget,
    "invalid_attraction_id": check_invalid_attraction_id,
    "session_isolation": check_session_isolation,
    "remove_must_same_session": check_remove_must_same_session,
    "start_in_avoid": check_start_in_avoid,
    "intent_direct_conflict": check_intent_direct_conflict,
    "normal_route_regression": check_normal_route_regression,
}


def main() -> int:
    ROUTE_MEMORY_STORE.clear()
    results: list[dict[str, Any]] = []
    for case in load_cases():
        check = CHECKS.get(case["id"])
        if check is None:
            results.append(result(case["id"], False, error="No check registered for case id."))
            continue
        case_result = check()
        case_result["description"] = case.get("description")
        results.append(case_result)

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
