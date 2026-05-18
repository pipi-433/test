from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from app.core.config import PROJECT_ROOT, get_settings
from app.services.avatar_speaker import _check_sidecar_ready, _resolve_avatar_sidecar


ALLOWED_CLIP_SOURCES = {"route", "attraction", "vision", "kiosk", "admin", "demo"}
CLIP_POLICY = "preset_clip_whitelist_only"
DEFAULT_CLIP_BASE_DIR = PROJECT_ROOT / "external" / "avatar-clips"


@dataclass(frozen=True)
class PresetAvatarClip:
    clip_id: str
    title: str
    attraction_name: str
    duration_seconds: int
    text_preview: str
    audio_filename: str
    source_note: str


PRESET_CLIPS: dict[str, PresetAvatarClip] = {
    "lingshan_buddha_intro_45s": PresetAvatarClip(
        clip_id="lingshan_buddha_intro_45s",
        title="灵山大佛介绍",
        attraction_name="灵山大佛",
        duration_seconds=45,
        text_preview="灵山大佛是灵山胜境的核心地标，适合在中轴线游览中作为重点讲解点。",
        audio_filename="lingshan_buddha_intro_45s.wav",
        source_note="演示用预存讲解 clip，音频文件需放在 external/avatar-clips。",
    ),
    "fan_gong_intro_45s": PresetAvatarClip(
        clip_id="fan_gong_intro_45s",
        title="灵山梵宫介绍",
        attraction_name="灵山梵宫",
        duration_seconds=45,
        text_preview="灵山梵宫以佛教文化展示和艺术空间见长，适合作为室内文化讲解片段。",
        audio_filename="fan_gong_intro_45s.wav",
        source_note="演示用预存讲解 clip，音频文件需放在 external/avatar-clips。",
    ),
    "jiulong_guanyu_intro_30s": PresetAvatarClip(
        clip_id="jiulong_guanyu_intro_30s",
        title="九龙灌浴介绍",
        attraction_name="九龙灌浴",
        duration_seconds=30,
        text_preview="九龙灌浴是灵山胜境标志性动态景观，适合在演出提醒和识景后触发短讲解。",
        audio_filename="jiulong_guanyu_intro_30s.wav",
        source_note="演示用预存讲解 clip，音频文件需放在 external/avatar-clips。",
    ),
}


def _public_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def _clip_base_dir() -> tuple[Path, str | None]:
    settings = get_settings()
    allowed_root = DEFAULT_CLIP_BASE_DIR.resolve()
    raw_base_dir = settings.avatar_clip_base_dir.strip()
    base_dir = Path(raw_base_dir) if raw_base_dir else DEFAULT_CLIP_BASE_DIR
    if not base_dir.is_absolute():
        base_dir = PROJECT_ROOT / base_dir
    resolved = base_dir.resolve()
    if resolved != allowed_root and not resolved.is_relative_to(allowed_root):
        return allowed_root, f"AVATAR_CLIP_BASE_DIR must stay inside {allowed_root}"
    return resolved, None


def _clip_audio_path(clip: PresetAvatarClip, base_dir: Path) -> tuple[Path, str | None]:
    candidate = (base_dir / clip.audio_filename).resolve()
    if not candidate.is_relative_to(base_dir):
        return base_dir / clip.audio_filename, "clip audio path escaped configured base directory"
    return candidate, None


def _clip_metadata(clip: PresetAvatarClip, audio_path: Path, *, audio_path_error: str | None) -> dict[str, object]:
    return {
        "clip_id": clip.clip_id,
        "title": clip.title,
        "attraction_name": clip.attraction_name,
        "duration_seconds": clip.duration_seconds,
        "text_preview": clip.text_preview,
        "audio_path": str(audio_path),
        "audio_exists": audio_path.is_file() if not audio_path_error else False,
        "source_note": clip.source_note,
        "policy": CLIP_POLICY,
        "audio_path_error": audio_path_error,
    }


def _sidecar_clip_url(base_url: str, clip_path: str) -> str:
    if clip_path.startswith("http://") or clip_path.startswith("https://"):
        return clip_path
    if not clip_path:
        raise ValueError("AVATAR_SIDECAR_CLIP_PATH is empty")
    return urljoin(base_url.rstrip("/") + "/", clip_path.lstrip("/"))


