"""Evaluate Task 06.10 full attraction pool route planning."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
CASE_PATH = ROOT / "evals" / "route_full_pool.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_full_pool_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import RouteConversationRequest, RouteIntentRequest, routes_conversation, routes_intent  # noqa: E402
from app.repositories.content_repository import list_attractions  # noqa: E402
from app.services.route_memory_service import ROUTE_MEMORY_STORE  # noqa: E402
from app.services.route_service import recommend_route  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def stop_ids(route: dict[str, Any]) -> list[str]:
    return [str(stop.get("attraction_id")) for stop in route.get("stops", [])]


def stop_by_id(route: dict[str, Any], attraction_id: str) -> dict[str, Any] | None:
    for stop in route.get("stops", []):
        if stop.get("attraction_id") == attraction_id:
            return stop
    return None


def trace_text(route: dict[str, Any]) -> str:
    return " ".join(str(item) for item in route.get("decision_trace", []))


def result(case_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"id": case_id, "passed": passed, **details}


def check_must_xiangyue_full_pool() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240, must_visit_attraction_ids=["nianhuawan-nh-003"])
    stop = stop_by_id(route, "nianhuawan-nh-003")
    passed = bool(
        stop
        and stop.get("constraint_type") == "must_visit"
        and stop.get("selection_source") == "must_visit"
        and "全量景点池" in trace_text(route)
    )
    return result("must_xiangyue_full_pool", passed, stop=stop, stop_ids=stop_ids(route))


def check_must_wudenghu_full_pool() -> dict[str, Any]:
    route = recommend_route(theme="history", time_budget_minutes=240, must_visit_attraction_ids=["nianhuawan-nh-005"])
    stop = stop_by_id(route, "nianhuawan-nh-005")
    passed = bool(stop and stop.get("constraint_type") == "must_visit" and stop.get("selection_source") == "must_visit")
    return result("must_wudenghu_full_pool", passed, stop=stop, stop_ids=stop_ids(route))


def check_optional_fantian_flower_sea() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240, optional_attraction_ids=["nianhuawan-nh-002"])
    stop = stop_by_id(route, "nianhuawan-nh-002")
    summary = route.get("constraint_summary") or {}
    selected_ok = bool(stop and stop.get("constraint_type") == "optional")
    explained_skip = "nianhuawan-nh-002" in summary.get("optional_not_selected_attraction_ids", [])
    passed = selected_ok or explained_skip or "梵天花海" in trace_text(route)
    return result(
        "optional_fantian_flower_sea",
        passed,
        selected=bool(stop),
        constraint_type=stop.get("constraint_type") if stop else None,
        summary=summary,
    )


def check_avoid_jiulong_full_pool() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240, avoid_attraction_ids=["lingshan-ls-006"])
    summary = route.get("constraint_summary") or {}
    passed = "lingshan-ls-006" not in stop_ids(route) and "lingshan-ls-006" in summary.get("skipped_avoid_attraction_ids", [])
    return result("avoid_jiulong_full_pool", passed, stop_ids=stop_ids(route), summary=summary)


def check_intent_xiangyue_must() -> dict[str, Any]:
    response = routes_intent(RouteIntentRequest(message="香月花街一定要去"))
    passed = "nianhuawan-nh-003" in response.get("must_visit_attraction_ids", [])
    return result(
        "intent_xiangyue_must",
        passed,
        intent=response.get("intent"),
        must_visit=response.get("must_visit_attraction_ids"),
    )


def check_intent_nianhuawan_wudeng_fantian() -> dict[str, Any]:
    response = routes_intent(RouteIntentRequest(message="我想去拈花湾的五灯湖和梵天花海"))
    optional = response.get("optional_attraction_ids", [])
    matched = (response.get("metadata") or {}).get("matched_attraction_ids", [])
    passed = all(attraction_id in optional or attraction_id in matched for attraction_id in ["nianhuawan-nh-005", "nianhuawan-nh-002"])
    return result(
        "intent_nianhuawan_wudeng_fantian",
        passed,
        intent=response.get("intent"),
        optional_attraction_ids=optional,
        matched_attraction_ids=matched,
    )


def check_non_template_selection_source() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240, must_visit_attraction_ids=["nianhuawan-nh-004"])
    stop = stop_by_id(route, "nianhuawan-nh-004")
    passed = bool(stop and stop.get("selection_source") in {"must_visit", "full_pool"})
    return result(
        "non_template_selection_source",
        passed,
        selection_source=stop.get("selection_source") if stop else None,
        stop_ids=stop_ids(route),
    )


def check_many_must_visits_preserved() -> dict[str, Any]:
    must_ids = [
        "nianhuawan-nh-003",
        "nianhuawan-nh-005",
        "nianhuawan-nh-002",
        "lingshan-ls-011",
        "lingshan-ls-012",
        "lingshan-ls-013",
        "lingshan-ls-014",
        "lingshan-ls-015",
    ]
    route = recommend_route(theme="family", time_budget_minutes=120, must_visit_attraction_ids=must_ids)
    ids = stop_ids(route)
    missing = [attraction_id for attraction_id in must_ids if attraction_id not in ids]
    must_stops = [stop for stop in route.get("stops", []) if stop.get("attraction_id") in must_ids]
    passed = not missing and all(stop.get("constraint_type") == "must_visit" for stop in must_stops)
    return result(
        "many_must_visits_preserved",
        passed,
        missing=missing,
        stop_ids=ids,
        warning=(route.get("constraint_summary") or {}).get("warning"),
    )


def check_stops_have_profile_reason() -> dict[str, Any]:
    route = recommend_route(theme="photo", time_budget_minutes=240, avoid_attraction_ids=["lingshan-ls-006"])
    missing = [
        stop.get("attraction_id")
        for stop in route.get("stops", [])
        if not stop.get("profile_match_reason") and not isinstance(stop.get("theme_score"), int)
    ]
    passed = not missing and len(route.get("stops", [])) >= 3
    return result("stops_have_profile_reason", passed, missing=missing, stop_count=len(route.get("stops", [])))


def check_classic_templates_regression() -> dict[str, Any]:
    themes = ["family", "history", "nature", "blessing", "photo"]
    previews: dict[str, list[str]] = {}
    failures: list[str] = []
    for theme in themes:
        route = recommend_route(theme=theme, time_budget_minutes=240)
        previews[theme] = stop_ids(route)
        if len(route.get("stops", [])) < 3 or route.get("theme") != theme or not route.get("decision_trace"):
            failures.append(theme)
    return result("classic_templates_regression", not failures, failures=failures, previews=previews)


def check_conversation_xiangyue_must_avoid_jiulong() -> dict[str, Any]:
    response = routes_conversation(
        RouteConversationRequest(
            message="香月花街一定要去，九龙灌浴避开",
            session_id="mock-eval-full-pool-conversation",
        )
    )
    route = response.get("route") or {}
    ids = stop_ids(route)
    passed = bool(
        not response.get("needs_clarification")
        and "nianhuawan-nh-003" in ids
        and "lingshan-ls-006" not in ids
        and "nianhuawan-nh-003" in response["memory"]["constraints"].get("must_visit_attraction_ids", [])
        and "lingshan-ls-006" in response["memory"]["constraints"].get("avoid_attraction_ids", [])
    )
    return result(
        "conversation_xiangyue_must_avoid_jiulong",
        passed,
        needs_clarification=response.get("needs_clarification"),
        stop_ids=ids,
        memory=response.get("memory", {}).get("constraints"),
    )


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "must_xiangyue_full_pool": check_must_xiangyue_full_pool,
    "must_wudenghu_full_pool": check_must_wudenghu_full_pool,
    "optional_fantian_flower_sea": check_optional_fantian_flower_sea,
    "avoid_jiulong_full_pool": check_avoid_jiulong_full_pool,
    "intent_xiangyue_must": check_intent_xiangyue_must,
    "intent_nianhuawan_wudeng_fantian": check_intent_nianhuawan_wudeng_fantian,
    "non_template_selection_source": check_non_template_selection_source,
    "many_must_visits_preserved": check_many_must_visits_preserved,
    "stops_have_profile_reason": check_stops_have_profile_reason,
    "classic_templates_regression": check_classic_templates_regression,
    "conversation_xiangyue_must_avoid_jiulong": check_conversation_xiangyue_must_avoid_jiulong,
}


def main() -> int:
    ROUTE_MEMORY_STORE.clear()
    attractions = list_attractions()
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
        "attraction_count": len(attractions),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "attraction_count", "total", "passed", "failed", "accuracy"]}, ensure_ascii=False))
    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
