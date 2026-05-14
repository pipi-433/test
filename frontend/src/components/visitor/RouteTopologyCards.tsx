import type { RouteRecommendation, RouteStop } from "../../api/client";
import { ImageIcon } from "../icons/LingshanImageIcons";

function backtrackRiskLabel(value: string | null | undefined) {
  const labels: Record<string, string> = {
    low: "顺路",
    medium: "轻微绕行",
    high: "可能折返",
    transfer: "跨区域",
  };
  return value ? labels[value] || value : "";
}

function transportLabel(value: string | null | undefined) {
  const labels: Record<string, string> = {
    walk: "步行",
    sightseeing_bus_optional: "可选观光车",
    sightseeing_bus_recommended: "建议观光车",
    area_transfer: "跨区域交通",
  };
  return value ? labels[value] || value : "";
}

function hasStopTopology(stop: RouteStop) {
  return Boolean(
    stop.topology_line_name ||
      stop.walking_minutes_to_next !== undefined ||
      stop.transport_hint ||
      stop.backtrack_risk ||
      stop.smoothness_reason,
  );
}

export function RouteTopologySummary({
  route,
  compact = false,
  showExplanation = true,
}: {
  route: RouteRecommendation;
  compact?: boolean;
  showExplanation?: boolean;
}) {
  const topology = route.route_topology;
  if (!topology) {
    return null;
  }

  const busSuggestion = topology.sightseeing_bus_suggestion || "以步行为主";
  const explanation = (topology.topology_explanation || []).slice(0, compact ? 2 : 3);

  return (
    <section className={compact ? "route-topology-card route-topology-card--compact" : "route-topology-card"} aria-label="导览图拓扑">
      <div className="route-topology-card__header">
        <div>
          <span className="eyebrow">基于导览图拓扑</span>
          <h3>导览图拓扑</h3>
        </div>
        <div className="route-topology-card__score">
          <strong>{topology.route_smoothness_score}</strong>
          <span>顺路指数</span>
        </div>
      </div>

      <div className="route-topology-metrics" aria-label="路线拓扑指标">
        <span>
          <small>总步行估算</small>
          <strong>{topology.total_walking_minutes} 分钟</strong>
        </span>
        <span>
          <small>回头路次数</small>
          <strong>{topology.backtrack_count} 次</strong>
        </span>
        <span>
          <small>观光车建议</small>
          <strong>{busSuggestion}</strong>
        </span>
      </div>

      {topology.line_names.length ? (
        <div className="route-topology-lines" aria-label="涉及游线">
          {topology.line_names.map((name) => (
            <span key={name}>{name}</span>
          ))}
        </div>
      ) : null}

      {showExplanation && explanation.length ? (
        <div className="route-topology-explain" aria-label="为什么这样顺路">
          <strong>为什么这样顺路</strong>
          <ul>
            {explanation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="route-topology-note">
        <ImageIcon name="route-path" size={17} />
        {topology.source_note || "导览图人工抽象，不代表真实 GPS 导航。"}
      </p>
    </section>
  );
}

export function StopTopologyMeta({ stop, compact = false }: { stop: RouteStop; compact?: boolean }) {
  if (!hasStopTopology(stop)) {
    return null;
  }

  const risk = backtrackRiskLabel(stop.backtrack_risk);
  const transport = transportLabel(stop.transport_hint);
  const hasNextWalk = typeof stop.walking_minutes_to_next === "number";
  const nextText =
    stop.transport_hint === "area_transfer"
      ? "下一段跨区域交通"
      : hasNextWalk
        ? `下一站步行约 ${stop.walking_minutes_to_next} 分钟`
        : "";

  return (
    <div className={compact ? "stop-topology stop-topology--compact" : "stop-topology"} aria-label={`${stop.name} 拓扑信息`}>
      <div className="stop-topology__chips">
        {stop.topology_line_name ? <span className="stop-topology__line">{stop.topology_line_name}</span> : null}
        {transport ? <span>{transport}</span> : null}
        {risk ? <span className={`stop-topology__risk stop-topology__risk--${stop.backtrack_risk || "unknown"}`}>{risk}</span> : null}
      </div>
      {nextText || stop.smoothness_reason ? (
        <div className="stop-topology__leg">
          {nextText ? <strong>{nextText}</strong> : null}
          {stop.smoothness_reason ? <small>{stop.smoothness_reason}</small> : null}
        </div>
      ) : null}
    </div>
  );
}
