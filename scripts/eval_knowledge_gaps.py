"""Evaluate Task 06.13 knowledge gap workflow."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "evals" / "reports" / "knowledge_gaps_latest.json"
EVAL_PATH = ROOT / "evals" / "knowledge_gaps.jsonl"
EVAL_PREFIX = "龘齉评测缺口"
STABLE_GAP_ID = "kgap-eval-stable"

sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import (  # noqa: E402
    FeedbackRequest,
    KnowledgeGapUpdateRequest,
    QARequest,
    admin_add_knowledge_gap_to_eval,
    admin_draft_knowledge_gap_faq,
    admin_knowledge_gaps,
    admin_update_knowledge_gap,
    feedback as feedback_endpoint,
    qa as qa_endpoint,
    analytics,
)
from app.repositories import knowledge_gap_repository as gap_repo  # noqa: E402


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def cleanup_eval_gaps() -> int:
    return gap_repo.delete_eval_gaps(query_prefix=EVAL_PREFIX)


def read_eval_cases() -> list[dict[str, Any]]:
    if not EVAL_PATH.exists():
        return []
    cases: list[dict[str, Any]] = []
    for line in EVAL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(json.loads(line))
    return cases


def find_gap(query: str) -> dict[str, Any] | None:
    for gap in admin_knowledge_gaps()["items"]:
        if gap["query"] == query:
            return gap
    return None


def count_open_or_drafted(query: str) -> int:
    return sum(
        1
        for gap in admin_knowledge_gaps()["items"]
        if gap["query"] == query and gap["status"] in {"open", "drafted"}
    )


def ensure_stable_eval_gap() -> dict[str, Any]:
    return gap_repo.insert_knowledge_gap(
        gap_id=STABLE_GAP_ID,
        query=f"{EVAL_PREFIX} 稳定评测缺口",
        trigger_type="manual",
        matched_sources=[],
        confidence=0.0,
        status="open",
    )


def main() -> int:
    cleanup_eval_gaps()
    checks: list[dict[str, Any]] = []
    try:
        no_source_query = f"{EVAL_PREFIX} 无资料问题"
        qa = qa_endpoint(QARequest(question=no_source_query, channel="mobile", top_k=5))
        qa_gap = find_gap(no_source_query)
        checks.append(
            {
                "id": "qa-no-source-gap-created",
                "passed": qa_gap is not None and qa_gap["trigger_type"] == "no_source" and len(qa.get("sources", [])) == 0,
                "gap_id": qa_gap["id"] if qa_gap else None,
            }
        )
        if qa_gap is None:
            qa_gap = gap_repo.insert_knowledge_gap(
                query=no_source_query,
                trigger_type="no_source",
                matched_sources=[],
                confidence=0.0,
                status="open",
            )

        qa_endpoint(QARequest(question=no_source_query, channel="mobile", top_k=5))
        checks.append(
            {
                "id": "duplicate-query-deduped",
                "passed": count_open_or_drafted(no_source_query) == 1,
                "open_or_drafted_count": count_open_or_drafted(no_source_query),
            }
        )

        drafted = admin_draft_knowledge_gap_faq(qa_gap["id"] if qa_gap else "missing")
        checks.append(
            {
                "id": "draft-faq-updates-status",
                "passed": drafted["status"] == "drafted" and bool(drafted.get("suggested_faq")),
                "status": drafted.get("status"),
            }
        )

        stable_gap = ensure_stable_eval_gap()
        before_cases = read_eval_cases()
        add_eval = admin_add_knowledge_gap_to_eval(stable_gap["id"])
        after_cases = read_eval_cases()
        stable_lines = [case for case in after_cases if case.get("gap_id") == STABLE_GAP_ID]
        checks.append(
            {
                "id": "add-eval-idempotent",
                "passed": bool(add_eval.get("eval_case_id"))
                and len(stable_lines) == 1
                and len(after_cases) in {len(before_cases), len(before_cases) + 1},
                "eval_case_id": add_eval.get("eval_case_id"),
                "stable_case_count": len(stable_lines),
            }
        )

        resolved = admin_update_knowledge_gap(qa_gap["id"] if qa_gap else "missing", KnowledgeGapUpdateRequest(status="resolved"))
        checks.append(
            {
                "id": "patch-status-resolved",
                "passed": resolved["status"] == "resolved",
                "status": resolved.get("status"),
            }
        )

        feedback_query = f"{EVAL_PREFIX} 这条讲解信息不准"
        feedback_endpoint(
            FeedbackRequest(
                channel="mobile",
                rating=2,
                tags=["信息不准"],
                comment=feedback_query,
            )
        )
        feedback_gap = find_gap(feedback_query)
        checks.append(
            {
                "id": "negative-feedback-gap-created",
                "passed": feedback_gap is not None and feedback_gap["trigger_type"] == "negative_feedback",
                "gap_id": feedback_gap["id"] if feedback_gap else None,
            }
        )
        if feedback_gap is None:
            feedback_gap = gap_repo.insert_knowledge_gap(
                query=feedback_query,
                trigger_type="negative_feedback",
                matched_sources=[],
                confidence=0.0,
                status="open",
            )

        ignored = admin_update_knowledge_gap(feedback_gap["id"] if feedback_gap else "missing", KnowledgeGapUpdateRequest(status="ignored"))
        checks.append(
            {
                "id": "patch-status-ignored",
                "passed": ignored["status"] == "ignored",
                "status": ignored.get("status"),
            }
        )

        listed = admin_knowledge_gaps()
        overview = analytics()
        checks.append(
            {
                "id": "admin-list-and-overview-fields",
                "passed": "items" in listed
                and all(key in overview for key in ["knowledge_gap_count", "open_knowledge_gap_count", "drafted_knowledge_gap_count"]),
                "count": listed.get("count"),
            }
        )
        checks.append(
            {
                "id": "no-session-id",
                "passed": not _contains_key({"gaps": listed, "overview": overview}, "session_id"),
            }
        )
    finally:
        cleaned = cleanup_eval_gaps()

    passed = sum(1 for check in checks if check["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "accuracy": round(passed / len(checks), 4) if checks else 0.0,
        "cleanup_deleted": cleaned,
        "results": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "total", "passed", "failed", "accuracy", "cleanup_deleted"]}, ensure_ascii=False))
    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
