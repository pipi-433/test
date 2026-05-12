from __future__ import annotations

import re
from typing import Any

from app.repositories.content_repository import get_attraction, list_attractions


GUIDE_INTENT_WORDS = [
    "介绍",
    "讲解",
    "看点",
    "亮点",
    "特色",
    "文化",
    "故事",
    "历史",
    "哪里",
    "在哪",
    "怎么游览",
    "如何游览",
    "适合",
    "怎么玩",
    "几点",
    "演出",
    "表演",
]

GENERIC_CONTEXT_WORDS = ["这个景点", "这个地方", "这里", "它", "那个", "那个景点", "当前景点", "该景点"]

ROUTE_STRONG_WORDS = [
    "路线",
    "规划",
    "安排行程",
    "安排路线",
    "怎么安排",
    "半天",
    "全天",
    "几小时",
    "小时",
    "老人",
    "孩子",
    "亲子",
    "别太挤",
    "避开人多",
    "不排队",
    "少走",
    "太累",
    "缩短",
    "换一个",
]

ROUTE_CONSTRAINT_WORDS = [
    "必去",
    "一定要去",
    "必须看",
    "必须去",
    "不能错过",
    "想去",
    "想看",
    "避开",
    "不想去",
    "不去",
    "跳过",
    "已经去过",
]

STYLE_WORDS = ["讲给孩子听", "30 秒", "三十秒", "简短点", "讲深入", "历史多一点", "文化多一点"]

OUT_OF_SCOPE_TERMS = [
    "海底两万里",
    "天上",
    "不存在",
    "电影",
    "写代码",
    "代码",
    "股票",
    "基金",
    "火星基地",
    "酒店预订",
    "外卖",
]

SCENIC_AREA_TERMS = ["灵山胜境", "灵山", "拈花湾", "无锡灵山", "拈花湾禅意小镇"]

