from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.providers import ProviderStatus, get_provider_status

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
