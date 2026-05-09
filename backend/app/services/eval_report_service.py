from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT_DIR / "evals" / "reports"


@dataclass(frozen=True)
class ReportDefinition:
    id: str
    title: str
    filename: str
    summary: str


REPORT_DEFINITIONS = [
    ReportDefinition("qa", "RAG 问答", "qa_latest.json", "本地知识库问答、来源约束和低置信兜底评测。"),
    ReportDefinition("vision", "识景识别", "vision_latest.json", "mock 多模态识景样例成功率。"),
    ReportDefinition("route", "路线推荐", "route_latest.json", "路线模板、站点顺序和分享基础能力。"),
    ReportDefinition("route_crowd", "拥挤分流", "route_crowd_latest.json", "拥挤点降权、错峰解释和 crowd 信息覆盖。"),
    ReportDefinition("route_share", "路线带走", "route_share_latest.json", "Kiosk 分享码、手机复取和错误码评测。"),
    ReportDefinition("analytics", "后台洞察", "analytics_latest.json", "交互日志、反馈和 overview 汇总评测。"),
    ReportDefinition("route_conversation", "自然语言路线", "route_conversation_latest.json", "Route Memory、重规划、澄清和讲解风格。"),
    ReportDefinition("route_constraints", "路线约束", "route_constraints_latest.json", "必去/避开冲突、时间预算和会话隔离护栏。"),
    ReportDefinition("route_full_pool", "全量景点池", "route_full_pool_latest.json", "22 个景点可作为必去、可选、避开或补充候选。"),
    ReportDefinition("operation_events", "运营事件", "operation_events_latest.json", "人工运营事件对路线决策的影响。"),
    ReportDefinition("multipart_parser", "上传解析", "multipart_parser_latest.json", "multipart 文件名和换行兼容性。"),
    ReportDefinition("knowledge_gaps", "知识缺口", "knowledge_gaps_latest.json", "低置信/反馈到 FAQ 草稿和评测集闭环。"),
]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _result_passed(result: dict[str, Any]) -> bool:
    if "passed" in result:
        return bool(result.get("passed"))
    if "success" in result:
        return bool(result.get("success"))
    return False


def _compute_counts(payload: dict[str, Any]) -> tuple[int, int, int]:
    results = payload.get("results")
    if isinstance(results, list):
        total = _safe_int(payload.get("total"), len(results))
        passed = _safe_int(payload.get("passed"), sum(1 for item in results if isinstance(item, dict) and _result_passed(item)))
        failed = _safe_int(payload.get("failed"), max(0, total - passed))
        return total, passed, failed
    total = _safe_int(payload.get("total"))
    passed = _safe_int(payload.get("passed"))
    failed = _safe_int(payload.get("failed"), max(0, total - passed))
    return total, passed, failed


def _summarize_failure(result: dict[str, Any]) -> dict[str, Any]:
    message = (
        result.get("description")
        or result.get("message")
        or result.get("error")
        or result.get("reason")
        or result.get("answer_preview")
        or "未提供失败说明"
    )
    sample = {
        "id": str(result.get("id") or result.get("case_id") or "unknown"),
        "message": str(message)[:220],
    }
    for key in ["expected", "actual", "expected_filename", "actual_filename", "mismatches", "trace_ok", "source_ok"]:
        if key in result:
            sample[key] = result[key]
    return sample


