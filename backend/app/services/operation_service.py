from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import status

from app.core.errors import ApiError
from app.repositories.content_repository import get_attraction
from app.repositories import operation_repository as repo


VALID_EVENT_TYPES = {"crowd", "closed", "show", "recommendation"}
VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_SOURCES = {"manual_admin", "mock_simulation"}


def _parse_time(value: str | None, *, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(
            code="OPERATION_EVENT_INVALID_TIME",
            message="运营事件时间格式不正确。",
            cause=f"Could not parse operation event time: {value}",
            fix="请使用 ISO 8601 时间，例如 2026-05-09T09:00:00+08:00。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _validate_choice(value: str, choices: set[str], *, code: str, label: str) -> str:
    clean = str(value or "").strip().lower()
    if clean not in choices:
        raise ApiError(
            code=code,
            message=f"{label} 不在支持范围内。",
            cause=f"Invalid {label}: {value}",
            fix=f"请使用以下值之一：{', '.join(sorted(choices))}。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return clean


def _validate_attraction(attraction_id: str) -> None:
    if not get_attraction(attraction_id):
        raise ApiError(
            code="ATTRACTION_NOT_FOUND",
            message="没有找到对应景点。",
            cause=f"Operation event attraction_id={attraction_id} was not found.",
            fix="请先调用 GET /api/attractions 确认可用景点 id。",
            status_code=status.HTTP_404_NOT_FOUND,
        )


def _enrich_event(event: dict[str, Any]) -> dict[str, Any]:
    attraction = get_attraction(event["attraction_id"])
    return {
        **event,
        "attraction_name": attraction.get("name") if attraction else event["attraction_id"],
        "scenic_area": attraction.get("scenic_area") if attraction else None,
    }


def _normalize_event_payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    now = datetime.now(timezone.utc)
    if "attraction_id" in payload or not partial:
        attraction_id = str(payload.get("attraction_id") or "").strip()
        _validate_attraction(attraction_id)
        normalized["attraction_id"] = attraction_id
    if "event_type" in payload or not partial:
        normalized["event_type"] = _validate_choice(
            str(payload.get("event_type") or ""),
            VALID_EVENT_TYPES,
            code="OPERATION_EVENT_INVALID_TYPE",
            label="event_type",
        )
    if "severity" in payload or not partial:
        normalized["severity"] = _validate_choice(
            str(payload.get("severity") or "info"),
            VALID_SEVERITIES,
            code="OPERATION_EVENT_INVALID_SEVERITY",
            label="severity",
        )
    if "source" in payload or not partial:
        normalized["source"] = _validate_choice(
            str(payload.get("source") or "manual_admin"),
            VALID_SOURCES,
            code="OPERATION_EVENT_INVALID_SOURCE",
            label="source",
        )
    if "message" in payload or not partial:
        message = str(payload.get("message") or "").strip()
        if not message:
            raise ApiError(
                code="OPERATION_EVENT_INVALID_MESSAGE",
                message="运营事件需要填写说明。",
                cause="Operation event message is empty.",
                fix="请在 message 中说明拥挤、关闭、演出或分流原因。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        normalized["message"] = message[:240]

    start_at = _parse_time(payload.get("start_at"), fallback=now)
    end_at = _parse_time(payload.get("end_at"), fallback=now + timedelta(hours=2))
    if partial:
        if "start_at" in payload:
            normalized["start_at"] = _format_time(start_at)
        if "end_at" in payload:
            normalized["end_at"] = _format_time(end_at)
    else:
        normalized["start_at"] = _format_time(start_at)
        normalized["end_at"] = _format_time(end_at)
    if "start_at" in normalized and "end_at" in normalized and normalized["end_at"] <= normalized["start_at"]:
        raise ApiError(
            code="OPERATION_EVENT_INVALID_TIME",
            message="运营事件结束时间必须晚于开始时间。",
            cause=f"start_at={normalized['start_at']} end_at={normalized['end_at']}",
            fix="请调整 start_at/end_at，让事件有效期为正。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if "created_by" in payload or not partial:
        normalized["created_by"] = str(payload.get("created_by") or "admin").strip()[:48] or "admin"
    if "active" in payload:
        normalized["active"] = bool(payload.get("active"))
    elif not partial:
        normalized["active"] = True
    return normalized


def list_operation_events(*, active_only: bool = False, attraction_id: str | None = None) -> list[dict[str, Any]]:
    return [_enrich_event(event) for event in repo.list_operation_events(active_only=active_only, attraction_id=attraction_id)]


def get_active_operation_events(*, attraction_id: str | None = None) -> list[dict[str, Any]]:
    return list_operation_events(active_only=True, attraction_id=attraction_id)


def get_events_for_attraction(attraction_id: str) -> list[dict[str, Any]]:
    return get_active_operation_events(attraction_id=attraction_id)


def create_operation_event(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_event_payload(payload, partial=False)
    return _enrich_event(repo.insert_operation_event(**normalized))


def update_operation_event(event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = repo.get_operation_event(event_id)
    if existing is None:
        raise ApiError(
            code="OPERATION_EVENT_NOT_FOUND",
            message="没有找到该运营事件。",
            cause=f"operation_event id={event_id} was not found.",
            fix="请刷新运营事件列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    normalized = _normalize_event_payload(payload, partial=True)
    merged_start = normalized.get("start_at", existing["start_at"])
    merged_end = normalized.get("end_at", existing["end_at"])
    if merged_end <= merged_start:
        raise ApiError(
            code="OPERATION_EVENT_INVALID_TIME",
            message="运营事件结束时间必须晚于开始时间。",
            cause=f"start_at={merged_start} end_at={merged_end}",
            fix="请调整 start_at/end_at，让事件有效期为正。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    updated = repo.update_operation_event(event_id, normalized)
    if updated is None:
        raise ApiError(
            code="OPERATION_EVENT_NOT_FOUND",
            message="没有找到该运营事件。",
            cause=f"operation_event id={event_id} disappeared before update.",
            fix="请刷新运营事件列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _enrich_event(updated)
