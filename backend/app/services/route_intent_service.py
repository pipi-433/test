from __future__ import annotations

import re
from typing import Any

from app.repositories.content_repository import list_attractions


THEME_KEYWORDS = {
    "family": ["孩子", "亲子", "老人孩子", "带娃", "小朋友"],
    "history": ["历史", "文化", "深入", "典故", "研学"],
    "nature": ["自然", "花海", "休闲", "慢游"],
    "blessing": ["祈福", "朝圣", "拜佛", "禅寺"],
    "photo": ["拍照", "打卡", "出片", "摄影"],
}

STYLE_KEYWORDS = {
    "child": ["讲给孩子听", "孩子听", "亲子版", "小朋友听"],
    "deep_history": ["讲深入", "深入一点", "历史多一点", "文化多一点"],
    "short_30s": ["30 秒", "三十秒", "简短点", "短一点", "一句话"],
    "photo": ["拍照讲", "打卡讲", "取景"],
    "comfort": ["安抚", "太累", "太挤", "赶时间"],
}

OPERATION_KEYWORDS = {
    "shorten": ["缩短", "短一点", "时间不够", "太长"],
    "less_walking": ["太累", "少走", "老人累", "走不动", "轻松点"],
    "avoid_crowd": ["人太多", "换一个", "别太挤", "避开人多", "不排队", "别排队"],
    "more_photo": ["多拍照", "打卡", "出片"],
    "more_history": ["想听历史", "历史多一点", "文化多一点"],
    "start_here": ["从这里", "我在", "从"],
}

MUST_VISIT_KEYWORDS = ["必去", "一定要去", "必须看", "必须去", "不能错过"]
REMOVE_MUST_VISIT_KEYWORDS = ["取消", "算了", "不去了", "别去了", "不用去", "不用去了", "不必去"]
AVOID_ATTRACTION_KEYWORDS = ["避开", "不想去", "跳过", "已经去过", "不去", "别去"]

TIME_WORDS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "半天": 4,
    "全天": 8,
}

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

CLAUSE_SEPARATORS = "，,。；;！!？?"


def _contains_any(message: str, values: list[str]) -> bool:
    return any(value in message for value in values)


def _attraction_aliases() -> list[tuple[str, str]]:
    attractions = list_attractions()
    aliases: dict[str, str] = dict(BASE_ATTRACTION_ALIASES)
    for item in attractions:
        name = str(item.get("name") or "")
        attraction_id = str(item.get("id") or "")
        if not name or not attraction_id:
            continue
        aliases[name] = attraction_id
        if name.startswith("灵山") and len(name) > 2:
            aliases.setdefault(name[2:], attraction_id)
        if name.startswith("拈花湾") and len(name) > 3:
            aliases.setdefault(name[3:], attraction_id)
    return sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True)


def _match_attraction_mentions(message: str) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    seen_spans: set[tuple[int, int, str]] = set()
    for alias, attraction_id in _attraction_aliases():
        if not alias or len(alias) < 2:
            continue
        start = 0
        while True:
            index = message.find(alias, start)
            if index < 0:
                break
            end = index + len(alias)
            key = (index, end, attraction_id)
            if key not in seen_spans:
                mentions.append({"alias": alias, "attraction_id": attraction_id, "start": index, "end": end})
                seen_spans.add(key)
            start = end
    mentions.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
    deduped: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for mention in mentions:
        span = (int(mention["start"]), int(mention["end"]))
        if any(span[0] >= current[0] and span[1] <= current[1] for current in occupied):
            continue
        occupied.append(span)
        deduped.append(mention)
    return deduped


def _match_attractions(message: str) -> list[str]:
    matches: list[str] = []
    for mention in _match_attraction_mentions(message):
        attraction_id = mention["attraction_id"]
        if attraction_id not in matches:
            matches.append(attraction_id)
    return matches


def _context_for_mention(message: str, mention: dict[str, Any], radius: int = 12) -> str:
    start = max(0, int(mention["start"]) - radius)
    end = min(len(message), int(mention["end"]) + radius)
    return message[start:end]


def _clause_for_mention(message: str, mention: dict[str, Any]) -> str:
    start = int(mention["start"])
    end = int(mention["end"])
    left = max(message.rfind(separator, 0, start) for separator in CLAUSE_SEPARATORS)
    right_candidates = [
        index
        for separator in CLAUSE_SEPARATORS
        for index in [message.find(separator, end)]
        if index >= 0
    ]
    right = min(right_candidates) if right_candidates else len(message)
    return message[left + 1 : right]


