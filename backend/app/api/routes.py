from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.providers import ProviderStatus, get_provider_status
from app.services.content_service import (
    get_attraction_or_error,
    get_attractions,
    get_behavior_summary_or_error,
    get_chunks,
)

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
