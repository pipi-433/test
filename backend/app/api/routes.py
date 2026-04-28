from typing import Any

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

from app.core.errors import ApiError
from app.core.config import get_settings
from app.providers import ProviderStatus, get_provider_status
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


class RouteRecommendRequest(BaseModel):
    theme: str | None = None
    time_budget_minutes: int | None = 240
    group_type: str | None = None
    intensity: str | None = None
    interests: list[str] | None = None
    start_attraction_id: str | None = None
    avoid_crowd: bool = True
    crowd_tolerance: str = "medium"


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
    return answer_question(
        question=question,
        attraction_id=payload.attraction_id,
        visitor_profile=payload.visitor_profile,
        top_k=top_k,
    )


@router.get("/routes/themes")
def route_themes() -> dict[str, object]:
    items = route_theme_options()
    return {"items": items, "count": len(items)}


@router.get("/crowd/snapshot")
def crowd_snapshot() -> dict[str, object]:
    return get_crowd_snapshot()


@router.post("/routes/recommend")
def routes_recommend(payload: RouteRecommendRequest) -> dict[str, object]:
    return recommend_route(
        theme=payload.theme,
        time_budget_minutes=payload.time_budget_minutes,
        group_type=payload.group_type,
        intensity=payload.intensity,
        interests=payload.interests,
        start_attraction_id=payload.start_attraction_id,
        avoid_crowd=payload.avoid_crowd,
        crowd_tolerance=payload.crowd_tolerance,
    )


@router.get("/routes/{route_id}/share")
def route_share(route_id: str) -> dict[str, object]:
    return get_route_share(route_id)


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
    return recognize_image_mock(
        filename=str(file_info.get("filename") or ""),
        hint=str(fields.get("hint") or ""),
        text_hint=str(fields.get("text_hint") or ""),
        file_size=file_size,
    )
