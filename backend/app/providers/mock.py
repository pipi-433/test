from pydantic import BaseModel

from app.core.config import get_settings


class ProviderStatus(BaseModel):
    provider: str
    status: str


def get_provider_status() -> dict[str, ProviderStatus]:
    settings = get_settings()
    return {
        "llm": ProviderStatus(provider=settings.llm_provider, status="ok"),
        "embedding": ProviderStatus(provider=settings.embedding_provider, status="ok"),
        "vlm": ProviderStatus(provider=settings.vlm_provider, status="ok"),
        "tts": ProviderStatus(provider=settings.tts_provider, status="ok"),
    }