BASE_ATTRACTION_ALIASES = {
    "大佛": "lingshan-ls-011",
    "灵山大佛": "lingshan-ls-011",
    "九龙": "lingshan-ls-006",
    "九龙灌浴": "lingshan-ls-006",
    "梵宫": "lingshan-ls-013",
    "灵山梵宫": "lingshan-ls-013",
    "禅寺": "lingshan-ls-010",
    "祥符禅寺": "lingshan-ls-010",
    "坛城": "lingshan-ls-014",
    "五印坛城": "lingshan-ls-014",
    "花海": "nianhuawan-nh-002",
    "梵天花海": "nianhuawan-nh-002",
    "花街": "nianhuawan-nh-003",
    "香月花街": "nianhuawan-nh-003",
    "五灯湖": "nianhuawan-nh-005",
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def _contains_any(text: str, values: list[str]) -> bool:
    return any(value and value in text for value in values)


def _attraction_maps() -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    attractions = list_attractions()
    by_id = {str(item["id"]): item for item in attractions if item.get("id")}
    aliases: dict[str, set[str]] = {}
    for alias, attraction_id in BASE_ATTRACTION_ALIASES.items():
        aliases.setdefault(alias, set()).add(attraction_id)
    for item in attractions:
        attraction_id = str(item.get("id") or "")
        name = str(item.get("name") or "")
        if not attraction_id or not name:
            continue
        aliases.setdefault(name, set()).add(attraction_id)
        aliases.setdefault(attraction_id.lower(), set()).add(attraction_id)
        if name.startswith("灵山") and len(name) > 2:
            aliases.setdefault(name[2:], set()).add(attraction_id)
        if name.startswith("拈花湾") and len(name) > 3:
            aliases.setdefault(name[3:], set()).add(attraction_id)
    return by_id, aliases


def _match_attraction_entities(message: str) -> tuple[list[dict[str, Any]], list[str]]:
    text = _compact(message).lower()
    by_id, aliases = _attraction_maps()
    matches: list[dict[str, Any]] = []
    ambiguous: list[str] = []
    occupied: list[tuple[int, int]] = []
    for alias, attraction_ids in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if len(alias) < 2:
            continue
        alias_norm = alias.lower()
        start = 0
        while True:
            index = text.find(alias_norm, start)
            if index < 0:
                break
            end = index + len(alias_norm)
            start = end
            if any(index >= left and end <= right for left, right in occupied):
                continue
            ids = sorted(attraction_ids)
            if len(ids) > 1:
                ambiguous.append(alias)
                continue
            attraction_id = ids[0]
            attraction = by_id.get(attraction_id)
            if not attraction:
                continue
            occupied.append((index, end))
            matches.append(
                {
                    "type": "attraction",
                    "id": attraction_id,
                    "name": attraction.get("name"),
                    "matched_text": alias,
                }
            )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in matches:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        deduped.append(item)
    return deduped, sorted(set(ambiguous))


def _has_time_budget(text: str) -> bool:
    return bool(re.search(r"\d+\s*(?:个)?小时", text)) or _contains_any(text, ["一小时", "二小时", "两小时", "三小时", "四小时", "半天", "全天"])


def _is_short_route_phrase(text: str) -> bool:
    normalized = re.sub(r"[，。！？；、,.!?;:：\s]+", "", text)
    return normalized in {"路线", "规划路线", "帮我安排", "帮我安排一下", "安排一下"}


def _is_generic_context_question(text: str) -> bool:
    normalized = re.sub(r"[，。！？；、,.!?;:：\s]+", "", text)
    if any(word in normalized for word in GENERIC_CONTEXT_WORDS) and _contains_any(normalized, GUIDE_INTENT_WORDS):
        return True
    return normalized in {"怎么游览", "如何游览", "怎么玩", "介绍一下", "讲解一下", "有什么看点", "看点"}


def _fallback_options() -> list[str]:
    return ["灵山大佛有什么看点？", "九龙灌浴适合怎么游览？", "帮我规划一条半天路线"]


def _result(
    *,
    domain: str,
    intent: str,
    entities: list[dict[str, Any]] | None = None,
    confidence: float,
    should_retrieve: bool,
    should_route: bool,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
    clarification_options: list[str] | None = None,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "domain": domain,
        "intent": intent,
        "entities": entities or [],
        "confidence": round(max(0.0, min(confidence, 1.0)), 4),
        "should_retrieve": should_retrieve,
        "should_route": should_route,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "clarification_options": clarification_options or [],
        "reasons": reasons or [],
        "mode": "mock_rule_gate",
    }


def build_gate_answer(understanding: dict[str, Any]) -> str:
    if understanding.get("domain") == "out_of_scope":
        return (
            "这个问题不在本地景区知识库范围内，我没有在本地资料里检索到可靠依据，所以先不编造答案。"
            "你可以问灵山胜境、拈花湾景点、路线或拥挤情况。"
        )
    if understanding.get("needs_clarification"):
        question = understanding.get("clarification_question") or "请补充一个具体景点名或路线需求。"
        return f"我还不能确定要调用哪类导览能力。{question}"
    return (
        "这个问题我暂时没有在本地资料里检索到可靠依据，所以先不编造答案。"
        "你可以换成具体景点名、演出名或游览需求再问一次。"
    )


def understand_query(
    message: str,
    selected_attraction_id: str | None = None,
    current_route_id: str | None = None,
) -> dict[str, Any]:
    text = _compact(message)
    if not text:
        return _result(
            domain="unclear",
            intent="unknown",
            confidence=0.0,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question="请先输入一个景区问题或路线需求。",
            clarification_options=_fallback_options(),
            reasons=["empty_message"],
        )

    entities, ambiguous_aliases = _match_attraction_entities(text)
    explicit_entity_ids = {item["id"] for item in entities}
    selected_attraction = get_attraction(selected_attraction_id) if selected_attraction_id else None
    has_entity = bool(entities)
    has_scenic_area = _contains_any(text, SCENIC_AREA_TERMS)
    has_guide_intent = _contains_any(text, GUIDE_INTENT_WORDS)
    has_route_strong = _contains_any(text, ROUTE_STRONG_WORDS) or _has_time_budget(text)
    has_route_constraint = _contains_any(text, ROUTE_CONSTRAINT_WORDS)
    has_style = _contains_any(text, STYLE_WORDS)
    has_out_of_scope = _contains_any(text, OUT_OF_SCOPE_TERMS)
    is_generic_context = _is_generic_context_question(text)

    if ambiguous_aliases:
        return _result(
            domain="unclear",
            intent="unknown",
            entities=entities,
            confidence=0.46,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question=f"“{'、'.join(ambiguous_aliases[:3])}”可能对应多个景点，请确认你想问哪一个。",
            clarification_options=_fallback_options(),
            reasons=["ambiguous_attraction_alias"],
        )

    if is_generic_context and selected_attraction and selected_attraction["id"] not in explicit_entity_ids:
        entities = [
            {
                "type": "attraction",
                "id": selected_attraction["id"],
                "name": selected_attraction["name"],
                "matched_text": "selected_attraction_id",
            }
        ]
        has_entity = True

    if has_out_of_scope and not has_entity and not has_scenic_area:
        return _result(
            domain="out_of_scope",
            intent="unknown",
            entities=entities,
            confidence=0.94,
            should_retrieve=False,
            should_route=False,
            reasons=["out_of_scope_term_without_scenic_entity", "guide_words_are_not_entities" if has_guide_intent else "non_scenic_query"],
        )

    if _is_short_route_phrase(text):
        return _result(
            domain="unclear",
            intent="route_request",
            entities=entities,
            confidence=0.45,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question="你想按多长时间、同行人群或必去景点来安排？",
            clarification_options=["2 小时轻松路线", "带老人孩子 3 小时", "灵山大佛一定要去"],
            reasons=["route_phrase_too_short"],
        )

    if is_generic_context and not has_entity:
        return _result(
            domain="unclear",
            intent="attraction_intro",
            entities=[],
            confidence=0.42,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question="你说的“这个景点”是指哪一个？请补充景点名，或从景点卡点击一键讲解。",
            clarification_options=["灵山大佛", "九龙灌浴", "灵山梵宫", "香月花街"],
            reasons=["generic_attraction_reference_without_context"],
        )

    if has_route_constraint and not has_entity and not has_scenic_area and not has_route_strong:
        return _result(
            domain="unclear",
            intent="route_request",
            entities=[],
            confidence=0.5,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question="你提到了必去或避开的点，但我还不知道具体是哪一个景点。",
            clarification_options=["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城"],
            reasons=["route_constraint_without_attraction_entity"],
        )

    route_by_constraints = has_route_constraint and (has_entity or has_scenic_area)
    route_by_group_time = has_route_strong and (_has_time_budget(text) or _contains_any(text, ["老人", "孩子", "亲子", "半天", "全天", "路线", "规划", "安排"]))
    route_by_replan = bool(current_route_id) and _contains_any(text, ["太累", "缩短", "换一个", "人太多", "少走", "重新安排", "重规划"])
    if route_by_constraints or route_by_group_time or route_by_replan:
        return _result(
            domain="route_planning",
            intent="route_replan" if route_by_replan else "route_request",
            entities=entities,
            confidence=0.86 if (has_entity or _has_time_budget(text)) else 0.74,
            should_retrieve=False,
            should_route=True,
            reasons=[
                "route_constraint" if route_by_constraints else "route_preference",
                "attraction_entity_present" if has_entity else "route_without_entity_allowed",
            ],
        )

    if has_entity or has_scenic_area:
        return _result(
            domain="scenic_guide",
            intent="attraction_intro" if has_guide_intent or has_style else "fact_qa",
            entities=entities,
            confidence=0.9 if has_entity else 0.72,
            should_retrieve=True,
            should_route=False,
            reasons=["scenic_entity_present" if has_entity else "scenic_area_present"],
        )

    if has_style:
        return _result(
            domain="unclear",
            intent="attraction_intro",
            confidence=0.48,
            should_retrieve=False,
            should_route=False,
            needs_clarification=True,
            clarification_question="你想让我用这种风格讲解哪个景点？",
            clarification_options=["灵山大佛", "九龙灌浴", "灵山梵宫"],
            reasons=["style_request_without_attraction"],
        )

    if has_guide_intent:
        return _result(
            domain="out_of_scope",
            intent="unknown",
            confidence=0.82,
            should_retrieve=False,
            should_route=False,
            reasons=["guide_intent_without_scenic_entity", "guide_words_are_not_entities"],
        )

    return _result(
        domain="out_of_scope",
        intent="unknown",
        confidence=0.72,
        should_retrieve=False,
        should_route=False,
        reasons=["no_scenic_entity_or_route_signal"],
    )
