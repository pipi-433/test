from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import status

from app.core.errors import ApiError
from app.repositories.content_repository import get_attraction, list_attractions
from app.services.crowd_service import CROWD_SOURCE, get_crowd_record


DEFAULT_THEME = "family"
VALID_TOLERANCES = {"low", "medium", "high"}

ROUTE_CONSTRAINT_RULES: dict[str, Any] = {
    "priority": [
        "data_available",
        "user_avoid_attraction",
        "user_must_visit",
        "time_budget",
        "crowd_comfort",
        "theme_preference",
        "template_default",
    ],
    "conflict_policy": {
        "must_visit_vs_avoid": "trigger clarification; do not silently delete or keep the conflicted stop.",
        "invalid_attraction_id": "exclude invalid ids and explain in constraint_summary/decision_trace.",
        "time_over_budget": "preserve valid must_visit stops, trim lower-priority recommended/alternative stops, then warn.",
        "start_in_avoid": "use the start only as context unless it is also an explicit must_visit stop.",
    },
    "crowd_policy": {
        "must_visit_high": "keep with warning or delay; never delete only because of simulated crowd.",
        "recommended_high": "delay or shorten when avoid_crowd is true.",
        "optional_high": "optional stops are weighted, not guaranteed, and may be delayed or omitted under pressure.",
    },
    "optional_policy": "optional_attraction_ids increase priority but do not guarantee inclusion.",
}

CONSTRAINT_CLARIFICATION_OPTIONS = ["保留为必去", "取消必去并避开", "重新规划不包含该点"]

THEME_LABELS = {
    "family": "亲子轻松",
    "history": "历史文化",
    "nature": "自然休闲",
    "blessing": "祈福朝圣",
    "photo": "拍照打卡",
}

CORE_LANDMARK_IDS = {
    "lingshan-ls-001",
    "lingshan-ls-006",
    "lingshan-ls-010",
    "lingshan-ls-011",
    "lingshan-ls-013",
    "lingshan-ls-014",
    "nianhuawan-nh-002",
    "nianhuawan-nh-003",
    "nianhuawan-nh-005",
}

THEME_PROFILE_KEYWORDS = {
    "family": ["亲子", "孩子", "儿童", "互动", "轻松", "弥勒", "广场", "演艺", "休闲"],
    "history": ["历史", "文化", "典故", "博览", "寺", "柱", "塔", "坛城", "照壁", "佛教"],
    "nature": ["自然", "花", "湖", "桥", "谷", "水", "大道", "休闲", "慢行", "漫步"],
    "blessing": ["祈福", "朝圣", "拜佛", "佛", "禅寺", "坛", "门", "大佛", "香"],
    "photo": ["拍照", "打卡", "夜游", "花街", "花海", "湖", "照壁", "塔", "广场", "出片"],
}

ROUTE_TEMPLATES: dict[str, dict[str, Any]] = {
    "family": {
        "title": "亲子轻松路线",
        "summary": "少爬坡、多故事，优先选择开阔广场、动态演绎和室内停留点。",
        "suitable_for": ["亲子", "长辈", "第一次到访"],
        "stops": [
            ("lingshan-ls-001", 10, 0, "入园文化序章", "先用大照壁建立灵山胜境的第一印象，适合拍一张全家合影。"),
            ("lingshan-ls-006", 30, 12, "观看九龙灌浴", "提前到开阔广场站位，用佛陀诞生故事做亲子讲解。"),
            ("lingshan-ls-009", 20, 8, "百子戏弥勒互动", "让孩子观察不同人物神态，讲轻松的欢喜文化。"),
            ("lingshan-ls-013", 55, 15, "梵宫室内艺术", "安排在午后或天气不佳时段，兼顾休息和演出体验。"),
            ("nianhuawan-nh-005", 40, 25, "夜间五灯湖", "如果还有体力，可把拈花湾夜游作为延伸。"),
        ],
    },
    "history": {
        "title": "历史文化深读路线",
        "summary": "围绕唐宋佛教脉络、建筑象征和佛教艺术，把景点串成一条文化叙事线。",
        "suitable_for": ["历史文化爱好者", "研学", "深度游客"],
        "stops": [
            ("lingshan-ls-001", 12, 0, "赵朴初题字与入口礼序", "从大照壁理解景区的文化序章和礼佛动线。"),
            ("lingshan-ls-002", 18, 8, "五明智慧", "解释五明桥象征的佛教智慧与通行礼序。"),
            ("lingshan-ls-010", 40, 15, "祥符禅寺历史", "讲唐贞观、窥基大师与北宋更名的历史线索。"),
            ("lingshan-ls-012", 45, 12, "佛教文化博览", "用展陈补足佛教历史、器物与艺术脉络。"),
            ("lingshan-ls-014", 35, 18, "藏传佛教坛城", "比较汉传与藏传佛教空间表达。"),
        ],
    },
    "nature": {
        "title": "自然慢游路线",
        "summary": "避开密集赶路，把水景、步道、花海和湖区串成舒缓路线。",
        "suitable_for": ["休闲慢游", "长辈", "情侣"],
        "stops": [
            ("lingshan-ls-005", 20, 0, "菩提大道慢行", "用树荫步道进入状态，适合轻松热身。"),
            ("lingshan-ls-002", 15, 8, "五明桥与香水海", "在桥面和水景处短暂停留，拍摄入口到核心区的过渡。"),
            ("nianhuawan-nh-002", 40, 28, "梵天花海", "安排在光线柔和时段，适合花海拍照和休息。"),
            ("nianhuawan-nh-005", 45, 10, "五灯湖水岸", "沿湖慢走，夜间可衔接灯光与演艺。"),
            ("nianhuawan-nh-006", 30, 12, "鹿鸣谷", "作为安静收尾点，减少人流干扰。"),
        ],
    },
    "blessing": {
        "title": "祈福朝圣路线",
        "summary": "沿灵山中轴线逐步进入核心礼佛区，强调礼序、祈福和庄重体验。",
        "suitable_for": ["祈福", "朝圣", "家庭长辈"],
        "stops": [
            ("lingshan-ls-003", 15, 0, "佛足坛礼敬", "从佛足象征开始，讲朝圣路线的起点。"),
            ("lingshan-ls-004", 15, 8, "五智门入境", "用五智门解释从世俗到礼佛空间的转换。"),
            ("lingshan-ls-006", 28, 10, "九龙灌浴", "观看动态景观，连接释迦牟尼诞生故事。"),
            ("lingshan-ls-010", 35, 12, "祥符禅寺祈福", "在寺院留足安静时间，适合长辈和家庭祈愿。"),
            ("lingshan-ls-011", 45, 15, "灵山大佛核心朝拜", "收束到核心地标，提醒台阶和体力安排。"),
        ],
    },
    "photo": {
        "title": "拍照打卡路线",
        "summary": "优先选择地标、开阔构图、花海和夜景，兼顾社交平台出片效率。",
        "suitable_for": ["情侣", "朋友", "摄影爱好者"],
        "stops": [
            ("lingshan-ls-001", 10, 0, "入口题字合影", "用大照壁做第一张到此一游照片。"),
            ("lingshan-ls-006", 25, 12, "九龙灌浴动态瞬间", "提前等候喷泉与太子佛转身的关键画面。"),
            ("lingshan-ls-013", 45, 15, "梵宫建筑与穹顶", "拍摄室内艺术细节，避开正午强光。"),
            ("nianhuawan-nh-002", 40, 28, "梵天花海", "用花海做轻松明亮的照片组。"),
            ("nianhuawan-nh-003", 35, 10, "香月花街夜景", "傍晚后拍灯笼、街巷和禅意商铺。"),
        ],
    },
}

