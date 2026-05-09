from __future__ import annotations

from typing import Any

from app.repositories import analytics_repository as repo
from app.repositories import knowledge_gap_repository as gap_repo
from app.services.crowd_service import get_crowd_snapshot


VALID_CHANNELS = {"mobile", "kiosk", "share", "admin", "api"}
VALID_FEEDBACK_TAGS = {"讲解清楚", "路线合理", "避开拥挤", "人多拥挤", "信息不准", "体验惊喜", "还想了解"}


def _safe_channel(value: str | None) -> str:
    channel = str(value or "api").strip().lower()
    return channel if channel in VALID_CHANNELS else "api"


def _preview(value: str | None, limit: int = 120) -> str | None:
    if not value:
        return None
    text = " ".join(str(value).split())
    return text[:limit]


def record_interaction_event(
    *,
    event_type: str,
    channel: str = "api",
    question: str | None = None,
    answer_preview: str | None = None,
    attraction_id: str | None = None,
    route_id: str | None = None,
    share_code: str | None = None,
    confidence: float | None = None,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return repo.insert_interaction_event(
        event_type=event_type,
        channel=_safe_channel(channel),
        question=_preview(question, 180),
        answer_preview=_preview(answer_preview),
        attraction_id=attraction_id,
        route_id=route_id,
        share_code=share_code,
        confidence=confidence,
        success=success,
        metadata=metadata or {},
    )


def record_feedback(
    *,
    channel: str,
    rating: int,
    tags: list[str] | None = None,
    route_id: str | None = None,
    attraction_id: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    clean_rating = max(1, min(int(rating), 5))
    clean_tags = [tag for tag in (tags or []) if tag in VALID_FEEDBACK_TAGS]
    feedback = repo.insert_feedback_event(
        channel=_safe_channel(channel),
        route_id=route_id,
        attraction_id=attraction_id,
        rating=clean_rating,
        tags=clean_tags,
        comment=_preview(comment, 300),
    )
    record_interaction_event(
        event_type="feedback",
        channel=channel,
        attraction_id=attraction_id,
        route_id=route_id,
        success=True,
        metadata={"rating": clean_rating, "tags": clean_tags, "has_comment": bool(comment)},
    )
    return {"id": feedback["id"], "status": "ok", "created_at": feedback["created_at"]}


def analytics_overview() -> dict[str, Any]:
    crowd_snapshot = get_crowd_snapshot()
    high_crowd_attractions = [
        {
            "attraction_id": item["attraction_id"],
            "name": item["name"],
            "scenic_area": item.get("scenic_area"),
            "crowd_level": item["crowd_level"],
            "crowd_score": item["crowd_score"],
            "wait_minutes": item["wait_minutes"],
            "source": item["source"],
        }
        for item in crowd_snapshot["items"]
        if item["crowd_level"] == "high"
    ]
    qa_count = repo.count_events("qa")
    vision_count = repo.count_events("vision")
    route_count = repo.count_events("route_recommend")
    share_open_count = repo.count_events("route_share_open")
    feedback_count = repo.feedback_count()
    knowledge_gap_count = gap_repo.count_knowledge_gaps()
    return {
        "service_count": qa_count + vision_count + route_count + share_open_count,
        "qa_count": qa_count,
        "vision_count": vision_count,
        "route_count": route_count,
        "share_open_count": share_open_count,
        "feedback_count": feedback_count,
        "knowledge_gap_count": knowledge_gap_count,
        "open_knowledge_gap_count": gap_repo.count_knowledge_gaps("open"),
        "drafted_knowledge_gap_count": gap_repo.count_knowledge_gaps("drafted"),
        "average_rating": repo.average_rating(),
        "popular_questions": repo.popular_questions(),
        "low_confidence_questions": repo.low_confidence_questions(),
        "route_theme_distribution": repo.route_theme_distribution(),
        "crowd_avoidance_count": repo.count_events("crowd_avoidance"),
        "high_crowd_attractions": high_crowd_attractions,
        "feedback_tags": repo.feedback_tags(),
        "recent_events": repo.recent_events(),
        "source_note": "当前 analytics 为本地演示日志 + mock/公开样例数据，不代表真实景区全量运营数据；不记录个人身份或图片原始内容。",
        "mode": "mock",
    }