def _classify_attraction_constraints(message: str) -> tuple[list[str], list[str], list[str], list[str]]:
    must: list[str] = []
    avoid: list[str] = []
    optional: list[str] = []
    conflicts: list[str] = []
    for mention in _match_attraction_mentions(message):
        attraction_id = mention["attraction_id"]
        context = _clause_for_mention(message, mention)
        is_remove = _contains_any(context, REMOVE_MUST_VISIT_KEYWORDS)
        is_must = _contains_any(context, MUST_VISIT_KEYWORDS)
        is_avoid = _contains_any(context, AVOID_ATTRACTION_KEYWORDS)
        is_optional = _contains_any(context, ["想去", "想看", "看看", "感兴趣", "顺路", "可以去"])
        if is_must and is_avoid and not is_remove:
            if attraction_id not in conflicts:
                conflicts.append(attraction_id)
            if attraction_id not in must:
                must.append(attraction_id)
            if attraction_id not in avoid:
                avoid.append(attraction_id)
        elif is_remove or is_avoid:
            if attraction_id not in avoid:
                avoid.append(attraction_id)
        elif is_must:
            if attraction_id not in must:
                must.append(attraction_id)
        elif is_optional:
            if attraction_id not in optional:
                optional.append(attraction_id)
        elif attraction_id not in optional:
            optional.append(attraction_id)
    return must, avoid, optional, conflicts


def _parse_time_budget(message: str) -> int | None:
    arabic = re.search(r"(\d+(?:\.\d+)?)\s*(?:个)?小时", message)
    if arabic:
        return int(float(arabic.group(1)) * 60)
    for word, hours in TIME_WORDS.items():
        if f"{word}小时" in message or word in {"半天", "全天"} and word in message:
            return int(hours * 60)
    return None


def _infer_theme(message: str) -> str | None:
    for theme, keywords in THEME_KEYWORDS.items():
        if _contains_any(message, keywords):
            return theme
    return None


def _infer_style(message: str) -> str:
    for style, keywords in STYLE_KEYWORDS.items():
        if _contains_any(message, keywords):
            return style
    return "default"


def _infer_operation(message: str) -> str:
    if _contains_any(message, REMOVE_MUST_VISIT_KEYWORDS):
        return "remove_must_visit"
    if _contains_any(message, MUST_VISIT_KEYWORDS):
        return "set_must_visit"
    for operation, keywords in OPERATION_KEYWORDS.items():
        if _contains_any(message, keywords):
            return operation
    return "none"


