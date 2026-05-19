import os

from pydantic import BaseModel

from app.core.config import get_settings


class ProviderStatus(BaseModel):
    provider: str
    status: str
    model: str | None = None
    configured: bool = True
    mode: str = "mock"


def _provider_configured(provider: str) -> bool:
    provider = provider.lower()
    if provider == "mock":
        return True
    if provider == "dashscope":
        return bool(os.getenv("DASHSCOPE_API_KEY", "").strip())
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    return False


def _status(provider: str, *, model: str | None = None) -> ProviderStatus:
    configured = _provider_configured(provider)
    return ProviderStatus(
        provider=provider,
        status="ok" if configured else "missing_key",
        model=model or None,
        configured=configured,
        mode="mock" if provider == "mock" else ("real" if configured else "fallback"),
    )


def get_provider_status() -> dict[str, ProviderStatus]:
    settings = get_settings()
    return {
        "llm": _status(settings.llm_provider, model=settings.llm_model),
        "embedding": _status(settings.embedding_provider),
        "vlm": _status(settings.vlm_provider, model=settings.vlm_model),
        "tts": _status(settings.tts_provider),
    }
