"""Evaluate Task 06.15 scenic graph route topology behavior."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
CASE_PATH = ROOT / "evals" / "route_topology.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_topology_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.repositories.content_repository import list_attractions  # noqa: E402
from app.services.scenic_graph_service import validate_graph_coverage  # noqa: E402
from app.services.route_service import recommend_route  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def stop_ids(route: dict[str, Any]) -> list[str]:
    return [str(stop.get("attraction_id")) for stop in route.get("stops", [])]


def trace_text(route: dict[str, Any]) -> str:
    return " ".join(str(item) for item in route.get("decision_trace", []))


def result(case_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"id": case_id, "passed": passed, **details}


def check_route_topology_present() -> dict[str, Any]:
    route = recommend_route(theme="family", time_budget_minutes=240)
    topology = route.get("route_topology") or {}
    source_note = str(topology.get("source_note") or "")
    passed = bool(
        topology
        and topology.get("source") == "scenic_graph"
        and ("不代表真实 GPS 导航" in source_note or "导览图人工抽象" in source_note)
    )
    return result(
        "route_topology_present",
        passed,
        route_topology=topology,
        decision_trace=route.get("decision_trace", [])[-5:],
    )


def check_stops_have_topology() -> dict[str, Any]:
    route = recommend_route(theme="history", time_budget_minutes=240)
    stops = route.get("stops", [])
    missing = []
    leg_missing = []
    for index, stop in enumerate(stops):
        if not stop.get("topology_line_name") or not stop.get("topology_node_id"):
            missing.append(stop.get("attraction_id"))
        if index < len(stops) - 1 and stop.get("walking_minutes_to_next") is None and stop.get("transport_hint") != "area_transfer":
            leg_missing.append(stop.get("attraction_id"))
    passed = bool(stops) and not missing and not leg_missing
    return result("stops_have_topology", passed, missing=missing, leg_missing=leg_missing, stop_count=len(stops))


def check_all_attractions_mapped() -> dict[str, Any]:
    attractions = list_attractions()
    coverage = validate_graph_coverage(attractions)
    passed = coverage.get("ok") and coverage.get("mapped_count") == len(attractions) == 22
    return result("all_attractions_mapped", bool(passed), coverage=coverage)


def check_all_must_visit_preserved() -> dict[str, Any]:
    attractions = list_attractions()
    failures: list[dict[str, Any]] = []
    for attraction in attractions:
        attraction_id = str(attraction["id"])
        route = recommend_route(theme="family", time_budget_minutes=120, must_visit_attraction_ids=[attraction_id])
        ids = stop_ids(route)
        stop = next((item for item in route.get("stops", []) if item.get("attraction_id") == attraction_id), None)
        topology_ok = bool(stop and stop.get("topology_node_id"))
        if attraction_id not in ids or not topology_ok:
            failures.append({"attraction_id": attraction_id, "ids": ids, "topology_ok": topology_ok})
    return result("all_must_visit_preserved", not failures, checked=len(attractions), failures=failures[:5])


def check_central_axis_smoothness() -> dict[str, Any]:
    route = recommend_route(theme="blessing", time_budget_minutes=240)
    topology = route.get("route_topology") or {}
    score = topology.get("route_smoothness_score")
    passed = isinstance(score, int) and 0 <= score <= 100 and "central_axis" in topology.get("line_ids", [])
    return result(
        "central_axis_smoothness",
        passed,
        score=score,
        line_ids=topology.get("line_ids"),
        line_names=topology.get("line_names"),
    )


def check_central_to_east_trace() -> dict[str, Any]:
    route = recommend_route(
        theme="history",
        time_budget_minutes=240,
        must_visit_attraction_ids=["lingshan-ls-011", "lingshan-ls-014", "lingshan-ls-013"],
    )
    text = trace_text(route)
    topology = route.get("route_topology") or {}
    passed = (
        "central_axis" in topology.get("line_ids", [])
        and "east_treasure" in topology.get("line_ids", [])
        and any(keyword in text for keyword in ["宝藏东线", "东线", "导览图"])
    )
    return result(
        "central_to_east_trace",
        passed,
        line_ids=topology.get("line_ids"),
        decision_trace=route.get("decision_trace", [])[-6:],
    )


def check_area_transfer_marked() -> dict[str, Any]:
    route = recommend_route(
        theme="photo",
        time_budget_minutes=240,
        must_visit_attraction_ids=["lingshan-ls-011", "nianhuawan-nh-003"],
    )
    transfer_stops = [
        stop
        for stop in route.get("stops", [])
        if stop.get("transport_hint") == "area_transfer" or stop.get("backtrack_risk") == "transfer"
    ]
    topology = route.get("route_topology") or {}
    text = " ".join(topology.get("topology_explanation", []))
    passed = bool(transfer_stops) and "不代表真实 GPS 导航" in text
    return result(
        "area_transfer_marked",
        passed,
        transfer_stops=[stop.get("name") for stop in transfer_stops],
        topology_explanation=topology.get("topology_explanation"),
    )


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "route_topology_present": check_route_topology_present,
    "stops_have_topology": check_stops_have_topology,
    "all_attractions_mapped": check_all_attractions_mapped,
    "all_must_visit_preserved": check_all_must_visit_preserved,
    "central_axis_smoothness": check_central_axis_smoothness,
    "central_to_east_trace": check_central_to_east_trace,
    "area_transfer_marked": check_area_transfer_marked,
}


def main() -> int:
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
