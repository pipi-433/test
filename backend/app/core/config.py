import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    service_name: str = "lingjing-guide"
    mode: str = "mock"
    llm_provider: str = "mock"
    embedding_provider: str = "mock"
    vlm_provider: str = "mock"
    tts_provider: str = "mock"
    database_url: str = "sqlite:///./data/app.db"


class ErrorResponse(BaseModel):
    code: str
    message: str
    cause: str
    fix: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        service_name=os.getenv("SERVICE_NAME", "lingjing-guide"),
        mode=os.getenv("APP_MODE", "mock"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "mock"),
        vlm_provider=os.getenv("VLM_PROVIDER", "mock"),
        tts_provider=os.getenv("TTS_PROVIDER", "mock"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
    )