def parse_route_intent(
    *,
    message: str,
    selected_attraction_id: str | None = None,
    current_route_id: str | None = None,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = " ".join(str(message or "").strip().split())
    matched_ids = _match_attractions(text)
    classified_must_ids, classified_avoid_ids, classified_optional_ids, classified_conflict_ids = _classify_attraction_constraints(text)
    has_must_phrase = _contains_any(text, MUST_VISIT_KEYWORDS)
    has_remove_phrase = _contains_any(text, REMOVE_MUST_VISIT_KEYWORDS)
    has_avoid_attraction_phrase = _contains_any(text, AVOID_ATTRACTION_KEYWORDS)
    has_direct_conflict = bool(classified_conflict_ids)
    operation = _infer_operation(text)
    style = _infer_style(text)
    theme = _infer_theme(text)
    time_budget = _parse_time_budget(text)
    interests: list[str] = []
    group_type: str | None = None
    intensity: str | None = None
    avoid_crowd = False
    crowd_tolerance = "medium"
    optional_ids: list[str] = []
    avoid_ids: list[str] = []
    must_visit_ids: list[str] = []

    if _contains_any(text, ["老人", "爸妈", "父母", "长辈"]):
        group_type = "family_elderly"
        intensity = "easy"
        interests.append("长辈友好")
    if _contains_any(text, ["孩子", "亲子", "带娃", "小朋友"]):
        theme = theme or "family"
        group_type = group_type or "family"
        interests.append("亲子")
    if _contains_any(text, ["轻松", "少走", "太累", "老人累"]):
        intensity = "easy"
    if _contains_any(text, ["别太挤", "避开人多", "不排队", "别排队", "人太多", "换一个"]):
        avoid_crowd = True
        crowd_tolerance = "low"
    if operation == "more_photo":
        theme = "photo"
        interests.append("拍照打卡")
    if operation == "more_history":
        theme = "history"
        interests.append("历史文化")

    if operation == "set_must_visit":
        must_visit_ids = classified_must_ids or matched_ids
        avoid_ids = classified_avoid_ids
    elif operation == "remove_must_visit":
        avoid_ids = classified_avoid_ids or matched_ids
    elif has_avoid_attraction_phrase:
        avoid_ids = classified_avoid_ids or matched_ids
    else:
        optional_ids = classified_optional_ids or matched_ids

    if has_direct_conflict:
        must_visit_ids = classified_conflict_ids
        avoid_ids = classified_conflict_ids

    route_keywords = [
        "路线",
        "怎么玩",
        "怎么安排",
        "几小时",
        "小时",
        "半天",
        "全天",
        "老人",
        "孩子",
        "太累",
        "人多",
        "不想去",
        "不去",
        "跳过",
        "避开",
        "一定要去",
        "必去",
        "必须看",
        "必须去",
        "缩短",
        "换一个",
        "少走",
    ]
    explicit_route_terms = [
        "路线",
        "怎么玩",
        "怎么安排",
        "小时",
        "半天",
        "全天",
        "太累",
        "人多",
        "一定要去",
        "必须看",
        "缩短",
        "换一个",
        "少走",
    ]
    style_only = style != "default" and not _contains_any(text, explicit_route_terms) and not current_route_id
    if style_only:
        intent = "explanation_style"
    elif operation in {"shorten", "less_walking", "avoid_crowd", "more_photo", "more_history", "start_here"} or current_route_id:
        intent = "route_replan"
    elif _contains_any(text, route_keywords) or theme or time_budget or must_visit_ids or optional_ids or avoid_ids:
        intent = "route_recommend"
    else:
        intent = "unknown"

    confidence = 0.3
    confidence += 0.16 if theme else 0
    confidence += 0.16 if time_budget else 0
    confidence += 0.16 if operation != "none" else 0
    confidence += 0.12 if matched_ids else 0
    confidence += 0.14 if avoid_ids else 0
    confidence += 0.1 if group_type else 0
    confidence += 0.1 if avoid_crowd else 0
    confidence += 0.3 if style != "default" else 0
    confidence += 0.2 if current_route_id and _contains_any(text, ["重新安排", "重规划", "路线"]) else 0
    confidence = min(round(confidence, 2), 0.96)

    needs_clarification = False
    clarification_question: str | None = None
    clarification_options: list[str] = []
    if intent == "unknown" or confidence < 0.45:
        needs_clarification = True
        clarification_question = "你想让我做景点问答，还是帮你重新规划路线？"
        clarification_options = ["帮我规划路线", "讲解当前景点", "避开拥挤重新安排"]
        intent = "clarification"
    elif has_direct_conflict:
        needs_clarification = True
        clarification_question = "这个景点同时被说成必去和不想去，我需要先确认。"
        clarification_options = ["保留为必去", "取消必去并避开", "重新规划不包含该点"]
        intent = "clarification"
    elif operation == "set_must_visit" and not must_visit_ids:
        needs_clarification = True
        clarification_question = "你说有必去点，但我还不确定是哪几个景点。"
        clarification_options = ["灵山大佛", "九龙灌浴", "灵山梵宫", "五印坛城"]
        intent = "clarification"

    return {
        "intent": intent,
        "operation": operation,
        "theme": theme,
        "time_budget_minutes": time_budget,
        "group_type": group_type,
        "intensity": intensity,
        "interests": interests,
        "must_visit_attraction_ids": must_visit_ids,
        "optional_attraction_ids": optional_ids,
        "avoid_attraction_ids": avoid_ids,
        "avoid_crowd": avoid_crowd,
        "crowd_tolerance": crowd_tolerance,
        "style": style,
        "intent_confidence": confidence,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "clarification_options": clarification_options,
        "selected_attraction_id": selected_attraction_id,
        "current_route_id": current_route_id,
        "mode": "mock_rule_parser",
        "metadata": {
            "matched_attraction_ids": matched_ids,
            "conflict_attraction_ids": classified_conflict_ids if has_direct_conflict else [],
            "memory_turn_count": (memory or {}).get("turn_count"),
        },
    }
