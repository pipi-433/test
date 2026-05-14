from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.repositories.content_repository import list_attractions


ROOT_DIR = Path(__file__).resolve().parents[3]
SCENIC_GRAPH_PATH = ROOT_DIR / "data" / "processed" / "scenic_graph.json"


@lru_cache(maxsize=1)
def load_scenic_graph() -> dict[str, Any]:
    return json.loads(SCENIC_GRAPH_PATH.read_text(encoding="utf-8"))


def _node_index(graph: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    payload = graph or load_scenic_graph()
    return {str(node["id"]): node for node in payload.get("nodes", [])}


def _line_index(graph: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    payload = graph or load_scenic_graph()
    return {str(line["id"]): line for line in payload.get("lines", [])}


def _edge_index(graph: dict[str, Any] | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    payload = graph or load_scenic_graph()
    return {(str(edge["from"]), str(edge["to"])): edge for edge in payload.get("edges", [])}


def _primary_line(node: dict[str, Any]) -> str | None:
    line_ids = node.get("line_ids") or []
    return str(line_ids[0]) if line_ids else None


def get_topology_for_attraction(attraction_id: str) -> dict[str, Any] | None:
    graph = load_scenic_graph()
    node_id = (graph.get("attraction_node_map") or {}).get(attraction_id)
    if not node_id:
        return None
    node = _node_index(graph).get(str(node_id))
    if not node:
        return None
    line_id = _primary_line(node)
    line = _line_index(graph).get(line_id or "", {})
    return {
        "node": dict(node),
        "line": dict(line) if line else None,
        "graph_version": graph.get("version"),
        "source_note": graph.get("source_note"),
    }


def get_topology_for_stop(attraction_id: str) -> dict[str, Any] | None:
    return get_topology_for_attraction(attraction_id)


def _same_area_leg(from_node: dict[str, Any], to_node: dict[str, Any]) -> dict[str, Any]:
    line_ids_from = set(str(item) for item in from_node.get("line_ids", []))
    line_ids_to = set(str(item) for item in to_node.get("line_ids", []))
    common_lines = line_ids_from & line_ids_to
    from_order = int(from_node.get("order_index") or 0)
    to_order = int(to_node.get("order_index") or 0)
    order_delta = to_order - from_order
    line_id = sorted(common_lines)[0] if common_lines else None

    if common_lines:
        if order_delta >= 0:
            risk = "low" if order_delta <= 4 else "medium"
            minutes = max(4, min(18, abs(order_delta) * 4))
            reason = "同一导览线顺向推进，回头路风险较低。"
        else:
            risk = "high"
            minutes = max(6, min(20, abs(order_delta) * 5))
            reason = "同一导览线反向移动，存在回头路风险。"
        return {
            "walking_minutes": minutes,
            "backtrack_risk": risk,
            "transport_hint": "walk",
            "line_id": line_id,
            "smoothness_reason": reason,
        }

    if "central_axis" in line_ids_from and "east_treasure" in line_ids_to:
        return {
            "walking_minutes": 14,
            "backtrack_risk": "medium",
            "transport_hint": "walk_or_sightseeing_bus",
            "line_id": "east_treasure",
            "smoothness_reason": "从中轴线转入宝藏东线，适合在九龙灌浴/百子戏弥勒后分流。",
        }
    if "east_treasure" in line_ids_from and "central_axis" in line_ids_to:
        return {
            "walking_minutes": 16,
            "backtrack_risk": "medium",
            "transport_hint": "walk_or_sightseeing_bus",
            "line_id": "central_axis",
            "smoothness_reason": "从宝藏东线回到中轴线，需要通过连接段回转。",
        }
    if {"east_treasure", "west_meditation"} & line_ids_from and {"east_treasure", "west_meditation"} & line_ids_to:
        return {
            "walking_minutes": 20,
            "backtrack_risk": "high",
            "transport_hint": "walk",
            "line_id": None,
            "smoothness_reason": "东线与西线跨线较远，建议通过中轴连接，回头路风险较高。",
        }

    return {
        "walking_minutes": 12,
        "backtrack_risk": "medium",
        "transport_hint": "walk",
        "line_id": None,
        "smoothness_reason": "两个点位不在同一抽象游线，按导览图连接段估算。",
    }


def estimate_leg(from_attraction_id: str, to_attraction_id: str) -> dict[str, Any]:
    graph = load_scenic_graph()
    nodes = _node_index(graph)
    lines = _line_index(graph)
    edge_lookup = _edge_index(graph)
    node_map = graph.get("attraction_node_map") or {}
    from_node_id = node_map.get(from_attraction_id)
    to_node_id = node_map.get(to_attraction_id)
    if not from_node_id or not to_node_id or from_node_id not in nodes or to_node_id not in nodes:
        return {
            "from_attraction_id": from_attraction_id,
            "to_attraction_id": to_attraction_id,
            "walking_minutes": 12,
            "backtrack_risk": "medium",
            "transport_hint": "walk",
            "line_id": None,
            "line_name": None,
            "direction_note": "拓扑映射缺失，使用保守演示估算。",
            "smoothness_reason": "缺少拓扑节点，按中等步行成本兜底。",
        }
    from_node = nodes[str(from_node_id)]
    to_node = nodes[str(to_node_id)]
    if from_node["area_id"] != to_node["area_id"]:
        return {
            "from_attraction_id": from_attraction_id,
            "to_attraction_id": to_attraction_id,
            "walking_minutes": None,
            "backtrack_risk": "transfer",
            "transport_hint": "area_transfer",
            "line_id": None,
            "line_name": None,
            "direction_note": "灵山胜境与拈花湾之间为跨景区转场，不按步行分钟估算。",
            "smoothness_reason": "跨景区移动需要交通转场；本拓扑不代表真实导航时间。",
        }
    edge = edge_lookup.get((str(from_node_id), str(to_node_id)))
    if edge:
        line = lines.get(str(edge.get("line_id")), {})
        return {
            "from_attraction_id": from_attraction_id,
            "to_attraction_id": to_attraction_id,
            "walking_minutes": edge.get("walking_minutes"),
            "backtrack_risk": edge.get("backtrack_risk"),
            "transport_hint": edge.get("transport_hint"),
            "line_id": edge.get("line_id"),
            "line_name": line.get("name"),
            "direction_note": edge.get("direction_note"),
            "smoothness_reason": "命中导览图抽象边，按该线段估算。",
        }
    reverse = edge_lookup.get((str(to_node_id), str(from_node_id)))
    if reverse:
        line = lines.get(str(reverse.get("line_id")), {})
        minutes = int(reverse.get("walking_minutes") or 8) + 2
        return {
            "from_attraction_id": from_attraction_id,
            "to_attraction_id": to_attraction_id,
            "walking_minutes": minutes,
            "backtrack_risk": "high",
            "transport_hint": reverse.get("transport_hint") or "walk",
            "line_id": reverse.get("line_id"),
            "line_name": line.get("name"),
            "direction_note": "该段与导览图推荐方向相反，按回头路估算。",
            "smoothness_reason": "反向经过导览图抽象边，回头路风险较高。",
        }
    leg = _same_area_leg(from_node, to_node)
    line = lines.get(str(leg.get("line_id")), {})
    return {
        "from_attraction_id": from_attraction_id,
        "to_attraction_id": to_attraction_id,
        "walking_minutes": leg.get("walking_minutes"),
        "backtrack_risk": leg.get("backtrack_risk"),
        "transport_hint": leg.get("transport_hint"),
        "line_id": leg.get("line_id"),
        "line_name": line.get("name"),
        "direction_note": leg.get("smoothness_reason"),
        "smoothness_reason": leg.get("smoothness_reason"),
    }


def _topology_payload_for_stop(attraction_id: str) -> dict[str, Any]:
    topology = get_topology_for_attraction(attraction_id)
    if not topology:
        return {
            "topology_line_id": None,
            "topology_line_name": None,
            "topology_node_id": None,
            "topology_order_index": None,
            "topology_note": "未找到导览图拓扑映射。",
        }
    node = topology["node"]
    line = topology.get("line") or {}
    return {
        "topology_line_id": line.get("id"),
        "topology_line_name": line.get("name"),
        "topology_node_id": node.get("id"),
        "topology_order_index": node.get("order_index"),
        "topology_note": node.get("topology_note") or node.get("source_note") or topology.get("source_note"),
    }


def _build_topology_summary(enriched_stops: list[dict[str, Any]], legs: list[dict[str, Any]]) -> dict[str, Any]:
    graph = load_scenic_graph()
    lines = _line_index(graph)
    line_ids: list[str] = []
    for stop in enriched_stops:
        line_id = stop.get("topology_line_id")
        if line_id and line_id not in line_ids:
            line_ids.append(str(line_id))
    total_walking = sum(int(leg.get("walking_minutes") or 0) for leg in legs if leg.get("walking_minutes") is not None)
    backtrack_count = sum(1 for leg in legs if leg.get("backtrack_risk") == "high")
    medium_count = sum(1 for leg in legs if leg.get("backtrack_risk") == "medium")
    transfer_count = sum(1 for leg in legs if leg.get("backtrack_risk") == "transfer")
    bus_edges = [leg for leg in legs if "sightseeing_bus" in str(leg.get("transport_hint") or "")]
    smoothness = max(0, min(100, 100 - backtrack_count * 16 - medium_count * 6 - transfer_count * 8 + min(len(bus_edges), 1) * 3))
    line_names = [str(lines[line_id]["name"]) for line_id in line_ids if line_id in lines]
    explanation = [
        "路线拓扑基于导览图人工抽象，用于顺路解释，不代表真实 GPS 导航。",
    ]
    if "central_axis" in line_ids:
        explanation.append("路线包含导览图中轴线，可按入口向北推进，减少回到入口的折返。")
    if "east_treasure" in line_ids:
        explanation.append("五印坛城、梵宫等点位属于线路2宝藏东线，适合作为中轴后的东线分流安排。")
    if "west_meditation" in line_ids:
        explanation.append("无尽意斋位于线路3愿心西线，跨线时会提示回头路风险。")
    if "nianhuawan_loop" in line_ids:
        explanation.append("拈花湾景点按独立环线覆盖，与灵山胜境之间标注为跨景区转场。")
    if backtrack_count:
        explanation.append(f"当前路线存在 {backtrack_count} 段较高回头路风险，已在站点 leg 上标注。")
    if transfer_count:
        explanation.append("路线包含灵山胜境与拈花湾之间的跨景区转场，不按步行分钟估算。")
    return {
        "source": "scenic_graph",
        "source_note": graph.get("source_note"),
        "line_ids": line_ids,
        "line_names": line_names,
        "route_smoothness_score": smoothness,
        "total_walking_minutes": total_walking,
        "backtrack_count": backtrack_count,
        "sightseeing_bus_suggestion": "可在九龙灌浴/灵山梵宫等观光车站附近结合现场运营选择观光车；当前为演示建议。" if bus_edges else None,
        "topology_explanation": explanation,
    }


def enrich_route_with_topology(stops: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched = [{**stop, **_topology_payload_for_stop(str(stop.get("attraction_id") or ""))} for stop in stops]
    legs: list[dict[str, Any]] = []
    for index, stop in enumerate(enriched):
        if index >= len(enriched) - 1:
            stop.update(
                {
                    "walking_minutes_to_next": None,
                    "next_attraction_id": None,
                    "transport_hint": None,
                    "backtrack_risk": None,
                    "smoothness_reason": "路线终点。",
                }
            )
            continue
        next_stop = enriched[index + 1]
        leg = estimate_leg(str(stop["attraction_id"]), str(next_stop["attraction_id"]))
        legs.append(leg)
        stop.update(
            {
                "walking_minutes_to_next": leg.get("walking_minutes"),
                "next_attraction_id": next_stop.get("attraction_id"),
                "transport_hint": leg.get("transport_hint"),
                "backtrack_risk": leg.get("backtrack_risk"),
                "smoothness_reason": leg.get("smoothness_reason"),
            }
        )
    return enriched, _build_topology_summary(enriched, legs)


def validate_graph_coverage(attractions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    graph = load_scenic_graph()
    nodes = _node_index(graph)
    node_map = graph.get("attraction_node_map") or {}
    items = attractions or list_attractions()
    attraction_ids = [str(item.get("id")) for item in items]
    missing_attraction_ids = [attraction_id for attraction_id in attraction_ids if attraction_id not in node_map]
    missing_node_ids = [
        str(node_id)
        for attraction_id, node_id in node_map.items()
        if attraction_id in attraction_ids and str(node_id) not in nodes
    ]
    route_candidate_missing_line = []
    for attraction_id in attraction_ids:
        node_id = node_map.get(attraction_id)
        node = nodes.get(str(node_id))
        if not node:
            continue
        if node.get("is_route_candidate") and (not node.get("line_ids") or node.get("order_index") is None):
            route_candidate_missing_line.append(attraction_id)
    return {
        "version": graph.get("version"),
        "attraction_count": len(attraction_ids),
        "mapped_count": len([item for item in attraction_ids if item in node_map]),
        "required_attraction_count": (graph.get("coverage") or {}).get("required_attraction_count"),
        "missing_attraction_ids": missing_attraction_ids,
        "missing_node_ids": missing_node_ids,
        "route_candidate_missing_line": route_candidate_missing_line,
        "ok": not missing_attraction_ids and not missing_node_ids and not route_candidate_missing_line,
    }
