from typing import Any

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel

from app.core.errors import ApiError
from app.core.config import get_settings
from app.providers import ProviderStatus, get_provider_status
from app.services.analytics_service import analytics_overview, record_feedback, record_interaction_event
from app.services.content_service import (
    get_attraction_or_error,
    get_attractions,
    get_behavior_summary_or_error,
    get_chunks,
)
from app.services.crowd_service import get_crowd_snapshot
from app.services.qa_service import answer_question
from app.services.route_service import get_route_share, recommend_route, route_theme_options
from app.services.vision_service import recognize_image_mock

router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str


class ProviderStatusResponse(BaseModel):
    llm: ProviderStatus
    embedding: ProviderStatus
    vlm: ProviderStatus
    tts: ProviderStatus


class QARequest(BaseModel):
    question: str
    attraction_id: str | None = None
    visitor_profile: dict[str, Any] | None = None
    top_k: int = 5
    channel: str = "mobile"


class RouteRecommendRequest(BaseModel):
    theme: str | None = None
    time_budget_minutes: int | None = 240
    group_type: str | None = None
    intensity: str | None = None
    interests: list[str] | None = None
    start_attraction_id: str | None = None
    avoid_crowd: bool = True
    crowd_tolerance: str = "medium"
    channel: str = "mobile"


class FeedbackRequest(BaseModel):
    channel: str = "mobile"
    route_id: str | None = None
    attraction_id: str | None = None
    rating: int
    tags: list[str] = []
    comment: str | None = None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        mode=settings.mode,
    )


@router.get("/provider/status", response_model=ProviderStatusResponse)
def provider_status() -> dict[str, ProviderStatus]:
    return get_provider_status()


@router.get("/attractions")
def attractions() -> dict[str, object]:
    items = get_attractions()
    return {"items": items, "count": len(items)}


@router.get("/attractions/{attraction_id}")
def attraction_detail(attraction_id: str) -> dict:
    return get_attraction_or_error(attraction_id)


@router.get("/knowledge/chunks")
def knowledge_chunks(attraction_id: str | None = None) -> dict[str, object]:
    items = get_chunks(attraction_id)
    return {"items": items, "count": len(items)}


@router.get("/analytics/behavior-summary")
def behavior_summary() -> dict:
    return get_behavior_summary_or_error()


@router.get("/analytics/overview")
def analytics() -> dict[str, object]:
    return analytics_overview()


@router.post("/qa")
def qa(payload: QARequest) -> dict[str, object]:
    question = payload.question.strip()
    if not question:
        raise ApiError(
            code="EMPTY_QUESTION",
            message="请先输入一个问题。",
            cause="POST /api/qa received an empty question.",
            fix="在 question 字段中传入游客想问的景点、文化或游览问题。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    top_k = max(1, min(payload.top_k, 10))
    result = answer_question(
        question=question,
        attraction_id=payload.attraction_id,
        visitor_profile=payload.visitor_profile,
        top_k=top_k,
    )
    source_scores = [float(source.get("score") or 0) for source in result.get("sources", [])]
    confidence = min(1.0, max(source_scores) / 4.0) if source_scores else 0.0
    record_interaction_event(
        event_type="qa",
        channel=payload.channel,
        question=question,
        answer_preview=str(result.get("answer") or ""),
        attraction_id=payload.attraction_id,
        confidence=round(confidence, 4),
        success=bool(result.get("sources")),
        metadata={
            "source_count": len(result.get("sources", [])),
            "fallback": len(result.get("sources", [])) == 0,
            "latency_ms": result.get("latency_ms"),
            "mode": result.get("mode"),
        },
    )
    return result


@router.get("/routes/themes")
def route_themes() -> dict[str, object]:
    items = route_theme_options()
    return {"items": items, "count": len(items)}


@router.get("/crowd/snapshot")
def crowd_snapshot() -> dict[str, object]:
    return get_crowd_snapshot()


@router.post("/routes/recommend")
def routes_recommend(payload: RouteRecommendRequest) -> dict[str, object]:
    result = recommend_route(
        theme=payload.theme,
        time_budget_minutes=payload.time_budget_minutes,
        group_type=payload.group_type,
        intensity=payload.intensity,
        interests=payload.interests,
        start_attraction_id=payload.start_attraction_id,
        avoid_crowd=payload.avoid_crowd,
        crowd_tolerance=payload.crowd_tolerance,
    )
    high_stops = [stop for stop in result.get("stops", []) if stop.get("crowd_level") == "high"]
    record_interaction_event(
        event_type="route_recommend",
        channel=payload.channel,
        attraction_id=payload.start_attraction_id,
        route_id=str(result.get("id")),
        share_code=(result.get("share") or {}).get("share_code"),
        confidence=float(result.get("recommendation_score") or 0) / 100,
        success=True,
        metadata={
            "theme": result.get("theme"),
            "theme_label": result.get("theme_label"),
            "score": result.get("recommendation_score"),
            "avoid_crowd": payload.avoid_crowd,
            "crowd_tolerance": payload.crowd_tolerance,
            "high_crowd_stops": [stop.get("name") for stop in high_stops],
            "stop_count": len(result.get("stops", [])),
        },
    )
    if payload.avoid_crowd or high_stops:
        record_interaction_event(
            event_type="crowd_avoidance",
            channel=payload.channel,
            attraction_id=payload.start_attraction_id,
            route_id=str(result.get("id")),
            share_code=(result.get("share") or {}).get("share_code"),
            confidence=float(result.get("recommendation_score") or 0) / 100,
            success=True,
            metadata={
                "source": "mock_simulation",
                "high_crowd_stops": [stop.get("name") for stop in high_stops],
                "decision_trace": result.get("decision_trace", [])[:4],
            },
        )
    return result


@router.get("/routes/{route_id}/share")
def route_share(route_id: str, code: str | None = Query(default=None)) -> dict[str, object]:
    result = get_route_share(route_id, code)
    record_interaction_event(
        event_type="route_share_open",
        channel="share",
        route_id=route_id,
        share_code=code,
        success=True,
        metadata={
            "theme": result.get("theme"),
            "theme_label": result.get("theme_label"),
            "score": result.get("recommendation_score"),
            "stop_count": len(result.get("stops", [])),
        },
    )
    return result


@router.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, object]:
    if payload.rating < 1 or payload.rating > 5:
        raise ApiError(
            code="INVALID_FEEDBACK_RATING",
            message="反馈评分需要在 1 到 5 分之间。",
            cause=f"Invalid rating: {payload.rating}",
            fix="请在 rating 字段传入 1、2、3、4 或 5。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return record_feedback(
        channel=payload.channel,
        route_id=payload.route_id,
        attraction_id=payload.attraction_id,
        rating=payload.rating,
        tags=payload.tags,
        comment=payload.comment,
    )


