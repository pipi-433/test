"""Evaluate Task 06.5 crowd-aware route recommendations."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "route_crowd.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_crowd_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.crowd_service import get_crowd_snapshot  # noqa: E402
from app.services.route_service import recommend_route  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(EVAL_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return cases


def check_case(case: dict[str, Any]) -> dict[str, Any]:
    response = recommend_route(
        theme=case.get("theme"),
        time_budget_minutes=case.get("time_budget_minutes"),
        group_type=case.get("group_type"),
        intensity=case.get("intensity"),
        interests=case.get("interests"),
        avoid_crowd=case.get("avoid_crowd", True),
        crowd_tolerance=case.get("crowd_tolerance", "medium"),
    )
    trace_text = " ".join(response.get("decision_trace", []))
    stops = response.get("stops", [])
    high_stops = [stop for stop in stops if stop.get("crowd_level") == "high"]
    delayed_or_explained = not high_stops or any(
        word in f"{stop.get('crowd_note', '')} {trace_text}" for stop in high_stops for word in ["错峰", "延后", "保留"]
    )
    score_ok = 0 <= int(response.get("recommendation_score", -1)) <= 100
    breakdown_ok = "crowd_comfort" in response.get("score_breakdown", {})
    trace_ok = "mock_simulation" in trace_text or "模拟" in trace_text
    stops_have_crowd = bool(stops) and all(
        {"crowd_level", "crowd_score", "wait_minutes", "crowd_note"}.issubset(stop.keys()) for stop in stops
    )
    passed = score_ok and breakdown_ok and trace_ok and stops_have_crowd and delayed_or_explained
    return {
        "id": case["id"],
        "passed": passed,
        "recommendation_score": response.get("recommendation_score"),
        "score_ok": score_ok,
        "breakdown_ok": breakdown_ok,
        "trace_ok": trace_ok,
        "stops_have_crowd": stops_have_crowd,
        "delayed_or_explained": delayed_or_explained,
        "high_stops": [stop.get("name") for stop in high_stops],
        "decision_trace": response.get("decision_trace", []),
        "latency_ms": response.get("latency_ms", 0),
    }


def main() -> int:
    snapshot = get_crowd_snapshot()
    snapshot_ok = snapshot["count"] > 0 and any(item["crowd_level"] == "high" for item in snapshot["items"])
    cases = load_cases()
    results = [check_case(case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    if snapshot_ok:
        passed += 1
    total = len(results) + 1
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "snapshot_ok": snapshot_ok,
        "snapshot_count": snapshot["count"],
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "avg_latency_ms": round(sum(result["latency_ms"] for result in results) / len(results), 2) if results else 0.0,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ["mode", "total", "passed", "failed", "accuracy", "avg_latency_ms"]},
            ensure_ascii=False,
        )
    )
    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
