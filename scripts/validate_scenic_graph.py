"""Validate the Task 06.15 scenic graph topology artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
GRAPH_PATH = ROOT / "data" / "processed" / "scenic_graph.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.repositories.content_repository import list_attractions  # noqa: E402
from app.services.scenic_graph_service import validate_graph_coverage  # noqa: E402


def load_graph() -> dict[str, Any]:
    if not GRAPH_PATH.exists():
        raise RuntimeError(f"Missing scenic graph: {GRAPH_PATH}")
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def main() -> int:
    graph = load_graph()
    errors: list[str] = []
    for key in ["areas", "lines", "nodes", "edges", "attraction_node_map"]:
        if not graph.get(key):
            errors.append(f"Missing or empty key: {key}")

    nodes = {str(node.get("id")): node for node in graph.get("nodes", [])}
    lines = {str(line.get("id")): line for line in graph.get("lines", [])}
    attractions = list_attractions()
    coverage = validate_graph_coverage(attractions)
    if not coverage["ok"]:
        errors.append(f"Coverage failed: {coverage}")

    for attraction_id, node_id in (graph.get("attraction_node_map") or {}).items():
        node = nodes.get(str(node_id))
        if not node:
            errors.append(f"Mapped node not found: {attraction_id} -> {node_id}")
            continue
        if node.get("attraction_id") != attraction_id:
            errors.append(f"Node attraction mismatch: {attraction_id} -> {node_id}")
        if node.get("is_route_candidate") and (not node.get("line_ids") or node.get("order_index") is None):
            errors.append(f"Route candidate missing line/order: {attraction_id} -> {node_id}")
        for line_id in node.get("line_ids") or []:
            if str(line_id) not in lines:
                errors.append(f"Node references unknown line: {node_id} -> {line_id}")

    for edge in graph.get("edges", []):
        from_node = str(edge.get("from"))
        to_node = str(edge.get("to"))
        line_id = str(edge.get("line_id"))
        if from_node not in nodes:
            errors.append(f"Edge from node missing: {from_node}")
        if to_node not in nodes:
            errors.append(f"Edge to node missing: {to_node}")
        if line_id not in lines:
            errors.append(f"Edge line missing: {line_id}")
        if edge.get("walking_minutes") is None:
            errors.append(f"Edge walking_minutes missing: {from_node}->{to_node}")

    summary = {
        "version": graph.get("version"),
        "area_count": len(graph.get("areas", [])),
        "line_count": len(graph.get("lines", [])),
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "attraction_count": len(attractions),
        "mapped_count": coverage.get("mapped_count"),
        "missing_attraction_ids": coverage.get("missing_attraction_ids"),
        "source_note": graph.get("source_note"),
        "ok": not errors,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
