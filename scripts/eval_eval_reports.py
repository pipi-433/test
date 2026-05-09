"""Evaluate Task 06.14 eval report dashboard aggregation."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "evals" / "reports" / "eval_reports_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import admin_eval_reports_overview  # noqa: E402
from app.services.eval_report_service import eval_reports_overview  # noqa: E402


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def main() -> int:
    overview = admin_eval_reports_overview()
    reports = overview.get("reports", [])
    overall = overview.get("overall", {})
    derived = overview.get("derived_metrics", {})
    missing_overview = eval_reports_overview(reports_dir=ROOT / "evals" / "reports" / "__missing_eval_report_dir__")

    checks = [
        {
            "id": "overview-api-available",
            "passed": isinstance(overview, dict) and isinstance(reports, list) and isinstance(overall, dict),
        },
        {
            "id": "reads-at-least-ten-reports",
            "passed": int(overall.get("available_reports") or 0) >= 10,
            "available_reports": overall.get("available_reports"),
            "total_reports": overall.get("total_reports"),
        },
        {
            "id": "overall-cases-summarized",
            "passed": int(overall.get("total_cases") or 0) > 0
            and int(overall.get("passed_cases") or 0) + int(overall.get("failed_cases") or 0) == int(overall.get("total_cases") or 0),
            "overall": overall,
        },
        {
            "id": "failure-samples-list",
            "passed": all(isinstance(item.get("failure_samples"), list) for item in reports if isinstance(item, dict)),
        },
        {
            "id": "derived-metrics-present",
            "passed": all(
                key in derived
                for key in [
                    "must_visit_preservation_rate",
                    "crowd_explanation_rate",
                    "clarification_pass_rate",
                    "knowledge_gap_workflow_rate",
                ]
            ),
            "derived_metric_keys": sorted(derived.keys()) if isinstance(derived, dict) else [],
        },
        {
            "id": "missing-report-tolerated",
            "passed": all(item.get("status") == "missing" for item in missing_overview.get("reports", []))
            and missing_overview.get("overall", {}).get("available_reports") == 0,
        },
        {
            "id": "no-secret-or-session-fields",
            "passed": not _contains_key(overview, "api_key") and not _contains_key(overview, "session_id"),
        },
    ]

    passed = sum(1 for check in checks if check["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "accuracy": round(passed / len(checks), 4) if checks else 0.0,
        "overview": {
            "available_reports": overall.get("available_reports"),
            "total_reports": overall.get("total_reports"),
            "total_cases": overall.get("total_cases"),
            "passed_cases": overall.get("passed_cases"),
            "failed_cases": overall.get("failed_cases"),
            "overall_accuracy": overall.get("overall_accuracy"),
            "latest_generated_at": overall.get("latest_generated_at"),
        },
        "results": checks,
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
