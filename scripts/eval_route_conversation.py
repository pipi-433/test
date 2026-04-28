"""Evaluate Task 06.8 natural language route planning and Route Memory Agent."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
INTENT_PATH = ROOT / "evals" / "route_intent.jsonl"
REPLAN_PATH = ROOT / "evals" / "route_replan.jsonl"
CLARIFICATION_PATH = ROOT / "evals" / "clarification_guard.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_conversation_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import (  # noqa: E402
    RouteConversationRequest,
    RouteIntentRequest,
    routes_conversation,
    routes_intent,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def check_intent_case(case: dict[str, Any]) -> dict[str, Any]:
    response = routes_intent(RouteIntentRequest(message=case["message"], selected_attraction_id="lingshan-ls-011"))
    expected = case.get("expected", {})
    mismatches = []
    for key, expected_value in expected.items():
        actual = response.get(key)
        if isinstance(expected_value, list):
            if not all(item in (actual or []) for item in expected_value):
                mismatches.append({"key": key, "expected": expected_value, "actual": actual})
        elif actual != expected_value:
            mismatches.append({"key": key, "expected": expected_value, "actual": actual})
    return {
        "id": case["id"],
        "type": "intent",
        "passed": not mismatches,
        "intent": response.get("intent"),
        "operation": response.get("operation"),
        "confidence": response.get("intent_confidence"),
        "mismatches": mismatches,
    }


def check_replan_case(case: dict[str, Any], index: int) -> dict[str, Any]:
    session_id = f"mock-eval-route-memory-{index}"
    first = routes_conversation(
        RouteConversationRequest(message=case["setup_message"], session_id=session_id, selected_attraction_id="lingshan-ls-011")
    )
    second = routes_conversation(
        RouteConversationRequest(
            message=case["message"],
            session_id=first["session_id"],
            current_route_id=(first.get("route") or {}).get("id"),
            selected_attraction_id="lingshan-ls-011",
        )
    )
    route = second.get("route") or {}
    stops = route.get("stops", [])
    stop_ids = [stop.get("attraction_id") for stop in stops]
    stop_by_id = {stop.get("attraction_id"): stop for stop in stops}
    operation_ok = second["intent"].get("operation") == case.get("expected_operation") if case.get("expected_operation") else True
    must_ok = True
    for attraction_id in case.get("expected_must_visit", []):
        stop = stop_by_id.get(attraction_id)
        if not stop or stop.get("constraint_type") != "must_visit" or stop.get("crowd_action") not in {"delay", "keep_with_warning", "keep"}:
            must_ok = False
    score_ok = 0 <= int(route.get("recommendation_score", -1)) <= 100
    breakdown_ok = "crowd_comfort" in (route.get("score_breakdown") or {})
    trace_text = " ".join(route.get("decision_trace") or [])
    trace_ok = "mock_simulation" in trace_text or "模拟" in trace_text
    stops_have_crowd = all("crowd_level" in stop and "wait_minutes" in stop and "constraint_type" in stop for stop in stops)
    shortened_ok = True
    if case.get("expected_operation") == "shorten":
        first_minutes = (first.get("route") or {}).get("estimated_duration_minutes", 999)
        second_minutes = route.get("estimated_duration_minutes", 999)
        shortened_ok = second_minutes <= first_minutes
    no_identity = not _contains_key(second, "user_id") and not _contains_key(second, "phone") and not _contains_key(second, "openid")
    passed = all([operation_ok, must_ok, score_ok, breakdown_ok, trace_ok, stops_have_crowd, shortened_ok, no_identity])
    return {
        "id": case["id"],
        "type": "replan",
        "passed": passed,
        "operation": second["intent"].get("operation"),
        "route_id": route.get("id"),
        "stop_ids": stop_ids,
        "score": route.get("recommendation_score"),
        "operation_ok": operation_ok,
        "must_ok": must_ok,
        "score_ok": score_ok,
        "breakdown_ok": breakdown_ok,
        "trace_ok": trace_ok,
        "stops_have_crowd": stops_have_crowd,
        "shortened_ok": shortened_ok,
        "no_identity": no_identity,
    }


def check_clarification_case(case: dict[str, Any]) -> dict[str, Any]:
    response = routes_conversation(RouteConversationRequest(message=case["message"], session_id=f"mock-eval-clarify-{case['id']}"))
    passed = bool(response.get("needs_clarification")) is bool(case.get("expected_needs_clarification"))
    return {
        "id": case["id"],
        "type": "clarification",
        "passed": passed,
        "needs_clarification": response.get("needs_clarification"),
        "options": response.get("clarification_options"),
    }


def main() -> int:
    results: list[dict[str, Any]] = []
    results.extend(check_intent_case(case) for case in load_jsonl(INTENT_PATH))
    results.extend(check_replan_case(case, index) for index, case in enumerate(load_jsonl(REPLAN_PATH), start=1))
    results.extend(check_clarification_case(case) for case in load_jsonl(CLARIFICATION_PATH))
    passed = sum(1 for result in results if result["passed"])
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
