"""Evaluate Task 04.7 Query Understanding Gate."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "query_understanding.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "query_understanding_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.query_understanding_service import understand_query  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in EVAL_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_case(case: dict[str, Any]) -> dict[str, Any]:
    response = understand_query(
        case["message"],
        selected_attraction_id=case.get("selected_attraction_id"),
        current_route_id=case.get("current_route_id"),
    )
    entity_ids = [entity.get("id") for entity in response.get("entities", []) if isinstance(entity, dict)]
    mismatches: list[dict[str, Any]] = []
    for key, expected_key in [
        ("domain", "expected_domain"),
        ("intent", "expected_intent"),
        ("should_retrieve", "expected_should_retrieve"),
        ("should_route", "expected_should_route"),
        ("needs_clarification", "expected_needs_clarification"),
    ]:
        if expected_key in case and response.get(key) != case[expected_key]:
            mismatches.append({"key": key, "expected": case[expected_key], "actual": response.get(key)})
    for attraction_id in case.get("expected_entity_ids", []):
        if attraction_id not in entity_ids:
            mismatches.append({"key": "entities", "expected_contains": attraction_id, "actual": entity_ids})
    for attraction_id in case.get("must_not_entity_ids", []):
        if attraction_id in entity_ids:
            mismatches.append({"key": "entities", "expected_absent": attraction_id, "actual": entity_ids})
    structure_ok = all(
        key in response
        for key in [
            "domain",
            "intent",
            "entities",
            "confidence",
            "should_retrieve",
            "should_route",
            "needs_clarification",
            "clarification_question",
            "clarification_options",
            "reasons",
            "mode",
        ]
    )
    if response.get("mode") != "mock_rule_gate":
        mismatches.append({"key": "mode", "expected": "mock_rule_gate", "actual": response.get("mode")})
    if not structure_ok:
        mismatches.append({"key": "structure", "expected": "all required fields", "actual": sorted(response.keys())})
    passed = not mismatches
    return {
        "id": case["id"],
        "message": case["message"],
        "passed": passed,
        "domain": response.get("domain"),
        "intent": response.get("intent"),
        "should_retrieve": response.get("should_retrieve"),
        "should_route": response.get("should_route"),
        "needs_clarification": response.get("needs_clarification"),
        "entity_ids": entity_ids,
        "confidence": response.get("confidence"),
        "reasons": response.get("reasons"),
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
