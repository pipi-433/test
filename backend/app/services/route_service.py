from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.repositories.content_repository import get_attraction, list_attractions


DEFAULT_THEME = "family"

THEME_LABELS = {
    "family": "亲子轻松",
    "history": "历史文化",
    "nature": "自然休闲",
    "blessing": "祈福朝圣",
    "photo": "拍照打卡",
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


def _make_stop(
    *,
    order: int,
    attraction: dict[str, Any],
    stay_minutes: int,
    walk_minutes: int,
    focus: str,
    reason: str,
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
            _make_stop(
                order=len(selected) + 1,
                attraction=attraction,
                stay_minutes=stay,
                walk_minutes=walk if selected else 0,
                focus=focus,
                reason=reason,
            )
        )

    if start_attraction_id:
        start = get_attraction(start_attraction_id)
        if start and all(stop["attraction_id"] != start["id"] for stop in selected):
            selected.insert(
                0,
                _make_stop(
                    order=1,
                    attraction=start,
                    stay_minutes=18,
                    walk_minutes=0,
                    focus="从当前景点出发",
                    reason="根据你当前选择的景点，把它放在路线开头，方便现场继续游览。",
                ),
            )

    for index, stop in enumerate(selected, start=1):
        stop["order"] = index
        if index == 1:
            stop["walk_minutes_from_previous"] = 0
    return selected[:6]


def _estimated_minutes(stops: list[dict[str, Any]]) -> int:
    return sum(int(stop["stay_minutes"]) + int(stop["walk_minutes_from_previous"]) for stop in stops)


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


def recommend_route(
    *,
    theme: str | None = None,
    time_budget_minutes: int | None = None,
    group_type: str | None = None,
    intensity: str | None = None,
    interests: list[str] | None = None,
    start_attraction_id: str | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    budget = _safe_budget(time_budget_minutes)
    chosen_theme = _infer_theme(theme, group_type, interests)
    stops = _select_template_stops(
        theme=chosen_theme,
        time_budget_minutes=budget,
        start_attraction_id=start_attraction_id,
    )
    estimated = _estimated_minutes(stops)
    template = ROUTE_TEMPLATES[chosen_theme]
    assumptions = [
        f"按{THEME_LABELS[chosen_theme]}偏好生成",
        f"游览时长约 {budget} 分钟",
        "当前为 mock 模式，步行时间为演示估算，不代表真实导航",
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
        "stops": [stop["attraction_id"] for stop in stops],
    }
    route_id = _route_id(route_core)
    share = _share_payload(route_id, template["title"])
    result = {
        "id": route_id,
        "title": template["title"],
        "theme": chosen_theme,
        "theme_label": THEME_LABELS[chosen_theme],
        "summary": template["summary"],
        "suitable_for": template["suitable_for"],
        "estimated_duration_minutes": estimated,
        "time_budget_minutes": budget,
        "stops": stops,
        "assumptions": assumptions,
        "performance_tips": [
            "演艺点建议提前 10-15 分钟到达。",
            "如果现场拥挤，可跳过单个停留点，直接进入下一站。",
        ],
        "share": share,
        "mode": "mock",
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }
    ROUTE_CACHE[route_id] = result
    return result


def get_route_share(route_id: str) -> dict[str, Any]:
    route = ROUTE_CACHE.get(route_id)
    return _share_payload(route_id, route.get("title") if route else None)


def route_theme_options() -> list[dict[str, str]]:
    return [{"id": key, "label": label} for key, label in THEME_LABELS.items()]
