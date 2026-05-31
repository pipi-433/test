from __future__ import annotations

import json
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.services.avatar_speaker import (
    _avatar_engine,
    _check_livetalking_ready,
    _check_sidecar_ready,
    _public_base_url,
    _resolve_avatar_sidecar,
    _resolve_livetalking_sidecar,
)


ALLOWED_WEBRTC_OFFER_TYPES = {"offer", "ice-candidate"}
WEBRTC_SIGNALING_TIMEOUT_SECONDS = 30


def _webrtc_offer_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def proxy_avatar_webrtc_offer(payload: dict[str, object]) -> dict[str, object]:
    started_at = perf_counter()
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
    offer_type = str(payload.get("type") or "").strip()
    webrtc_id = str(payload.get("webrtc_id") or payload.get("client_id") or "").strip()

    if offer_type not in ALLOWED_WEBRTC_OFFER_TYPES:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "unsupported WebRTC signaling type",
            "fallback_reason": f"unsupported_webrtc_type:{offer_type or 'empty'}",
            "metadata": {"allowed_types": sorted(ALLOWED_WEBRTC_OFFER_TYPES)},
        }
    if not webrtc_id:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "webrtc_id is required",
            "fallback_reason": "missing_webrtc_id",
            "metadata": {},
        }
    if engine == "livetalking":
        lt_base_url = _resolve_livetalking_sidecar(settings.avatar_livetalking_base_url)
        ready, reason = _check_livetalking_ready(lt_base_url, settings.avatar_speaker_timeout_seconds)
        if not ready:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking sidecar is not ready",
                "fallback_reason": reason or "livetalking_not_ready",
                "metadata": {"webrtc_id": webrtc_id},
            }
        sidecar_payload = dict(payload)
        body = json.dumps(sidecar_payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            _webrtc_offer_url(lt_base_url, settings.avatar_livetalking_webrtc_path),
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            signaling_timeout = max(settings.avatar_speaker_timeout_seconds, WEBRTC_SIGNALING_TIMEOUT_SECONDS)
            with urlopen(request, timeout=signaling_timeout) as response:
                raw = response.read()
                parsed: dict[str, object] = {}
                if raw:
                    loaded = json.loads(raw.decode("utf-8"))
                    if isinstance(loaded, dict):
                        parsed = loaded
                if not parsed.get("sdp") or not parsed.get("type"):
                    return {
                        "accepted": False,
                        "mode": "mock",
                        "engine": "livetalking",
                        "message": "LiveTalking WebRTC signaling returned incomplete payload",
                        "fallback_reason": "livetalking_webrtc_incomplete_response",
                        "metadata": {"webrtc_id": webrtc_id, "sidecar_response": parsed},
                    }
                parsed.update(
                    {
                        "accepted": True,
                        "mode": "livetalking",
                        "engine": "livetalking",
                        "sidecar_url": _public_base_url(lt_base_url),
                        "webrtc_id": webrtc_id,
                        "latency_ms": round((perf_counter() - started_at) * 1000),
                        "adapter": "livetalking_webrtc_proxy",
                    }
                )
                return parsed
        except HTTPError as exc:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking WebRTC signaling failed",
                "fallback_reason": f"livetalking_webrtc_http_{exc.code}",
                "metadata": {"webrtc_id": webrtc_id},
            }
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking WebRTC signaling returned invalid payload",
                "fallback_reason": f"livetalking_webrtc_parse_error:{exc}",
                "metadata": {"webrtc_id": webrtc_id},
            }
        except URLError as exc:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking sidecar is unreachable",
                "fallback_reason": f"livetalking_webrtc_unreachable:{exc.reason}",
                "metadata": {"webrtc_id": webrtc_id},
            }
        except TimeoutError:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking WebRTC signaling timed out",
                "fallback_reason": "livetalking_webrtc_timeout",
                "metadata": {"webrtc_id": webrtc_id},
            }
        except OSError as exc:
            return {
                "accepted": False,
                "mode": "mock",
                "engine": "livetalking",
                "message": "LiveTalking WebRTC signaling failed",
                "fallback_reason": f"livetalking_webrtc_error:{exc}",
                "metadata": {"webrtc_id": webrtc_id},
            }

    if effective_mode != "sidecar" or not base_url:
        return {
            "accepted": False,
            "mode": effective_mode or "mock",
            "message": "avatar sidecar is not configured",
            "fallback_reason": None if requested_mode != "sidecar" else "AVATAR_SIDECAR_BASE_URL is empty",
            "metadata": {"webrtc_id": webrtc_id},
        }

    ready, reason = _check_sidecar_ready(base_url, settings.avatar_speaker_timeout_seconds)
    if not ready:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar sidecar is not ready",
            "fallback_reason": reason or "sidecar_not_ready",
            "metadata": {"webrtc_id": webrtc_id},
        }

    sidecar_payload = dict(payload)
    sidecar_payload["webrtc_id"] = webrtc_id
    sidecar_payload.pop("client_id", None)
    body = json.dumps(sidecar_payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        _webrtc_offer_url(base_url, "webrtc/offer"),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        signaling_timeout = max(settings.avatar_speaker_timeout_seconds, WEBRTC_SIGNALING_TIMEOUT_SECONDS)
        with urlopen(request, timeout=signaling_timeout) as response:
            raw = response.read()
            parsed: dict[str, object] = {}
            if raw:
                loaded = json.loads(raw.decode("utf-8"))
                if isinstance(loaded, dict):
                    parsed = loaded
            if parsed.get("status") == "failed":
                return {
                    "accepted": False,
                    "mode": "sidecar",
                    "message": "avatar WebRTC signaling was rejected by sidecar",
                    "fallback_reason": str((parsed.get("meta") or {}).get("error") if isinstance(parsed.get("meta"), dict) else "sidecar_webrtc_rejected"),
                    "metadata": {"webrtc_id": webrtc_id, "sidecar_response": parsed},
                }
            parsed.update(
                {
                    "accepted": True,
                    "mode": "sidecar",
                    "sidecar_url": _public_base_url(base_url),
                    "webrtc_id": webrtc_id,
                    "latency_ms": round((perf_counter() - started_at) * 1000),
                    "auto_detected": auto_detected,
                }
            )
            return parsed
    except HTTPError as exc:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar WebRTC signaling failed",
            "fallback_reason": f"sidecar_webrtc_http_{exc.code}",
            "metadata": {"webrtc_id": webrtc_id},
        }
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar WebRTC signaling returned invalid payload",
            "fallback_reason": f"sidecar_webrtc_parse_error:{exc}",
            "metadata": {"webrtc_id": webrtc_id},
        }
    except URLError as exc:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar sidecar is unreachable",
            "fallback_reason": f"sidecar_webrtc_unreachable:{exc.reason}",
            "metadata": {"webrtc_id": webrtc_id},
        }
    except TimeoutError:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar WebRTC signaling timed out",
            "fallback_reason": "sidecar_webrtc_timeout",
            "metadata": {"webrtc_id": webrtc_id},
        }
    except OSError as exc:
        return {
            "accepted": False,
            "mode": "mock",
            "message": "avatar WebRTC signaling failed",
            "fallback_reason": f"sidecar_webrtc_error:{exc}",
            "metadata": {"webrtc_id": webrtc_id},
        }
