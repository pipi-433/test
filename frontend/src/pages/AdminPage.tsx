import {
  AlertTriangle,
  BookOpenCheck,
  Bot,
  CalendarClock,
  ChartNoAxesCombined,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileWarning,
  FilePlus2,
  Gauge,
  Heart,
  HelpCircle,
  ListChecks,
  MessageSquareText,
  Plus,
  Route,
  Search,
  Settings,
  Share2,
  ShieldCheck,
  Timer,
  ToggleLeft,
  ToggleRight,
  Users,
  XCircle,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import {
  addKnowledgeGapToEval,
  createOperationEvent,
  draftKnowledgeGapFaq,
  fetchAttractions,
  getAdminOperationEvents,
  getAnalyticsOverview,
  getEvalReportsOverview,
  getKnowledgeGaps,
  updateKnowledgeGapStatus,
  updateOperationEvent,
} from "../api/client";
import type {
  AnalyticsOverview,
  Attraction,
  EvalDerivedMetric,
  EvalReportItem,
  EvalReportStatus,
  EvalReportsOverview,
  KnowledgeGap,
  KnowledgeGapStatus,
  OperationEvent,
  OperationEventSeverity,
  OperationEventType,
} from "../api/client";
import { Button } from "../components/Button";
import { MetricCard } from "../components/MetricCard";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { providerRows } from "../data/mock";

type ProviderMap = Record<string, { provider: string; status: string }>;

const quickOperationEvents: Array<{
  label: string;
  iconLabel: string;
  event_type: OperationEventType;
  severity: OperationEventSeverity;
}> = [
  {
    label: "拥挤",
    iconLabel: "crowd",
    event_type: "crowd",
    severity: "warning",
  },
  {
    label: "临时关闭",
    iconLabel: "closed",
    event_type: "closed",
    severity: "critical",
  },
  {
    label: "演出提醒",
    iconLabel: "show",
    event_type: "show",
    severity: "info",
  },
  {
    label: "推荐分流",
    iconLabel: "recommendation",
    event_type: "recommendation",
    severity: "info",
  },
];

type OperationFormState = {
  attraction_id: string;
  event_type: OperationEventType;
  severity: OperationEventSeverity;
  message: string;
  duration_hours: number;
};

const defaultOperationForm: OperationFormState = {
  attraction_id: "",
  event_type: "crowd",
  severity: "warning",
  message: "",
  duration_hours: 3,
};

const adminNavItems = [
  { id: "admin-overview", label: "概览", path: "/admin", Icon: ChartNoAxesCombined },
  { id: "admin-evals", label: "评测看板", path: "/admin/evals", Icon: ClipboardCheck },
  { id: "admin-operations", label: "运营事件", path: "/admin/operations", Icon: CalendarClock },
  { id: "admin-knowledge-gaps", label: "知识缺口", path: "/admin/knowledge-gaps", Icon: Database },
  { id: "admin-analytics", label: "运营分析", path: "/admin/analytics", Icon: Gauge },
  { id: "admin-system", label: "系统状态", path: "/admin/system", Icon: Settings },
];

function currentAdminSection(pathname: string) {
  return adminNavItems.find((item) => item.path === pathname)?.id || "admin-overview";
}

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

function defaultOperationMessage(type: OperationEventType, attractionName?: string) {
  const name = attractionName || "所选景点";
  const messages: Record<OperationEventType, string> = {
    crowd: `管理员发布：${name} 当前游客较多，建议路线预留等待时间或安排错峰游览。`,
    closed: `管理员发布：${name} 临时关闭或维护，非必去路线建议暂时避开。`,
    show: `管理员发布：${name} 附近有演出或活动提醒，建议游客提前安排到达时间。`,
    recommendation: `管理员发布：推荐将游客分流至 ${name}，用于缓解热门点压力。`,
  };
  return messages[type];
}

function defaultOperationSeverity(type: OperationEventType): OperationEventSeverity {
  if (type === "closed") return "critical";
  if (type === "crowd") return "warning";
  return "info";
}

function gapStatusLabel(status: KnowledgeGapStatus | string) {
  const labels: Record<string, string> = {
    open: "待处理",
    drafted: "已草拟",
    resolved: "已解决",
    ignored: "已忽略",
  };
  return labels[status] || status;
}

function gapTriggerLabel(trigger: string) {
  const labels: Record<string, string> = {
    low_confidence: "低置信",
    no_source: "无来源",
    negative_feedback: "信息不准反馈",
    manual: "手动记录",
  };
  return labels[trigger] || trigger;
}

function gapStatusTone(status: KnowledgeGapStatus | string) {
  return status === "open" ? "warning" : status === "resolved" ? "ok" : "neutral";
}

function reportStatusLabel(status: EvalReportStatus) {
  const labels: Record<EvalReportStatus, string> = {
    fail: "失败",
    missing: "缺失",
    pass: "通过",
  };
  return labels[status];
}

function reportStatusTone(status: EvalReportStatus) {
  return status === "pass" ? "ok" : status === "fail" ? "warning" : "neutral";
}

function formatRate(value?: number | null) {
  if (value === null || value === undefined) {
    return "暂无";
  }
  return `${Math.round(value * 100)}%`;
}

function formatMaybeDate(value?: string | null) {
  if (!value) {
    return "未生成";
  }
  return new Date(value).toLocaleString("zh-CN", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
  });
}