def _post_sidecar_clip(
    *,
    base_url: str,
    clip_path: str,
    timeout_seconds: float,
    clip: PresetAvatarClip,
    audio_path: Path,
    source: str,
    interrupt: bool,
) -> tuple[bool, str | None, dict[str, object]]:
    try:
        sidecar_url = _sidecar_clip_url(base_url, clip_path)
    except ValueError as exc:
        return False, str(exc), {}

    payload = {
        "clip_id": clip.clip_id,
        "title": clip.title,
        "attraction_name": clip.attraction_name,
        "duration_seconds": clip.duration_seconds,
        "audio_path": str(audio_path),
        "source": source,
        "interrupt": interrupt,
        "policy": CLIP_POLICY,
        "llm_bypassed": True,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        sidecar_url,
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
            if parsed.get("accepted") is False:
                reason = str(parsed.get("message") or parsed.get("error") or "sidecar_clip_rejected")
                return False, reason, parsed
            if 200 <= response.status < 300:
                return True, None, parsed
            return False, f"sidecar_clip_status_{response.status}", parsed
    except HTTPError as exc:
        return False, f"sidecar_clip_http_{exc.code}", {}
    except URLError as exc:
        return False, f"sidecar_clip_unreachable: {exc.reason}", {}
    except TimeoutError:
        return False, "sidecar_clip_timeout", {}
    except OSError as exc:
        return False, f"sidecar_clip_error: {exc}", {}


def play_avatar_clip(
    *,
    clip_id: str,
    source: str = "demo",
    interrupt: bool = True,
) -> dict[str, object]:
    normalized_clip_id = clip_id.strip()
    normalized_source = source.strip().lower()
    started_at = perf_counter()

    if normalized_source not in ALLOWED_CLIP_SOURCES:
        return {
            "mode": "mock",
            "accepted": False,
            "message": "预存讲解来源不受支持",
            "fallback_reason": "invalid_clip_source",
            "metadata": {
                "clip_id": normalized_clip_id,
                "source": source,
                "allowed_sources": sorted(ALLOWED_CLIP_SOURCES),
                "policy": CLIP_POLICY,
            },
        }

    clip = PRESET_CLIPS.get(normalized_clip_id)
    if clip is None:
        return {
            "mode": "mock",
            "accepted": False,
            "message": "未知的预存讲解 clip_id",
            "fallback_reason": "unknown_clip_id",
            "metadata": {
                "clip_id": normalized_clip_id,
                "known_clip_ids": sorted(PRESET_CLIPS),
                "source": normalized_source,
                "policy": CLIP_POLICY,
            },
        }

    base_dir, base_dir_error = _clip_base_dir()
    audio_path, audio_path_error = _clip_audio_path(clip, base_dir)
    path_error = base_dir_error or audio_path_error
    metadata = _clip_metadata(clip, audio_path, audio_path_error=path_error)
    metadata.update(
        {
            "requested_source": normalized_source,
            "interrupt": interrupt,
            "clip_sidecar_adapter_pending": False,
            "llm_bypassed": True,
        }
    )

    settings = get_settings()
    requested_mode = (settings.avatar_speaker_mode or "mock").strip().lower()
    effective_mode, base_url, auto_detected = _resolve_avatar_sidecar(
        requested_mode,
        settings.avatar_sidecar_base_url,
        settings.avatar_speaker_timeout_seconds,
    )
    fallback_reason = None
    mode = "mock"

    if effective_mode == "sidecar":
        clip_path = settings.avatar_sidecar_clip_path.strip()
        if path_error:
            fallback_reason = f"{path_error}; using mock preset clip queue."
        elif not audio_path.is_file():
            fallback_reason = "preset clip audio file missing; using mock preset clip queue."
        elif not base_url:
            fallback_reason = "AVATAR_SIDECAR_BASE_URL is empty; using mock preset clip queue."
        elif not clip_path:
            fallback_reason = (
                "AVATAR_SIDECAR_CLIP_PATH is empty; clip sidecar adapter pending, "
                "using mock preset clip queue."
            )
            metadata["clip_sidecar_adapter_pending"] = True
        else:
            ready, reason = _check_sidecar_ready(base_url, settings.avatar_speaker_timeout_seconds)
            if ready:
                ok, inject_reason, sidecar_response = _post_sidecar_clip(
                    base_url=base_url,
                    clip_path=clip_path,
                    timeout_seconds=settings.avatar_speaker_timeout_seconds,
                    clip=clip,
                    audio_path=audio_path,
                    source=normalized_source,
                    interrupt=interrupt,
                )
                metadata.update(
                    {
                        "adapter": "http_json_clip",
                        "sidecar_url": _public_base_url(base_url),
                        "auto_detected": auto_detected,
                        "sidecar_response": sidecar_response,
                    }
                )
                if ok:
                    mode = "sidecar"
                else:
                    fallback_reason = inject_reason or "sidecar_clip_injection_failed"
            else:
                fallback_reason = reason or "sidecar_not_ready"

    metadata.update(
        {
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "latency_ms": round((perf_counter() - started_at) * 1000),
        }
    )
    return {
        "mode": mode,
        "accepted": True,
        "message": "已进入数字人预存讲解播放队列",
        "fallback_reason": fallback_reason,
        "metadata": metadata,
    }
