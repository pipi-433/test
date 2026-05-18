from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.errors import ApiError
from app.repositories import admin_avatar_repository as repo
from app.services.avatar_speaker import enqueue_avatar_speech


SOURCE_NOTE = "数字人管理为后台本地 mock 配置闭环；数字人仅作表现层，不接管 RAG、路线、识景或运营分析。"
VALID_EMOTIONS = {"welcome", "thinking", "speaking", "comforting", "error", "happy", "neutral"}


def _with_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "mode": "mock", "source_note": SOURCE_NOTE}


def _clean_text(value: Any, *, fallback: str = "", max_length: int = 300) -> str:
    text = str(value or fallback).strip()
    return text[:max_length]


def _clamp_float(value: Any, *, fallback: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = fallback
    return round(max(minimum, min(maximum, parsed)), 2)


def get_admin_avatar_profile() -> dict[str, Any]:
    return _with_meta(repo.get_avatar_profile())


def update_admin_avatar_profile(payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field in ("name", "outfit_style", "voice_name", "background_style"):
        if field in payload:
            updates[field] = _clean_text(payload.get(field), max_length=80)
    if "speech_rate" in payload:
        updates["speech_rate"] = _clamp_float(payload.get("speech_rate"), fallback=1.0, minimum=0.5, maximum=1.8)
    if "volume" in payload:
        updates["volume"] = _clamp_float(payload.get("volume"), fallback=0.9, minimum=0.0, maximum=1.0)
    if "default_emotion" in payload:
        emotion = _clean_text(payload.get("default_emotion"), fallback="happy", max_length=32)
        if emotion not in VALID_EMOTIONS:
            raise ApiError(
                code="ADMIN_AVATAR_INVALID_EMOTION",
                message="默认表情不在支持范围内。",
                cause=f"Invalid default_emotion: {emotion}",
                fix=f"请使用以下值之一：{', '.join(sorted(VALID_EMOTIONS))}。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        updates["default_emotion"] = emotion
    return _with_meta(repo.update_avatar_profile(updates))


def run_admin_avatar_voice_test(payload: dict[str, Any]) -> dict[str, Any]:
    profile = repo.get_avatar_profile()
    voice_name = _clean_text(payload.get("voice_name"), fallback=profile["voice_name"], max_length=80)
    text = _clean_text(
        payload.get("text"),
        fallback="您好，我是灵境导游，正在进行音色试听。",
        max_length=300,
    )
    result = enqueue_avatar_speech(
        text=text,
        emotion=profile.get("default_emotion") or "happy",
        source="system",
        interrupt=True,
    )
    return _with_meta(
        {
            **result,
            "voice_name": voice_name,
            "text_preview": text[:80],
            "message": result.get("message") or "已进入数字人播报队列。",
        }
    )


def create_admin_avatar_clip_job(payload: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(payload.get("title"), fallback="预存讲解生成任务", max_length=120)
    attraction_id = _clean_text(payload.get("attraction_id"), max_length=80) or None
    clip_id = _clean_text(payload.get("clip_id"), max_length=120) or None
    message = "已创建预存讲解生成任务；当前不生成音频文件，需上传或标准化 wav 后进入演示。"
    job = repo.insert_clip_job(
        title=title,
        clip_id=clip_id,
        attraction_id=attraction_id,
        status="mock_created",
        message=message,
    )
    return _with_meta(job)


def list_admin_avatar_clip_jobs() -> dict[str, Any]:
    items = repo.list_clip_jobs()
    return _with_meta({"items": items, "count": len(items)})
