"""Run the Task 04.5 mock vision recognition evaluation set."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "vision_samples.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "vision_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.services.vision_service import recognize_image_mock  # noqa: E402


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
    image_path = ROOT / case["image_path"]
    content = image_path.read_bytes()
    response = recognize_image_mock(
        filename=image_path.name,
        hint=case.get("hint"),
        text_hint=case.get("text_hint"),
        file_size=len(content),
    )
    matched = response["matched_attraction"]
    matched_id = matched["id"] if matched else None
    candidates = response.get("candidates", [])
    candidate_ids = [item["attraction"]["id"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    candidate_confidences = [float(item.get("confidence") or 0.0) for item in candidates if isinstance(item, dict)]
    expect_match = case.get("expect_match", True)
    id_ok = matched_id == case.get("expected_attraction_id")
    match_ok = (matched is not None) if expect_match else (matched is None)
    old_fields_ok = all(key in response for key in ["matched_attraction", "confidence", "suggested_questions"])
    candidates_present_ok = (len(candidates) >= 1) if expect_match else len(candidates) == 0
    top1_ok = (candidate_ids[0] == case.get("expected_attraction_id")) if expect_match and candidate_ids else not expect_match
    max3_ok = len(candidates) <= 3
    sorted_ok = candidate_confidences == sorted(candidate_confidences, reverse=True)
    needs_confirmation_ok = isinstance(response.get("needs_confirmation"), bool)
    passed = id_ok and match_ok and old_fields_ok and candidates_present_ok and top1_ok and max3_ok and sorted_ok and needs_confirmation_ok
    return {
        "id": case["id"],
        "image_path": case["image_path"],
        "expected_attraction_id": case.get("expected_attraction_id"),
        "matched_attraction_id": matched_id,
        "candidate_ids": candidate_ids,
        "candidates_count": len(candidates),
        "confidence": response["confidence"],
        "passed": passed,
        "match_ok": match_ok,
        "id_ok": id_ok,
        "old_fields_ok": old_fields_ok,
        "candidates_present_ok": candidates_present_ok,
        "top1_ok": top1_ok,
        "max3_ok": max3_ok,
        "sorted_ok": sorted_ok,
        "needs_confirmation_ok": needs_confirmation_ok,
        "needs_confirmation": response.get("needs_confirmation"),
        "latency_ms": response["latency_ms"],
        "explanation": response["explanation"],
    }


def check_ambiguous_case() -> dict[str, Any]:
    response = recognize_image_mock(
        filename="ambiguous_mock.jpg",
        hint="大佛 九龙",
        text_hint="",
        file_size=12,
    )
    candidates = response.get("candidates", [])
    candidate_ids = [item["attraction"]["id"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    passed = (
        len(candidates) >= 2
        and len(candidates) <= 3
        and response.get("needs_confirmation") is True
        and {"lingshan-ls-011", "lingshan-ls-006"}.issubset(set(candidate_ids))
    )
    return {
        "id": "vision_ambiguous_confirmation",
        "image_path": "synthetic",
        "expected_attraction_id": None,
        "matched_attraction_id": (response.get("matched_attraction") or {}).get("id")
        if isinstance(response.get("matched_attraction"), dict)
        else None,
        "candidate_ids": candidate_ids,
        "candidates_count": len(candidates),
        "confidence": response.get("confidence"),
        "passed": passed,
        "match_ok": True,
        "id_ok": True,
        "old_fields_ok": all(key in response for key in ["matched_attraction", "confidence", "suggested_questions"]),
        "candidates_present_ok": len(candidates) >= 2,
        "top1_ok": True,
        "max3_ok": len(candidates) <= 3,
        "sorted_ok": True,
        "needs_confirmation_ok": response.get("needs_confirmation") is True,
        "needs_confirmation": response.get("needs_confirmation"),
        "latency_ms": response["latency_ms"],
        "explanation": response["explanation"],
    }


def main() -> int:
    cases = load_cases()
    results = [check_case(case) for case in cases]
    results.append(check_ambiguous_case())
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
