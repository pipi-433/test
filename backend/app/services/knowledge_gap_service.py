from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import status

from app.core.errors import ApiError
from app.repositories import knowledge_gap_repository as repo


VALID_TRIGGER_TYPES = {"low_confidence", "no_source", "negative_feedback", "manual"}
VALID_STATUSES = {"open", "drafted", "resolved", "ignored"}
ROOT_DIR = Path(__file__).resolve().parents[3]
KNOWLEDGE_GAP_EVAL_PATH = ROOT_DIR / "evals" / "knowledge_gaps.jsonl"


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


def _normalize_sources(sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        normalized.append(
            {
                "chunk_id": source.get("chunk_id") or source.get("id"),
                "title": source.get("title"),
                "source_file": source.get("source_file"),
                "source_section": source.get("source_section"),
                "attraction_id": source.get("attraction_id"),
                "score": source.get("score"),
            }
        )
    return normalized[:8]


def _preview(value: str | None, limit: int = 240) -> str | None:
    if not value:
        return None
    text = " ".join(str(value).split())
    return text[:limit]


def _get_gap_or_error(gap_id: str) -> dict[str, Any]:
    gap = repo.get_knowledge_gap(gap_id)
    if gap is None:
        raise ApiError(
            code="KNOWLEDGE_GAP_NOT_FOUND",
            message="没有找到对应的知识缺口。",
            cause=f"knowledge_gap id={gap_id} was not found.",
            fix="请刷新知识缺口列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return gap


def list_knowledge_gaps(*, status_filter: str | None = None) -> list[dict[str, Any]]:
    status_value = None
    if status_filter:
        status_value = _validate_choice(
            status_filter,
            VALID_STATUSES,
            code="KNOWLEDGE_GAP_INVALID_STATUS",
            label="status",
        )
    return repo.list_knowledge_gaps(status=status_value)


def create_knowledge_gap(
    *,
    query: str,
    trigger_type: str,
    matched_sources: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
    suggested_faq: str | None = None,
    status_value: str = "open",
    dedupe: bool = True,
) -> dict[str, Any]:
    clean_query = _preview(query, 500) or ""
    if not clean_query:
        raise ApiError(
            code="KNOWLEDGE_GAP_EMPTY_QUERY",
            message="知识缺口需要填写问题内容。",
            cause="create_knowledge_gap received an empty query.",
            fix="请提供游客原始问题、反馈内容或管理员手动记录。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    clean_trigger = _validate_choice(
        trigger_type,
        VALID_TRIGGER_TYPES,
        code="KNOWLEDGE_GAP_INVALID_TRIGGER",
        label="trigger_type",
    )
    clean_status = _validate_choice(
        status_value,
        VALID_STATUSES,
        code="KNOWLEDGE_GAP_INVALID_STATUS",
        label="status",
    )
    if dedupe:
        existing = repo.find_existing_gap(clean_query)
        if existing:
            return {**existing, "deduped": True}
    clean_confidence = None if confidence is None else max(0.0, min(float(confidence), 1.0))
    return repo.insert_knowledge_gap(
        query=clean_query,
        trigger_type=clean_trigger,
        matched_sources=_normalize_sources(matched_sources),
        confidence=clean_confidence,
        suggested_faq=_preview(suggested_faq, 2000),
        status=clean_status,
    )


def safe_record_knowledge_gap(
    *,
    query: str,
    trigger_type: str,
    matched_sources: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
) -> dict[str, Any] | None:
    try:
        return create_knowledge_gap(
            query=query,
            trigger_type=trigger_type,
            matched_sources=matched_sources,
            confidence=confidence,
            dedupe=True,
        )
    except Exception:
        return None


def generate_faq_draft(gap_id: str) -> dict[str, Any]:
    gap = _get_gap_or_error(gap_id)
    sources = gap.get("matched_sources") or []
    if sources:
        source_lines = []
        for source in sources[:3]:
            title = source.get("title") or source.get("chunk_id") or "未命名来源"
            source_file = source.get("source_file") or "本地资料"
            source_lines.append(f"- {title}（{source_file}）")
        draft = (
            f"### 问题\n{gap['query']}\n\n"
            "### 草稿回答\n"
            "可基于下列已命中资料补充一条简短 FAQ；发布前仍需管理员核对表述、时效和适用场景。\n\n"
            "### 参考来源\n"
            + "\n".join(source_lines)
        )
    else:
        draft = (
            f"### 问题\n{gap['query']}\n\n"
            "### 草稿回答\n"
            "当前没有可靠来源，需管理员补充资料后发布。建议先确认官方资料、开放时间、演出安排或服务规则，再加入知识库。\n"
        )
    updated = repo.update_knowledge_gap(gap_id, {"suggested_faq": draft, "status": "drafted"})
    if updated is None:
        raise ApiError(
            code="KNOWLEDGE_GAP_NOT_FOUND",
            message="生成草稿时没有找到该知识缺口。",
            cause=f"knowledge_gap id={gap_id} disappeared before draft update.",
            fix="请刷新列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return updated


def update_knowledge_gap_status(gap_id: str, status_value: str) -> dict[str, Any]:
    _get_gap_or_error(gap_id)
    clean_status = _validate_choice(
        status_value,
        VALID_STATUSES,
        code="KNOWLEDGE_GAP_INVALID_STATUS",
        label="status",
    )
    updated = repo.update_knowledge_gap(gap_id, {"status": clean_status})
    if updated is None:
        raise ApiError(
            code="KNOWLEDGE_GAP_NOT_FOUND",
            message="更新状态时没有找到该知识缺口。",
            cause=f"knowledge_gap id={gap_id} disappeared before status update.",
            fix="请刷新列表后重试。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return updated


def _read_eval_cases() -> list[dict[str, Any]]:
    if not KNOWLEDGE_GAP_EVAL_PATH.exists():
        return []
    cases: list[dict[str, Any]] = []
    for line in KNOWLEDGE_GAP_EVAL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            cases.append(parsed)
    return cases


def add_gap_to_eval(gap_id: str) -> dict[str, Any]:
    gap = _get_gap_or_error(gap_id)
    KNOWLEDGE_GAP_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    cases = _read_eval_cases()
    existing = next((case for case in cases if case.get("gap_id") == gap_id), None)
    if existing:
        eval_case_id = str(existing.get("id") or f"knowledge_gap_{gap_id}")
        updated = repo.update_knowledge_gap(gap_id, {"eval_case_id": eval_case_id})
        return {"gap": updated or gap, "eval_case_id": eval_case_id, "created": False}

    eval_case_id = f"knowledge_gap_{gap_id}"
    record = {
        "id": eval_case_id,
        "query": gap["query"],
        "expected_behavior": "clarify_or_answer_with_source",
        "source": "knowledge_gap",
        "gap_id": gap_id,
    }
    with KNOWLEDGE_GAP_EVAL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    updated = repo.update_knowledge_gap(gap_id, {"eval_case_id": eval_case_id})
    return {"gap": updated or gap, "eval_case_id": eval_case_id, "created": True}


def knowledge_gap_counts() -> dict[str, int]:
    return {
        "knowledge_gap_count": repo.count_knowledge_gaps(),
        "open_knowledge_gap_count": repo.count_knowledge_gaps("open"),
        "drafted_knowledge_gap_count": repo.count_knowledge_gaps("drafted"),
    }
