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
    llm_model: str = ""
    llm_fallback_model: str = ""
    llm_max_output_tokens: int = 300
    llm_enable_search: bool = False
    llm_search_policy: str = "gap_only"
    llm_thinking_mode: str = "off"
    llm_thinking_budget: int | None = None
    llm_timeout_seconds: float = 10
    embedding_provider: str = "mock"
    vlm_provider: str = "mock"
    vlm_model: str = ""
    vlm_timeout_seconds: float = 12
    tts_provider: str = "mock"
    avatar_engine: str = "livetalking"
    avatar_speaker_mode: str = "mock"
    avatar_sidecar_base_url: str = ""
    avatar_sidecar_adapter: str = "readiness"
    avatar_sidecar_speak_path: str = ""
    avatar_sidecar_clip_path: str = ""
    avatar_clip_base_dir: str = ""
    avatar_livetalking_base_url: str = "http://127.0.0.1:8011"
    avatar_livetalking_session_id: str = "0"
    avatar_livetalking_speak_path: str = "/human"
    avatar_livetalking_audio_path: str = "/humanaudio"
    avatar_livetalking_webrtc_path: str = "/offer"
    avatar_tts_cache_enabled: bool = False
    avatar_tts_cache_dir: str = ""
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
        llm_model=os.getenv("LLM_MODEL", ""),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", ""),
        llm_max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "300")),
        llm_enable_search=os.getenv("LLM_ENABLE_SEARCH", "false").strip().lower() in {"1", "true", "yes", "on"},
        llm_search_policy=os.getenv("LLM_SEARCH_POLICY", "gap_only"),
        llm_thinking_mode=os.getenv("LLM_THINKING_MODE", "off"),
        llm_thinking_budget=int(os.getenv("LLM_THINKING_BUDGET", "0") or "0") or None,
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "10")),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "mock"),
        vlm_provider=os.getenv("VLM_PROVIDER", "mock"),
        vlm_model=os.getenv("VLM_MODEL", ""),
        vlm_timeout_seconds=float(os.getenv("VLM_TIMEOUT_SECONDS", "12")),
        tts_provider=os.getenv("TTS_PROVIDER", "mock"),
        avatar_engine=os.getenv("AVATAR_ENGINE", "livetalking"),
        avatar_speaker_mode=os.getenv("AVATAR_SPEAKER_MODE", "mock"),
        avatar_sidecar_base_url=os.getenv("AVATAR_SIDECAR_BASE_URL", ""),
        avatar_sidecar_adapter=os.getenv("AVATAR_SIDECAR_ADAPTER", "readiness"),
        avatar_sidecar_speak_path=os.getenv("AVATAR_SIDECAR_SPEAK_PATH", ""),
        avatar_sidecar_clip_path=os.getenv("AVATAR_SIDECAR_CLIP_PATH", ""),
        avatar_clip_base_dir=os.getenv("AVATAR_CLIP_BASE_DIR", ""),
        avatar_livetalking_base_url=os.getenv("AVATAR_LIVETALKING_BASE_URL", "http://127.0.0.1:8011"),
        avatar_livetalking_session_id=os.getenv("AVATAR_LIVETALKING_SESSION_ID") or "0",
        avatar_livetalking_speak_path=os.getenv("AVATAR_LIVETALKING_SPEAK_PATH") or "/human",
        avatar_livetalking_audio_path=os.getenv("AVATAR_LIVETALKING_AUDIO_PATH") or "/humanaudio",
        avatar_livetalking_webrtc_path=os.getenv("AVATAR_LIVETALKING_WEBRTC_PATH") or "/offer",
        avatar_tts_cache_enabled=os.getenv("AVATAR_TTS_CACHE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
        avatar_tts_cache_dir=os.getenv("AVATAR_TTS_CACHE_DIR", ""),
        avatar_speaker_timeout_seconds=float(os.getenv("AVATAR_SPEAKER_TIMEOUT_SECONDS", "3")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
    )
