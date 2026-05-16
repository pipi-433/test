from __future__ import annotations

import json
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from fastapi import status

from app.core.config import get_settings
from app.core.errors import ApiError


MAX_SPEAK_TEXT_CHARS = 300
ALLOWED_EMOTIONS = {"welcome", "thinking", "speaking", "comforting", "error", "happy", "neutral"}
ALLOWED_SOURCES = {"qa", "route", "vision", "clarification", "feedback", "kiosk", "share", "system"}
ALLOWED_SIDECAR_ADAPTERS = {"readiness", "http_json"}


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


def _public_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def _sidecar_speak_url(base_url: str, speak_path: str) -> str:
    if speak_path.startswith("http://") or speak_path.startswith("https://"):
        return speak_path
    if not speak_path:
        raise ValueError("AVATAR_SIDECAR_SPEAK_PATH is empty")
    return urljoin(base_url.rstrip("/") + "/", speak_path.lstrip("/"))


def _post_sidecar_text(
    *,
    base_url: str,
    speak_path: str,
    timeout_seconds: float,
    text: str,
    emotion: str,
    source: str,
    interrupt: bool,
) -> tuple[bool, str | None, dict[str, object]]:
    try:
        speak_url = _sidecar_speak_url(base_url, speak_path)
    except ValueError as exc:
        return False, str(exc), {}

    payload = {
        "text": text,
        "emotion": emotion,
        "source": source,
        "interrupt": interrupt,
        "policy": "trusted_backend_text_only",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        speak_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            parsed: dict[str, object] = {}
            if raw:
                try:
                    loaded = json.loads(raw.decode("utf-8"))
                    if isinstance(loaded, dict):
                        parsed = loaded
                except json.JSONDecodeError:
                    parsed = {"raw_response": raw.decode("utf-8", errors="replace")[:200]}
            accepted = parsed.get("accepted")
            if accepted is False:
                reason = str(parsed.get("message") or parsed.get("error") or "sidecar_text_rejected")
                return False, reason, parsed
            if 200 <= response.status < 300:
                return True, None, parsed
            return False, f"sidecar_speak_status_{response.status}", parsed
    except HTTPError as exc:
        return False, f"sidecar_speak_http_{exc.code}", {}
    except URLError as exc:
        return False, f"sidecar_speak_unreachable: {exc.reason}", {}
    except TimeoutError:
        return False, "sidecar_speak_timeout", {}
    except OSError as exc:
        return False, f"sidecar_speak_error: {exc}", {}


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
    adapter = (settings.avatar_sidecar_adapter or "readiness").strip().lower()
    mode = "mock"
    fallback_reason = None
    adapter_metadata: dict[str, object] = {}
    started_at = perf_counter()

    if requested_mode == "sidecar":
        base_url = settings.avatar_sidecar_base_url.strip()
        if not base_url:
            fallback_reason = "AVATAR_SIDECAR_BASE_URL is empty; using mock speaker queue."
        elif adapter not in ALLOWED_SIDECAR_ADAPTERS:
            fallback_reason = (
                f"Unsupported AVATAR_SIDECAR_ADAPTER '{adapter}'; "
                f"supported values: {', '.join(sorted(ALLOWED_SIDECAR_ADAPTERS))}."
            )
        else:
            ready, reason = _check_sidecar_ready(base_url, settings.avatar_speaker_timeout_seconds)
            if ready:
                if adapter == "http_json":
                    ok, inject_reason, response_metadata = _post_sidecar_text(
                        base_url=base_url,
                        speak_path=settings.avatar_sidecar_speak_path.strip(),
                        timeout_seconds=settings.avatar_speaker_timeout_seconds,
                        text=normalized_text,
                        emotion=emotion,
                        source=source,
                        interrupt=interrupt,
                    )
                    adapter_metadata = {
                        "adapter": "http_json",
                        "sidecar_url": _public_base_url(base_url),
                        "sidecar_response": response_metadata,
                    }
                    if ok:
                        mode = "sidecar"
                    else:
                        fallback_reason = inject_reason or "sidecar_text_injection_failed"
                else:
                    # OpenAvatarChat 0.6.x exposes health/WebUI/WebRTC flows. Its WebUI
                    # SendHumanText message is user input for the chat engine, not a trusted
                    # "speak this backend answer" endpoint; mapping to it would re-enter LLM.
                    fallback_reason = (
                        "sidecar is ready, but no trusted text speaker bridge is configured; "
                        "using mock speaker queue."
                    )
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
            **adapter_metadata,
        },
    }
