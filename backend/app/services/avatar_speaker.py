from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from fastapi import status

from app.core.config import PROJECT_ROOT, get_settings
from app.core.errors import ApiError


MAX_SPEAK_TEXT_CHARS = 300
ALLOWED_EMOTIONS = {"welcome", "thinking", "speaking", "comforting", "error", "happy", "neutral"}
ALLOWED_SOURCES = {"qa", "route", "vision", "clarification", "feedback", "kiosk", "share", "system", "manual"}
ALLOWED_SIDECAR_ADAPTERS = {"readiness", "http_json"}
DEFAULT_LOCAL_SIDECAR_BASE_URL = "http://127.0.0.1:8282"
DEFAULT_LOCAL_LIVETALKING_BASE_URL = "http://127.0.0.1:8011"
DEFAULT_TTS_CACHE_DIR = PROJECT_ROOT / "external" / "avatar-tts-cache"


def _avatar_engine() -> str:
    settings = get_settings()
    explicit = (settings.avatar_engine or "").strip().lower()
    if explicit:
        return explicit
    mode = (settings.avatar_speaker_mode or "mock").strip().lower()
    if mode == "sidecar":
        return "openavatarchat"
    return mode or "mock"


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


def _check_livetalking_ready(base_url: str, timeout_seconds: float) -> tuple[bool, str | None]:
    # LiveTalking has no dedicated liveness endpoint; its static WebRTC page is
    # the lightest stable local readiness probe.
    last_reason = "livetalking_probe_failed"
    for path in ("webrtcapi.html", "dashboard.html"):
        probe_url = urljoin(base_url.rstrip("/") + "/", path)
        request = Request(probe_url, method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                if 200 <= response.status < 300:
                    return True, None
        except HTTPError as exc:
            last_reason = f"livetalking_probe_http_{exc.code}"
        except URLError as exc:
            return False, f"livetalking_unreachable: {exc.reason}"
        except TimeoutError:
            return False, "livetalking_probe_timeout"
        except OSError as exc:
            return False, f"livetalking_probe_error: {exc}"
    return False, last_reason


def _public_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def _resolve_avatar_sidecar(requested_mode: str, configured_base_url: str, timeout_seconds: float) -> tuple[str, str, bool]:
    mode = (requested_mode or "mock").strip().lower()
    base_url = configured_base_url.strip()
    if base_url:
        return mode, base_url, False

    ready, _reason = _check_sidecar_ready(DEFAULT_LOCAL_SIDECAR_BASE_URL, timeout_seconds)
    if ready:
        return "sidecar", DEFAULT_LOCAL_SIDECAR_BASE_URL, True
    return mode or "mock", "", False


def _resolve_livetalking_sidecar(configured_base_url: str) -> str:
    return configured_base_url.strip() or DEFAULT_LOCAL_LIVETALKING_BASE_URL


def _tts_cache_metadata(text: str) -> dict[str, object]:
    settings = get_settings()
    normalized_text = " ".join(text.split())
    cache_key = sha256(normalized_text.encode("utf-8")).hexdigest()[:32]
    allowed_root = DEFAULT_TTS_CACHE_DIR.resolve()
    raw_cache_dir = (settings.avatar_tts_cache_dir or "").strip()
    cache_dir = Path(raw_cache_dir) if raw_cache_dir else DEFAULT_TTS_CACHE_DIR
    if not cache_dir.is_absolute():
        cache_dir = PROJECT_ROOT / cache_dir
    resolved_dir = cache_dir.resolve()
    path_error = None
    if resolved_dir != allowed_root and not resolved_dir.is_relative_to(allowed_root):
        resolved_dir = allowed_root
        path_error = f"AVATAR_TTS_CACHE_DIR must stay inside {allowed_root}"
    cache_path = resolved_dir / f"{cache_key}.wav"
    enabled = bool(settings.avatar_tts_cache_enabled)
    return {
        "enabled": enabled,
        "cache_key": cache_key,
        "cache_dir": str(resolved_dir),
        "cache_path": str(cache_path),
        "cache_hit": enabled and cache_path.is_file() and path_error is None,
        "path_error": path_error,
        "policy": "disabled_by_default_no_vendor_tts",
    }


def _fetch_sidecar_active_session(base_url: str, timeout_seconds: float) -> tuple[str | None, str | None]:
    sessions_url = urljoin(base_url.rstrip("/") + "/", "lingjing/avatar/sessions")
    request = Request(sessions_url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            if not (200 <= response.status < 300):
                return None, f"sidecar_sessions_status_{response.status}"
            if not raw:
                return None, None
            loaded = json.loads(raw.decode("utf-8"))
            if not isinstance(loaded, dict):
                return None, "sidecar_sessions_payload_not_object"
            active_session_id = loaded.get("active_session_id")
            if isinstance(active_session_id, str) and active_session_id.strip():
                return active_session_id.strip(), None
            sessions = loaded.get("sessions")
            if isinstance(sessions, list):
                for item in sessions:
                    if isinstance(item, dict):
                        session_id = item.get("session_id") or item.get("id")
                        if isinstance(session_id, str) and session_id.strip():
                            return session_id.strip(), None
            return None, None
    except HTTPError as exc:
        return None, f"sidecar_sessions_http_{exc.code}"
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return None, f"sidecar_sessions_parse_error: {exc}"
    except URLError as exc:
        return None, f"sidecar_sessions_unreachable: {exc.reason}"
    except TimeoutError:
        return None, "sidecar_sessions_timeout"
    except OSError as exc:
        return None, f"sidecar_sessions_error: {exc}"


def get_avatar_status() -> dict[str, object]:
    settings = get_settings()
    engine = _avatar_engine()
    if engine == "livetalking":
        base_url = _resolve_livetalking_sidecar(settings.avatar_livetalking_base_url)
        ready, reason = _check_livetalking_ready(base_url, settings.avatar_speaker_timeout_seconds)
        session_id = (settings.avatar_livetalking_session_id or "0").strip() or "0"
        speaking_status = None
        if ready:
            speaking_status = _fetch_livetalking_speaking_status(
                base_url=base_url,
                path="/is_speaking",
                timeout_seconds=settings.avatar_speaker_timeout_seconds,
                session_id=session_id,
            )
        return {
            "mode": "livetalking",
            "engine": "livetalking",
            "adapter": "livetalking_http",
            "sidecar_ready": ready,
            "sidecar_url": _public_base_url(base_url) if ready else "",
            "active_session_id": session_id if ready else None,
            "fallback_available": True,
            "message": "LiveTalking sidecar presentation is ready." if ready else "LiveTalking sidecar presentation is not ready.",
            "fallback_reason": None if ready else reason,
            "session_status": speaking_status,
        }

    requested_mode = (settings.avatar_speaker_mode or "mock").strip().lower()
    if engine == "openavatarchat" and (settings.avatar_engine or "").strip():
        requested_mode = "sidecar"
    timeout_seconds = settings.avatar_speaker_timeout_seconds
    effective_mode, base_url, auto_detected = _resolve_avatar_sidecar(
        requested_mode,
        settings.avatar_sidecar_base_url,
        timeout_seconds,
    )

    if effective_mode != "sidecar" or not base_url:
        return {
            "mode": effective_mode or "mock",
            "engine": engine,
            "adapter": "mock",
            "sidecar_ready": False,
            "sidecar_url": "",
            "active_session_id": None,
            "fallback_available": True,
            "message": "mock avatar presentation is available.",
            "fallback_reason": None if requested_mode != "sidecar" else "AVATAR_SIDECAR_BASE_URL is empty",
        }

    ready, reason = _check_sidecar_ready(base_url, timeout_seconds)
    active_session_id = None
    session_reason = None
    if ready:
        active_session_id, session_reason = _fetch_sidecar_active_session(base_url, timeout_seconds)

    return {
        "mode": "sidecar",
        "engine": "openavatarchat",
        "adapter": settings.avatar_sidecar_adapter,
        "sidecar_ready": ready,
        "sidecar_url": _public_base_url(base_url) if ready else "",
        "active_session_id": active_session_id,
        "fallback_available": True,
        "message": "sidecar avatar presentation is ready." if ready else "sidecar avatar presentation is not ready.",
        "fallback_reason": None if ready else reason,
        "session_status": session_reason,
        "auto_detected": auto_detected,
    }


def _sidecar_speak_url(base_url: str, speak_path: str) -> str:
    if speak_path.startswith("http://") or speak_path.startswith("https://"):
        return speak_path
    if not speak_path:
        raise ValueError("AVATAR_SIDECAR_SPEAK_PATH is empty")
    return urljoin(base_url.rstrip("/") + "/", speak_path.lstrip("/"))


def _join_sidecar_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path:
        raise ValueError("sidecar path is empty")
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _fetch_livetalking_speaking_status(
    *,
    base_url: str,
    path: str,
    timeout_seconds: float,
    session_id: str,
) -> str | None:
    payload = {"sessionid": session_id}
    request = Request(
        _join_sidecar_url(base_url, path),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            if not raw:
                return None
            loaded = json.loads(raw.decode("utf-8"))
            if isinstance(loaded, dict):
                if loaded.get("code") == 0:
                    return f"is_speaking:{loaded.get('data')}"
                return f"is_speaking_unavailable:{loaded.get('msg')}"
            return "is_speaking_payload_not_object"
    except Exception as exc:  # status must not make the primary API fragile
        return f"is_speaking_probe_failed:{exc}"


def _livetalking_session_id(session_id: str | None) -> str:
    settings = get_settings()
    candidate = (session_id or "").strip() or (settings.avatar_livetalking_session_id or "").strip()
    return candidate or "0"


def _post_livetalking_text(
    *,
    base_url: str,
    path: str,
    timeout_seconds: float,
    text: str,
    interrupt: bool,
    session_id: str | None = None,
) -> tuple[bool, str | None, dict[str, object]]:
    try:
        speak_url = _join_sidecar_url(base_url, path)
    except ValueError as exc:
        return False, str(exc), {}

    lt_session_id = _livetalking_session_id(session_id)
    payload = {
        "sessionid": lt_session_id,
        "type": "echo",
        "text": text,
        "interrupt": interrupt,
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
            if parsed.get("code") not in (None, 0):
                return False, str(parsed.get("msg") or "livetalking_text_rejected"), parsed
            if 200 <= response.status < 300:
                return True, None, parsed
            return False, f"livetalking_speak_status_{response.status}", parsed
    except HTTPError as exc:
        return False, f"livetalking_speak_http_{exc.code}", {}
    except URLError as exc:
        return False, f"livetalking_speak_unreachable: {exc.reason}", {}
    except TimeoutError:
        return False, "livetalking_speak_timeout", {}
    except OSError as exc:
        return False, f"livetalking_speak_error: {exc}", {}


def _post_livetalking_interrupt(
    *,
    base_url: str,
    timeout_seconds: float,
    session_id: str,
) -> tuple[bool, str | None, dict[str, object]]:
    request = Request(
        _join_sidecar_url(base_url, "/interrupt_talk"),
        data=json.dumps({"sessionid": session_id}).encode("utf-8"),
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
            if parsed.get("code") not in (None, 0):
                return False, str(parsed.get("msg") or "livetalking_interrupt_rejected"), parsed
            if 200 <= response.status < 300:
                return True, None, parsed
            return False, f"livetalking_interrupt_status_{response.status}", parsed
    except HTTPError as exc:
        return False, f"livetalking_interrupt_http_{exc.code}", {}
    except URLError as exc:
        return False, f"livetalking_interrupt_unreachable: {exc.reason}", {}
    except TimeoutError:
        return False, "livetalking_interrupt_timeout", {}
    except OSError as exc:
        return False, f"livetalking_interrupt_error: {exc}", {}


def _post_sidecar_text(
    *,
    base_url: str,
    speak_path: str,
    timeout_seconds: float,
    text: str,
    emotion: str,
    source: str,
    interrupt: bool,
    session_id: str | None = None,
) -> tuple[bool, str | None, dict[str, object]]:
    try:
        speak_url = _sidecar_speak_url(base_url, speak_path)
    except ValueError as exc:
        return False, str(exc), {}

    # The LiteAvatar trusted endpoint is a presentation-layer bridge, so keep
    # business provenance in Lingjing metadata and send only the small source
    # vocabulary the sidecar accepts.
    sidecar_source = source if source in {"route", "vision", "kiosk", "share", "system"} else "system"
    payload = {
        "text": text,
        "emotion": emotion,
        "source": sidecar_source,
        "interrupt": interrupt,
        "policy": "trusted_backend_text_only",
        "lingjing_source": source,
    }
    if session_id:
        payload["session_id"] = session_id
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
    session_id: str | None = None,
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
    engine = _avatar_engine()
    requested_mode = (settings.avatar_speaker_mode or "mock").strip().lower()
    if engine == "openavatarchat" and (settings.avatar_engine or "").strip():
        requested_mode = "sidecar"
    effective_mode, base_url, auto_detected = _resolve_avatar_sidecar(
        requested_mode,
        settings.avatar_sidecar_base_url,
        settings.avatar_speaker_timeout_seconds,
    )
    adapter = (settings.avatar_sidecar_adapter or "readiness").strip().lower()
    mode = "mock"
    fallback_reason = None
    adapter_metadata: dict[str, object] = {}
    started_at = perf_counter()

    if engine == "livetalking":
        lt_base_url = _resolve_livetalking_sidecar(settings.avatar_livetalking_base_url)
        ready, reason = _check_livetalking_ready(lt_base_url, settings.avatar_speaker_timeout_seconds)
        if ready:
            ok, inject_reason, response_metadata = _post_livetalking_text(
                base_url=lt_base_url,
                path=settings.avatar_livetalking_speak_path,
                timeout_seconds=settings.avatar_speaker_timeout_seconds,
                text=normalized_text,
                interrupt=interrupt,
                session_id=session_id,
            )
            adapter_metadata = {
                "adapter": "livetalking_http_echo",
                "engine": "livetalking",
                "sidecar_url": _public_base_url(lt_base_url),
                "session_id": _livetalking_session_id(session_id),
                "sidecar_response": response_metadata,
                "llm_bypassed": True,
                "livetalking_type": "echo",
            }
            if ok:
                mode = "livetalking"
                effective_mode = "sidecar"
                base_url = lt_base_url
            else:
                fallback_reason = inject_reason or "livetalking_text_injection_failed"
        else:
            fallback_reason = reason or "livetalking_not_ready"
    elif effective_mode == "sidecar":
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
                        session_id=session_id,
                    )
                    adapter_metadata = {
                        "adapter": "http_json",
                        "sidecar_url": _public_base_url(base_url),
                        "auto_detected": auto_detected,
                        "session_id": session_id,
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
            "engine": engine,
            "effective_mode": effective_mode,
            "emotion": emotion,
            "source": source,
            "interrupt": interrupt,
            "text_chars": len(normalized_text),
            "session_id": session_id,
            "latency_ms": latency_ms,
            "policy": "trusted_backend_text_only",
            "tts_cache": _tts_cache_metadata(normalized_text),
            **adapter_metadata,
        },
    }


def warmup_avatar_speech(
    *,
    text: str = "您好。",
    source: str = "system",
    interrupt: bool = False,
    session_id: str | None = None,
    silent: bool = False,
) -> dict[str, object]:
    warmup_text = " ".join((text or "").split()) or "您好。"
    warmup_source = source if source in ALLOWED_SOURCES else "system"
    result = enqueue_avatar_speech(
        text=warmup_text[:MAX_SPEAK_TEXT_CHARS],
        emotion="neutral",
        source=warmup_source,
        interrupt=interrupt,
        session_id=session_id,
    )
    metadata = dict(result.get("metadata") or {})
    metadata.update(
        {
            "warmup": True,
            "silent_requested": silent,
            "llm_bypassed": True,
            "policy": "presentation_warmup_only",
        }
    )
    return {
        **result,
        "message": "数字人表现层预热请求已处理",
        "metadata": metadata,
    }


def stop_avatar_speech(*, session_id: str | None = None) -> dict[str, object]:
    settings = get_settings()
    engine = _avatar_engine()
    started_at = perf_counter()
    mode = "mock"
    accepted = True
    fallback_reason = None
    metadata: dict[str, object] = {
        "engine": engine,
        "session_id": session_id,
        "policy": "presentation_interrupt_only",
    }

    if engine == "livetalking":
        lt_base_url = _resolve_livetalking_sidecar(settings.avatar_livetalking_base_url)
        ready, reason = _check_livetalking_ready(lt_base_url, settings.avatar_speaker_timeout_seconds)
        lt_session_id = _livetalking_session_id(session_id)
        metadata.update(
            {
                "adapter": "livetalking_http_interrupt",
                "sidecar_url": _public_base_url(lt_base_url) if ready else "",
                "session_id": lt_session_id,
                "llm_bypassed": True,
            }
        )
        if ready:
            ok, interrupt_reason, sidecar_response = _post_livetalking_interrupt(
                base_url=lt_base_url,
                timeout_seconds=settings.avatar_speaker_timeout_seconds,
                session_id=lt_session_id,
            )
            metadata["sidecar_response"] = sidecar_response
            if ok:
                mode = "livetalking"
            else:
                fallback_reason = interrupt_reason or "livetalking_interrupt_failed"
        else:
            fallback_reason = reason or "livetalking_not_ready"
    elif engine == "openavatarchat":
        fallback_reason = "openavatarchat_interrupt_not_configured"

    metadata["latency_ms"] = round((perf_counter() - started_at) * 1000)
    return {
        "mode": mode,
        "accepted": accepted,
        "message": "avatar playback stop requested",
        "fallback_reason": fallback_reason,
        "metadata": metadata,
    }
