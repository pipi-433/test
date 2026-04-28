"""Run the Task 04 mock QA evaluation set."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "qa_lingshan.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "qa_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.qa_service import answer_question  # noqa: E402


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
    response = answer_question(
        question=case["question"],
        attraction_id=case.get("attraction_id"),
        visitor_profile=case.get("visitor_profile"),
        top_k=case.get("top_k", 5),
    )
    answer = response["answer"]
    expected_keywords = case.get("expected_keywords", [])
    missing_keywords = [keyword for keyword in expected_keywords if keyword not in answer]
    forbidden_hits = [keyword for keyword in case.get("must_not_include", []) if keyword in answer]
    expect_sources = case.get("expect_sources")
    source_count = len(response["sources"])
    source_ok = True
    if expect_sources is True:
        source_ok = source_count > 0
    elif expect_sources is False:
        source_ok = source_count == 0

    passed = not missing_keywords and not forbidden_hits and source_ok
    return {
        "id": case["id"],
        "category": case.get("category"),
        "question": case["question"],
        "passed": passed,
        "missing_keywords": missing_keywords,
        "forbidden_hits": forbidden_hits,
        "source_count": source_count,
        "source_ok": source_ok,
        "latency_ms": response["latency_ms"],
        "answer_preview": answer[:220],
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
