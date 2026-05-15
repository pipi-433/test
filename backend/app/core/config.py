import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    service_name: str = "lingjing-guide"
    mode: str = "mock"
    llm_provider: str = "mock"
    embedding_provider: str = "mock"
    vlm_provider: str = "mock"
    tts_provider: str = "mock"
    avatar_speaker_mode: str = "mock"
    avatar_sidecar_base_url: str = ""
    avatar_speaker_timeout_seconds: float = 3
    database_url: str = "sqlite:///./data/app.db"

    def sqlite_path(self) -> Path:
        parsed = urlparse(self.database_url)
        if parsed.scheme != "sqlite":
            raise ValueError("Only sqlite DATABASE_URL is supported in mock/local mode.")

        raw_path = unquote(parsed.path)
        if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
            path = Path(raw_path[1:])
        elif raw_path.startswith("/"):
            path = PROJECT_ROOT / raw_path.lstrip("/")
        else:
            path = PROJECT_ROOT / raw_path

        resolved = path.resolve()
        if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
            raise ValueError(f"Database path must stay inside workspace: {resolved}")
        return resolved


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
        avatar_speaker_mode=os.getenv("AVATAR_SPEAKER_MODE", "mock"),
        avatar_sidecar_base_url=os.getenv("AVATAR_SIDECAR_BASE_URL", ""),
        avatar_speaker_timeout_seconds=float(os.getenv("AVATAR_SPEAKER_TIMEOUT_SECONDS", "3")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
    )
