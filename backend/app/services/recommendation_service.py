from __future__ import annotations

from collections import Counter
from typing import Any

from app.repositories.content_repository import get_attraction, list_attractions


INTEREST_LABELS = {
    "history": "历史文化",
    "photo": "拍照打卡",
    "family": "亲子友好",
    "elderly": "轻松少走",
    "nature": "自然风景",
    "blessing": "祈福禅意",
    "show": "演出表演",
}

INTEREST_TERMS = {
    "history": ["历史", "文化", "典故", "故事", "赵朴初", "佛教", "藏传"],
    "photo": ["拍照", "打卡", "出片", "花海", "湖", "街", "照壁", "夜景"],
    "family": ["亲子", "孩子", "小朋友", "演出", "互动", "轻松"],
    "elderly": ["老人", "长辈", "少走", "轻松", "休闲", "禅寺", "湖"],
    "nature": ["自然", "花海", "湖", "太湖", "风景", "水", "休闲"],
    "blessing": ["祈福", "拜佛", "禅意", "佛", "朝圣", "许愿", "寺"],
    "show": ["演出", "表演", "吉祥颂", "九龙灌浴", "动态"],
}


def _norm(value: Any) -> str:
    return str(value or "").lower()


def _haystack(attraction: dict[str, Any]) -> str:
    values = [
        attraction.get("name"),
        attraction.get("scenic_area"),
        attraction.get("category"),
        attraction.get("summary"),
        attraction.get("description"),
        " ".join(map(str, attraction.get("tags", []) or [])),
        " ".join(map(str, attraction.get("visitor_tips", []) or [])),
    ]
    return " ".join(_norm(value) for value in values)


def _score_for_interest(attraction: dict[str, Any], interest: str) -> tuple[float, list[str]]:
    haystack = _haystack(attraction)
    terms = INTEREST_TERMS.get(interest, [])
    hits = [term for term in terms if term.lower() in haystack]
    score = len(hits) * 12.0
    tags = [_norm(tag) for tag in attraction.get("tags", []) or []]
    if interest == "photo" and any("拍照" in tag or "打卡" in tag for tag in tags):
        score += 22
    if interest == "history" and any("历史" in tag or "文化" in tag for tag in tags):
        score += 18
    if interest == "blessing" and ("佛教" in haystack or "禅" in haystack):
        score += 18
    if interest == "nature" and attraction.get("scenic_area") == "拈花湾":
        score += 8
    if interest == "family" and ("演出" in haystack or "互动" in haystack):
        score += 10
    if interest == "elderly" and any(word in haystack for word in ["步行", "休闲", "湖", "寺"]):
        score += 8
    return score, hits[:5]


def recommend_attractions(
    *,
    interests: list[str] | None = None,
    scenic_area: str | None = None,
    group_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    clean_interests = list(dict.fromkeys(interests or []))
    if group_type == "family" and "family" not in clean_interests:
        clean_interests.append("family")
    if group_type == "elderly" and "elderly" not in clean_interests:
        clean_interests.append("elderly")
    if not clean_interests:
        clean_interests = ["history", "photo"]

    rows: list[dict[str, Any]] = []
    for attraction in list_attractions():
        if scenic_area and attraction.get("scenic_area") != scenic_area and not str(attraction.get("scenic_area") or "").startswith(scenic_area):
            continue
        total = 0.0
        matched_terms: list[str] = []
        matched_interests: list[str] = []
        for interest in clean_interests:
            score, hits = _score_for_interest(attraction, interest)
            if score > 0:
                total += score
                matched_terms.extend(hits)
                matched_interests.append(interest)
        if total <= 0:
            continue
        total += 8 if attraction.get("id") in {"lingshan-ls-011", "lingshan-ls-006", "lingshan-ls-013"} else 0
        matched_labels = [INTEREST_LABELS.get(item, item) for item in matched_interests]
        reason = f"匹配{'、'.join(matched_labels[:3])}；命中关键词：{'、'.join(dict.fromkeys(matched_terms[:5])) or '景点标签'}。"
        rows.append(
            {
                "attraction_id": attraction["id"],
                "name": attraction["name"],
                "scenic_area": attraction.get("scenic_area"),
                "score": round(min(total, 100.0), 2),
                "reason": reason,
                "matched_interests": matched_labels,
                "suggested_question": f"{attraction['name']}有什么看点？",
            }
        )
    rows.sort(key=lambda item: (-float(item["score"]), item["scenic_area"], item["name"]))
    return rows[: max(1, min(limit, 8))]


def _target_summary(target: dict[str, Any], interests: list[str]) -> dict[str, Any]:
    if target.get("type") == "scenic_area":
        area = str(target.get("id") or target.get("name"))
        items = [item for item in list_attractions() if item.get("scenic_area") == area or str(item.get("scenic_area") or "").startswith(area)]
        counter: Counter[str] = Counter()
        total = 0.0
        for item in items:
            for interest in interests or ["photo", "history"]:
                score, _hits = _score_for_interest(item, interest)
                total += score
            for tag in item.get("tags", []) or []:
                counter[str(tag)] += 1
        return {
            "type": "scenic_area",
            "id": area,
            "name": area,
            "score": round(min(total / max(len(items), 1), 100.0), 2),
            "strengths": [tag for tag, _count in counter.most_common(4)],
        }

    attraction = get_attraction(str(target.get("id") or ""))
    if not attraction:
        return {"type": target.get("type"), "id": target.get("id"), "name": target.get("name"), "score": 0, "strengths": []}
    total = 0.0
    strengths: list[str] = []
    for interest in interests or ["photo", "history"]:
        score, hits = _score_for_interest(attraction, interest)
        total += score
        strengths.extend(hits)
    return {
        "type": "attraction",
        "id": attraction["id"],
        "name": attraction["name"],
        "score": round(min(total, 100.0), 2),
        "strengths": list(dict.fromkeys([*strengths, *(attraction.get("tags", []) or [])]))[:4],
    }


def compare_targets(*, compare_targets: list[dict[str, Any]], interests: list[str] | None = None) -> dict[str, Any]:
    clean_interests = interests or ["photo"]
    summaries = [_target_summary(target, clean_interests) for target in compare_targets[:3]]
    summaries.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("name"))))
    winner = summaries[0] if summaries else None
    dimensions = [INTEREST_LABELS.get(item, item) for item in clean_interests] or ["综合体验"]
    return {
        "compare_targets": summaries,
        "dimensions": dimensions,
        "recommendation": f"如果优先看{dimensions[0]}，更推荐 {winner['name']}。" if winner else "请先提供两个可比较的景点或景区。",
        "reasons": [
            f"{item['name']}：得分 {item['score']}，优势 {('、'.join(item.get('strengths') or []) or '本地资料覆盖较少')}。"
            for item in summaries
        ],
        "suggested_next_questions": [
            f"{winner['name']}适合怎么游览？" if winner else "灵山和拈花湾哪个适合拍照？",
            "帮我规划一条半天路线",
        ],
    }