function derivedMetricText(metric: EvalDerivedMetric) {
  if (metric.value === null) {
    return metric.reason || "暂无可推导数据";
  }
  const countText = metric.total ? ` · ${metric.passed ?? 0}/${metric.total}` : "";
  return `${formatRate(metric.value)}${countText}`;
}

function eventTimeWindow(event: OperationEvent) {
  const start = new Date(event.start_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  const end = new Date(event.end_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return `${start} - ${end}`;
}

export function AdminPage() {
  const [providers, setProviders] = useState<ProviderMap | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [evalOverview, setEvalOverview] = useState<EvalReportsOverview | null>(null);
  const activeAdminSection = currentAdminSection(window.location.pathname);
  const [operationAttractions, setOperationAttractions] = useState<Attraction[]>([]);
  const [operationEvents, setOperationEvents] = useState<OperationEvent[]>([]);
  const [operationForm, setOperationForm] = useState<OperationFormState>(defaultOperationForm);
  const [operationMessage, setOperationMessage] = useState("");
  const [operationLoading, setOperationLoading] = useState(false);
  const [operationBusyId, setOperationBusyId] = useState("");
  const [knowledgeGaps, setKnowledgeGaps] = useState<KnowledgeGap[]>([]);
  const [gapStatusFilter, setGapStatusFilter] = useState<KnowledgeGapStatus | "all">("all");
  const [gapMessage, setGapMessage] = useState("");
  const [gapBusyId, setGapBusyId] = useState("");

  useEffect(() => {
    fetch("/api/provider/status")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(setProviders)
      .catch(() => setProviders(null));
    getAnalyticsOverview()
      .then(setOverview)
      .catch(() => setOverview(null));
    getEvalReportsOverview()
      .then(setEvalOverview)
      .catch(() => setEvalOverview(null));
    loadOperationAttractions();
    loadOperationEvents();
    loadKnowledgeGaps();
  }, []);

  async function loadOperationAttractions() {
    try {
      const items = await fetchAttractions();
      setOperationAttractions(items);
      setOperationForm((current) => (current.attraction_id || !items[0] ? current : { ...current, attraction_id: items[0].id }));
    } catch {
      setOperationAttractions([]);
    }
  }

  async function loadOperationEvents() {
    try {
      const payload = await getAdminOperationEvents(false);
      setOperationEvents(payload.items);
    } catch {
      setOperationEvents([]);
    }
  }

  function applyOperationTemplate(eventType: OperationEventType, severity: OperationEventSeverity) {
    setOperationForm((current) => {
      const attractionId = current.attraction_id || operationAttractions[0]?.id || "";
      const attraction = operationAttractions.find((item) => item.id === attractionId);
      return {
        ...current,
        attraction_id: attractionId,
        event_type: eventType,
        severity,
        message: defaultOperationMessage(eventType, attraction?.name),
      };
    });
    setOperationMessage("已套用事件模板。请确认景点、等级和说明后再发布。");
  }

  async function handleCreateOperationEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const attraction = operationAttractions.find((item) => item.id === operationForm.attraction_id);
    if (!operationForm.attraction_id || !attraction) {
      setOperationMessage("请先选择要发布事件的景点。");
      return;
    }
    setOperationLoading(true);
    setOperationMessage("");
    const now = Date.now();
    const durationHours = Number.isFinite(operationForm.duration_hours) ? Math.min(Math.max(operationForm.duration_hours, 0.5), 24) : 3;
    const message = operationForm.message.trim() || defaultOperationMessage(operationForm.event_type, attraction.name);
    try {
      await createOperationEvent({
        attraction_id: operationForm.attraction_id,
        event_type: operationForm.event_type,
        severity: operationForm.severity,
        message,
        source: "manual_admin",
        created_by: "admin-console",
        active: true,
        start_at: new Date(now - 60_000).toISOString(),
        end_at: new Date(now + durationHours * 60 * 60 * 1000).toISOString(),
      });
      setOperationMessage(`已发布 ${attraction.name} 的${operationTypeLabel(operationForm.event_type)}事件，新的路线推荐会立即读取该事件。`);
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

  async function loadKnowledgeGaps() {
    try {
      const payload = await getKnowledgeGaps();
      setKnowledgeGaps(payload.items);
    } catch {
      setKnowledgeGaps([]);
    }
  }

  async function handleDraftKnowledgeGap(gapId: string) {
    setGapBusyId(gapId);
    setGapMessage("");
    try {
      await draftKnowledgeGapFaq(gapId);
      setGapMessage("FAQ 草稿已生成，发布前仍需管理员确认。");
      await loadKnowledgeGaps();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "FAQ 草稿生成失败。");
    } finally {
      setGapBusyId("");
    }
  }

  async function handleAddKnowledgeGapToEval(gapId: string) {
    setGapBusyId(gapId);
    setGapMessage("");
    try {
      await addKnowledgeGapToEval(gapId);
      setGapMessage("已加入知识缺口评测集，不会重复追加同一 gap。");
      await loadKnowledgeGaps();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "加入评测集失败。");
    } finally {
      setGapBusyId("");
    }
  }

  async function handleUpdateKnowledgeGapStatus(gapId: string, status: KnowledgeGapStatus) {
    setGapBusyId(gapId);
    setGapMessage("");
    try {
      await updateKnowledgeGapStatus(gapId, status);
      setGapMessage(`知识缺口已标记为${gapStatusLabel(status)}。`);
      await loadKnowledgeGaps();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "知识缺口状态更新失败。");
    } finally {
      setGapBusyId("");
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
  const filteredKnowledgeGaps =
    gapStatusFilter === "all" ? knowledgeGaps : knowledgeGaps.filter((gap) => gap.status === gapStatusFilter);
  const evalReports = evalOverview?.reports || [];
  const failureSamples = evalReports
    .flatMap((report: EvalReportItem) =>
      report.failure_samples.map((sample) => ({
        reportTitle: report.title,
        sample,
      })),
    )
    .slice(0, 3);
  const gapCounts = knowledgeGaps.reduce<Record<KnowledgeGapStatus, number>>(
    (acc, gap) => {
      acc[gap.status] += 1;
      return acc;
    },
    { open: 0, drafted: 0, resolved: 0, ignored: 0 },
  );
  return (
    <PageShell className="admin-page">
      <aside className="admin-sidebar" aria-label="管理后台导航">
        <div className="admin-brand">
          <Bot aria-hidden="true" />
          <strong>灵境后台</strong>
        </div>
        {adminNavItems.map(({ id, label, path, Icon }) => (
          <a
            className={activeAdminSection === id ? "admin-nav admin-nav--active" : "admin-nav"}
            href={path}
            key={id}
          >
            <Icon aria-hidden="true" />
            <span>{label}</span>
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

        {activeAdminSection === "admin-overview" ? (
          <>
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
          </>
        ) : null}

        {activeAdminSection === "admin-evals" ? (
        <section className="admin-panel eval-dashboard" aria-label="评测看板">
          <div className="section-title-row">
            <div>
              <h2>评测看板 / 可信度证明</h2>
              <p>
                {evalOverview?.source_note ||
                  "评测看板读取本地 eval reports，用于比赛演示可信度证明；mock 模式不代表生产 SLA。"}
              </p>
            </div>
            <StatusBadge tone={evalOverview?.overall.failed_cases ? "warning" : "ok"}>
              {formatRate(evalOverview?.overall.overall_accuracy)}
            </StatusBadge>
          </div>

          <div className="eval-summary-grid" aria-label="评测总体摘要">
            <div className="eval-summary-stat">
              <ShieldCheck aria-hidden="true" />
              <span>总通过率</span>
              <strong>{formatRate(evalOverview?.overall.overall_accuracy)}</strong>
            </div>
            <div className="eval-summary-stat">
              <ClipboardCheck aria-hidden="true" />
              <span>样例通过</span>
              <strong>
                {evalOverview?.overall.passed_cases ?? 0}/{evalOverview?.overall.total_cases ?? 0}
              </strong>
            </div>
            <div className="eval-summary-stat">
              <FileWarning aria-hidden="true" />
              <span>报告覆盖</span>
              <strong>
                {evalOverview?.overall.available_reports ?? 0}/{evalOverview?.overall.total_reports ?? 0}
              </strong>
            </div>
            <div className="eval-summary-stat">
              <Timer aria-hidden="true" />
              <span>最新评测</span>
              <strong>{formatMaybeDate(evalOverview?.overall.latest_generated_at)}</strong>
            </div>
          </div>

          <div className="eval-derived-grid" aria-label="衍生可信指标">
            <div className="eval-derived-item">
              <span>必去景点保留率</span>
              <strong>{evalOverview ? derivedMetricText(evalOverview.derived_metrics.must_visit_preservation_rate) : "暂无"}</strong>
            </div>
            <div className="eval-derived-item">
              <span>拥挤点错峰解释率</span>
              <strong>{evalOverview ? derivedMetricText(evalOverview.derived_metrics.crowd_explanation_rate) : "暂无"}</strong>
            </div>
            <div className="eval-derived-item">
              <span>低置信澄清准确率</span>
              <strong>{evalOverview ? derivedMetricText(evalOverview.derived_metrics.clarification_pass_rate) : "暂无"}</strong>
            </div>
            <div className="eval-derived-item">
              <span>知识缺口闭环通过率</span>
              <strong>{evalOverview ? derivedMetricText(evalOverview.derived_metrics.knowledge_gap_workflow_rate) : "暂无"}</strong>
            </div>
          </div>

          <div className="eval-report-list" aria-label="评测报告列表">
            {evalReports.length > 0 ? (
              evalReports.map((report) => (
                <article className="eval-report-row" key={report.id}>
                  <div className="eval-report-main">
                    <div className="eval-report-title">
                      <strong>{report.title}</strong>
                      <StatusBadge tone={reportStatusTone(report.status)}>{reportStatusLabel(report.status)}</StatusBadge>
                    </div>
                    <p>{report.summary}</p>
                    <div className="eval-progress" aria-label={`${report.title} 通过率 ${formatRate(report.accuracy)}`}>
                      <i style={{ width: `${Math.max(0, Math.min(100, Math.round((report.accuracy ?? 0) * 100)))}%` }} />
                    </div>
                  </div>
                  <div className="eval-report-meta">
                    <span>通过率 <strong>{formatRate(report.accuracy)}</strong></span>
                    <span>样本 <strong>{report.passed}/{report.total}</strong></span>
                    <span>失败 <strong>{report.failed}</strong></span>
                    <span>延迟 <strong>{report.avg_latency_ms === null ? "-" : `${report.avg_latency_ms.toFixed(1)}ms`}</strong></span>
                    <span>时间 <strong>{formatMaybeDate(report.generated_at)}</strong></span>
                  </div>
                </article>
              ))
            ) : (
              <p className="empty-state">暂未读取到评测报告。运行 eval 脚本后这里会展示本地可信度证明。</p>
            )}
          </div>

          <div className="eval-failure-list" aria-label="失败样例摘要">
            <h3>失败样例摘要</h3>
            {failureSamples.length > 0 ? (
              failureSamples.map(({ reportTitle, sample }) => (
                <article className="eval-failure-row" key={`${reportTitle}-${sample.id}`}>
                  <strong>{reportTitle} · {sample.id}</strong>
                  <p>{sample.message || "该样例未给出失败说明。"}</p>
                </article>
              ))
            ) : (
              <p className="empty-state">当前最新 report 没有失败样例。</p>
            )}
          </div>
        </section>
        ) : null}

        {activeAdminSection === "admin-operations" ? (
        <section className="admin-panel operation-console" aria-label="运营事件控制台">
          <div className="section-title-row">
            <div>
              <h2>运营事件控制台</h2>
              <p>manual_admin / mock_simulation 演示事件，不代表真实闸机、摄像头、Wi-Fi、GPS 或 IoT 数据。</p>
            </div>
            <StatusBadge tone="neutral">{operationEvents.filter((item) => item.active).length} active</StatusBadge>
          </div>

          <form className="operation-create-form" onSubmit={(event) => void handleCreateOperationEvent(event)}>
            <div className="operation-template-row" aria-label="运营事件模板">
              {quickOperationEvents.map((item) => (
                <button
                  className={operationForm.event_type === item.event_type ? "operation-template-button operation-template-button--active" : "operation-template-button"}
                  key={item.iconLabel}
                  onClick={() => applyOperationTemplate(item.event_type, item.severity)}
                  type="button"
                >
                  <Plus aria-hidden="true" size={16} />
                  {item.label}
                </button>
              ))}
            </div>

            <div className="operation-form-grid">
              <label className="operation-field">
                <span>影响景点</span>
                <select
                  disabled={operationAttractions.length === 0}
                  onChange={(event) => {
                    const attraction = operationAttractions.find((item) => item.id === event.target.value);
                    setOperationForm((current) => ({
                      ...current,
                      attraction_id: event.target.value,
                      message: current.message ? current.message : defaultOperationMessage(current.event_type, attraction?.name),
                    }));
                  }}
                  required
                  value={operationForm.attraction_id}
                >
                  {operationAttractions.length > 0 ? (
                    operationAttractions.map((attraction) => (
                      <option key={attraction.id} value={attraction.id}>
                        {attraction.scenic_area} · {attraction.name}
                      </option>
                    ))
                  ) : (
                    <option value="">景点加载中</option>
                  )}
                </select>
              </label>

              <label className="operation-field">
                <span>事件类型</span>
                <select
                  onChange={(event) => {
                    const eventType = event.target.value as OperationEventType;
                    setOperationForm((current) => ({
                      ...current,
                      event_type: eventType,
                      severity: defaultOperationSeverity(eventType),
                      message: defaultOperationMessage(eventType, operationAttractions.find((item) => item.id === current.attraction_id)?.name),
                    }));
                  }}
                  value={operationForm.event_type}
                >
                  {(["crowd", "closed", "show", "recommendation"] as OperationEventType[]).map((type) => (
                    <option key={type} value={type}>
                      {operationTypeLabel(type)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="operation-field">
                <span>影响等级</span>
                <select
                  onChange={(event) => setOperationForm((current) => ({ ...current, severity: event.target.value as OperationEventSeverity }))}
                  value={operationForm.severity}
                >
                  {(["info", "warning", "critical"] as OperationEventSeverity[]).map((severity) => (
                    <option key={severity} value={severity}>
                      {severityLabel(severity)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="operation-field">
                <span>持续小时</span>
                <input
                  max={24}
                  min={0.5}
                  onChange={(event) => setOperationForm((current) => ({ ...current, duration_hours: Number(event.target.value) }))}
                  step={0.5}
                  type="number"
                  value={operationForm.duration_hours}
                />
              </label>
            </div>

            <label className="operation-field operation-field--wide">
              <span>对游客展示的说明</span>
              <textarea
                onChange={(event) => setOperationForm((current) => ({ ...current, message: event.target.value }))}
                placeholder="例如：当前排队较多，建议先前往周边景点，稍后返回。"
                rows={3}
                value={operationForm.message}
              />
            </label>

            <div className="operation-form-actions">
              <Button
                disabled={operationAttractions.length === 0}
                icon={<Plus size={16} />}
                loading={operationLoading}
                type="submit"
                variant={operationForm.event_type === "closed" ? "accent" : "primary"}
              >
                发布运营事件
              </Button>
              <p>模板只填充类型和建议文案；最终发布会使用当前选择的景点。</p>
            </div>
          </form>
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
        ) : null}

        {activeAdminSection === "admin-knowledge-gaps" ? (
        <section className="admin-panel knowledge-gap-console" aria-label="知识缺口闭环">
          <div className="section-title-row">
            <div>
              <h2>知识缺口闭环</h2>
              <p>低置信、无来源和“信息不准”反馈会沉淀为待处理缺口；FAQ 草稿为规则生成，需管理员确认后发布。</p>
            </div>
            <StatusBadge tone="warning">{overview?.open_knowledge_gap_count ?? gapCounts.open} open</StatusBadge>
          </div>

          <div className="knowledge-gap-summary" aria-label="知识缺口状态统计">
            <button
              className={gapStatusFilter === "all" ? "knowledge-gap-filter knowledge-gap-filter--active" : "knowledge-gap-filter"}
              onClick={() => setGapStatusFilter("all")}
              type="button"
            >
              <ListChecks aria-hidden="true" size={17} />
              全部 <strong>{knowledgeGaps.length}</strong>
            </button>
            {(["open", "drafted", "resolved", "ignored"] as KnowledgeGapStatus[]).map((status) => (
              <button
                className={gapStatusFilter === status ? "knowledge-gap-filter knowledge-gap-filter--active" : "knowledge-gap-filter"}
                key={status}
                onClick={() => setGapStatusFilter(status)}
                type="button"
              >
                {status === "open" ? <HelpCircle aria-hidden="true" size={17} /> : null}
                {status === "drafted" ? <BookOpenCheck aria-hidden="true" size={17} /> : null}
                {status === "resolved" ? <CheckCircle2 aria-hidden="true" size={17} /> : null}
                {status === "ignored" ? <XCircle aria-hidden="true" size={17} /> : null}
                {gapStatusLabel(status)} <strong>{gapCounts[status]}</strong>
              </button>
            ))}
          </div>

          {gapMessage ? <p className="knowledge-gap-message">{gapMessage}</p> : null}

          <div className="knowledge-gap-list" aria-label="知识缺口列表">
            {filteredKnowledgeGaps.length > 0 ? (
              filteredKnowledgeGaps.map((gap) => (
                <article className="knowledge-gap-row" key={gap.id}>
                  <div className="knowledge-gap-row__main">
                    <div className="knowledge-gap-row__title">
                      <strong>{gap.query}</strong>
                      <StatusBadge tone={gapStatusTone(gap.status)}>{gapStatusLabel(gap.status)}</StatusBadge>
                      <StatusBadge tone="neutral">{gapTriggerLabel(gap.trigger_type)}</StatusBadge>
                    </div>
                    <p>{gap.suggested_faq ? gap.suggested_faq.replace(/[#*\n]/g, " ").slice(0, 150) : "暂无 FAQ 草稿。无可靠来源时需管理员补充资料，避免编造。"}</p>
                    <span>
                      confidence={gap.confidence ?? "-"} · {new Date(gap.created_at).toLocaleString("zh-CN")} · eval={gap.eval_case_id || "未加入"}
                    </span>
                  </div>
                  <div className="knowledge-gap-actions">
                    <Button
                      disabled={gapBusyId === gap.id}
                      icon={<BookOpenCheck size={15} />}
                      onClick={() => void handleDraftKnowledgeGap(gap.id)}
                      type="button"
                      variant="secondary"
                    >
                      生成 FAQ
                    </Button>
                    <Button
                      disabled={gapBusyId === gap.id}
                      icon={<FilePlus2 size={15} />}
                      onClick={() => void handleAddKnowledgeGapToEval(gap.id)}
                      type="button"
                      variant="secondary"
                    >
                      加入评测
                    </Button>
                    <Button
                      disabled={gapBusyId === gap.id}
                      icon={<CheckCircle2 size={15} />}
                      onClick={() => void handleUpdateKnowledgeGapStatus(gap.id, "resolved")}
                      type="button"
                      variant="quiet"
                    >
                      已解决
                    </Button>
                    <Button
                      disabled={gapBusyId === gap.id}
                      icon={<XCircle size={15} />}
                      onClick={() => void handleUpdateKnowledgeGapStatus(gap.id, "ignored")}
                      type="button"
                      variant="quiet"
                    >
                      忽略
                    </Button>
                  </div>
                </article>
              ))
            ) : (
              <p className="empty-state">当前没有该状态的知识缺口。游客端出现无来源问答或“信息不准”反馈后会自动进入这里。</p>
            )}
          </div>
        </section>
        ) : null}

        {activeAdminSection === "admin-analytics" ? (
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
        ) : null}

        {activeAdminSection === "admin-system" ? (
          <section className="admin-content-grid">
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
        ) : null}
      </section>
    </PageShell>
  );
}