def _parse_content_disposition(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        result[key.strip().lower()] = raw.strip().strip('"')
    return result


def _parse_multipart_form(content_type: str, body: bytes) -> dict[str, object]:
    marker = "boundary="
    if marker not in content_type:
        raise ApiError(
            code="INVALID_MULTIPART",
            message="请使用 multipart/form-data 上传图片。",
            cause=f"Content-Type missing boundary: {content_type}",
            fix="表单字段使用 file 上传文件，可选 hint 或 text_hint 提供识别提示。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = f"--{boundary}".encode("utf-8")
    fields: dict[str, object] = {}
    for part in body.split(delimiter):
        part = part.strip()
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip()
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, value = part.split(b"\r\n\r\n", 1)
        value = value.rstrip(b"\r\n")
        headers = {}
        for line in raw_headers.decode("utf-8", errors="ignore").split("\r\n"):
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            headers[key.strip().lower()] = raw.strip()
        disposition = _parse_content_disposition(headers.get("content-disposition", ""))
        name = disposition.get("name")
        if not name:
            continue
        if "filename" in disposition:
            fields[name] = {
                "filename": disposition.get("filename", ""),
                "content_type": headers.get("content-type", "application/octet-stream"),
                "content": value,
            }
        else:
            fields[name] = value.decode("utf-8", errors="ignore").strip()
    return fields


@router.post("/vision/recognize")
async def vision_recognize(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    fields = _parse_multipart_form(content_type, body)
    file_info = fields.get("file")
    if not isinstance(file_info, dict):
        raise ApiError(
            code="IMAGE_FILE_REQUIRED",
            message="请上传一张图片文件。",
            cause="POST /api/vision/recognize did not include form field 'file'.",
            fix="用 multipart/form-data 提交 file 字段，可附加 hint 或 text_hint。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    content = file_info.get("content", b"")
    file_size = len(content) if isinstance(content, bytes) else None
    result = recognize_image_mock(
        filename=str(file_info.get("filename") or ""),
        hint=str(fields.get("hint") or ""),
        text_hint=str(fields.get("text_hint") or ""),
        file_size=file_size,
    )
    matched = result.get("matched_attraction")
    record_interaction_event(
        event_type="vision",
        channel=str(fields.get("channel") or "mobile"),
        attraction_id=matched.get("id") if isinstance(matched, dict) else None,
        confidence=float(result.get("confidence") or 0),
        success=matched is not None,
        metadata={
            "filename": file_info.get("filename"),
            "mode": result.get("mode"),
            "matched_attraction_name": matched.get("name") if isinstance(matched, dict) else None,
            "latency_ms": result.get("latency_ms"),
            "strategy": (result.get("metadata") or {}).get("strategy") if isinstance(result.get("metadata"), dict) else None,
        },
    )
    return result
