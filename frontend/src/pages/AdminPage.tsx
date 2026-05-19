import {
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpenCheck,
  Bot,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  CloudUpload,
  FilePlus2,
  Gauge,
  Heart,
  Home,
  Layers3,
  LineChart,
  MessageSquareText,
  Mic2,
  MonitorPlay,
  PlayCircle,
  Plus,
  RefreshCw,
  Route,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Smile,
  Star,
  Upload,
  UserCog,
  Users,
  Volume2,
  XCircle,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  addKnowledgeGapToEval,
  createAdminFaq,
  createAdminKnowledgeAsset,
  createOperationEvent,
  draftKnowledgeGapFaq,
  fetchAttractions,
  generateAdminAvatarClip,
  generateAdminSentimentReport,
  getAdminAvatarClipJobs,
  getAdminAvatarProfile,
  getAdminFaqs,
  getAdminKnowledgeAssets,
  getAdminOperationEvents,
  getAdminSentimentReport,
  getAdminSystemSettings,
  getAnalyticsOverview,
  getEvalReportsOverview,
  getKnowledgeGaps,
  publishAdminKnowledge,
  reindexAdminKnowledge,
  runAdminSystemHealthcheck,
  runAdminAvatarVoiceTest,
  updateAdminFaq,
  updateAdminSystemSettings,
  updateAdminAvatarProfile,
  updateKnowledgeGapStatus,
  updateOperationEvent,
} from "../api/client";
import type {
  AdminAvatarClipJob,
  AdminAvatarProfile,
  AdminFaq,
  AdminKnowledgeAsset,
  AdminKnowledgeStatus,
  AdminSentimentReport,
  AdminSystemHealthcheck,
  AdminSystemSettings,
  AnalyticsOverview,
  Attraction,
  EvalReportsOverview,
  KnowledgeGap,
  KnowledgeGapStatus,
  OperationEvent,
  OperationEventSeverity,
  OperationEventType,
} from "../api/client";
import { Button } from "../components/Button";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { providerRows } from "../data/mock";

type ProviderMap = Record<
  string,
  {
    provider: string;
    status: string;
    model?: string | null;
    configured?: boolean;
    mode?: string;
  }
>;
type AdminTabId = "overview" | "knowledge" | "avatar" | "operations" | "sentiment" | "dashboard" | "settings";

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

const defaultAdminAvatarProfile: AdminAvatarProfile = {
  name: "小灵",
  outfit_style: "宋韵青绿",
  voice_name: "温柔女声",
  speech_rate: 1,
  volume: 0.9,
  default_emotion: "happy",
  background_style: "灵山山水",
};

const defaultAdminSystemSettings: AdminSystemSettings = {
  scenic_area_name: "灵山胜境",
  default_provider_mode: "mock",
  avatar_mode: "mock",
  mock_crowd_enabled: true,
  route_topology_enabled: true,
  data_boundary_notice: "本地演示日志、公开样例与 mock 数据，不代表真实全园运营数据。",
};

const adminNavItems: Array<{ id: AdminTabId; label: string; path: string; Icon: typeof Home }> = [
  { id: "overview", label: "首页概览", path: "/admin", Icon: Home },
  { id: "knowledge", label: "知识库管理", path: "/admin/knowledge", Icon: Layers3 },
  { id: "avatar", label: "数字人管理", path: "/admin/avatar", Icon: Bot },
  { id: "operations", label: "运营事件", path: "/admin/operations", Icon: CalendarClock },
  { id: "sentiment", label: "游客感受度", path: "/admin/sentiment", Icon: Smile },
  { id: "dashboard", label: "数据大屏", path: "/admin/dashboard", Icon: BarChart3 },
  { id: "settings", label: "系统设置", path: "/admin/settings", Icon: Settings },
];

const trendPoints = [42, 55, 51, 59, 67, 62, 82];
const sentimentTrend = [4.5, 4.6, 4.4, 4.6, 4.7, 4.6, 4.7];
const routeThemes = [
  { label: "礼佛文化", value: 42, percent: 32 },
  { label: "家庭舒缓", value: 34, percent: 26 },
  { label: "拍照打卡", value: 24, percent: 18 },
  { label: "历史深度", value: 18, percent: 14 },
  { label: "拈花湾夜游", value: 14, percent: 10 },
];
const clipRows = [
  { id: "lingshan_buddha_intro_45s", name: "灵山大佛", duration: "00:45", audio: "已就绪", lip: "已通过", updated: "2026-05-16 14:32" },
  { id: "fan_gong_intro_45s", name: "灵山梵宫", duration: "00:45", audio: "已就绪", lip: "已通过", updated: "2026-05-16 11:08" },
  { id: "jiulong_guanyu_intro_30s", name: "九龙灌浴", duration: "00:30", audio: "处理中", lip: "待验证", updated: "2026-05-15 16:45" },
];
const mockCrowdRows = [
  { area: "灵山大佛", state: "拥挤", estimate: "8,560", density: 9, action: "建议错峰出行" },
  { area: "梵宫", state: "较拥挤", estimate: "3,210", density: 6, action: "建议分流参观" },
  { area: "九龙灌浴", state: "舒适", estimate: "2,450", density: 4, action: "正常游览" },
  { area: "五印坛城", state: "舒适", estimate: "1,860", density: 3, action: "正常游览" },
];
const feedbackRows = [
  { time: "14:32", channel: "小程序", topic: "灵山大佛路线", sentiment: "正向", confidence: "0.94", action: "已回答" },
  { time: "14:28", channel: "数字人终端", topic: "老人路线推荐", sentiment: "中性", confidence: "0.91", action: "已生成路线" },
  { time: "14:23", channel: "APP", topic: "五印坛城识景", sentiment: "正向", confidence: "0.88", action: "已识别" },
  { time: "14:18", channel: "小程序", topic: "寄存行李位置", sentiment: "负向", confidence: "0.62", action: "加入知识缺口" },
];
const routeAdviceRows = [
  { theme: "礼佛文化", ratio: "32%", path: "灵山大佛 -> 五印坛城", note: "人流较多，建议分时预约" },
  { theme: "家庭舒缓", ratio: "26%", path: "梵宫 -> 祥符禅寺 -> 灵山大佛", note: "适合家庭游客，节奏平缓" },
  { theme: "拍照打卡", ratio: "18%", path: "拈花湾 -> 梵宫 -> 灵山大佛", note: "拍照点集中，注意光线时段" },
  { theme: "历史深度", ratio: "14%", path: "梵宫 -> 五印坛城 -> 静心体验", note: "内容较深，建议配合导览" },
  { theme: "拈花湾夜游", ratio: "10%", path: "拈花湾夜游", note: "夜间客流上升，建议提前入园" },
];
const wordCloud = ["灵山大佛", "九龙灌浴", "梵宫", "老人路线", "景区地图", "门票价格", "开放时间", "如公预约", "停车收费", "洗手间"];

function currentAdminSection(pathname: string): AdminTabId {
  const match = adminNavItems.find((item) => item.path === pathname);
  if (match) return match.id;
  if (pathname.includes("/knowledge-gaps") || pathname.includes("/evals")) return "knowledge";
  if (pathname.includes("/analytics")) return "dashboard";
  if (pathname.includes("/system")) return "settings";
  return "overview";
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

function adminKnowledgeStatusLabel(status: string) {
  const labels: Record<string, string> = {
    archived: "已归档",
    draft: "草稿",
    pending_review: "待审核",
    published: "已发布",
  };
  return labels[status] || status;
}

function adminKnowledgeStatusTone(status: string) {
  return status === "published" ? "ok" : status === "draft" || status === "pending_review" ? "warning" : "neutral";
}

function assetTypeLabel(type: string) {
  const labels: Record<string, string> = {
    faq: "FAQ",
    guide_script: "讲解词",
    history_doc: "文史资料",
    other: "其他",
    route_note: "路线说明",
  };
  return labels[type] || type;
}

function formatRate(value?: number | null) {
  if (value === null || value === undefined) return "暂无";
  return `${Math.round(value * 100)}%`;
}

function formatMaybeDate(value?: string | null) {
  if (!value) return "未生成";
  return new Date(value).toLocaleString("zh-CN", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
  });
}

function sentimentLabel(value: string) {
  if (value === "positive") return "正向";
  if (value === "negative") return "负向";
  if (value === "neutral") return "中性";
  return value;
}

function sentimentTone(value: string): "ok" | "warning" | "neutral" {
  if (value === "positive") return "ok";
  if (value === "negative") return "warning";
  return "neutral";
}

