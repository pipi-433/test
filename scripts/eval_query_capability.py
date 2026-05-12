"""Evaluate Task 04.8 natural language capability matrix."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "query_capability.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "query_capability_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.qa_service import answer_question  # noqa: E402
from app.services.query_understanding_service import understand_query  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in EVAL_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _payload_present(response: dict[str, Any], payload_name: str | None) -> bool:
    if not payload_name:
        return True
    value = response.get(payload_name)
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def _understanding_mismatches(case: dict[str, Any], understanding: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for key, expected_key in [
        ("domain", "expected_domain"),
        ("intent", "expected_intent"),
        ("handler", "expected_handler"),
        ("should_retrieve", "expected_should_retrieve"),
        ("should_route", "expected_should_route"),
        ("needs_clarification", "expected_needs_clarification"),
    ]:
        if expected_key in case and understanding.get(key) != case[expected_key]:
            mismatches.append({"key": key, "expected": case[expected_key], "actual": understanding.get(key)})

    entity_ids = [entity.get("id") for entity in understanding.get("entities", []) if isinstance(entity, dict)]
    for attraction_id in case.get("expected_entity_ids", []):
        if attraction_id not in entity_ids:
            mismatches.append({"key": "entities", "expected_contains": attraction_id, "actual": entity_ids})

    slots = understanding.get("slots") if isinstance(understanding.get("slots"), dict) else {}
    if "expected_slot_scenic_area" in case and slots.get("scenic_area") != case["expected_slot_scenic_area"]:
        mismatches.append({"key": "slots.scenic_area", "expected": case["expected_slot_scenic_area"], "actual": slots.get("scenic_area")})
    if "expected_slot_time_budget" in case and slots.get("time_budget_minutes") != case["expected_slot_time_budget"]:
        mismatches.append({"key": "slots.time_budget_minutes", "expected": case["expected_slot_time_budget"], "actual": slots.get("time_budget_minutes")})
    for interest in case.get("expected_slot_interests", []):
        if interest not in (slots.get("interests") or []):
            mismatches.append({"key": "slots.interests", "expected_contains": interest, "actual": slots.get("interests")})

    required = [
        "domain",
        "intent",
        "entities",
        "slots",
        "confidence",
        "should_retrieve",
        "should_route",
        "handler",
        "needs_clarification",
        "clarification_question",
        "clarification_options",
        "reasons",
        "mode",
    ]
    missing = [key for key in required if key not in understanding]
    if missing:
        mismatches.append({"key": "structure", "expected": required, "actual_missing": missing})
    return mismatches


def check_case(case: dict[str, Any]) -> dict[str, Any]:
    understanding = understand_query(
        case["message"],
        selected_attraction_id=case.get("selected_attraction_id"),
        current_route_id=case.get("current_route_id"),
    )
    response = answer_question(
        question=case["message"],
        attraction_id=case.get("selected_attraction_id") if understanding.get("should_retrieve") else None,
        top_k=case.get("top_k", 5),
    )
    mismatches = _understanding_mismatches(case, understanding)

    if "expected_type" in case and response.get("type") != case["expected_type"]:
        mismatches.append({"key": "response.type", "expected": case["expected_type"], "actual": response.get("type")})
    if not _payload_present(response, case.get("expected_payload")):
        mismatches.append({"key": "payload", "expected_present": case.get("expected_payload"), "actual_keys": sorted(response.keys())})
    if case.get("expect_sources") is True and len(response.get("sources", [])) <= 0:
        mismatches.append({"key": "sources", "expected": ">0", "actual": 0})
    if case.get("expect_sources") is False and len(response.get("sources", [])) != 0:
        mismatches.append({"key": "sources", "expected": 0, "actual": len(response.get("sources", []))})
    answer = str(response.get("answer") or "")
    for keyword in case.get("expected_keywords", []):
        if keyword not in answer:
            mismatches.append({"key": "answer", "expected_contains": keyword, "actual_preview": answer[:180]})

    return {
        "id": case["id"],
        "category": case.get("category"),
        "message": case["message"],
        "passed": not mismatches,
        "domain": understanding.get("domain"),
        "intent": understanding.get("intent"),
        "handler": understanding.get("handler"),
        "type": response.get("type"),
        "source_count": len(response.get("sources", [])),
        "payload_keys": sorted(key for key in response.keys() if key not in {"answer"}),
        "mismatches": mismatches,
    }


def main() -> int:
    results = [check_case(case) for case in load_cases()]
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
        for result in results:
            if not result["passed"]:
                print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
