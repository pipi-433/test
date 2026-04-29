from __future__ import annotations

import hashlib
import time
from copy import deepcopy
from typing import Any


ROUTE_MEMORY_STORE: dict[str, dict[str, Any]] = {}


def _new_session_id() -> str:
    digest = hashlib.sha1(str(time.perf_counter_ns()).encode("utf-8")).hexdigest()[:10]
    return f"mock-session-{digest}"


def default_memory(session_id: str | None = None) -> dict[str, Any]:
    return {
        "session_id": session_id or _new_session_id(),
        "preferences": {
            "theme": None,
            "time_budget_minutes": 240,
            "group_type": None,
            "intensity": "balanced",
            "interests": [],
            "avoid_crowd": True,
            "crowd_tolerance": "medium",
            "start_attraction_id": None,
        },
        "constraints": {
            "must_visit_attraction_ids": [],
            "optional_attraction_ids": [],
            "avoid_attraction_ids": [],
        },
        "current_route_id": None,
        "current_stop_index": 0,
        "removed_stops": [],
        "delayed_stops": [],
        "high_crowd_stops": [],
        "last_operation": None,
        "last_reason": None,
        "turn_count": 0,
    }


def get_route_memory(session_id: str | None = None) -> dict[str, Any]:
    if session_id and session_id in ROUTE_MEMORY_STORE:
        return deepcopy(ROUTE_MEMORY_STORE[session_id])
    memory = default_memory(session_id)
    ROUTE_MEMORY_STORE[memory["session_id"]] = deepcopy(memory)
    return memory


def save_route_memory(memory: dict[str, Any]) -> dict[str, Any]:
    ROUTE_MEMORY_STORE[memory["session_id"]] = deepcopy(memory)
    return deepcopy(memory)


def _merge_unique(current: list[str], incoming: list[str]) -> list[str]:
    result = list(current)
    for item in incoming:
        if item and item not in result:
            result.append(item)
    return result


def _remove_many(current: list[str], values: list[str]) -> list[str]:
    remove = set(values)
    return [item for item in current if item not in remove]


def apply_intent_to_memory(
    *,
    memory: dict[str, Any],
    intent: dict[str, Any],
    selected_attraction_id: str | None = None,
    current_route_id: str | None = None,
) -> dict[str, Any]:
    updated = deepcopy(memory)
    preferences = updated["preferences"]
    constraints = updated["constraints"]
    operation = intent.get("operation") or "none"

    if intent.get("theme"):
        preferences["theme"] = intent["theme"]
    if intent.get("time_budget_minutes"):
        preferences["time_budget_minutes"] = int(intent["time_budget_minutes"])
    if intent.get("group_type"):
        preferences["group_type"] = intent["group_type"]
    if intent.get("intensity"):
        preferences["intensity"] = intent["intensity"]
    if intent.get("interests"):
        preferences["interests"] = _merge_unique(preferences.get("interests", []), intent["interests"])
    if intent.get("avoid_crowd"):
        preferences["avoid_crowd"] = True
    if intent.get("crowd_tolerance"):
        preferences["crowd_tolerance"] = intent["crowd_tolerance"]
    if selected_attraction_id:
        preferences["start_attraction_id"] = selected_attraction_id
    if operation == "start_here" and selected_attraction_id:
        preferences["start_attraction_id"] = selected_attraction_id

    constraints["must_visit_attraction_ids"] = _merge_unique(
        constraints.get("must_visit_attraction_ids", []),
        intent.get("must_visit_attraction_ids") or [],
    )
    constraints["optional_attraction_ids"] = _merge_unique(
        constraints.get("optional_attraction_ids", []),
        intent.get("optional_attraction_ids") or [],
    )
    if operation == "remove_must_visit":
        remove_ids = intent.get("avoid_attraction_ids") or []
        constraints["must_visit_attraction_ids"] = _remove_many(
            constraints.get("must_visit_attraction_ids", []),
            remove_ids,
        )
        constraints["optional_attraction_ids"] = _remove_many(
            constraints.get("optional_attraction_ids", []),
            remove_ids,
        )
        constraints["avoid_attraction_ids"] = _merge_unique(
            constraints.get("avoid_attraction_ids", []),
            remove_ids,
        )
    else:
        constraints["avoid_attraction_ids"] = _merge_unique(
            constraints.get("avoid_attraction_ids", []),
            intent.get("avoid_attraction_ids") or [],
        )

    if operation == "shorten":
        preferences["time_budget_minutes"] = max(90, int(preferences.get("time_budget_minutes") or 240) - 60)
        updated["last_reason"] = "用户要求缩短路线，已降低时间预算并保留必去点。"
    elif operation == "less_walking":
        preferences["intensity"] = "easy"
        preferences["time_budget_minutes"] = max(90, int(preferences.get("time_budget_minutes") or 240) - 30)
        updated["last_reason"] = "用户表示疲劳或少走路，已切换轻松强度。"
    elif operation == "avoid_crowd":
        preferences["avoid_crowd"] = True
        preferences["crowd_tolerance"] = "low"
        updated["last_reason"] = "用户要求避开拥挤，已切换舒适优先。"
    elif operation == "more_photo":
        preferences["theme"] = "photo"
        updated["last_reason"] = "用户希望多拍照，已提高拍照打卡路线权重。"
    elif operation == "more_history":
        preferences["theme"] = "history"
        updated["last_reason"] = "用户希望文化历史更深入，已提高历史主题权重。"
    elif operation == "set_must_visit":
        updated["last_reason"] = "用户设置了必去景点，规划器会优先保留。"
    elif operation == "remove_must_visit":
        updated["last_reason"] = "用户明确放弃部分必去点，已从必去约束中移除。"
    else:
        updated["last_reason"] = "已根据自然语言偏好更新路线记忆。"

    if current_route_id:
        updated["current_route_id"] = current_route_id
    updated["last_operation"] = operation
    updated["turn_count"] = int(updated.get("turn_count") or 0) + 1
    return save_route_memory(updated)


def update_memory_after_route(memory: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(memory)
    updated["current_route_id"] = route.get("id")
    updated["high_crowd_stops"] = [
        stop["attraction_id"] for stop in route.get("stops", []) if stop.get("crowd_level") == "high"
    ]
    updated["delayed_stops"] = [
        stop["attraction_id"] for stop in route.get("stops", []) if stop.get("crowd_action") == "delay"
    ]
    return save_route_memory(updated)
