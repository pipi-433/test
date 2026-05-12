from __future__ import annotations

from collections import Counter
from typing import Any

from app.repositories.content_repository import list_attractions


SCENIC_AREAS = ["灵山胜境", "拈花湾"]


def _area_items(scenic_area: str) -> list[dict[str, Any]]:
    return [
        item
        for item in list_attractions()
        if item.get("scenic_area") == scenic_area or str(item.get("scenic_area") or "").startswith(scenic_area)
    ]


def _top_tags(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for item in items:
        for tag in item.get("tags", []) or []:
            if tag:
                counter[str(tag)] += 1
    return [tag for tag, _count in counter.most_common(limit)]


def _item_names(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    return [str(item.get("name")) for item in items[:limit] if item.get("name")]


def build_scenic_area_intro(scenic_area: str | None = None) -> dict[str, Any]:
    areas = SCENIC_AREAS if scenic_area is None else [scenic_area]
    sections: list[dict[str, Any]] = []
    for area in areas:
        items = _area_items(area)
        tags = _top_tags(items)
        names = _item_names(items)
        if not items:
            continue
        sections.append(
            {
                "scenic_area": area,
                "attraction_count": len(items),
                "highlights": [
                    f"代表点位：{'、'.join(names[:4])}。",
                    f"核心体验：{'、'.join(tags[:4]) if tags else '文化导览、休闲游览'}。",
                    "回答基于 data/processed 本地公开资料整理，不接真实模型自由生成。",
                ],
                "suggested_questions": [
                    f"{names[0]}有什么看点？" if names else f"介绍{area}",
                    f"{area}适合拍照的地方有哪些？",
                    f"帮我规划一条{area}半天路线",
                ],
            }
        )

    if not sections:
        return {
            "title": "景区总览",
            "summary": "本地资料里暂未找到对应景区的结构化景点。",
            "highlights": [],
            "suggested_questions": ["介绍灵山胜境", "介绍拈花湾"],
            "source": "local_processed_data",
            "disclaimer": "基于本地公开资料整理，mock 模式不代表实时运营信息。",
        }

    if scenic_area:
        section = sections[0]
        summary = (
            f"{scenic_area}当前本地资料包含 {section['attraction_count']} 个结构化景点，"
            f"适合围绕{section['highlights'][1].replace('核心体验：', '').rstrip('。')}展开游览。"
        )
        title = f"{scenic_area}总览"
        highlights = section["highlights"]
        suggested_questions = section["suggested_questions"]
    else:
        summary = "灵境当前覆盖灵山胜境与拈花湾两个景区，可分别按文化朝圣、禅意休闲、拍照打卡和亲子轻松游来理解。"
        title = "灵山胜境与拈花湾总览"
        highlights = [highlight for section in sections for highlight in section["highlights"][:2]]
        suggested_questions = ["介绍灵山胜境", "介绍拈花湾", "灵山和拈花湾哪个适合拍照？"]

    return {
        "title": title,
        "summary": summary,
        "highlights": highlights[:6],
        "suggested_questions": suggested_questions[:5],
        "source": "local_processed_data",
        "disclaimer": "基于本地公开资料整理；当前不是实时票务、天气或硬件客流信息。",
        "sections": sections,
    }
