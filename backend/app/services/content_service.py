from fastapi import status

from app.core.errors import ApiError
from app.repositories.content_repository import (
    get_attraction,
    get_behavior_summary,
    list_attractions,
    list_knowledge_chunks,
)


def get_attractions() -> list[dict]:
    return list_attractions()


def get_attraction_or_error(attraction_id: str) -> dict:
    attraction = get_attraction(attraction_id)
    if attraction is None:
        raise ApiError(
            code="ATTRACTION_NOT_FOUND",
            message="未找到对应景点。",
            cause=f"No attraction matched id or attraction_id: {attraction_id}",
            fix="请使用 GET /api/attractions 查看可用景点 id。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return attraction


def get_chunks(attraction_id: str | None = None) -> list[dict]:
    if attraction_id:
        attraction = get_attraction_or_error(attraction_id)
        return list_knowledge_chunks(attraction["id"])
    return list_knowledge_chunks(None)


def get_behavior_summary_or_error() -> dict:
    summary = get_behavior_summary()
    if summary is None:
        raise ApiError(
            code="BEHAVIOR_SUMMARY_NOT_FOUND",
            message="尚未找到行为数据摘要。",
            cause="behavior_summary table does not contain the default row.",
            fix="运行 python .\\scripts\\init_db.py 初始化 SQLite 数据库。",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return summary
