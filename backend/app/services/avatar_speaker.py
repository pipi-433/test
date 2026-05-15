from __future__ import annotations

from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from fastapi import status

from app.core.config import get_settings
from app.core.errors import ApiError


MAX_SPEAK_TEXT_CHARS = 300
ALLOWED_EMOTIONS = {"welcome", "thinking", "speaking", "comforting", "error", "happy", "neutral"}
ALLOWED_SOURCES = {"qa", "route", "vision", "clarification", "feedback", "kiosk", "share", "system"}


def _check_sidecar_ready(base_url: str, timeout_seconds: float) -> tuple[bool, str | None]:
    readiness_url = urljoin(base_url.rstrip("/") + "/", "readiness")
    request = Request(readiness_url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if 200 <= response.status < 300:
                return True, None
            return False, f"sidecar_readiness_status_{response.status}"
    except HTTPError as exc:
        return False, f"sidecar_readiness_http_{exc.code}"
    except URLError as exc:
        return False, f"sidecar_unreachable: {exc.reason}"
    except TimeoutError:
        return False, "sidecar_readiness_timeout"
    except OSError as exc:
        return False, f"sidecar_readiness_error: {exc}"


def enqueue_avatar_speech(
    *,
    text: str,
    emotion: str = "happy",
    source: str = "system",
    interrupt: bool = True,
) -> dict[str, object]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        raise ApiError(
            code="AVATAR_SPEAK_EMPTY_TEXT",
            message="请提供需要数字人播报的文本。",
            cause="POST /api/avatar/speak received empty text.",
            fix="传入灵境后端已生成的可信短文本，长度不超过 300 字。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if len(normalized_text) > MAX_SPEAK_TEXT_CHARS:
        raise ApiError(
            code="AVATAR_SPEAK_TEXT_TOO_LONG",
            message="数字人播报文本过长，请先生成更短的讲解摘要。",
            cause=f"Avatar speak text length is {len(normalized_text)}, limit is {MAX_SPEAK_TEXT_CHARS}.",
            fix="只传入 QA、路线、识景等灵境后端产出的 300 字以内可信摘要。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if emotion not in ALLOWED_EMOTIONS:
        raise ApiError(
            code="AVATAR_SPEAK_INVALID_EMOTION",
            message="数字人表情状态不支持。",
            cause=f"Unsupported avatar emotion: {emotion}",
            fix=f"emotion 可选值：{', '.join(sorted(ALLOWED_EMOTIONS))}。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if source not in ALLOWED_SOURCES:
        raise ApiError(
            code="AVATAR_SPEAK_INVALID_SOURCE",
            message="数字人播报来源不支持。",
            cause=f"Unsupported avatar speech source: {source}",
            fix=f"source 可选值：{', '.join(sorted(ALLOWED_SOURCES))}。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    settings = get_settings()
    requested_mode = (settings.avatar_speaker_mode or "mock").strip().lower()
    mode = "mock"
    fallback_reason = None
    started_at = perf_counter()

    if requested_mode == "sidecar":
        base_url = settings.avatar_sidecar_base_url.strip()
        if not base_url:
            fallback_reason = "AVATAR_SIDECAR_BASE_URL is empty; using mock speaker queue."
        else:
            ready, reason = _check_sidecar_ready(base_url, settings.avatar_speaker_timeout_seconds)
            if ready:
                # OpenAvatarChat 0.6.x exposes health/WebUI/WebRTC flows, but this project has
                # not yet installed a stable trusted-text injection endpoint. Keep the API
                # accepted and fall back until the adapter is explicitly implemented.
                fallback_reason = "sidecar is ready, but trusted text injection adapter is not implemented."
            else:
                fallback_reason = reason or "sidecar_not_ready"

    latency_ms = round((perf_counter() - started_at) * 1000)
    return {
        "mode": mode,
        "accepted": True,
        "message": "已进入数字人播报队列",
        "fallback_reason": fallback_reason,
        "metadata": {
            "requested_mode": requested_mode,
            "emotion": emotion,
            "source": source,
            "interrupt": interrupt,
            "text_chars": len(normalized_text),
            "latency_ms": latency_ms,
            "policy": "trusted_backend_text_only",
        },
    }