function eventTimeWindow(event: OperationEvent) {
  const start = new Date(event.start_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  const end = new Date(event.end_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return `${start} - ${end}`;
}

function MiniTrend({ values = trendPoints }: { values?: number[] }) {
  const points = values.map((value, index) => `${(index / Math.max(1, values.length - 1)) * 100},${100 - value}`).join(" ");
  return (
    <svg className="admin-mini-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={`0,100 ${points} 100,100`} className="admin-mini-line__area" />
      <polyline points={points} className="admin-mini-line__stroke" />
    </svg>
  );
}

function DonutChart({ items }: { items: Array<{ label: string; percent: number }> }) {
  const gradient = items
    .reduce<{ cursor: number; stops: string[] }>(
      (acc, item, index) => {
        const colors = ["#00645a", "#2f8c7d", "#7fb2a8", "#c2943f", "#dfbd72"];
        const next = acc.cursor + item.percent;
        acc.stops.push(`${colors[index % colors.length]} ${acc.cursor}% ${next}%`);
        acc.cursor = next;
        return acc;
      },
      { cursor: 0, stops: [] },
    )
    .stops.join(", ");
  return (
    <div className="admin-donut" style={{ background: `conic-gradient(${gradient})` }} aria-hidden="true">
      <span />
    </div>
  );
}

function AdminMetricCard({
  Icon,
  label,
  trend,
  value,
  suffix = "",
}: {
  Icon: typeof Users;
  label: string;
  trend: string;
  value: string;
  suffix?: string;
}) {
  return (
    <article className="admin-kpi-card">
      <span className="admin-kpi-card__icon">
        <Icon aria-hidden="true" size={22} />
      </span>
      <div>
        <p>{label}</p>
        <strong>
          {value}
          {suffix ? <small>{suffix}</small> : null}
        </strong>
      </div>
      <span className="admin-kpi-card__trend">{trend}</span>
    </article>
  );
}

function AdminPanel({
  children,
  className = "",
  subtitle,
  title,
  toolbar,
}: {
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
  title: string;
  toolbar?: React.ReactNode;
}) {
  return (
    <section className={`admin-work-panel ${className}`}>
      <div className="admin-panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {toolbar ? <div className="admin-panel-toolbar">{toolbar}</div> : null}
      </div>
      {children}
    </section>
  );
}

function StubButton({
  children,
  disabled = false,
  icon,
  onClick,
  tone = "default",
}: {
  children: React.ReactNode;
  disabled?: boolean;
  icon?: React.ReactNode;
  onClick?: () => void;
  tone?: "default" | "primary" | "gold";
}) {
  return (
    <button className={`admin-action admin-action--${tone}`} disabled={disabled} onClick={onClick} type="button">
      {icon}
      <span>{children}</span>
    </button>
  );
}

function AdminTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Array<Array<React.ReactNode>>;
}) {
  return (
    <div className="admin-table-wrap">
      <table className="admin-data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CrowdDots({ count }: { count: number }) {
  return (
    <span className="admin-crowd-dots" aria-label={`拥挤度 ${count}/10`}>
      {Array.from({ length: 10 }).map((_, index) => (
        <i className={index < count ? "is-active" : ""} key={index} />
      ))}
    </span>
  );
}

export function AdminPage() {
  const [topbarMenu, setTopbarMenu] = useState<"gaps" | "scenic" | "user" | null>(null);
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
  const [knowledgeAssets, setKnowledgeAssets] = useState<AdminKnowledgeAsset[]>([]);
  const [adminFaqs, setAdminFaqs] = useState<AdminFaq[]>([]);
  const [knowledgeAdminMessage, setKnowledgeAdminMessage] = useState("");
  const [knowledgeAdminBusy, setKnowledgeAdminBusy] = useState("");
  const [knowledgeAssetDraft, setKnowledgeAssetDraft] = useState({
    attraction_id: "lingshan-ls-011",
    content: "灵山大佛夜间灯光秀为演示新增知识，建议游客在傍晚后前往观景区观看，具体开放以现场公告为准。",
    scenic_area: "灵山胜境",
    source_filename: "admin-night-light-demo.md",
    title: "灵山大佛夜间灯光测试说明",
  });
  const [faqDraft, setFaqDraft] = useState({
    answer: "建议从灵山大佛主轴线开始，结合梵宫、九龙灌浴与五印坛城安排半日游。回答需要附公开资料来源，避免编造。",
    question: "灵山大佛适合怎么游览？",
    tags: "导览,路线,讲解",
  });
  const [avatarProfile, setAvatarProfile] = useState<AdminAvatarProfile>(defaultAdminAvatarProfile);
  const [faqEditingId, setFaqEditingId] = useState("");
  const [avatarJobs, setAvatarJobs] = useState<AdminAvatarClipJob[]>([]);
  const [avatarMessage, setAvatarMessage] = useState("");
  const [avatarBusy, setAvatarBusy] = useState("");
  const [sentimentReport, setSentimentReport] = useState<AdminSentimentReport | null>(null);
  const [sentimentMessage, setSentimentMessage] = useState("");
  const [sentimentBusy, setSentimentBusy] = useState("");
  const [systemSettings, setSystemSettings] = useState<AdminSystemSettings>(defaultAdminSystemSettings);
  const [systemHealth, setSystemHealth] = useState<AdminSystemHealthcheck | null>(null);
  const [systemMessage, setSystemMessage] = useState("");
  const [systemBusy, setSystemBusy] = useState("");

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
    void loadOperationAttractions();
    void loadOperationEvents();
    void loadKnowledgeGaps();
    void loadAdminKnowledge();
    void loadAdminAvatar();
    void loadAdminSentimentReport();
    void loadAdminSystemSettings();
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

  async function loadKnowledgeGaps() {
    try {
      const payload = await getKnowledgeGaps();
      setKnowledgeGaps(payload.items);
    } catch {
      setKnowledgeGaps([]);
    }
  }

  async function loadAdminKnowledge() {
    try {
      const [assetsPayload, faqsPayload] = await Promise.all([getAdminKnowledgeAssets(), getAdminFaqs()]);
      setKnowledgeAssets(assetsPayload.items);
      setAdminFaqs(faqsPayload.items);
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "知识库管理数据加载失败。");
    }
  }

  async function loadAdminAvatar() {
    try {
      const [profile, jobsPayload] = await Promise.all([getAdminAvatarProfile(), getAdminAvatarClipJobs()]);
      setAvatarProfile(profile);
      setAvatarJobs(jobsPayload.items);
    } catch (cause) {
      setAvatarMessage(cause instanceof Error ? cause.message : "数字人管理数据加载失败。");
    }
  }

  async function loadAdminSentimentReport() {
    try {
      const report = await getAdminSentimentReport();
      setSentimentReport(report);
    } catch (cause) {
      setSentimentMessage(cause instanceof Error ? cause.message : "游客感受度报告加载失败。");
    }
  }

  async function loadAdminSystemSettings() {
    try {
      const settings = await getAdminSystemSettings();
      setSystemSettings(settings);
    } catch (cause) {
      setSystemMessage(cause instanceof Error ? cause.message : "系统设置加载失败。");
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
      setOperationMessage(`已发布 ${attraction.name} 的${operationTypeLabel(operationForm.event_type)}事件，新的路线推荐会读取该事件。`);
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

  async function handleDraftKnowledgeGap(gapId: string) {
    setGapBusyId(gapId);
    setGapMessage("");
    try {
      const gap = await draftKnowledgeGapFaq(gapId);
      setGapMessage(`FAQ 草稿已生成，linked_faq=${gap.linked_faq_id || gap.faq?.id || "待刷新"}，发布前仍需管理员确认。`);
      await loadKnowledgeGaps();
      await loadAdminKnowledge();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "FAQ 草稿生成失败。");
    } finally {
      setGapBusyId("");
    }
  }

  async function handlePublishGapFaq(gap: KnowledgeGap) {
    const faqId = gap.linked_faq_id || gap.faq?.id;
    if (!faqId) {
      setGapMessage("请先生成 FAQ 草稿，再发布到本地知识库。");
      return;
    }
    setGapBusyId(gap.id);
    setGapMessage("");
    try {
      const result = await publishAdminKnowledge({ faq_ids: [faqId] });
      const faqResult = result.faq_results?.find((item) => (item.faq_id || item.id) === faqId);
      setGapMessage(
        `FAQ 已发布到本地 RAG，写入 ${faqResult?.published_chunks ?? result.published_chunks ?? 0} 个 chunk；gap=${faqResult?.gap_status_after_publish || "已刷新"}。`,
      );
      await loadKnowledgeGaps();
      await loadAdminKnowledge();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "FAQ 发布失败。");
    } finally {
      setGapBusyId("");
    }
  }

  async function handleSaveGapFaqFromEditor(gap: KnowledgeGap) {
    const faqId = gap.linked_faq_id || gap.faq?.id;
    if (!faqId) {
      setGapMessage("请先生成 FAQ 草稿，再用右侧 FAQ 编辑区保存。");
      return;
    }
    setGapBusyId(gap.id);
    setGapMessage("");
    try {
      await updateAdminFaq(faqId, {
        answer: faqDraft.answer,
        question: faqDraft.question || gap.query,
        tags: faqDraft.tags
          .split(/[，,锛?]/)
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setGapMessage("已用右侧 FAQ 编辑区内容更新 linked FAQ 草稿，发布前仍需管理员确认。");
      await loadAdminKnowledge();
      await loadKnowledgeGaps();
    } catch (cause) {
      setGapMessage(cause instanceof Error ? cause.message : "FAQ 草稿更新失败。");
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

  async function handleCreateKnowledgeAsset() {
    setKnowledgeAdminBusy("asset");
    setKnowledgeAdminMessage("");
    try {
      const asset = await createAdminKnowledgeAsset({
        asset_type: "guide_script",
        attraction_id: knowledgeAssetDraft.attraction_id || undefined,
        content: knowledgeAssetDraft.content,
        note: "管理员通过后台新增的本地知识正文，可发布进 SQLite RAG chunk。",
        scenic_area: knowledgeAssetDraft.scenic_area || undefined,
        source_filename: knowledgeAssetDraft.source_filename || "admin-knowledge.md",
        title: knowledgeAssetDraft.title || "后台新增知识内容",
      });
      setKnowledgeAdminMessage(`已保存“${asset.title}”，可点击发布到知识库写入本地 RAG。`);
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "上传文档记录创建失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handleCreateAdminFaq(status: AdminKnowledgeStatus = "draft") {
    setKnowledgeAdminBusy(status === "published" ? "publish-faq" : "faq");
    setKnowledgeAdminMessage("");
    try {
      const faq = await createAdminFaq({
        answer: faqDraft.answer,
        question: faqDraft.question,
        status: "draft",
        tags: faqDraft.tags
          .split(/[，,]/)
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      if (status === "published") {
        const result = await publishAdminKnowledge({ faq_ids: [faq.id] });
        setKnowledgeAdminMessage(`FAQ 已保存并发布到本地 RAG，写入 ${result.published_chunks ?? 0} 个 chunk。`);
      } else {
        setKnowledgeAdminMessage("FAQ 草稿已保存。");
      }
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "FAQ 保存失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handleReindexKnowledge() {
    setKnowledgeAdminBusy("reindex");
    setKnowledgeAdminMessage("");
    try {
      const result = await reindexAdminKnowledge();
      setKnowledgeAdminMessage(result.message);
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "重建索引失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handlePublishKnowledge() {
    setKnowledgeAdminBusy("publish");
    setKnowledgeAdminMessage("");
    try {
      const result = await publishAdminKnowledge({ publish_all_drafts: true });
      setKnowledgeAdminMessage(`${result.message} 资产 ${result.published_assets ?? 0} 条，FAQ ${result.published_faqs ?? 0} 条。`);
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "发布到知识库失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handlePublishFaq(faqId: string) {
    setKnowledgeAdminBusy(faqId);
    setKnowledgeAdminMessage("");
    try {
      const result = await publishAdminKnowledge({ faq_ids: [faqId] });
      setKnowledgeAdminMessage(`FAQ 已发布到本地 RAG，写入 ${result.published_chunks ?? 0} 个 chunk。`);
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "FAQ 发布失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handlePublishAsset(assetId: string) {
    setKnowledgeAdminBusy(assetId);
    setKnowledgeAdminMessage("");
    try {
      const result = await publishAdminKnowledge({ asset_ids: [assetId] });
      setKnowledgeAdminMessage(`知识资产已发布到本地 RAG，写入 ${result.published_chunks ?? 0} 个 chunk。`);
      await loadAdminKnowledge();
    } catch (cause) {
      setKnowledgeAdminMessage(cause instanceof Error ? cause.message : "知识资产发布失败。");
    } finally {
      setKnowledgeAdminBusy("");
    }
  }

  async function handleSaveAvatarProfile() {
    setAvatarBusy("profile");
    setAvatarMessage("");
    try {
      const profile = await updateAdminAvatarProfile({
        background_style: avatarProfile.background_style || "",
        default_emotion: avatarProfile.default_emotion,
        name: avatarProfile.name,
        outfit_style: avatarProfile.outfit_style,
        speech_rate: avatarProfile.speech_rate,
        voice_name: avatarProfile.voice_name,
        volume: avatarProfile.volume,
      });
      setAvatarProfile(profile);
      setAvatarMessage("数字人配置已保存到本地 SQLite，刷新后仍会保留。");
    } catch (cause) {
      setAvatarMessage(cause instanceof Error ? cause.message : "数字人配置保存失败。");
    } finally {
      setAvatarBusy("");
    }
  }

  async function handleAvatarVoiceTest() {
    setAvatarBusy("voice");
    setAvatarMessage("");
    try {
      const result = await runAdminAvatarVoiceTest({
        text: "您好，我是灵境导游，正在进行音色试听。",
        voice_name: avatarProfile.voice_name,
      });
      setAvatarMessage(`${result.message} mode=${result.mode}`);
    } catch (cause) {
      setAvatarMessage(cause instanceof Error ? cause.message : "试听音色失败。");
    } finally {
      setAvatarBusy("");
    }
  }

  async function handleGenerateAvatarClip() {
    setAvatarBusy("clip");
    setAvatarMessage("");
    try {
      const title = `预存讲解任务 ${avatarJobs.length + 1}`;
      await generateAdminAvatarClip({
        attraction_id: "lingshan-ls-011",
        title,
      });
      setAvatarMessage("已创建预存讲解 mock 任务；未生成真实音频文件。");
      await loadAdminAvatar();
    } catch (cause) {
      setAvatarMessage(cause instanceof Error ? cause.message : "预存讲解任务创建失败。");
    } finally {
      setAvatarBusy("");
    }
  }

  async function handleGenerateSentimentReport() {
    setSentimentBusy("generate");
    setSentimentMessage("");
    try {
      const report = await generateAdminSentimentReport();
      setSentimentReport(report);
      setSentimentMessage(`${report.message} job=${report.job_id}`);
    } catch (cause) {
      setSentimentMessage(cause instanceof Error ? cause.message : "游客感受度周报生成失败。");
    } finally {
      setSentimentBusy("");
    }
  }

  function handleSentimentPdfStub() {
    setSentimentMessage("演示版已生成报告数据，PDF 导出待接入；当前不会生成或下载文件。");
  }

  function handleSentimentOperationHint() {
    setSentimentMessage("如需创建运营事件，请切换到“运营事件”页发布 crowd / closed / show / recommendation 事件。");
  }

  async function handleSaveSystemSettings() {
    setSystemBusy("settings");
    setSystemMessage("");
    try {
      const settings = await updateAdminSystemSettings({
        avatar_mode: systemSettings.avatar_mode,
        data_boundary_notice: systemSettings.data_boundary_notice,
        default_provider_mode: systemSettings.default_provider_mode,
        mock_crowd_enabled: systemSettings.mock_crowd_enabled,
        route_topology_enabled: systemSettings.route_topology_enabled,
        scenic_area_name: systemSettings.scenic_area_name,
      });
      setSystemSettings(settings);
      setSystemMessage("系统设置已保存到本地 SQLite，mock 模式无 API Key 可运行。");
    } catch (cause) {
      setSystemMessage(cause instanceof Error ? cause.message : "系统设置保存失败。");
    } finally {
      setSystemBusy("");
    }
  }

  async function handleRunSystemHealthcheck() {
    setSystemBusy("health");
    setSystemMessage("");
    try {
      const result = await runAdminSystemHealthcheck();
      setSystemHealth(result);
      setSystemMessage("健康检查已完成，结果来自后端本地状态与 mock fallback。");
    } catch (cause) {
      setSystemMessage(cause instanceof Error ? cause.message : "健康检查失败。");
    } finally {
      setSystemBusy("");
    }
  }

  const providerEntries = providers
    ? Object.entries(providers).map(([name, value]) => ({
        name,
        provider: value.provider,
        status: value.status,
        model: value.model,
        configured: value.configured,
        mode: value.mode,
      }))
    : providerRows.map(([name, provider, status]) => ({
        name,
        provider,
        status,
        model: null,
        configured: true,
        mode: "mock",
      }));
  const tags = overview?.feedback_tags || [];
  const themes = overview?.route_theme_distribution || [];
  const popularQuestions = overview?.popular_questions || [];
  const lowConfidence = overview?.low_confidence_questions || [];
  const recentEvents = overview?.recent_events || [];
  const highCrowdItems = overview?.high_crowd_attractions || [];
  const filteredKnowledgeGaps = gapStatusFilter === "all" ? knowledgeGaps : knowledgeGaps.filter((gap) => gap.status === gapStatusFilter);
  const evalReports = evalOverview?.reports || [];
  const activeNav = adminNavItems.find((item) => item.id === activeAdminSection) || adminNavItems[0];
  const gapCounts = knowledgeGaps.reduce<Record<KnowledgeGapStatus, number>>(
    (acc, gap) => {
      acc[gap.status] += 1;
      return acc;
    },
    { open: 0, drafted: 0, resolved: 0, ignored: 0 },
  );
  const openGapCount = overview?.open_knowledge_gap_count ?? gapCounts.open;
  const analyticsNote = overview?.source_note || "本地演示数据 / 公开样例与交互日志汇总，非真实硬件客流。";
  const topbarSubtitle: Record<AdminTabId, string> = {
    overview: "本地演示数据 / 公开样例与交互日志汇总",
    knowledge: "文档资产、FAQ 与知识缺口闭环",
    avatar: "配置外观、声音与演示表现层",
    operations: "运营事件、智能评估与分流提示",
    sentiment: "基于本地交互日志与反馈记录生成服务建议",
    dashboard: "服务趋势、热门问答、满意度与路线偏好",
    settings: "Provider、表现层与演示边界配置",
  };
  const todayServiceCount = overview?.service_count && overview.service_count > 0 ? overview.service_count : 328;
  const weekServiceCount = Math.max(overview?.service_count ? overview.service_count * 6 + 178 : 2146, todayServiceCount);
  const qaAccuracy = evalOverview?.overall.overall_accuracy ?? 0.926;
  const satisfaction = overview?.average_rating ?? 4.7;
  const sentimentSatisfaction = sentimentReport?.satisfaction_score ?? satisfaction;
  const sentimentPositiveRate = Math.round((sentimentReport?.positive_rate ?? 0.82) * 100);
  const sentimentPendingIssues = sentimentReport?.pending_issues ?? (openGapCount || 18);
  const sentimentLowConfidenceCount = sentimentReport?.low_confidence_count ?? (lowConfidence.length || 7);
  const sentimentVolatilityIndex = sentimentReport?.emotion_volatility_index ?? 12;
  const avatarSuccessRate = 0.961;
  const dashboardThemes = themes.length > 0 ? themes.map((item) => ({ label: item.theme_label, value: item.count, percent: Math.min(46, Math.max(10, item.count * 10)) })) : routeThemes;
  const documentRows =
    knowledgeAssets.length > 0
      ? knowledgeAssets.map((asset) => [
          asset.title,
          assetTypeLabel(asset.asset_type),
          <StatusBadge tone={adminKnowledgeStatusTone(asset.status)}>{adminKnowledgeStatusLabel(asset.status)}</StatusBadge>,
          asset.chunk_count > 0 ? `${asset.chunk_count} chunks` : "未写入",
          formatMaybeDate(asset.updated_at),
          <div className="admin-inline-actions">
            {asset.status === "published" && asset.chunk_count > 0 ? (
              <span>{asset.last_publish_message || "已进入本地 RAG"}</span>
            ) : (
              <button className="operation-toggle" disabled={knowledgeAdminBusy === asset.id} onClick={() => void handlePublishAsset(asset.id)} type="button">发布资产</button>
            )}
          </div>,
        ])
      : [["暂无文档资产", "-", <StatusBadge tone="neutral">empty</StatusBadge>, "-", "-", "填写新增知识内容后保存"]];
  const faqRows =
    adminFaqs.length > 0
      ? adminFaqs.map((faq) => [
          <span>{faq.question}{faq.source_gap_id ? <small className="admin-linked-meta"> gap:{faq.source_gap_id}</small> : null}</span>,
          <StatusBadge tone={adminKnowledgeStatusTone(faq.status)}>{adminKnowledgeStatusLabel(faq.status)}</StatusBadge>,
          faq.tags.join("、") || "-",
          formatMaybeDate(faq.updated_at),
          faq.status === "published" ? "已发布" : <button className="operation-toggle" disabled={knowledgeAdminBusy === faq.id} onClick={() => void handlePublishFaq(faq.id)} type="button">发布 FAQ</button>,
        ])
      : [["暂无 FAQ", <StatusBadge tone="neutral">empty</StatusBadge>, "-", "-", "保存草稿后显示"]];
  const hotQuestionRows = useMemo(
    () =>
      (popularQuestions.length > 0
        ? popularQuestions.slice(0, 5).map((item, index) => [index + 1, item.question, item.count])
        : [
            [1, "灵山大佛怎么游览？", 128],
            [2, "九龙灌浴几点表演？", 97],
            [3, "梵宫有什么看点？", 81],
            [4, "适合老人路线推荐？", 65],
            [5, "拈花湾夜游怎么玩？", 52],
          ]) as Array<Array<React.ReactNode>>,
    [popularQuestions],
  );

  return (
    <PageShell className="admin-console-page">
      <aside className="admin-console-sidebar" aria-label="管理后台导航">
        <div className="admin-console-brand">
          <span className="admin-console-brand__mark">
            <Bot aria-hidden="true" />
          </span>
          <div>
            <strong>灵境导游</strong>
            <span>管理平台</span>
          </div>
        </div>
        <nav className="admin-console-nav">
          {adminNavItems.map(({ id, label, path, Icon }) => (
            <a className={activeAdminSection === id ? "is-active" : ""} href={path} key={id}>
              <Icon aria-hidden="true" size={22} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="admin-sidebar-art" aria-hidden="true" />
      </aside>

      <section className="admin-console-main">
        <header className="admin-console-topbar">
          <div>
            <span>{activeNav.label}</span>
            <h1>
              {activeAdminSection === "overview" ? "运营总览" : null}
              {activeAdminSection === "knowledge" ? "知识库管理" : null}
              {activeAdminSection === "avatar" ? "数字人形象管理" : null}
              {activeAdminSection === "operations" ? "运营事件管理" : null}
              {activeAdminSection === "sentiment" ? "游客感受度报告" : null}
              {activeAdminSection === "dashboard" ? "数据大屏概览" : null}
              {activeAdminSection === "settings" ? "系统设置" : null}
            </h1>
            <p>{topbarSubtitle[activeAdminSection]}</p>
          </div>
          <div className="admin-console-tools">
            <div className="admin-topbar-menu">
              <button
                aria-expanded={topbarMenu === "gaps"}
                aria-label={`知识缺口提醒，${openGapCount} 条待处理`}
                className="admin-icon-button"
                onClick={() => setTopbarMenu((current) => (current === "gaps" ? null : "gaps"))}
                type="button"
              >
                <Bell aria-hidden="true" size={20} />
                <span>{openGapCount}</span>
              </button>
              {topbarMenu === "gaps" ? (
                <div className="admin-popover admin-popover--notice" role="status">
                  <strong>知识缺口提醒</strong>
                  <p>{openGapCount > 0 ? `当前有 ${openGapCount} 条待处理知识缺口。` : "当前没有待处理知识缺口。"}</p>
                  <a href="/admin/knowledge">查看知识缺口</a>
                </div>
              ) : null}
            </div>
            <label className="admin-date-filter">
              <CalendarClock aria-hidden="true" size={18} />
              <input readOnly value="2026-05-17" />
            </label>
            <div className="admin-topbar-menu">
              <button
                aria-expanded={topbarMenu === "scenic"}
                className="admin-select-button"
                onClick={() => setTopbarMenu((current) => (current === "scenic" ? null : "scenic"))}
                type="button"
              >
                <span>灵山胜境</span>
                <ChevronDown aria-hidden="true" size={16} />
              </button>
              {topbarMenu === "scenic" ? (
                <div className="admin-popover">
                  <strong>演示景区</strong>
                  <button type="button">灵山胜境</button>
                  <button type="button">拈花湾（样例）</button>
                </div>
              ) : null}
            </div>
            <div className="admin-topbar-menu">
              <button
                aria-expanded={topbarMenu === "user"}
                className="admin-user-button"
                onClick={() => setTopbarMenu((current) => (current === "user" ? null : "user"))}
                type="button"
              >
                <UserCog aria-hidden="true" size={18} />
                <span>管理员</span>
                <ChevronDown aria-hidden="true" size={16} />
              </button>
              {topbarMenu === "user" ? (
                <div className="admin-popover">
                  <strong>管理员</strong>
                  <button type="button">账号权限</button>
                  <button type="button">演示模式设置</button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        {activeAdminSection === "overview" ? (
          <>
            <section className="admin-kpi-grid" aria-label="核心指标">
              <AdminMetricCard Icon={Users} label="今日服务" trend="较昨日 ↑ 12.4%" value={String(todayServiceCount)} />
              <AdminMetricCard Icon={CalendarClock} label="本周服务" trend="较上周 ↑ 18.7%" value={String(weekServiceCount)} />
              <AdminMetricCard Icon={Gauge} label="问答准确率" trend="较昨日 ↑ 1.8%" value={formatRate(qaAccuracy)} />
              <AdminMetricCard Icon={Star} label="游客满意度" trend="较昨日 ↑ 0.2" value={satisfaction.toFixed(1)} suffix="/5" />
              <AdminMetricCard Icon={Volume2} label="数字人播报成功率" trend="较昨日 ↑ 1.2%" value={formatRate(avatarSuccessRate)} />
            </section>

            <section className="admin-dashboard-grid">
              <AdminPanel className="admin-panel--span-8" title="服务趋势" subtitle="近 7 天，本地演示日志汇总">
                <MiniTrend />
              </AdminPanel>
              <AdminPanel className="admin-panel--span-4" title="今日智能评估" subtitle="本地演示数据">
                <div className="admin-progress-list">
                  {[
                    ["知识命中率", "89.3%", 89],
                    ["路线生成成功率", "88.1%", 88],
                    ["识景确认率", "91.8%", 92],
                    ["低置信率", "3.2%", 8],
                  ].map(([label, value, percent]) => (
                    <div className="admin-progress-row" key={label as string}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                      <i><b style={{ width: `${percent}%` }} /></i>
                    </div>
                  ))}
                </div>
              </AdminPanel>
              <AdminPanel className="admin-panel--span-4" title="热门问答 TOP5" subtitle="今日">
                <AdminTable columns={["排名", "问题", "提问次数"]} rows={hotQuestionRows} />
              </AdminPanel>
              <AdminPanel className="admin-panel--span-4" title="路线偏好分布" subtitle="今日">
                <div className="admin-chart-with-legend">
                  <DonutChart items={dashboardThemes} />
                  <div className="admin-legend-list">
                    {dashboardThemes.map((item) => (
                      <span key={item.label}>
                        <i />
                        {item.label}
                        <strong>{item.percent}%</strong>
                      </span>
                    ))}
                  </div>
                </div>
              </AdminPanel>
              <AdminPanel className="admin-panel--span-4" title="知识缺口提醒" subtitle="近 7 天">
                <AdminTable
                  columns={["缺口主题", "相关问题数", "优先级"]}
                  rows={(knowledgeGaps.length > 0 ? knowledgeGaps.slice(0, 5) : []).map((gap) => [
                    gap.query,
                    gap.confidence ?? "-",
                    <StatusBadge tone={gap.status === "open" ? "warning" : "neutral"}>{gapStatusLabel(gap.status)}</StatusBadge>,
                  ])}
                />
                {knowledgeGaps.length === 0 ? <p className="admin-empty-compact">暂无知识缺口，低置信或无来源问答会进入这里。</p> : null}
              </AdminPanel>
              <AdminPanel className="admin-panel--span-12" title="最近交互记录" subtitle="不包含个人身份字段">
                <AdminTable
                  columns={["时间", "渠道", "问题 / 操作", "结果", "置信度", "操作"]}
                  rows={
                    recentEvents.length > 0
                      ? recentEvents.slice(0, 5).map((item) => [
                          item.created_at,
                          item.channel,
                          item.question || String(item.metadata.theme_label || item.metadata.matched_attraction_name || item.route_id || item.id),
                          item.success ? "已处理" : "待复核",
                          item.confidence ?? "-",
                          "查看详情  会话回放",
                        ])
                      : feedbackRows.map((item) => [item.time, item.channel, item.topic, item.action, item.confidence, "查看详情"])
                  }
                />
              </AdminPanel>
            </section>
          </>
        ) : null}

        {activeAdminSection === "knowledge" ? (
          <section className="admin-dashboard-grid">
            <AdminPanel
              className="admin-panel--span-7"
              title="知识文档管理"
              subtitle="上传讲解词 / 文史资料 / FAQ"
              toolbar={
                <>
                  <StubButton disabled={knowledgeAdminBusy === "asset"} icon={<Upload size={16} />} onClick={() => void handleCreateKnowledgeAsset()} tone="primary">上传文档</StubButton>
                  <StubButton disabled={knowledgeAdminBusy === "faq"} icon={<FilePlus2 size={16} />} onClick={() => void handleCreateAdminFaq("draft")}>新增 FAQ</StubButton>
                  <StubButton disabled={knowledgeAdminBusy === "reindex"} icon={<RefreshCw size={16} />} onClick={() => void handleReindexKnowledge()}>重建索引</StubButton>
                  <StubButton disabled={knowledgeAdminBusy === "publish"} icon={<BookOpenCheck size={16} />} onClick={() => void handlePublishKnowledge()} tone="gold">发布到知识库</StubButton>
                </>
              }
            >
              <div className="admin-upload-zone">
                <CloudUpload aria-hidden="true" size={42} />
                <strong>新增知识内容</strong>
                <span>本轮使用 JSON 文本入口，发布后会写入本地 RAG，不修改原始资料包。</span>
              </div>
              <div className="admin-knowledge-asset-form">
                <label>
                  <span>标题</span>
                  <input
                    onChange={(event) => setKnowledgeAssetDraft((current) => ({ ...current, title: event.target.value }))}
                    value={knowledgeAssetDraft.title}
                  />
                </label>
                <label>
                  <span>关联景点</span>
                  <select
                    onChange={(event) => {
                      const attraction = operationAttractions.find((item) => item.id === event.target.value);
                      setKnowledgeAssetDraft((current) => ({
                        ...current,
                        attraction_id: event.target.value,
                        scenic_area: attraction?.scenic_area || current.scenic_area,
                      }));
                    }}
                    value={knowledgeAssetDraft.attraction_id}
                  >
                    <option value="">不绑定景点</option>
                    {operationAttractions.map((item) => (
                      <option key={item.id} value={item.id}>{item.name} · {item.scenic_area}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>来源文件名</span>
                  <input
                    onChange={(event) => setKnowledgeAssetDraft((current) => ({ ...current, source_filename: event.target.value }))}
                    value={knowledgeAssetDraft.source_filename}
                  />
                </label>
                <label className="admin-knowledge-asset-form__content">
                  <span>正文</span>
                  <textarea
                    maxLength={20000}
                    onChange={(event) => setKnowledgeAssetDraft((current) => ({ ...current, content: event.target.value }))}
                    rows={6}
                    value={knowledgeAssetDraft.content}
                  />
                </label>
              </div>
              {knowledgeAdminMessage ? <p className="knowledge-gap-message">{knowledgeAdminMessage}</p> : null}
              <AdminTable columns={["文档名称", "类型", "状态", "RAG chunks", "更新时间", "操作"]} rows={documentRows} />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-5" title="FAQ 编辑区" subtitle="UI 预留，发布前需人工确认">
              <div className="admin-faq-editor">
                <label>
                  <span>问题</span>
                  <input onChange={(event) => setFaqDraft((current) => ({ ...current, question: event.target.value }))} value={faqDraft.question} />
                </label>
                <label>
                  <span>标准回答草稿</span>
                  <textarea onChange={(event) => setFaqDraft((current) => ({ ...current, answer: event.target.value }))} rows={7} value={faqDraft.answer} />
                </label>
                <label>
                  <span>标签</span>
                  <input onChange={(event) => setFaqDraft((current) => ({ ...current, tags: event.target.value }))} value={faqDraft.tags} />
                </label>
                <div className="admin-form-actions">
                  <StubButton disabled={knowledgeAdminBusy === "faq"} onClick={() => void handleCreateAdminFaq("draft")} tone="primary">保存草稿</StubButton>
                  <StubButton disabled={knowledgeAdminBusy === "publish-faq"} onClick={() => void handleCreateAdminFaq("published")} tone="gold">发布 FAQ</StubButton>
                </div>
                <AdminTable columns={["问题", "状态", "标签", "更新时间", "操作"]} rows={faqRows} />
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12 knowledge-gap-console" title="知识缺口闭环" subtitle="复用现有低置信 / 无来源 / 负反馈闭环能力">
              <div className="knowledge-gap-summary">
                <button className={gapStatusFilter === "all" ? "knowledge-gap-filter knowledge-gap-filter--active" : "knowledge-gap-filter"} onClick={() => setGapStatusFilter("all")} type="button">
                  全部 <strong>{knowledgeGaps.length}</strong>
                </button>
                {(["open", "drafted", "resolved", "ignored"] as KnowledgeGapStatus[]).map((status) => (
                  <button className={gapStatusFilter === status ? "knowledge-gap-filter knowledge-gap-filter--active" : "knowledge-gap-filter"} key={status} onClick={() => setGapStatusFilter(status)} type="button">
                    {gapStatusLabel(status)} <strong>{gapCounts[status]}</strong>
                  </button>
                ))}
              </div>
              {gapMessage ? <p className="knowledge-gap-message">{gapMessage}</p> : null}
              <div className="knowledge-gap-list">
                {filteredKnowledgeGaps.length > 0 ? (
                  filteredKnowledgeGaps.map((gap) => (
                    <article className="knowledge-gap-row" key={gap.id}>
                      <div className="knowledge-gap-row__main">
                        <div className="knowledge-gap-row__title">
                          <strong>{gap.query}</strong>
                          <StatusBadge tone={gapStatusTone(gap.status)}>{gapStatusLabel(gap.status)}</StatusBadge>
                          <StatusBadge tone="neutral">{gapTriggerLabel(gap.trigger_type)}</StatusBadge>
                          {gap.linked_faq_id ? (
                            <StatusBadge tone={gap.linked_faq_status === "published" ? "ok" : "warning"}>
                              FAQ {gap.linked_faq_status || "draft"}
                            </StatusBadge>
                          ) : null}
                        </div>
                        <p>{gap.suggested_faq ? gap.suggested_faq.replace(/[#*\n]/g, " ").slice(0, 150) : "暂无 FAQ 草稿。无可靠来源时需管理员补充资料，避免编造。"}</p>
                        {gap.resolution_note ? <p className="knowledge-gap-row__note">{gap.resolution_note}</p> : null}
                        <span>confidence={gap.confidence ?? "-"} · {new Date(gap.created_at).toLocaleString("zh-CN")} · eval={gap.eval_case_id || "未加入"} · faq={gap.linked_faq_id || "未生成"}</span>
                      </div>
                      <div className="knowledge-gap-actions">
                        <Button disabled={gapBusyId === gap.id} icon={<BookOpenCheck size={15} />} onClick={() => void handleDraftKnowledgeGap(gap.id)} type="button" variant="secondary">生成 FAQ</Button>
                        {gap.linked_faq_id && gap.linked_faq_status !== "published" ? (
                          <Button disabled={gapBusyId === gap.id} icon={<FilePlus2 size={15} />} onClick={() => void handleSaveGapFaqFromEditor(gap)} type="button" variant="secondary">保存编辑</Button>
                        ) : null}
                        {gap.linked_faq_id && gap.linked_faq_status !== "published" ? (
                          <Button disabled={gapBusyId === gap.id} icon={<BookOpenCheck size={15} />} onClick={() => void handlePublishGapFaq(gap)} type="button" variant="secondary">发布 FAQ</Button>
                        ) : null}
                        <Button disabled={gapBusyId === gap.id} icon={<FilePlus2 size={15} />} onClick={() => void handleAddKnowledgeGapToEval(gap.id)} type="button" variant="secondary">加入评测</Button>
                        <Button disabled={gapBusyId === gap.id} icon={<CheckCircle2 size={15} />} onClick={() => void handleUpdateKnowledgeGapStatus(gap.id, "resolved")} type="button" variant="quiet">已解决</Button>
                        <Button disabled={gapBusyId === gap.id} icon={<XCircle size={15} />} onClick={() => void handleUpdateKnowledgeGapStatus(gap.id, "ignored")} type="button" variant="quiet">忽略</Button>
                      </div>
                    </article>
                  ))
                ) : (
                  <p className="empty-state">当前没有该状态的知识缺口。游客端出现无来源问答或“信息不准”反馈后会进入这里。</p>
                )}
              </div>
            </AdminPanel>
          </section>
        ) : null}

        {activeAdminSection === "avatar" ? (
          <section className="admin-dashboard-grid">
            <AdminPanel className="admin-panel--span-5" title="形象预览" subtitle="LiteAvatar sidecar · 本地演示">
              <div className="admin-avatar-preview">
                <div className="admin-avatar-figure">
                  <Bot aria-hidden="true" size={78} />
                  <span>数字人表现层</span>
                </div>
                <div className="admin-avatar-float-tools" aria-hidden="true">
                  <MonitorPlay size={18} />
                  <Mic2 size={18} />
                  <Volume2 size={18} />
                </div>
              </div>
              <p className="admin-inline-note">已连接时仅用于播报与可视化展示，不输出决策内容。</p>
              <div className="admin-form-actions">
                <StubButton icon={<PlayCircle size={16} />} tone="primary">启动预览</StubButton>
                <StubButton>占位模式</StubButton>
                <StubButton>打开表现层</StubButton>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-3" title="形象配置" subtitle="外观、服装、背景">
              <div className="admin-setting-form">
                <label>
                  <span>形象名称</span>
                  <input onChange={(event) => setAvatarProfile((current) => ({ ...current, name: event.target.value }))} value={avatarProfile.name} />
                </label>
                <label>
                  <span>服装风格</span>
                  <input onChange={(event) => setAvatarProfile((current) => ({ ...current, outfit_style: event.target.value }))} value={avatarProfile.outfit_style} />
                </label>
                <label>
                  <span>默认情绪</span>
                  <select onChange={(event) => setAvatarProfile((current) => ({ ...current, default_emotion: event.target.value }))} value={avatarProfile.default_emotion}>
                    <option value="happy">亲和</option>
                    <option value="comforting">安抚</option>
                    <option value="neutral">讲解</option>
                  </select>
                </label>
                <label>
                  <span>背景风格</span>
                  <input onChange={(event) => setAvatarProfile((current) => ({ ...current, background_style: event.target.value }))} value={avatarProfile.background_style || ""} />
                </label>
                <div className="admin-segmented">
                  <button className={avatarProfile.default_emotion === "happy" ? "is-active" : ""} onClick={() => setAvatarProfile((current) => ({ ...current, default_emotion: "happy" }))} type="button">亲和</button>
                  <button className={avatarProfile.default_emotion === "neutral" ? "is-active" : ""} onClick={() => setAvatarProfile((current) => ({ ...current, default_emotion: "neutral" }))} type="button">讲解</button>
                  <button className={avatarProfile.default_emotion === "comforting" ? "is-active" : ""} onClick={() => setAvatarProfile((current) => ({ ...current, default_emotion: "comforting" }))} type="button">安抚</button>
                </div>
                <StubButton disabled={avatarBusy === "profile"} onClick={() => void handleSaveAvatarProfile()} tone="primary">保存配置</StubButton>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="声音配置" subtitle="TTS 合成与播报">
              <div className="admin-slider-list">
                <label>
                  <span>音色</span>
                  <select aria-label="音色选择" onChange={(event) => setAvatarProfile((current) => ({ ...current, voice_name: event.target.value }))} value={avatarProfile.voice_name}>
                    <option value="温柔女声">温柔女声</option>
                    <option value="清朗女声">清朗女声</option>
                    <option value="沉稳讲解声">沉稳讲解声</option>
                  </select>
                </label>
                <label>
                  <span>语速 {avatarProfile.speech_rate.toFixed(2)}x</span>
                  <input max={1.8} min={0.5} onChange={(event) => setAvatarProfile((current) => ({ ...current, speech_rate: Number(event.target.value) }))} step={0.05} type="range" value={avatarProfile.speech_rate} />
                </label>
                <label>
                  <span>音量 {Math.round(avatarProfile.volume * 100)}%</span>
                  <input max={1} min={0} onChange={(event) => setAvatarProfile((current) => ({ ...current, volume: Number(event.target.value) }))} step={0.05} type="range" value={avatarProfile.volume} />
                </label>
                <div className="admin-form-actions">
                  <StubButton disabled={avatarBusy === "voice"} icon={<Volume2 size={16} />} onClick={() => void handleAvatarVoiceTest()} tone="primary">试听音色</StubButton>
                  <StubButton disabled={avatarBusy === "clip"} onClick={() => void handleGenerateAvatarClip()} tone="gold">生成预存讲解</StubButton>
                </div>
                {avatarMessage ? <p className="operation-message">{avatarMessage}</p> : null}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="预存讲解 Clip" subtitle="用于播报与口型驱动">
              <AdminTable columns={["clip_id / job", "景点", "时长", "音频状态", "口型验证", "更新时间", "操作"]} rows={[...clipRows.map((clip) => [clip.id, clip.name, clip.duration, <StatusBadge tone={clip.audio === "已就绪" ? "ok" : "warning"}>{clip.audio}</StatusBadge>, <StatusBadge tone={clip.lip === "已通过" ? "ok" : "warning"}>{clip.lip}</StatusBadge>, clip.updated, "播放  替换音频  重新标准化"]), ...avatarJobs.map((job) => [job.clip_id || job.id, job.title, "-", <StatusBadge tone="neutral">{job.status}</StatusBadge>, <StatusBadge tone="warning">待处理</StatusBadge>, formatMaybeDate(job.updated_at), job.message])]} />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="表现层健康状态" subtitle="仅反映本地演示环境，不代表生产级别">
              <div className="admin-health-grid">
                <div><span>Sidecar 状态</span><strong>ready</strong><small>v1.3.1 liteavatar-sidecar</small></div>
                <div><span>活跃会话</span><strong>1</strong><small>receive-only viewer</small></div>
                <div><span>GPU 显存估算</span><strong>1.6GB / 4.0GB</strong><small>显存占用率 40%</small></div>
                <div><span>降级兜底</span><strong>available</strong><small>sidecar 不可用时静态占位 + 文本播报</small></div>
                <div><span>边界说明</span><strong>表现层</strong><small>不接管 RAG、路线、识景或运营分析。</small></div>
              </div>
            </AdminPanel>
          </section>
        ) : null}

        {activeAdminSection === "operations" ? (
          <section className="admin-dashboard-grid">
            <AdminPanel className="admin-panel--span-7 operation-console" title="事件创建" subtitle="影响后续路线推荐，发布前请确认景点与时段">
              <div className="operation-template-row">
                {(["crowd", "closed", "show", "recommendation"] as OperationEventType[]).map((type) => (
                  <button className={operationForm.event_type === type ? "operation-template-button operation-template-button--active" : "operation-template-button"} key={type} onClick={() => applyOperationTemplate(type, defaultOperationSeverity(type))} type="button">
                    {operationTypeLabel(type)}
                  </button>
                ))}
              </div>
              <form className="operation-create-form" onSubmit={handleCreateOperationEvent}>
                <div className="operation-form-grid">
                  <label className="operation-field">
                    <span>景点</span>
                    <select onChange={(event) => {
                      const attraction = operationAttractions.find((item) => item.id === event.target.value);
                      setOperationForm((current) => ({ ...current, attraction_id: event.target.value, message: current.message ? current.message : defaultOperationMessage(current.event_type, attraction?.name) }));
                    }} required value={operationForm.attraction_id}>
                      {operationAttractions.length > 0 ? operationAttractions.map((attraction) => <option key={attraction.id} value={attraction.id}>{attraction.scenic_area} · {attraction.name}</option>) : <option value="">景点加载中</option>}
                    </select>
                  </label>
                  <label className="operation-field">
                    <span>事件类型</span>
                    <select onChange={(event) => {
                      const eventType = event.target.value as OperationEventType;
                      setOperationForm((current) => ({ ...current, event_type: eventType, severity: defaultOperationSeverity(eventType), message: defaultOperationMessage(eventType, operationAttractions.find((item) => item.id === current.attraction_id)?.name) }));
                    }} value={operationForm.event_type}>
                      {(["crowd", "closed", "show", "recommendation"] as OperationEventType[]).map((type) => <option key={type} value={type}>{operationTypeLabel(type)}</option>)}
                    </select>
                  </label>
                  <label className="operation-field">
                    <span>影响等级</span>
                    <select onChange={(event) => setOperationForm((current) => ({ ...current, severity: event.target.value as OperationEventSeverity }))} value={operationForm.severity}>
                      {(["info", "warning", "critical"] as OperationEventSeverity[]).map((severity) => <option key={severity} value={severity}>{severityLabel(severity)}</option>)}
                    </select>
                  </label>
                  <label className="operation-field">
                    <span>持续小时</span>
                    <input max={24} min={0.5} onChange={(event) => setOperationForm((current) => ({ ...current, duration_hours: Number(event.target.value) }))} step={0.5} type="number" value={operationForm.duration_hours} />
                  </label>
                </div>
                <label className="operation-field operation-field--wide">
                  <span>对游客展示的说明</span>
                  <textarea onChange={(event) => setOperationForm((current) => ({ ...current, message: event.target.value }))} placeholder="例如：当前排队较多，建议先前往周边景点，稍后返回。" rows={3} value={operationForm.message} />
                </label>
                <div className="operation-form-actions">
                  <Button disabled={operationAttractions.length === 0} icon={<Plus size={16} />} loading={operationLoading} type="submit" variant={operationForm.event_type === "closed" ? "accent" : "primary"}>发布运营事件</Button>
                </div>
              </form>
              {operationMessage ? <p className="operation-message">{operationMessage}</p> : null}
            </AdminPanel>
            <AdminPanel className="admin-panel--span-5" title="今日智能评估" subtitle="规则 + 本地日志汇总">
              <div className="admin-assessment-list">
                <p><strong>推荐分流：</strong>灵山大佛咨询较集中，可引导部分游客先游览五印坛城。</p>
                <p><strong>知识补齐：</strong>停车收费、寄存行李、夜游灯光时间仍需补充来源。</p>
                <p><strong>服务提醒：</strong>低置信回答进入知识缺口，不自动编造。</p>
              </div>
              <div className="admin-alert-note">实时客流预警为 mock_simulation / 非真实硬件采集。</div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="实时客流预警" subtitle="mock_simulation / 非真实硬件客流">
              <AdminTable columns={["区域", "客流状态", "人数估算", "拥挤度", "建议操作"]} rows={mockCrowdRows.map((row) => [row.area, <StatusBadge tone={row.state === "拥挤" ? "warning" : "neutral"}>{row.state}</StatusBadge>, row.estimate, <CrowdDots count={row.density} />, row.action])} />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="最近运营事件" subtitle="复用现有运营事件 API">
              <div className="operation-event-list">
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
                        <span>{eventTimeWindow(event)} · source={event.source}</span>
                      </div>
                      <button className="operation-toggle" disabled={operationBusyId === event.id} onClick={() => void toggleOperationEvent(event)} type="button">{event.active ? "启用中" : "已停用"}</button>
                    </article>
                  ))
                ) : (
                  <p className="empty-state">暂无运营事件。可用上方按钮发布拥挤、临时关闭、演出提醒或推荐分流事件。</p>
                )}
              </div>
            </AdminPanel>
          </section>
        ) : null}

        {activeAdminSection === "sentiment" ? (
          <section className="admin-dashboard-grid admin-sentiment-screen">
            <section className="admin-kpi-grid admin-panel--span-12" aria-label="游客感受度指标">
              <AdminMetricCard Icon={Star} label="满意度均值（5分制）" trend="本地反馈汇总" value={sentimentSatisfaction.toFixed(1)} suffix="/5" />
              <AdminMetricCard Icon={Smile} label="正向反馈占比" trend="本地样例口径" value={String(sentimentPositiveRate)} suffix="%" />
              <AdminMetricCard Icon={AlertTriangle} label="待跟进问题" trend="知识缺口 + 低置信" value={String(sentimentPendingIssues)} />
              <AdminMetricCard Icon={MessageSquareText} label="低置信问答" trend="本地日志识别" value={String(sentimentLowConfidenceCount)} />
              <AdminMetricCard Icon={LineChart} label="情绪波动指数" trend="演示指数" value={String(sentimentVolatilityIndex)} suffix="%" />
            </section>
            <AdminPanel className="admin-panel--span-7" title="情感趋势" subtitle="近 7 天">
              <div className="admin-sentiment-chart">
                <div className="admin-chart-legend">
                  <span><i className="is-positive" />正向</span>
                  <span><i className="is-neutral" />中性</span>
                  <span><i className="is-negative" />负向</span>
                </div>
                <MiniTrend values={[70, 75, 69, 74, 71, 77, 86]} />
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-5" title="服务建议" subtitle="基于数据洞察与反馈聚类">
              <ol className="admin-advice-list admin-advice-list--numbered">
                {(sentimentReport?.service_suggestions || [
                  "补充九龙灌浴演出时间 FAQ，明确具体时段与注意事项。",
                  "优化老人路线讲解，增加无障碍设施与休息点指引。",
                  "完善低置信兜底话术，提升未命中问题的引导与体验。",
                ]).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
              {sentimentMessage ? <p className="operation-message">{sentimentMessage}</p> : null}
              <div className="admin-form-actions admin-form-actions--spread">
                <StubButton disabled={sentimentBusy === "generate"} onClick={() => void handleGenerateSentimentReport()} tone="primary">
                  {sentimentBusy === "generate" ? "生成中" : "生成周报"}
                </StubButton>
                <StubButton icon={<Upload size={16} />} onClick={handleSentimentPdfStub}>导出 PDF</StubButton>
                <StubButton onClick={handleSentimentOperationHint} tone="gold">创建运营事件</StubButton>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="游客关注点 TOP5" subtitle="近 7 天">
              <div className="admin-rank-list">
                {(sentimentReport?.focus_topics || (tags.length > 0 ? tags.slice(0, 5).map((item) => ({ topic: item.tag, count: item.count })) : [
                  { topic: "灵山大佛怎么游览", count: 12856 },
                  { topic: "九龙灌浴几点表演", count: 9732 },
                  { topic: "梵宫有什么看点", count: 8421 },
                  { topic: "适合老人路线", count: 7215 },
                  { topic: "拈花湾夜游", count: 6184 },
                ])).map((item, index) => (
                  <div key={item.topic}><span>{index + 1}</span><strong>{item.topic}</strong><em>{item.count}</em></div>
                ))}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="负向反馈原因" subtitle="近 7 天">
              <div className="admin-compact-bars admin-compact-bars--red">
                {(sentimentReport?.negative_reasons || [
                  { reason: "信息不准确 / 过时", percent: 38, count: 262 },
                  { reason: "路线指引不清晰", percent: 26, count: 178 },
                  { reason: "演出时间不明确", percent: 18, count: 122 },
                  { reason: "内容不完整", percent: 10, count: 69 },
                ]).map((item) => (
                  <div className="admin-compact-bar-row" key={item.reason}>
                    <span>{item.reason}</span>
                    <i><b style={{ width: `${item.percent}%` }} /></i>
                    <strong>{item.percent}%</strong>
                    <em>{item.count}</em>
                  </div>
                ))}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="路线体验标签" subtitle="近 7 天">
              <div className="admin-compact-bars">
                {(sentimentReport?.route_experience_tags || [
                  { tag: "路线合理", percent: 42, count: 1285 },
                  { tag: "避开拥挤", percent: 32, count: 978 },
                  { tag: "讲解清楚", percent: 24, count: 554 },
                  { tag: "人多拥挤", percent: 14, count: 421 },
                ]).map((item) => (
                  <div className="admin-compact-bar-row" key={item.tag}>
                    <span>{item.tag}</span>
                    <i><b style={{ width: `${item.percent}%` }} /></i>
                    <strong>{item.percent}%</strong>
                    <em>{item.count}</em>
                  </div>
                ))}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="反馈明细" subtitle="近 7 天">
              <AdminTable
                columns={["时间", "渠道", "场景", "评分（5分制）", "标签", "反馈摘要", "处理状态", "操作"]}
                rows={(sentimentReport?.feedback_rows || []).length > 0 ? (sentimentReport?.feedback_rows || []).map((row) => [
                  formatMaybeDate(row.time),
                  row.channel,
                  row.topic,
                  row.rating.toFixed(1),
                  <StatusBadge tone={sentimentTone(row.sentiment)}>{sentimentLabel(row.sentiment)}</StatusBadge>,
                  row.comment,
                  <StatusBadge tone={row.status.includes("待") ? "warning" : row.status.includes("已") ? "ok" : "neutral"}>{row.status}</StatusBadge>,
                  "查看  转知识缺口  标记已处理",
                ]) : [
                  ["暂无反馈", "-", "-", "-", <StatusBadge tone="neutral">empty</StatusBadge>, "生成周报后会读取本地反馈样例。", <StatusBadge tone="neutral">待生成</StatusBadge>, "-"],
                ]}
              />
            </AdminPanel>
            <p className="admin-source-footnote admin-panel--span-12">{sentimentReport?.source_note || "分析来源：本地演示交互日志 / 反馈样例，不代表真实景区全量运营数据。"}</p>
          </section>
        ) : null}

        {activeAdminSection === "dashboard" ? (
          <section className="admin-dashboard-grid admin-big-screen">
            <section className="admin-kpi-grid admin-kpi-grid--six admin-panel--span-12">
              <AdminMetricCard Icon={Users} label="今日服务人次" trend="较昨日 ↑ 12.4%" value={String(todayServiceCount)} />
              <AdminMetricCard Icon={CalendarClock} label="本周服务" trend="较上周 ↑ 18.7%" value={String(weekServiceCount)} />
              <AdminMetricCard Icon={MessageSquareText} label="热门问答" trend="较昨日 ↑ 8" value={String(popularQuestions[0]?.count || 76)} />
              <AdminMetricCard Icon={Star} label="平均满意度" trend="较昨日 ↑ 0.2" value={satisfaction.toFixed(1)} suffix="/5" />
              <AdminMetricCard Icon={Route} label="路线生成" trend="较昨日 ↑ 15" value={String(overview?.route_count || 132)} />
              <AdminMetricCard Icon={Volume2} label="数字人播报" trend="较昨日 ↑ 21" value="219" />
            </section>
            <AdminPanel className="admin-panel--span-4" title="服务人次趋势" subtitle="近 7 天">
              <MiniTrend />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="热门问答词云" subtitle="近 7 天">
              <div className="admin-word-cloud">
                {wordCloud.map((word, index) => <span className={`size-${(index % 4) + 1}`} key={word}>{word}</span>)}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="游客满意度趋势" subtitle="近 7 天">
              <MiniTrend values={sentimentTrend.map((item) => item * 16)} />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="路线主题分布" subtitle="今日">
              <div className="admin-chart-with-legend">
                <DonutChart items={dashboardThemes} />
                <div className="admin-legend-list">
                  {dashboardThemes.map((item) => <span key={item.label}><i />{item.label}<strong>{item.value}</strong></span>)}
                </div>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="路线主题分布" subtitle="详情">
              <div className="admin-compact-bars">
                {routeThemes.map((item) => (
                  <div className="admin-compact-bar-row" key={item.label}>
                    <span>{item.label}</span>
                    <i><b style={{ width: `${item.percent * 2.4}%` }} /></i>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-4" title="渠道占比" subtitle="今日">
              <div className="admin-chart-with-legend">
                <DonutChart items={[{ label: "小程序", percent: 58 }, { label: "数字人终端", percent: 22 }, { label: "景区 App", percent: 12 }, { label: "微信公众号", percent: 6 }, { label: "其他", percent: 2 }]} />
                <div className="admin-legend-list">
                  {["小程序 58%", "数字人终端 22%", "景区 App 12%", "微信公众号 6%", "其他 2%"].map((item) => <span key={item}><i />{item}</span>)}
                </div>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-5" title="高频低置信问题" subtitle="近 7 天">
              <AdminTable
                columns={["排名", "问题", "出现次数", "低置信率", "操作"]}
                rows={(lowConfidence.length > 0 ? lowConfidence.slice(0, 5).map((item, index) => [index + 1, item.question, "-", item.confidence ?? "-", "加入知识库"]) : [
                  [1, "灵山大佛要不要票额外收费？", 128, "38%", "加入知识库"],
                  [2, "九龙灌浴演出一般持续多久？", 97, "26%", "加入知识库"],
                  [3, "五印坛城适合老人参观吗？", 81, "22%", "加入知识库"],
                  [4, "梵宫晚上有灯光秀吗？", 65, "31%", "加入知识库"],
                  [5, "景区内存包寄存位置在哪里？", 52, "24%", "加入知识库"],
                ])}
              />
            </AdminPanel>
            <AdminPanel className="admin-panel--span-7" title="今日路线分流建议" subtitle="不代表真实硬件客流">
              <AdminTable columns={["路线主题", "推荐比例", "建议方向", "建议说明", "操作"]} rows={routeAdviceRows.map((row) => [row.theme, row.ratio, row.path, row.note, "查看详情"])} />
            </AdminPanel>
            <p className="admin-source-footnote admin-panel--span-6">数据来源：本地演示日志、mock_simulation 与公开样例，不代表真实硬件客流。</p>
            <div className="admin-dashboard-actions admin-panel--span-6">
              <StubButton icon={<RefreshCw size={16} />}>刷新数据</StubButton>
              <StubButton icon={<Upload size={16} />}>导出大屏</StubButton>
              <StubButton>查看评测报告</StubButton>
              <StubButton tone="gold">生成运营建议</StubButton>
            </div>
          </section>
        ) : null}

        {activeAdminSection === "settings" ? (
          <section className="admin-dashboard-grid">
            <AdminPanel className="admin-panel--span-6" title="AI Provider 配置" subtitle="mock 无 Key 可运行，真实 Key 不写入前端">
              <div className="provider-list">
                {providerEntries.map((item) => (
                  <div className="provider-row" key={item.name}>
                    <span>{item.name}</span>
                    <strong>{item.provider}{item.model ? ` / ${item.model}` : ""}</strong>
                    <StatusBadge tone={item.status === "ok" ? "ok" : "warning"}>
                      {item.configured === false ? "missing key" : item.mode || item.status}
                    </StatusBadge>
                  </div>
                ))}
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-6" title="数字人表现层配置" subtitle="后端统一转发，前端不直连模型厂商">
              <div className="admin-endpoint-list">
                <span><b>sidecar URL</b><code>AVATAR_SIDECAR_BASE_URL</code></span>
                <span><b>speak path</b><code>POST /api/avatar/speak</code></span>
                <span><b>clip path</b><code>POST /api/avatar/play-clip</code></span>
                <span><b>receive-only viewer</b><code>POST /api/avatar/webrtc/offer</code></span>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-6" title="安全与边界" subtitle="演示边界保持清晰">
              <div className="admin-boundary-list">
                <p><ShieldCheck aria-hidden="true" size={18} /> 前端只调用本项目后端 API。</p>
                <p><ShieldCheck aria-hidden="true" size={18} /> mock 模式不需要 API Key。</p>
                <p><ShieldCheck aria-hidden="true" size={18} /> 不声称真实 GPS、真实客流、真实硬件或真实地图导航。</p>
                <p><ShieldCheck aria-hidden="true" size={18} /> 数字人只是表现层，不接管 RAG、路线、识景、运营分析。</p>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-3" title="账号权限" subtitle="UI 预留">
              <div className="admin-permission-list">
                <span>管理员 · 全部模块</span>
                <span>运营 · 事件与反馈</span>
                <span>内容 · 知识库与 FAQ</span>
              </div>
              <StubButton icon={<UserCog size={16} />}>管理账号</StubButton>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-6" title="演示模式与数据边界" subtitle="本地 mock 配置保存到 SQLite">
              <div className="admin-setting-form">
                <label>
                  演示景区名称
                  <input
                    onChange={(event) => setSystemSettings((current) => ({ ...current, scenic_area_name: event.target.value }))}
                    value={systemSettings.scenic_area_name}
                  />
                </label>
                <label>
                  默认 provider 模式
                  <select
                    onChange={(event) => setSystemSettings((current) => ({ ...current, default_provider_mode: event.target.value }))}
                    value={systemSettings.default_provider_mode}
                  >
                    <option value="mock">mock</option>
                    <option value="local">local</option>
                    <option value="sidecar">sidecar</option>
                  </select>
                </label>
                <label>
                  数字人模式
                  <select
                    onChange={(event) => setSystemSettings((current) => ({ ...current, avatar_mode: event.target.value }))}
                    value={systemSettings.avatar_mode}
                  >
                    <option value="mock">mock</option>
                    <option value="sidecar">sidecar</option>
                    <option value="browser_fallback">browser fallback</option>
                  </select>
                </label>
                <label className="admin-checkbox-row">
                  <input
                    checked={systemSettings.mock_crowd_enabled}
                    onChange={(event) => setSystemSettings((current) => ({ ...current, mock_crowd_enabled: event.target.checked }))}
                    type="checkbox"
                  />
                  启用 mock 拥挤度演示数据
                </label>
                <label className="admin-checkbox-row">
                  <input
                    checked={systemSettings.route_topology_enabled}
                    onChange={(event) => setSystemSettings((current) => ({ ...current, route_topology_enabled: event.target.checked }))}
                    type="checkbox"
                  />
                  启用导览图拓扑路线说明
                </label>
                <label>
                  数据边界提示
                  <textarea
                    onChange={(event) => setSystemSettings((current) => ({ ...current, data_boundary_notice: event.target.value }))}
                    rows={3}
                    value={systemSettings.data_boundary_notice}
                  />
                </label>
              </div>
              {systemMessage ? <p className="operation-message">{systemMessage}</p> : null}
              <div className="admin-form-actions">
                <StubButton disabled={systemBusy === "settings"} icon={<SlidersHorizontal size={16} />} onClick={() => void handleSaveSystemSettings()} tone="gold">
                  {systemBusy === "settings" ? "保存中" : "保存设置"}
                </StubButton>
                <StubButton disabled={systemBusy === "health"} icon={<RefreshCw size={16} />} onClick={() => void handleRunSystemHealthcheck()} tone="primary">
                  {systemBusy === "health" ? "检查中" : "运行健康检查"}
                </StubButton>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-3" title="健康检查" subtitle="后端本地状态">
              <div className="admin-toggle-list">
                <span>backend <b>{String(systemHealth?.backend?.["status"] || "待检查")}</b></span>
                <span>database <b>{String(systemHealth?.database?.["status"] || "待检查")}</b></span>
                <span>avatar mock <b>{String(systemHealth?.avatar_mock?.["status"] || "待检查")}</b></span>
                <span>sidecar <b>{String(systemHealth?.sidecar_status?.["status"] || "mock_fallback")}</b></span>
                <span>knowledge local <b>{String(systemHealth?.knowledge_local?.["status"] || "待检查")}</b></span>
              </div>
            </AdminPanel>
            <AdminPanel className="admin-panel--span-12" title="评测看板" subtitle="保留现有 eval reports 概览">
              <AdminTable
                columns={["报告", "状态", "样例", "通过率", "平均延迟", "生成时间"]}
                rows={
                  evalReports.length > 0
                    ? evalReports.map((report) => [report.title, <StatusBadge tone={report.status === "pass" ? "ok" : report.status === "fail" ? "warning" : "neutral"}>{report.status}</StatusBadge>, `${report.passed}/${report.total}`, formatRate(report.accuracy), report.avg_latency_ms ? `${Math.round(report.avg_latency_ms)}ms` : "暂无", formatMaybeDate(report.generated_at)])
                    : [["暂无评测报告", <StatusBadge tone="neutral">missing</StatusBadge>, "0/0", "暂无", "暂无", "未生成"]]
                }
              />
            </AdminPanel>
          </section>
        ) : null}
      </section>
    </PageShell>
  );
}
