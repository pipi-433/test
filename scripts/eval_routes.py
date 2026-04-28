"""Run the Task 06 mock route recommendation evaluation set."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "route_lingshan.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "route_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.route_service import get_route_share, recommend_route  # noqa: E402


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
        start_attraction_id=case.get("start_attraction_id"),
    )
    stop_names = [stop["name"] for stop in response["stops"]]
    route_text = " ".join([response["title"], response["summary"], *stop_names])
    missing_keywords = [keyword for keyword in case.get("expected_keywords", []) if keyword not in route_text]
    theme_ok = response["theme"] == case.get("expected_theme")
    stop_count_ok = len(response["stops"]) >= int(case.get("min_stops", 3))
    duration_ok = response["estimated_duration_minutes"] <= response["time_budget_minutes"] + 45
    share = get_route_share(response["id"], response["share"]["share_code"])["share"]
    share_ok = share["share_code"].startswith("LJ-") and share["expires_in_minutes"] == 30
    passed = theme_ok and stop_count_ok and duration_ok and share_ok and not missing_keywords
    return {
        "id": case["id"],
        "passed": passed,
        "theme": response["theme"],
        "expected_theme": case.get("expected_theme"),
        "theme_ok": theme_ok,
        "stop_count": len(response["stops"]),
        "stop_count_ok": stop_count_ok,
        "estimated_duration_minutes": response["estimated_duration_minutes"],
        "time_budget_minutes": response["time_budget_minutes"],
        "duration_ok": duration_ok,
        "share_ok": share_ok,
        "missing_keywords": missing_keywords,
        "latency_ms": response["latency_ms"],
        "route_preview": " > ".join(stop_names[:6]),
    }


def main() -> int:
    cases = load_cases()
    results = [check_case(case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "avg_latency_ms": round(sum(result["latency_ms"] for result in results) / len(results), 2) if results else 0.0,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "total", "passed", "failed", "accuracy", "avg_latency_ms"]}, ensure_ascii=False))
    if report["failed"]:
        for result in results:
            if not result["passed"]:
                print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