ROUTE_CACHE: dict[str, dict[str, Any]] = {}


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def _infer_theme(theme: str | None, group_type: str | None, interests: list[str] | None) -> str:
    requested = _normalize(theme)
    if requested in ROUTE_TEMPLATES:
        return requested

    text = " ".join([_normalize(group_type), *[_normalize(item) for item in interests or []]])
    if any(key in text for key in ["亲子", "family", "孩子", "长辈"]):
        return "family"
    if any(key in text for key in ["历史", "文化", "研学"]):
        return "history"
    if any(key in text for key in ["自然", "花海", "休闲", "慢游"]):
        return "nature"
    if any(key in text for key in ["祈福", "朝圣", "佛教", "禅寺"]):
        return "blessing"
    if any(key in text for key in ["拍照", "打卡", "摄影", "夜景"]):
        return "photo"
    return DEFAULT_THEME


def _safe_budget(value: int | None) -> int:
    if value is None:
        return 240
    return max(90, min(int(value), 480))


def _attraction_map() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in list_attractions()}


def _clean_ids(values: list[str] | None, attractions: dict[str, dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values or []:
        attraction_id = str(value or "").strip()
        if attraction_id and attraction_id in attractions and attraction_id not in seen:
            cleaned.append(attraction_id)
            seen.add(attraction_id)
    return cleaned


def _constraint_label(value: str) -> str:
    return {
        "must_visit": "必去",
        "optional": "可选",
        "recommended": "推荐",
        "alternative": "替代",
    }.get(value, "推荐")


def _make_stop(
    *,
    order: int,
    attraction: dict[str, Any],
    stay_minutes: int,
    walk_minutes: int,
    focus: str,
    reason: str,
    selection_source: str = "template_seed",
) -> dict[str, Any]:
    return {
        "order": order,
        "attraction_id": attraction["id"],
        "name": attraction["name"],
        "scenic_area": attraction["scenic_area"],
        "category": attraction.get("category"),
        "tags": attraction.get("tags", []),
        "stay_minutes": stay_minutes,
        "walk_minutes_from_previous": walk_minutes,
        "focus": focus,
        "reason": reason,
        "narration_question": f"请讲解{attraction['name']}的看点和游览建议。",
        "constraint_type": "recommended",
        "constraint_reason": "来自主题路线模板的系统推荐点。",
        "crowd_action": "keep",
        "decision_reason": "符合当前路线主题与基础动线。",
        "selection_source": selection_source,
    }


def _profile_text(attraction: dict[str, Any]) -> str:
    values = [
        attraction.get("name"),
        attraction.get("scenic_area"),
        attraction.get("category"),
        attraction.get("summary"),
        attraction.get("description"),
        attraction.get("location"),
        attraction.get("core_function"),
        " ".join(str(tag) for tag in attraction.get("tags", [])),
        " ".join(str(item) for item in attraction.get("visitor_tips", [])),
        " ".join(str(item) for item in attraction.get("culture_points", [])),
        " ".join(str(item) for item in attraction.get("history_points", [])),
    ]
    return " ".join(str(value or "") for value in values)


def build_attraction_route_profile(attraction: dict[str, Any]) -> dict[str, Any]:
    text = _profile_text(attraction)
    category = str(attraction.get("category") or "")
    tags = [str(tag) for tag in attraction.get("tags", [])]
    attraction_id = str(attraction.get("id") or "")
    name = str(attraction.get("name") or "")
    scores: dict[str, int] = {}
    for theme, keywords in THEME_PROFILE_KEYWORDS.items():
        score = 32
        score += sum(9 for keyword in keywords if keyword in text)
        score += 12 if THEME_LABELS[theme][:2] in text else 0
        if theme == "family" and any(tag in tags for tag in ["亲子友好", "演艺提醒", "休闲漫步"]):
            score += 18
        if theme == "history" and ("历史文化" in tags or "佛教文化" in tags or "博览" in name):
            score += 18
        if theme == "nature" and (category == "自然休闲" or any(tag in tags for tag in ["休闲漫步", "夜游"])):
            score += 18
        if theme == "blessing" and ("佛教文化" in tags or any(key in name for key in ["佛", "寺", "坛", "门"])):
            score += 18
        if theme == "photo" and any(tag in tags for tag in ["拍照打卡", "夜游"]):
            score += 18
        scores[f"{theme}_score"] = max(0, min(100, score))

    is_core = attraction_id in CORE_LANDMARK_IDS
    route_priority = 66 if is_core else 50
    route_priority += 8 if any(tag in tags for tag in ["路线节点", "演艺提醒"]) else 0
    route_priority += 8 if any(tag in tags for tag in ["拍照打卡", "历史文化"]) else 0
    route_priority += 4 if attraction.get("scenic_area") == "拈花湾禅意小镇" else 0
    default_stay = get_default_stay_minutes(attraction)
    return {
        **scores,
        "route_priority": max(0, min(100, route_priority)),
        "default_stay_minutes": default_stay,
        "is_core_landmark": is_core,
    }


def score_attraction_for_theme(attraction: dict[str, Any], theme: str) -> int:
    profile = build_attraction_route_profile(attraction)
    return int(profile.get(f"{theme}_score", 45))


def get_default_stay_minutes(attraction: dict[str, Any]) -> int:
    name = str(attraction.get("name") or "")
    category = str(attraction.get("category") or "")
    tags = set(str(tag) for tag in attraction.get("tags", []))
    if name in {"灵山梵宫", "五印坛城", "佛教文化博览馆"}:
        return 40
    if name in {"灵山大佛", "祥符禅寺", "九龙灌浴", "梵天花海", "五灯湖", "香月花街"}:
        return 32
    if "演艺提醒" in tags or category == "演艺互动":
        return 28
    if category == "自然休闲" or "休闲漫步" in tags:
        return 24
    if category == "禅意商业":
        return 30
    return 22


def explain_profile_match(attraction: dict[str, Any], theme: str) -> str:
    profile = build_attraction_route_profile(attraction)
    tags = [str(tag) for tag in attraction.get("tags", [])]
    tag_text = "、".join(tags[:3]) or str(attraction.get("category") or "景点")
    return f"{attraction['name']} 与{THEME_LABELS[theme]}主题匹配 {profile.get(f'{theme}_score', 0)} 分，依据：{tag_text}。"


def _with_route_profile(
    stop: dict[str, Any],
    *,
    theme: str,
    selection_source: str | None = None,
    profile_match_reason: str | None = None,
) -> dict[str, Any]:
    attraction = get_attraction(stop["attraction_id"]) or stop
    profile = build_attraction_route_profile(attraction)
    source = selection_source or stop.get("selection_source") or "template_seed"
    return {
        **stop,
        "selection_source": source,
        "route_profile_scores": profile,
        "theme_score": int(profile.get(f"{theme}_score", 0)),
        "profile_match_reason": profile_match_reason or explain_profile_match(attraction, theme),
    }


def _select_template_stops(
    *,
    theme: str,
    time_budget_minutes: int,
    start_attraction_id: str | None,
) -> list[dict[str, Any]]:
    attractions = _attraction_map()
    template = ROUTE_TEMPLATES[theme]
    selected: list[dict[str, Any]] = []
    total = 0

    for attraction_id, stay, walk, focus, reason in template["stops"]:
        attraction = attractions.get(attraction_id)
        if attraction is None:
            continue
        proposed_total = total + stay + walk
        if selected and proposed_total > time_budget_minutes and len(selected) >= 3:
            break
        total = proposed_total
        selected.append(
            _with_route_profile(
                _make_stop(
                    order=len(selected) + 1,
                    attraction=attraction,
                    stay_minutes=stay,
                    walk_minutes=walk if selected else 0,
                    focus=focus,
                    reason=reason,
                    selection_source="template_seed",
                ),
                theme=theme,
                selection_source="template_seed",
            )
        )

    if start_attraction_id:
        start = get_attraction(start_attraction_id)
        if start and all(stop["attraction_id"] != start["id"] for stop in selected):
            selected.insert(
                0,
                _with_route_profile(
                    _make_stop(
                        order=1,
                        attraction=start,
                        stay_minutes=max(18, min(get_default_stay_minutes(start), 28)),
                        walk_minutes=0,
                        focus="从当前景点出发",
                        reason="根据你当前选择的景点，把它放在路线开头，方便现场继续游览。",
                        selection_source="start_context",
                    ),
                    theme=theme,
                    selection_source="start_context",
                ),
            )

    for index, stop in enumerate(selected, start=1):
        stop["order"] = index
        if index == 1:
            stop["walk_minutes_from_previous"] = 0
    return selected[:6]


def _estimated_minutes(stops: list[dict[str, Any]]) -> int:
    return sum(int(stop["stay_minutes"]) + int(stop["walk_minutes_from_previous"]) for stop in stops)


def _raw_ids(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        attraction_id = str(value or "").strip()
        if attraction_id and attraction_id not in seen:
            result.append(attraction_id)
            seen.add(attraction_id)
    return result


def normalize_route_constraints(
    *,
    must_visit_attraction_ids: list[str] | None = None,
    optional_attraction_ids: list[str] | None = None,
    avoid_attraction_ids: list[str] | None = None,
    start_attraction_id: str | None = None,
) -> dict[str, Any]:
    attractions = _attraction_map()
    raw_must = _raw_ids(must_visit_attraction_ids)
    raw_optional = _raw_ids(optional_attraction_ids)
    raw_avoid = _raw_ids(avoid_attraction_ids)
    must_visit = _clean_ids(raw_must, attractions)
    avoid = _clean_ids(raw_avoid, attractions)
    optional = [
        item
        for item in _clean_ids(raw_optional, attractions)
        if item not in must_visit and item not in avoid
    ]
    invalid_ids = sorted(
        {
            item
            for item in [*raw_must, *raw_optional, *raw_avoid]
            if item and item not in attractions
        }
    )
    conflict_ids = sorted(set(must_visit) & set(avoid))
    start_context_only = bool(start_attraction_id and start_attraction_id in avoid and start_attraction_id not in must_visit)
    return {
        "must_visit_attraction_ids": must_visit,
        "optional_attraction_ids": optional,
        "avoid_attraction_ids": avoid,
        "invalid_attraction_ids": invalid_ids,
        "conflict_attraction_ids": conflict_ids,
        "start_attraction_id": start_attraction_id,
        "start_context_only": start_context_only,
    }


def detect_constraint_conflicts(constraints: dict[str, Any]) -> list[dict[str, Any]]:
    attractions = _attraction_map()
    conflicts: list[dict[str, Any]] = []
    for attraction_id in constraints.get("conflict_attraction_ids", []):
        attraction = attractions.get(attraction_id, {})
        name = attraction.get("name") or attraction_id
        conflicts.append(
            {
                "code": "MUST_VISIT_AVOID_CONFLICT",
                "attraction_id": attraction_id,
                "name": name,
                "message": f"{name} 同时被标记为必去和避开，需要先确认你的真实意图。",
                "options": CONSTRAINT_CLARIFICATION_OPTIONS,
            }
        )
    return conflicts


def build_constraint_decision_reason(*, constraint_type: str, attraction_name: str, source: str) -> str:
    if constraint_type == "must_visit":
        return f"必去点：{attraction_name}由{source}指定，优先保留；若拥挤只能延后或提示错峰。"
    if constraint_type == "optional":
        return f"可选点：{attraction_name}由{source}触发，时间和舒适度允许时优先加入。"
    if constraint_type == "alternative":
        return f"替代点：{attraction_name}用于替换被避开的模板点或避免空路线。"
    return f"推荐点：{attraction_name}来自主题模板，低于用户明确约束。"


def _constraint_reason(*, constraint_type: str, attraction_name: str) -> str:
    source = "用户明确" if constraint_type in {"must_visit", "optional"} else "系统模板"
    return f"{_constraint_label(constraint_type)}：{attraction_name}由{source}指定。"


def _reorder_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, stop in enumerate(stops, start=1):
        stop["order"] = index
        if index == 1:
            stop["walk_minutes_from_previous"] = 0
    return stops


def _new_constraint_summary(constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "priority": ROUTE_CONSTRAINT_RULES["priority"],
        "must_visit_attraction_ids": constraints["must_visit_attraction_ids"],
        "optional_attraction_ids": constraints["optional_attraction_ids"],
        "avoid_attraction_ids": constraints["avoid_attraction_ids"],
        "invalid_attraction_ids": constraints["invalid_attraction_ids"],
        "conflict_attraction_ids": constraints["conflict_attraction_ids"],
        "start_context_only": constraints["start_context_only"],
        "skipped_avoid_attraction_ids": [],
        "optional_not_selected_attraction_ids": [],
        "full_pool_selected_attraction_ids": [],
        "full_pool_not_selected_attraction_ids": [],
        "trimmed_attraction_ids": [],
        "warning": None,
        "notes": [],
    }


def _trim_for_time_budget(
    *,
    stops: list[dict[str, Any]],
    budget: int,
    summary: dict[str, Any],
    trace: list[str],
) -> list[dict[str, Any]]:
    if _estimated_minutes(stops) <= budget:
        return _reorder_stops(stops)

    removable_order = {"recommended": 0, "alternative": 1, "optional": 2}
    while _estimated_minutes(stops) > budget and len(stops) > 1:
        candidates = [
            (index, removable_order.get(stop.get("constraint_type"), 9))
            for index, stop in enumerate(stops)
            if stop.get("constraint_type") != "must_visit"
        ]
        if not candidates:
            break
        index_to_remove = sorted(candidates, key=lambda item: (item[1], -item[0]))[0][0]
        removed = stops.pop(index_to_remove)
        summary["trimmed_attraction_ids"].append(removed["attraction_id"])
        trace.append(f"{removed['name']} 因时间预算优先级较低，已从路线中删减；必去点保留。")

    estimated = _estimated_minutes(stops)
    if estimated > budget:
        warning = f"必去点导致预计 {estimated} 分钟，超过 {budget} 分钟预算；已保留必去点，建议现场再确认是否缩短。"
        summary["warning"] = warning
        summary["notes"].append(warning)
        trace.append(warning)
    elif summary["trimmed_attraction_ids"]:
        trace.append("时间预算不足时已优先删除 recommended/alternative 点，必去点没有被删除。")
    return _reorder_stops(stops)


def apply_route_constraints(
    *,
    stops: list[dict[str, Any]],
    constraints: dict[str, Any],
    time_budget_minutes: int,
    theme: str = DEFAULT_THEME,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any], list[dict[str, Any]]]:
    attractions = _attraction_map()
    must_visit = constraints["must_visit_attraction_ids"]
    optional = constraints["optional_attraction_ids"]
    avoid = constraints["avoid_attraction_ids"]
    must_set = set(must_visit)
    optional_set = set(optional)
    avoid_set = set(avoid)
    conflicts = detect_constraint_conflicts(constraints)
    summary = _new_constraint_summary(constraints)
    trace: list[str] = []
    constrained: list[dict[str, Any]] = []

    if constraints["invalid_attraction_ids"]:
        text = f"约束规则忽略无效景点 id：{'、'.join(constraints['invalid_attraction_ids'])}。"
        trace.append(text)
        summary["notes"].append(text)
    if constraints["start_context_only"]:
        start = constraints.get("start_attraction_id")
        text = f"{start} 被用户标记为避开景点，本次只作为起点上下文，不作为停留点。"
        trace.append(text)
        summary["notes"].append(text)
    if conflicts:
        names = "、".join(item["name"] for item in conflicts)
        warning = f"检测到必去/避开冲突：{names}；conversation API 会先澄清，直接推荐结果仅保留冲突说明。"
        summary["warning"] = warning
        summary["notes"].append(warning)
        trace.append(warning)

    for stop in stops:
        attraction_id = stop["attraction_id"]
        if attraction_id in avoid_set and attraction_id not in must_set:
            trace.append(f"{stop['name']} 被用户标记为避开景点，已从候选路线移除。")
            summary["skipped_avoid_attraction_ids"].append(attraction_id)
            continue
        constraint_type = "must_visit" if attraction_id in must_set else "optional" if attraction_id in optional_set else "recommended"
        if attraction_id in must_set and attraction_id in avoid_set:
            trace.append(f"{stop['name']} 同时命中必去和避开约束，本结果记录冲突；推荐前端应先让游客澄清。")
        selection_source = "must_visit" if attraction_id in must_set else "optional_boost" if attraction_id in optional_set else stop.get("selection_source", "template_seed")
        constrained.append(
            _with_route_profile(
                {
                **stop,
                "selection_source": selection_source,
                "constraint_type": constraint_type,
                "constraint_reason": _constraint_reason(
                    constraint_type=constraint_type,
                    attraction_name=attractions[attraction_id]["name"],
                ),
                "decision_reason": build_constraint_decision_reason(
                    constraint_type=constraint_type,
                    attraction_name=attractions[attraction_id]["name"],
                    source="用户明确" if constraint_type != "recommended" else "路线模板",
                ),
                },
                theme=theme,
                selection_source=selection_source,
            )
        )

    existing_ids = {stop["attraction_id"] for stop in constrained}
    for attraction_id in must_visit:
        if attraction_id in existing_ids:
            continue
        attraction = attractions[attraction_id]
        stop = _with_route_profile(
            _make_stop(
                order=len(constrained) + 1,
                attraction=attraction,
                stay_minutes=max(get_default_stay_minutes(attraction), 28),
                walk_minutes=12 if constrained else 0,
                focus="必去景点讲解",
                reason="用户明确提出一定要去，规划器按最高优先级保留。",
                selection_source="must_visit",
            ),
            theme=theme,
            selection_source="must_visit",
        )
        stop.update(
            {
                "constraint_type": "must_visit",
                "constraint_reason": f"必去：{attraction['name']}由用户明确指定。",
                "decision_reason": build_constraint_decision_reason(
                    constraint_type="must_visit",
                    attraction_name=attraction["name"],
                    source="用户明确",
                ),
            }
        )
        constrained.append(stop)
        existing_ids.add(attraction_id)
        trace.append(f"{attraction['name']} 不在经典模板 seed 中，已从全量景点池按必去约束追加到路线。")

    for attraction_id in optional:
        if attraction_id in existing_ids:
            continue
        if attraction_id in avoid_set or len(constrained) >= 7:
            summary["optional_not_selected_attraction_ids"].append(attraction_id)
            if attraction_id in avoid_set:
                trace.append(f"{attractions[attraction_id]['name']} 是可选点但也被标记为避开，未加入路线。")
            else:
                trace.append(f"{attractions[attraction_id]['name']} 是可选点，但当前站点数已满，未强制加入。")
            continue
        attraction = attractions[attraction_id]
        stop = _with_route_profile(
            _make_stop(
                order=len(constrained) + 1,
                attraction=attraction,
                stay_minutes=get_default_stay_minutes(attraction),
                walk_minutes=10 if constrained else 0,
                focus="可选兴趣点",
                reason="用户表达了兴趣，时间允许时作为补充站点。",
                selection_source="optional_boost",
            ),
            theme=theme,
            selection_source="optional_boost",
        )
        stop.update(
            {
                "constraint_type": "optional",
                "constraint_reason": f"可选：{attraction['name']}由用户兴趣触发，可被替换或延后。",
                "decision_reason": build_constraint_decision_reason(
                    constraint_type="optional",
                    attraction_name=attraction["name"],
                    source="用户兴趣",
                ),
            }
        )
        constrained.append(stop)
        existing_ids.add(attraction_id)
        trace.append(f"{attraction['name']} 已从全量景点池作为可选景点补充进路线。")

    if not constrained:
        fallback = next((item for item in attractions.values() if item["id"] not in avoid_set), next(iter(attractions.values())))
        constrained.append(
            _with_route_profile(
                _make_stop(
                    order=1,
                    attraction=fallback,
                    stay_minutes=get_default_stay_minutes(fallback),
                    walk_minutes=0,
                    focus="兜底推荐",
                    reason="避开约束过滤了全部模板点，系统保留一个低风险入口点。",
                    selection_source="full_pool",
                ),
                theme=theme,
                selection_source="full_pool",
            )
        )
        constrained[0]["constraint_type"] = "alternative"
        constrained[0]["constraint_reason"] = "替代：原候选被避开约束过滤后的兜底站点。"
        constrained[0]["decision_reason"] = build_constraint_decision_reason(
            constraint_type="alternative",
            attraction_name=fallback["name"],
            source="系统兜底",
        )
        trace.append(f"避开约束过滤了全部模板点，已补充低风险替代点 {fallback['name']}。")

    selected_ids = {stop["attraction_id"] for stop in constrained}
    for attraction_id in optional:
        if attraction_id not in selected_ids and attraction_id not in summary["optional_not_selected_attraction_ids"]:
            summary["optional_not_selected_attraction_ids"].append(attraction_id)
    constrained = _trim_for_time_budget(
        stops=constrained[:7],
        budget=time_budget_minutes,
        summary=summary,
        trace=trace,
    )
    return constrained, trace, summary, conflicts


def _apply_constraint_rules(
    *,
    stops: list[dict[str, Any]],
    must_visit_attraction_ids: list[str] | None,
    optional_attraction_ids: list[str] | None,
    avoid_attraction_ids: list[str] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    constraints = normalize_route_constraints(
        must_visit_attraction_ids=must_visit_attraction_ids,
        optional_attraction_ids=optional_attraction_ids,
        avoid_attraction_ids=avoid_attraction_ids,
    )
    constrained, trace, _summary, _conflicts = apply_route_constraints(
        stops=stops,
        constraints=constraints,
        time_budget_minutes=480,
        theme=DEFAULT_THEME,
    )
    return constrained, trace


def _full_pool_candidate_score(
    *,
    attraction: dict[str, Any],
    theme: str,
    optional_set: set[str],
    avoid_crowd: bool,
    tolerance: str,
) -> int:
    profile = build_attraction_route_profile(attraction)
    record = get_crowd_record(attraction["id"])
    score = int(profile.get(f"{theme}_score", 0)) + int(profile.get("route_priority", 0)) // 2
    if attraction["id"] in optional_set:
        score += 32
    if profile.get("is_core_landmark"):
        score += 8
    if avoid_crowd and record["crowd_level"] == "high":
        score -= 28 if tolerance != "high" else 12
    elif avoid_crowd and tolerance == "low" and record["crowd_level"] == "medium":
        score -= 8
    elif record["crowd_level"] == "low":
        score += 8
    return score


def _add_full_pool_candidates(
    *,
    stops: list[dict[str, Any]],
    constraints: dict[str, Any],
    theme: str,
    time_budget_minutes: int,
    avoid_crowd: bool,
    crowd_tolerance: str,
    summary: dict[str, Any],
    trace: list[str],
) -> list[dict[str, Any]]:
    attractions = _attraction_map()
    existing_ids = {stop["attraction_id"] for stop in stops}
    avoid_set = set(constraints["avoid_attraction_ids"])
    optional_set = set(constraints["optional_attraction_ids"])
    target_count = 3 if time_budget_minutes <= 120 else 5
    max_count = 7
    if len(stops) >= target_count and not optional_set.difference(existing_ids):
        return stops

    candidates: list[tuple[int, dict[str, Any]]] = []
    for attraction in attractions.values():
        attraction_id = attraction["id"]
        if attraction_id in existing_ids or attraction_id in avoid_set:
            continue
        score = _full_pool_candidate_score(
            attraction=attraction,
            theme=theme,
            optional_set=optional_set,
            avoid_crowd=avoid_crowd,
            tolerance=crowd_tolerance,
        )
        candidates.append((score, attraction))

    candidates.sort(key=lambda item: (item[0], item[1].get("scenic_area") == "拈花湾禅意小镇"), reverse=True)
    for score, attraction in candidates:
        if len(stops) >= max_count:
            if attraction["id"] in optional_set:
                summary["optional_not_selected_attraction_ids"].append(attraction["id"])
                trace.append(f"{attraction['name']} 是可选点，但路线站点已达到上限，未纳入。")
            else:
                summary["full_pool_not_selected_attraction_ids"].append(attraction["id"])
            continue
        if len(stops) >= target_count and attraction["id"] not in optional_set and score < 102:
            summary["full_pool_not_selected_attraction_ids"].append(attraction["id"])
            continue
        stay = get_default_stay_minutes(attraction)
        projected = _estimated_minutes(stops) + stay + (10 if stops else 0)
        if stops and projected > time_budget_minutes and attraction["id"] not in optional_set:
            summary["full_pool_not_selected_attraction_ids"].append(attraction["id"])
            continue
        selection_source = "optional_boost" if attraction["id"] in optional_set else "full_pool"
        constraint_type = "optional" if attraction["id"] in optional_set else "recommended"
        stop = _with_route_profile(
            _make_stop(
                order=len(stops) + 1,
                attraction=attraction,
                stay_minutes=stay,
                walk_minutes=10 if stops else 0,
                focus="全量候选池推荐",
                reason=explain_profile_match(attraction, theme),
                selection_source=selection_source,
            ),
            theme=theme,
            selection_source=selection_source,
        )
        stop.update(
            {
                "constraint_type": constraint_type,
                "constraint_reason": (
                    f"可选：{attraction['name']}由全量景点池和用户兴趣共同加权。"
                    if constraint_type == "optional"
                    else "推荐：经典模板之外的全量景点池补充点。"
                ),
                "decision_reason": (
                    f"{attraction['name']} 来自全量景点候选池，主题分 {stop['theme_score']}，用于补足路线丰富度。"
                    if constraint_type != "optional"
                    else f"{attraction['name']} 是用户可选兴趣点，来自全量景点候选池，已优先纳入。"
                ),
            }
        )
        stops.append(stop)
        existing_ids.add(attraction["id"])
        summary["full_pool_selected_attraction_ids"].append(attraction["id"])
        trace.append(
            f"{attraction['name']} 来自全量景点池，selection_source={selection_source}，主题分 {stop['theme_score']}。"
        )

    return _reorder_stops(stops)


def _safe_tolerance(value: str | None) -> str:
    normalized = _normalize(value)
    return normalized if normalized in VALID_TOLERANCES else "medium"


def _crowd_note(record: dict[str, Any], *, avoid_crowd: bool, tolerance: str, adjusted: bool) -> str:
    level = record["crowd_level"]
    wait = record["wait_minutes"]
    if level == "high" and avoid_crowd:
        if adjusted:
            return f"模拟拥挤度高，预计等待 {wait} 分钟；已建议错峰或延后，不把这里作为长停留点。"
        return f"模拟拥挤度高，预计等待 {wait} 分钟；这是核心点，建议稍后返回或缩短停留。"
    if level == "high":
        return f"模拟拥挤度高，预计等待 {wait} 分钟；你选择可接受排队，路线保留该点。"
    if level == "medium" and tolerance == "low":
        return f"模拟拥挤度适中，预计等待 {wait} 分钟；舒适优先时建议快速通过。"
    if level == "medium":
        return f"模拟拥挤度适中，预计等待 {wait} 分钟；按计划游览即可。"
    return f"模拟拥挤度较低，预计等待 {wait} 分钟；适合停留和讲解。"


def classify_crowd_action(
    *,
    stop: dict[str, Any],
    record: dict[str, Any],
    avoid_crowd: bool,
    threshold: int,
) -> str:
    is_must_visit = stop.get("constraint_type") == "must_visit"
    over_threshold = record["crowd_score"] > threshold
    if not avoid_crowd:
        return "keep"
    if is_must_visit and record["crowd_level"] == "high":
        return "delay" if stop["order"] > 1 else "keep_with_warning"
    if over_threshold and stop["order"] > 1:
        return "delay"
    if record["crowd_level"] == "high":
        return "keep_with_warning"
    return "keep"


def _apply_crowd_to_stops(
    *,
    stops: list[dict[str, Any]],
    avoid_crowd: bool,
    crowd_tolerance: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    enriched: list[dict[str, Any]] = []
    trace: list[str] = []
    tolerance = _safe_tolerance(crowd_tolerance)
    threshold = {"low": 45, "medium": 70, "high": 90}[tolerance]
    delayed: list[dict[str, Any]] = []

    for stop in stops:
        record = get_crowd_record(stop["attraction_id"])
        is_must_visit = stop.get("constraint_type") == "must_visit"
        crowd_action = classify_crowd_action(
            stop=stop,
            record=record,
            avoid_crowd=avoid_crowd,
            threshold=threshold,
        )
        should_delay = crowd_action == "delay"
        if crowd_action == "delay":
            crowd_decision = "拥挤处理：延后该站并缩短停留。"
        elif crowd_action == "keep_with_warning":
            crowd_decision = "拥挤处理：保留该站，但提醒错峰或缩短停留。"
        else:
            crowd_decision = "拥挤处理：按计划保留。"
        adjusted_stop = {
            **stop,
            "crowd_level": record["crowd_level"],
            "crowd_score": record["crowd_score"],
            "wait_minutes": record["wait_minutes"],
            "crowd_note": _crowd_note(record, avoid_crowd=avoid_crowd, tolerance=tolerance, adjusted=should_delay),
            "crowd_action": crowd_action,
            "decision_reason": f"{stop.get('decision_reason', '')} {crowd_decision}".strip(),
        }
        if should_delay:
            adjusted_stop["stay_minutes"] = max(12, int(adjusted_stop["stay_minutes"]) - 8)
            delayed.append(adjusted_stop)
            if is_must_visit:
                trace.append(f"{stop['name']} 是必去点且当前拥挤，规则禁止删除，已延后并提示错峰。")
            else:
                trace.append(
                    f"{stop['name']} 当前为 high/高拥挤或超过容忍阈值，已降权并延后，建议错峰返回。"
                    if record["crowd_level"] == "high"
                    else f"{stop['name']} 超过舒适阈值，已缩短停留。"
                )
        else:
            enriched.append(adjusted_stop)
            if record["crowd_level"] == "high":
                if is_must_visit:
                    trace.append(f"{stop['name']} 是必去点但模拟拥挤度高，路线保留并提示稍后错峰。")
                else:
                    trace.append(f"{stop['name']} 是路线核心点但模拟拥挤度高，路线保留并提示错峰。")

    if delayed:
        trace.append("已将可延后的拥挤站点放到路线后段，优先保障前半程舒适度。")
    adjusted = [*enriched, *delayed]
    for index, stop in enumerate(adjusted, start=1):
        stop["order"] = index
        if index == 1:
            stop["walk_minutes_from_previous"] = 0
    return adjusted, trace


def _score_route(
    *,
    theme: str,
    stops: list[dict[str, Any]],
    budget: int,
    estimated: int,
    group_type: str | None,
    intensity: str | None,
    interests: list[str] | None,
    avoid_crowd: bool,
    tolerance: str,
) -> dict[str, int]:
    route_text = " ".join(
        [
            theme,
            group_type or "",
            intensity or "",
            " ".join(interests or []),
            " ".join(str(tag) for stop in stops for tag in stop.get("tags", [])),
        ]
    ).lower()
    theme_keywords = {
        "family": ["亲子", "family", "孩子", "长辈"],
        "history": ["历史", "文化", "研学"],
        "nature": ["自然", "花海", "休闲", "慢游"],
        "blessing": ["祈福", "朝圣", "佛教", "禅寺"],
        "photo": ["拍照", "打卡", "摄影", "夜景"],
    }
    theme_match = 82 + (10 if any(key in route_text for key in theme_keywords[theme]) else 0)
    time_over = max(0, estimated - budget)
    time_fit = max(60, 96 - int(time_over * 0.65) - abs(budget - estimated) // 18)
    group_fit = 88
    if theme == "family" and group_type in {"family", "亲子", "长辈"}:
        group_fit = 96
    elif group_type:
        group_fit = 86
    avg_crowd = sum(int(stop.get("crowd_score", 20)) for stop in stops) / max(len(stops), 1)
    high_count = sum(1 for stop in stops if stop.get("crowd_level") == "high")
    tolerance_bonus = {"low": 0, "medium": 5, "high": 10}[tolerance]
    crowd_comfort = max(45, int(104 - avg_crowd - high_count * (9 if avoid_crowd else 4) + tolerance_bonus))
    stop_quality = min(96, 78 + len(stops) * 3)
    return {
        "theme_match": min(theme_match, 96),
        "time_fit": min(time_fit, 98),
        "group_fit": group_fit,
        "crowd_comfort": min(crowd_comfort, 96),
        "stop_quality": stop_quality,
    }


def _overall_score(score_breakdown: dict[str, int]) -> int:
    weighted = (
        score_breakdown["theme_match"] * 0.24
        + score_breakdown["time_fit"] * 0.2
        + score_breakdown["group_fit"] * 0.16
        + score_breakdown["crowd_comfort"] * 0.24
        + score_breakdown["stop_quality"] * 0.16
    )
    return max(0, min(100, round(weighted)))


def _route_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(str(payload).encode("utf-8")).hexdigest()[:10]
    return f"route-{digest}"


def _share_payload(route_id: str, title: str | None = None) -> dict[str, Any]:
    digest = hashlib.sha1(route_id.encode("utf-8")).hexdigest()[:6].upper()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(timespec="seconds")
    return {
        "route_id": route_id,
        "route_title": title,
        "share_code": f"LJ-{digest}",
        "share_url": f"/route/{route_id}/share?code=LJ-{digest}",
        "qr_payload": f"lingjing://route/{route_id}?code=LJ-{digest}",
        "expires_at": expires_at,
        "expires_in_minutes": 30,
    }


def _parse_share_expires_at(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def recommend_route(
    *,
    theme: str | None = None,
    time_budget_minutes: int | None = None,
    group_type: str | None = None,
    intensity: str | None = None,
    interests: list[str] | None = None,
    start_attraction_id: str | None = None,
    avoid_crowd: bool = True,
    crowd_tolerance: str = "medium",
    must_visit_attraction_ids: list[str] | None = None,
    optional_attraction_ids: list[str] | None = None,
    avoid_attraction_ids: list[str] | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    budget = _safe_budget(time_budget_minutes)
    chosen_theme = _infer_theme(theme, group_type, interests)
    tolerance = _safe_tolerance(crowd_tolerance)
    stops = _select_template_stops(
        theme=chosen_theme,
        time_budget_minutes=budget,
        start_attraction_id=start_attraction_id,
    )
    normalized_constraints = normalize_route_constraints(
        must_visit_attraction_ids=must_visit_attraction_ids,
        optional_attraction_ids=optional_attraction_ids,
        avoid_attraction_ids=avoid_attraction_ids,
        start_attraction_id=start_attraction_id,
    )
    stops, constraint_trace, constraint_summary, constraint_conflicts = apply_route_constraints(
        stops=stops,
        constraints=normalized_constraints,
        time_budget_minutes=budget,
        theme=chosen_theme,
    )
    full_pool_trace: list[str] = []
    stops = _add_full_pool_candidates(
        stops=stops,
        constraints=normalized_constraints,
        theme=chosen_theme,
        time_budget_minutes=budget,
        avoid_crowd=avoid_crowd,
        crowd_tolerance=tolerance,
        summary=constraint_summary,
        trace=full_pool_trace,
    )
    stops = _trim_for_time_budget(
        stops=stops,
        budget=budget,
        summary=constraint_summary,
        trace=full_pool_trace,
    )
    stops, crowd_trace = _apply_crowd_to_stops(
        stops=stops,
        avoid_crowd=avoid_crowd,
        crowd_tolerance=tolerance,
    )
    estimated = _estimated_minutes(stops)
    template = ROUTE_TEMPLATES[chosen_theme]
    score_breakdown = _score_route(
        theme=chosen_theme,
        stops=stops,
        budget=budget,
        estimated=estimated,
        group_type=group_type,
        intensity=intensity,
        interests=interests,
        avoid_crowd=avoid_crowd,
        tolerance=tolerance,
    )
    recommendation_score = _overall_score(score_breakdown)
    high_stops = [stop for stop in stops if stop.get("crowd_level") == "high"]
    assumptions = [
        f"按{THEME_LABELS[chosen_theme]}偏好生成",
        f"游览时长约 {budget} 分钟",
        "当前为 mock 模式，步行时间为演示估算，不代表真实导航",
        "拥挤度来自 mock_simulation 模拟数据，不代表真实景区客流",
    ]
    if group_type:
        assumptions.append(f"同行类型：{group_type}")
    if intensity:
        assumptions.append(f"体力偏好：{intensity}")
    if interests:
        assumptions.append(f"兴趣：{'、'.join(interests[:4])}")

    route_core = {
        "theme": chosen_theme,
        "time_budget_minutes": budget,
        "group_type": group_type,
        "intensity": intensity,
        "interests": interests or [],
        "start_attraction_id": start_attraction_id,
        "avoid_crowd": avoid_crowd,
        "crowd_tolerance": tolerance,
        "must_visit_attraction_ids": normalized_constraints["must_visit_attraction_ids"],
        "optional_attraction_ids": normalized_constraints["optional_attraction_ids"],
        "avoid_attraction_ids": normalized_constraints["avoid_attraction_ids"],
        "stops": [stop["attraction_id"] for stop in stops],
    }
    route_id = _route_id(route_core)
    share = _share_payload(route_id, template["title"])
    decision_trace = [
        f"根据主题={THEME_LABELS[chosen_theme]}、时长={budget}分钟、同行={group_type or '未指定'}、体力={intensity or '未指定'}生成候选路线。",
        "经典路线模板仅作为 seed，最终会结合全部已解析景点候选池、用户约束和拥挤度重新筛选。",
        f"约束优先级：{' > '.join(ROUTE_CONSTRAINT_RULES['priority'])}。",
        *constraint_trace,
        *full_pool_trace,
        f"拥挤策略：avoid_crowd={str(avoid_crowd).lower()}，crowd_tolerance={tolerance}，数据源={CROWD_SOURCE}。",
        *crowd_trace,
    ]
    if constraint_summary.get("warning"):
        decision_trace.append(f"约束提醒：{constraint_summary['warning']}")
    if high_stops:
        names = "、".join(stop["name"] for stop in high_stops)
        decision_trace.append(f"高拥挤点：{names}；核心点保留时会提示错峰，非核心点会降权或延后。")
    else:
        decision_trace.append("当前候选路线没有 high 拥挤站点，整体舒适度较好。")
    decision_trace.append("mock_simulation 仅用于比赛演示，不代表实时客流。")
    result = {
        "id": route_id,
        "title": template["title"],
        "theme": chosen_theme,
        "theme_label": THEME_LABELS[chosen_theme],
        "summary": template["summary"],
        "suitable_for": template["suitable_for"],
        "constraints": {
            "must_visit_attraction_ids": normalized_constraints["must_visit_attraction_ids"],
            "optional_attraction_ids": normalized_constraints["optional_attraction_ids"],
            "avoid_attraction_ids": normalized_constraints["avoid_attraction_ids"],
            "rules": ROUTE_CONSTRAINT_RULES,
        },
        "constraint_summary": constraint_summary,
        "constraint_conflicts": constraint_conflicts,
        "estimated_duration_minutes": estimated,
        "time_budget_minutes": budget,
        "recommendation_score": recommendation_score,
        "score_breakdown": score_breakdown,
        "decision_trace": decision_trace,
        "crowd_policy": {
            "avoid_crowd": avoid_crowd,
            "crowd_tolerance": tolerance,
            "source": CROWD_SOURCE,
            "caveat": "当前为模拟拥挤度/演示数据，不代表真实客流。",
        },
        "stops": stops,
        "assumptions": assumptions,
        "performance_tips": [
            "演艺点建议提前 10-15 分钟到达。",
            "如果现场拥挤，可跳过单个停留点，直接进入下一站。",
            "高拥挤站点建议避开整点前后 20 分钟，或先游览低拥挤替代点。",
        ],
        "share": share,
        "mode": "mock",
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }
    ROUTE_CACHE[route_id] = result
    return result


def get_route_share(route_id: str, code: str | None = None) -> dict[str, Any]:
    route = ROUTE_CACHE.get(route_id)
    if route is None:
        raise ApiError(
            code="ROUTE_SHARE_NOT_FOUND",
            message="没有找到这条路线分享。",
            cause=f"Route share cache does not contain route_id={route_id}.",
            fix="请先在当前服务进程中重新生成路线，再使用新的分享链接。",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    share = route.get("share") or {}
    expected_code = str(share.get("share_code") or "")
    if not code or code != expected_code:
        raise ApiError(
            code="ROUTE_SHARE_CODE_INVALID",
            message="分享码不正确，请回到终端重新生成路线。",
            cause=f"Invalid share code for route_id={route_id}.",
            fix="确认 URL 中的 code 参数与路线分享码一致。",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    expires_at = _parse_share_expires_at(str(share.get("expires_at") or "1970-01-01T00:00:00+00:00"))
    if expires_at <= datetime.now(timezone.utc):
        raise ApiError(
            code="ROUTE_SHARE_EXPIRED",
            message="这条路线分享已过期，请在 Kiosk 重新生成。",
            cause=f"Share expired at {expires_at.isoformat()} for route_id={route_id}.",
            fix="分享码默认 30 分钟有效，过期后重新调用 POST /api/routes/recommend。",
            status_code=status.HTTP_410_GONE,
        )

    return route


def route_theme_options() -> list[dict[str, str]]:
    return [{"id": key, "label": label} for key, label in THEME_LABELS.items()]
