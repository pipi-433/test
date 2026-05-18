from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.errors import ApiError
from app.repositories import admin_knowledge_repository as repo


VALID_ASSET_TYPES = {"guide_script", "history_doc", "faq", "route_note", "other"}
VALID_KNOWLEDGE_STATUSES = {"draft", "pending_review", "published", "archived"}
SOURCE_NOTE = "后台本地知识库管理闭环为 mock/local 演示；发布仅更新后台管理状态，不直接改写现有 RAG knowledge_chunks。"


def _validate_choice(value: str, choices: set[str], *, code: str, field_name: str) -> str:
    clean = str(value or "").strip().lower()
    if clean not in choices:
        raise ApiError(
            code=code,
            message=f"{field_name} 不在支持范围内。",
            cause=f"Invalid {field_name}: {value}",
            fix=f"请使用以下值之一：{', '.join(sorted(choices))}。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return clean


def _clean_text(value: Any, *, fallback: str = "", max_length: int = 300) -> str:
    text = str(value or fallback).strip()
    return text[:max_length]


def _with_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "mode": "mock", "source_note": SOURCE_NOTE}


def list_admin_knowledge_assets() -> dict[str, Any]:
    items = repo.list_assets()
    return _with_meta({"items": items, "count": len(items)})


def create_admin_knowledge_asset(payload: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(payload.get("title") or payload.get("source_filename"), max_length=120)
    if not title:
        raise ApiError(
            code="ADMIN_KNOWLEDGE_ASSET_INVALID_TITLE",
            message="请填写知识资产标题。",
            cause="Admin knowledge asset title is empty.",
            fix="在 title 或 source_filename 字段中传入可读名称。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    asset_type = _validate_choice(
        payload.get("asset_type") or "other",
        VALID_ASSET_TYPES,
        code="ADMIN_KNOWLEDGE_ASSET_INVALID_TYPE",
        field_name="asset_type",
    )
    status_value = _validate_choice(
        payload.get("status") or "draft",
        VALID_KNOWLEDGE_STATUSES,
        code="ADMIN_KNOWLEDGE_INVALID_STATUS",
        field_name="status",
    )
    item = repo.insert_asset(
        title=title,
        asset_type=asset_type,
        scenic_area=_clean_text(payload.get("scenic_area"), max_length=80) or None,
        attraction_id=_clean_text(payload.get("attraction_id"), max_length=80) or None,
        status=status_value,
        chunk_count=max(0, int(payload.get("chunk_count") or 0)),
        source_filename=_clean_text(payload.get("source_filename"), max_length=160) or None,
        note=_clean_text(payload.get("note"), max_length=300) or "后台演示上传记录，未进行真实资料解析入库。",
    )
    return _with_meta(item)


def update_admin_knowledge_asset(asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field in ("title", "scenic_area", "attraction_id", "source_filename", "note"):
        if field in payload:
            updates[field] = _clean_text(payload.get(field), max_length=300) or None
    if "asset_type" in payload:
        updates["asset_type"] = _validate_choice(
            payload.get("asset_type"),
            VALID_ASSET_TYPES,
            code="ADMIN_KNOWLEDGE_ASSET_INVALID_TYPE",
            field_name="asset_type",
        )
    if "status" in payload:
        updates["status"] = _validate_choice(
            payload.get("status"),
            VALID_KNOWLEDGE_STATUSES,
            code="ADMIN_KNOWLEDGE_INVALID_STATUS",
            field_name="status",
        )
    if "chunk_count" in payload:
        updates["chunk_count"] = max(0, int(payload.get("chunk_count") or 0))
    item = repo.update_asset(asset_id, updates)
    if item is None:
        raise ApiError(
            code="ADMIN_KNOWLEDGE_ASSET_NOT_FOUND",
            message="没有找到该知识资产。",
            cause=f"admin_knowledge_asset id={asset_id} was not found.",
            fix="请刷新知识资产列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _with_meta(item)


def list_admin_faqs() -> dict[str, Any]:
    items = repo.list_faqs()
    return _with_meta({"items": items, "count": len(items)})


def create_admin_faq(payload: dict[str, Any]) -> dict[str, Any]:
    question = _clean_text(payload.get("question"), max_length=200)
    answer = _clean_text(payload.get("answer"), max_length=1200)
    if not question or not answer:
        raise ApiError(
            code="ADMIN_FAQ_INVALID_CONTENT",
            message="FAQ 需要同时填写问题和答案草稿。",
            cause="Admin FAQ question or answer is empty.",
            fix="请在 question 与 answer 字段中传入内容。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    status_value = _validate_choice(
        payload.get("status") or "draft",
        VALID_KNOWLEDGE_STATUSES,
        code="ADMIN_KNOWLEDGE_INVALID_STATUS",
        field_name="status",
    )
    raw_tags = payload.get("tags") or []
    tags = [str(tag).strip()[:40] for tag in raw_tags if str(tag).strip()] if isinstance(raw_tags, list) else []
    item = repo.insert_faq(
        question=question,
        answer=answer,
        scenic_area=_clean_text(payload.get("scenic_area"), max_length=80) or None,
        attraction_id=_clean_text(payload.get("attraction_id"), max_length=80) or None,
        tags=tags,
        status=status_value,
        source_gap_id=_clean_text(payload.get("source_gap_id"), max_length=80) or None,
    )
    return _with_meta(item)


def update_admin_faq(faq_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field in ("question", "answer", "scenic_area", "attraction_id", "source_gap_id"):
        if field in payload:
            max_length = 1200 if field == "answer" else 200
            updates[field] = _clean_text(payload.get(field), max_length=max_length) or None
    if "tags" in payload:
        raw_tags = payload.get("tags") or []
        updates["tags"] = [str(tag).strip()[:40] for tag in raw_tags if str(tag).strip()] if isinstance(raw_tags, list) else []
    if "status" in payload:
        updates["status"] = _validate_choice(
            payload.get("status"),
            VALID_KNOWLEDGE_STATUSES,
            code="ADMIN_KNOWLEDGE_INVALID_STATUS",
            field_name="status",
        )
    item = repo.update_faq(faq_id, updates)
    if item is None:
        raise ApiError(
            code="ADMIN_FAQ_NOT_FOUND",
            message="没有找到该 FAQ。",
            cause=f"admin_faq id={faq_id} was not found.",
            fix="请刷新 FAQ 列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _with_meta(item)


def rebuild_admin_knowledge_index() -> dict[str, Any]:
    assets = repo.list_assets()
    return _with_meta(
        {
            "accepted": True,
            "job_id": f"reindex-{len(assets):03d}",
            "message": "已完成本地演示索引重建；未改写线上 RAG chunks。",
            "affected_assets": len(assets),
        }
    )


def publish_admin_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
    result = repo.publish_admin_knowledge(
        asset_ids=payload.get("asset_ids") if isinstance(payload.get("asset_ids"), list) else None,
        faq_ids=payload.get("faq_ids") if isinstance(payload.get("faq_ids"), list) else None,
        publish_all_drafts=bool(payload.get("publish_all_drafts")),
    )
    return _with_meta(
        {
            "accepted": True,
            "message": "已发布到后台本地知识库管理视图；现有 RAG 索引需后续任务显式重建。",
            **result,
        }
    )
