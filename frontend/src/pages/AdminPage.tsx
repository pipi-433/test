import {
  Activity,
  AlertTriangle,
  Bot,
  CalendarClock,
  ChartNoAxesCombined,
  Database,
  Gauge,
  Heart,
  HelpCircle,
  MessageSquareText,
  Plus,
  Route,
  Search,
  Settings,
  Share2,
  ToggleLeft,
  ToggleRight,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";

import { createOperationEvent, getAdminOperationEvents, getAnalyticsOverview, updateOperationEvent } from "../api/client";
import type { AnalyticsOverview, OperationEvent, OperationEventCreateRequest, OperationEventSeverity, OperationEventType } from "../api/client";
import { Button } from "../components/Button";
import { MetricCard } from "../components/MetricCard";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { providerRows } from "../data/mock";

type ProviderMap = Record<string, { provider: string; status: string }>;

const quickOperationEvents: Array<{
  label: string;
  iconLabel: string;
  payload: OperationEventCreateRequest;
}> = [
  {
    label: "拥挤",
    iconLabel: "crowd",
    payload: {
      attraction_id: "lingshan-ls-006",
      event_type: "crowd",
      severity: "warning",
      message: "管理员发布：九龙灌浴广场排队增多，建议路线预留 30 分钟或错峰。",
    },
  },
  {
    label: "临时关闭",
    iconLabel: "closed",
    payload: {
      attraction_id: "lingshan-ls-013",
      event_type: "closed",
      severity: "critical",
      message: "管理员发布：灵山梵宫临时维护，非必去路线建议避开。",
    },
  },
  {
    label: "演出提醒",
    iconLabel: "show",
    payload: {
      attraction_id: "lingshan-ls-006",
      event_type: "show",
      severity: "info",
      message: "管理员发布：九龙灌浴演出即将开始，附近游客可提前就位。",
    },
  },
  {
    label: "推荐分流",
    iconLabel: "recommendation",
    payload: {
      attraction_id: "nianhuawan-nh-003",
      event_type: "recommendation",
      severity: "info",
      message: "管理员发布：亲子与休闲游客建议分流至香月花街。",
    },
  },
];

function eventLabel(type: string) {
  const labels: Record<string, string> = {
    qa: "问答",
    vision: "识景",
    route_recommend: "路线",
    route_share_open: "带走",
    feedback: "反馈",
    crowd_avoidance: "避峰",
  };
  return labels[type] || type;
}

function operationTypeLabel(type: OperationEventType | string) {
  const labels: Record<string, string> = {
    crowd: "拥挤",
    closed: "临时关闭",
    show: "演出提醒",
    recommendation: "推荐分流",
  };
  return labels[type] || type;
}

function severityLabel(severity: OperationEventSeverity | string) {
  return severity === "critical" ? "严重" : severity === "warning" ? "提醒" : "信息";
}

function severityTone(severity: OperationEventSeverity | string) {
  return severity === "critical" || severity === "warning" ? "warning" : "neutral";
}

function eventTimeWindow(event: OperationEvent) {
  const start = new Date(event.start_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  const end = new Date(event.end_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return `${start} - ${end}`;
}

export function AdminPage() {
  const [providers, setProviders] = useState<ProviderMap | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [operationEvents, setOperationEvents] = useState<OperationEvent[]>([]);
  const [operationMessage, setOperationMessage] = useState("");
  const [operationLoading, setOperationLoading] = useState(false);
  const [operationBusyId, setOperationBusyId] = useState("");

  useEffect(() => {
    fetch("/api/provider/status")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(setProviders)
      .catch(() => setProviders(null));
    getAnalyticsOverview()
      .then(setOverview)
      .catch(() => setOverview(null));
    loadOperationEvents();
  }, []);

  async function loadOperationEvents() {
    try {
      const payload = await getAdminOperationEvents(false);
      setOperationEvents(payload.items);
    } catch {
      setOperationEvents([]);
    }
  }

  async function quickCreateOperationEvent(payload: OperationEventCreateRequest) {
    setOperationLoading(true);
    setOperationMessage("");
    const now = Date.now();
    try {
      await createOperationEvent({
        ...payload,
        source: "manual_admin",
        created_by: "admin-console",
        active: true,
        start_at: new Date(now - 60_000).toISOString(),
        end_at: new Date(now + 3 * 60 * 60 * 1000).toISOString(),
      });
      setOperationMessage("运营事件已发布，新的路线推荐会立即读取该事件。");
      await loadOperationEvents();
    } catch (cause) {
      setOperationMessage(cause instanceof Error ? cause.message : "运营事件发布失败。");
    } finally {
      setOperationLoading(false);
    }
  }

  async function toggleOperationEvent(event: OperationEvent) {
    setOperationBusyId(event.id);
    setOperationMessage("");
    try {
      await updateOperationEvent(event.id, { active: !event.active });
      setOperationMessage(event.active ? "事件已停用，不再影响新路线。" : "事件已启用，会影响新路线。");
      await loadOperationEvents();
    } catch (cause) {
      setOperationMessage(cause instanceof Error ? cause.message : "事件状态更新失败。");
    } finally {
      setOperationBusyId("");
    }
  }

  const providerEntries = providers
    ? Object.entries(providers).map(([name, value]) => [name, value.provider, value.status])
    : providerRows;
  const tags = overview?.feedback_tags || [];
  const themes = overview?.route_theme_distribution || [];
  const popularQuestions = overview?.popular_questions || [];
  const lowConfidence = overview?.low_confidence_questions || [];
  const recentEvents = overview?.recent_events || [];
  const highCrowdItems = overview?.high_crowd_attractions || [];

  return (
    <PageShell className="admin-page">
      <aside className="admin-sidebar" aria-label="管理后台导航">
        <div className="admin-brand">
          <Bot aria-hidden="true" />
          <strong>灵境后台</strong>
        </div>
        {[
          ["概览", ChartNoAxesCombined],
          ["知识库", Database],
          ["数字人", Bot],
          ["交互日志", Activity],
          ["行为分析", Gauge],
          ["系统设置", Settings],
        ].map(([label, Icon]) => (
          <a className={label === "概览" ? "admin-nav admin-nav--active" : "admin-nav"} href="/admin" key={label as string}>
            <Icon aria-hidden="true" />
            <span>{label as string}</span>
          </a>
        ))}
      </aside>

      <section className="admin-main">
        <header className="admin-topbar">
          <div>
            <span className="eyebrow">运营概览</span>
            <h1>景区导览服务状态</h1>
          </div>
          <div className="admin-topbar__right">
            <label className="admin-search">
              <Search aria-hidden="true" size={18} />
              <span className="sr-only">搜索后台内容</span>
              <input placeholder="搜索问题、景点、知识切片" />
            </label>
            <StatusBadge tone="ok">mock provider</StatusBadge>
          </div>
        </header>

        <section className="metric-grid" aria-label="核心指标">
          <MetricCard icon={<Users />} label="服务事件" trend="本地日志" value={String(overview?.service_count ?? 0)} />
          <MetricCard icon={<Heart />} label="平均满意度" trend={`${overview?.feedback_count ?? 0} 条反馈`} value={overview?.average_rating?.toFixed(2) || "-"} />
          <MetricCard icon={<Share2 />} label="路线带走" trend="share open" value={String(overview?.share_open_count ?? 0)} />
          <MetricCard icon={<AlertTriangle />} label="避峰分流" trend="mock crowd" value={String(overview?.crowd_avoidance_count ?? 0)} />
        </section>

        <section className="admin-mini-grid" aria-label="服务拆解">
          <div className="admin-mini-stat">
            <MessageSquareText aria-hidden="true" />
            <span>问答</span>
            <strong>{overview?.qa_count ?? 0}</strong>
          </div>
          <div className="admin-mini-stat">
            <Database aria-hidden="true" />
            <span>识景</span>
            <strong>{overview?.vision_count ?? 0}</strong>
          </div>
          <div className="admin-mini-stat">
            <Route aria-hidden="true" />
            <span>路线</span>
            <strong>{overview?.route_count ?? 0}</strong>
          </div>
          <div className="admin-mini-stat">
            <Heart aria-hidden="true" />
            <span>反馈</span>
            <strong>{overview?.feedback_count ?? 0}</strong>
          </div>
        </section>

        <p className="admin-source-note">{overview?.source_note || "当前 analytics 为本地演示日志 + mock/公开样例数据。"}</p>

        <section className="admin-panel operation-console" aria-label="运营事件控制台">
          <div className="section-title-row">
            <div>
              <h2>运营事件控制台</h2>
              <p>manual_admin / mock_simulation 演示事件，不代表真实闸机、摄像头、Wi-Fi、GPS 或 IoT 数据。</p>
            </div>
            <StatusBadge tone="neutral">{operationEvents.filter((item) => item.active).length} active</StatusBadge>
          </div>

          <div className="operation-quick-actions" aria-label="快速创建运营事件">
            {quickOperationEvents.map((item) => (
              <Button
                icon={<Plus size={16} />}
                key={item.iconLabel}
                loading={operationLoading}
                onClick={() => void quickCreateOperationEvent(item.payload)}
                type="button"
                variant={item.payload.event_type === "closed" ? "accent" : "secondary"}
              >
                {item.label}
              </Button>
            ))}
          </div>
          {operationMessage ? <p className="operation-message">{operationMessage}</p> : null}

          <div className="operation-event-list" aria-label="运营事件列表">
            {operationEvents.length > 0 ? (
              operationEvents.map((event) => (
                <article className={event.active ? "operation-event-row" : "operation-event-row operation-event-row--off"} key={event.id}>
                  <div className="operation-event-main">
                    <div className="operation-event-title">
                      <strong>{event.attraction_name || event.attraction_id}</strong>
                      <StatusBadge tone={severityTone(event.severity)}>{severityLabel(event.severity)}</StatusBadge>
                      <StatusBadge tone="neutral">{operationTypeLabel(event.event_type)}</StatusBadge>
                    </div>
                    <p>{event.message}</p>
                    <span>
                      <CalendarClock aria-hidden="true" size={15} />
                      {eventTimeWindow(event)} · source={event.source}
                    </span>
                  </div>
                  <button
                    className="operation-toggle"
                    disabled={operationBusyId === event.id}
                    onClick={() => void toggleOperationEvent(event)}
                    type="button"
                  >
                    {event.active ? <ToggleRight aria-hidden="true" size={20} /> : <ToggleLeft aria-hidden="true" size={20} />}
                    {event.active ? "启用中" : "已停用"}
                  </button>
                </article>
              ))
            ) : (
              <p className="empty-state">暂无运营事件。可用上方按钮发布拥挤、临时关闭、演出提醒或推荐分流事件。</p>
            )}
          </div>
        </section>

        <section className="admin-content-grid">
          <article className="admin-panel admin-panel--wide">
            <div className="section-title-row">
              <div>
                <h2>路线偏好分布</h2>
                <p>单位：路线生成次数，来源：本地 interaction_events</p>
              </div>
              <StatusBadge tone="neutral">local</StatusBadge>
            </div>
            {themes.length > 0 ? (
              <div className="admin-bar-list">
                {themes.map((item) => (
                  <div className="admin-bar-row" key={item.theme}>
                    <span>{item.theme_label}</span>
                    <div aria-hidden="true">
                      <i style={{ width: `${Math.max(12, Math.min(100, item.count * 24))}%` }} />
                    </div>
                    <strong>{item.count}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">还没有路线推荐日志。游客端或 Kiosk 生成路线后会出现分布。</p>
            )}
          </article>

          <article className="admin-panel">
            <h2>Provider 状态</h2>
            <div className="provider-list">
              {providerEntries.map(([name, provider, status]) => (
                <div className="provider-row" key={name}>
                  <span>{name}</span>
                  <strong>{provider}</strong>
                  <StatusBadge tone={status === "ok" ? "ok" : "warning"}>{status}</StatusBadge>
                </div>
              ))}
            </div>
          </article>

          <article className="admin-panel">
            <div className="section-title-row">
              <div>
                <h2>拥挤分流</h2>
                <p>source=mock_simulation，非真实客流</p>
              </div>
              <AlertTriangle aria-hidden="true" />
            </div>
            <div className="crowd-alert-list">
              {highCrowdItems.length > 0 ? (
                highCrowdItems.map((item) => (
                  <div className="crowd-alert-row" key={item.attraction_id}>
                    <div>
                      <strong>{item.name}</strong>
                      <span>{item.scenic_area} · 等待约 {item.wait_minutes} 分钟</span>
                    </div>
                    <StatusBadge tone="warning">{item.crowd_score}</StatusBadge>
                    <p>建议通过游客端路线规划引导至低拥挤点，或提示错峰返回。</p>
                  </div>
                ))
              ) : (
                <p className="empty-state">当前没有 high 拥挤点。</p>
              )}
            </div>
          </article>

          <article className="admin-panel">
            <div className="section-title-row">
              <div>
                <h2>热门问题</h2>
                <p>单位：提问次数</p>
              </div>
            </div>
            <div className="question-list">
              {popularQuestions.length > 0 ? (
                popularQuestions.map((item) => (
                  <div className="question-row" key={item.question}>
                    <span>{item.question}</span>
                    <strong>{item.count}</strong>
                  </div>
                ))
              ) : (
                <p className="empty-state">暂无问答日志。</p>
              )}
            </div>
          </article>

          <article className="admin-panel">
            <div className="section-title-row">
              <div>
                <h2>低置信问题</h2>
                <p>检索为空或置信度偏低</p>
              </div>
              <HelpCircle aria-hidden="true" />
            </div>
            <div className="question-list">
              {lowConfidence.length > 0 ? (
                lowConfidence.map((item) => (
                  <div className="question-row question-row--stack" key={`${item.question}-${item.created_at}`}>
                    <span>{item.question}</span>
                    <small>{item.answer_preview || "系统已避免编造答案"}</small>
                  </div>
                ))
              ) : (
                <p className="empty-state">暂无低置信问题。</p>
              )}
            </div>
          </article>

          <article className="admin-panel">
            <div className="section-title-row">
              <div>
                <h2>反馈标签</h2>
                <p>单位：标签命中次数</p>
              </div>
              <Heart aria-hidden="true" />
            </div>
            <div className="tag-list">
              {tags.length > 0 ? (
                tags.map((item) => (
                  <span className="tag-count" key={item.tag}>
                    {item.tag}<strong>{item.count}</strong>
                  </span>
                ))
              ) : (
                <p className="empty-state">暂无反馈标签。</p>
              )}
            </div>
          </article>

          <article className="admin-panel admin-panel--wide">
            <div className="section-title-row">
              <div>
                <h2>最近事件</h2>
                <p>不包含 session_id 或个人身份字段</p>
              </div>
            </div>
            <div className="event-list">
              {recentEvents.length > 0 ? (
                recentEvents.map((item) => (
                  <div className="event-row" key={item.id}>
                    <StatusBadge tone={item.success ? "ok" : "warning"}>{eventLabel(item.event_type)}</StatusBadge>
                    <div>
                      <strong>
                        {item.question ||
                          String(item.metadata.theme_label || item.metadata.matched_attraction_name || item.route_id || item.id)}
                      </strong>
                      <span>{item.channel} · {item.created_at}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="empty-state">暂无交互事件。完成一次问答、识景、路线或反馈后会更新。</p>
              )}
            </div>
          </article>
        </section>
      </section>
    </PageShell>
  );
}
