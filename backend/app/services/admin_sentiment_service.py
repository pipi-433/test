from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.repositories import analytics_repository as analytics_repo
from app.services.analytics_service import analytics_overview


SOURCE_NOTE = "游客感受度报告基于本地演示交互日志、反馈样例和 mock 数据汇总，不代表真实全园运营数据。"

DEFAULT_FOCUS_TOPICS = [
    {"topic": "灵山大佛怎么游览", "count": 128},
    {"topic": "九龙灌浴演出提醒", "count": 97},
    {"topic": "老人孩子轻松路线", "count": 81},
    {"topic": "梵宫室内动线", "count": 65},
    {"topic": "拈花湾夜游拍照", "count": 52},
]
DEFAULT_NEGATIVE_REASONS = [
    {"reason": "信息不准确 / 过时", "count": 6, "percent": 38},
    {"reason": "路线指引不清晰", "count": 4, "percent": 26},
    {"reason": "演出时间不明确", "count": 3, "percent": 18},
    {"reason": "内容不完整", "count": 2, "percent": 12},
]
DEFAULT_ROUTE_TAGS = [
    {"tag": "路线合理", "count": 12, "percent": 42},
    {"tag": "避开拥挤", "count": 9, "percent": 32},
    {"tag": "讲解清楚", "count": 7, "percent": 24},
    {"tag": "人多拥挤", "count": 4, "percent": 14},
]
DEFAULT_FEEDBACK_ROWS = [
    {
        "id": "sentiment-demo-001",
        "time": "2026-05-17T14:32:18+08:00",
        "channel": "mobile",
        "topic": "灵山大佛游览",
        "rating": 5,
        "tags": ["讲解清楚", "路线合理"],
        "comment": "讲解很清晰，路线推荐很实用。",
        "sentiment": "positive",
        "status": "已处理",
    },
    {
        "id": "sentiment-demo-002",
        "time": "2026-05-17T13:18:07+08:00",
        "channel": "kiosk",
        "topic": "九龙灌浴演出",
        "rating": 4,
        "tags": ["还想了解"],
        "comment": "希望再明确一下演出具体时段和地点。",
        "sentiment": "neutral",
        "status": "处理中",
    },
    {
        "id": "sentiment-demo-003",
        "time": "2026-05-17T11:46:22+08:00",
        "channel": "mobile",
        "topic": "梵宫参观",
        "rating": 3,
        "tags": ["信息不准"],
        "comment": "室内动线有点绕，找不到重点展区。",
        "sentiment": "negative",
        "status": "待跟进",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def _percent_rows(rows: list[dict[str, Any]], label_key: str) -> list[dict[str, Any]]:
    total = sum(int(item.get("count") or 0) for item in rows)
    if total <= 0:
        return rows
    return [
        {
            **item,
            "percent": int(round(int(item.get("count") or 0) * 100 / total)),
            label_key: item.get(label_key) or item.get("tag") or item.get("reason") or "未分类",
        }
        for item in rows
    ]


def _negative_reasons(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reason_map = {
        "信息不准": "信息不准确 / 过时",
        "人多拥挤": "现场拥挤体验",
        "路线合理": "路线指引不清晰",
        "还想了解": "内容不完整",
    }
    rows: dict[str, int] = {}
    for item in tags:
        tag = str(item.get("tag") or "")
        if tag not in reason_map:
            continue
        reason = reason_map[tag]
        rows[reason] = rows.get(reason, 0) + int(item.get("count") or 0)
    if not rows:
        return DEFAULT_NEGATIVE_REASONS
    return _percent_rows(
        [{"reason": reason, "count": count} for reason, count in sorted(rows.items(), key=lambda item: (-item[1], item[0]))],
        "reason",
    )


def _route_experience_tags(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {"讲解清楚", "路线合理", "避开拥挤", "人多拥挤", "体验惊喜"}
    rows = [{"tag": item["tag"], "count": int(item.get("count") or 0)} for item in tags if item.get("tag") in allowed]
    if not rows:
        return DEFAULT_ROUTE_TAGS
    return _percent_rows(rows, "tag")


def get_admin_sentiment_report() -> dict[str, Any]:
    overview = analytics_overview()
    feedback_distribution = analytics_repo.feedback_rating_distribution()
    average_rating = overview.get("average_rating")
    satisfaction_score = float(average_rating) if average_rating is not None else 4.7
    positive_rate = (
        feedback_distribution["positive"] / feedback_distribution["total"]
        if feedback_distribution["total"] > 0
        else 0.82
    )
    low_confidence = overview.get("low_confidence_questions") or []
    pending_issues = int(overview.get("open_knowledge_gap_count") or 0) + len(low_confidence)
    service_count = max(1, int(overview.get("service_count") or 0))
    emotion_volatility_index = min(35, max(8, int(round((pending_issues / service_count) * 100 + (100 - _pct(positive_rate)) * 0.18))))
    tags = overview.get("feedback_tags") or []
    focus_topics = [
        {"topic": item.get("question") or "游客关注问题", "count": int(item.get("count") or 0)}
        for item in (overview.get("popular_questions") or [])[:5]
    ] or DEFAULT_FOCUS_TOPICS
    feedback_rows = analytics_repo.feedback_rows(limit=10) or DEFAULT_FEEDBACK_ROWS
    suggestions = [
        "优先补齐低置信问题对应的 FAQ 草稿，发布前由管理员确认。",
        "对高拥挤点保留错峰提示，并在路线说明中突出替代点。",
        "对老人亲子路线增加休息点、少走路和观光车建议。",
    ]
    if any(item.get("tag") == "信息不准" for item in tags):
        suggestions.insert(0, "把“信息不准”反馈转为知识缺口，进入 FAQ 草稿和评测集。")
    return {
        "satisfaction_score": round(satisfaction_score, 2),
        "positive_rate": round(positive_rate, 4),
        "pending_issues": pending_issues,
        "low_confidence_count": len(low_confidence),
        "emotion_volatility_index": emotion_volatility_index,
        "focus_topics": focus_topics,
        "negative_reasons": _negative_reasons(tags),
        "route_experience_tags": _route_experience_tags(tags),
        "service_suggestions": suggestions,
        "feedback_rows": feedback_rows,
        "generated_at": _now(),
        "mode": "mock",
        "source_note": SOURCE_NOTE,
    }


def generate_admin_sentiment_report() -> dict[str, Any]:
    report = get_admin_sentiment_report()
    return {
        **report,
        "accepted": True,
        "job_id": f"sentiment-report-{uuid.uuid4().hex[:10]}",
        "message": "已生成游客感受度演示报告数据；PDF 导出为后续接入项。",
    }