def _failure_samples(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    failures = [item for item in results if isinstance(item, dict) and not _result_passed(item)]
    return [_summarize_failure(item) for item in failures[:3]]


def _load_report(definition: ReportDefinition, *, reports_dir: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = reports_dir / definition.filename
    if not path.exists():
        return (
            {
                "id": definition.id,
                "title": definition.title,
                "status": "missing",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "accuracy": None,
                "avg_latency_ms": None,
                "generated_at": None,
                "mode": "mock",
                "summary": f"未找到 {definition.filename}，请先运行对应 eval 脚本。",
                "failure_samples": [],
            },
            None,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            {
                "id": definition.id,
                "title": definition.title,
                "status": "fail",
                "total": 0,
                "passed": 0,
                "failed": 1,
                "accuracy": 0.0,
                "avg_latency_ms": None,
                "generated_at": None,
                "mode": "mock",
                "summary": f"{definition.filename} 无法读取：{exc}",
                "failure_samples": [{"id": "report-json", "message": str(exc)[:220]}],
            },
            None,
        )
    if not isinstance(payload, dict):
        payload = {}
    total, passed, failed = _compute_counts(payload)
    accuracy = _safe_float(payload.get("accuracy"))
    if accuracy is None and total > 0:
        accuracy = round(passed / total, 4)
    status = "pass" if failed == 0 else "fail"
    if total == 0 and not isinstance(payload.get("results"), list):
        status = "fail"
    summary = f"{definition.summary} 通过 {passed}/{total}，失败 {failed}。"
    return (
        {
            "id": definition.id,
            "title": definition.title,
            "status": status,
            "total": total,
            "passed": passed,
            "failed": failed,
            "accuracy": accuracy,
            "avg_latency_ms": _safe_float(payload.get("avg_latency_ms")),
            "generated_at": payload.get("generated_at"),
            "mode": payload.get("mode") or "mock",
            "summary": summary,
            "failure_samples": _failure_samples(payload),
        },
        payload,
    )


def _metric_from_results(
    payloads: dict[str, dict[str, Any]],
    report_ids: list[str],
    keywords: list[str],
    *,
    fallback_report_ids: list[str] | None = None,
) -> dict[str, Any]:
    picked: list[dict[str, Any]] = []
    for report_id in report_ids:
        results = payloads.get(report_id, {}).get("results")
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            haystack = " ".join(str(item.get(key, "")) for key in ["id", "description", "type"]).lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                picked.append(item)
    if not picked and fallback_report_ids:
        for report_id in fallback_report_ids:
            results = payloads.get(report_id, {}).get("results")
            if isinstance(results, list):
                picked.extend(item for item in results if isinstance(item, dict))
    if not picked:
        return {"value": None, "passed": None, "total": None, "reason": "没有足够的相关评测样例，暂不推断。"}
    passed = sum(1 for item in picked if _result_passed(item))
    total = len(picked)
    return {"value": round(passed / total, 4), "passed": passed, "total": total, "reason": None}


def _metric_from_report(payloads: dict[str, dict[str, Any]], report_id: str) -> dict[str, Any]:
    payload = payloads.get(report_id)
    if not payload:
        return {"value": None, "passed": None, "total": None, "reason": f"{report_id} report missing."}
    total, passed, _failed = _compute_counts(payload)
    if total <= 0:
        return {"value": None, "passed": None, "total": None, "reason": f"{report_id} report has no cases."}
    return {"value": round(passed / total, 4), "passed": passed, "total": total, "reason": None}


def _derived_metrics(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        "must_visit_preservation_rate": _metric_from_results(
            payloads,
            ["route_constraints", "route_full_pool", "route_conversation"],
            ["must"],
        ),
        "crowd_explanation_rate": _metric_from_results(
            payloads,
            ["route_crowd", "operation_events"],
            ["crowd", "closed", "show", "manual"],
            fallback_report_ids=["route_crowd"],
        ),
        "clarification_pass_rate": _metric_from_results(
            payloads,
            ["route_conversation", "route_constraints", "knowledge_gaps"],
            ["clarify", "clarification", "conflict", "no-source"],
        ),
        "knowledge_gap_workflow_rate": _metric_from_report(payloads, "knowledge_gaps"),
    }


def eval_reports_overview(*, reports_dir: Path | None = None) -> dict[str, Any]:
    report_dir = reports_dir or REPORTS_DIR
    reports: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    latest_time: datetime | None = None
    latest_generated_at: str | None = None

    for definition in REPORT_DEFINITIONS:
        report, payload = _load_report(definition, reports_dir=report_dir)
        reports.append(report)
        if payload is not None:
            payloads[definition.id] = payload
        parsed_time = _parse_time(report.get("generated_at"))
        if parsed_time and (latest_time is None or parsed_time > latest_time):
            latest_time = parsed_time
            latest_generated_at = str(report.get("generated_at"))

    available = [report for report in reports if report["status"] != "missing"]
    passing = [report for report in reports if report["status"] == "pass"]
    total_cases = sum(int(report["total"]) for report in available)
    passed_cases = sum(int(report["passed"]) for report in available)
    failed_cases = sum(int(report["failed"]) for report in available)
    return {
        "reports": reports,
        "overall": {
            "total_reports": len(reports),
            "available_reports": len(available),
            "passing_reports": len(passing),
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "overall_accuracy": round(passed_cases / total_cases, 4) if total_cases else None,
            "latest_generated_at": latest_generated_at,
        },
        "derived_metrics": _derived_metrics(payloads),
        "source_note": "评测看板读取本地 eval reports，用于比赛演示可信度证明；mock 模式不代表生产 SLA。",
        "mode": "mock",
    }
