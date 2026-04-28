import {
  Activity,
  AlertTriangle,
  Bot,
  ChartNoAxesCombined,
  Database,
  Gauge,
  Heart,
  HelpCircle,
  MessageSquareText,
  Route,
  Search,
  Settings,
  Share2,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";

import { getAnalyticsOverview } from "../api/client";
import type { AnalyticsOverview } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { providerRows } from "../data/mock";

type ProviderMap = Record<string, { provider: string; status: string }>;

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

export function AdminPage() {
  const [providers, setProviders] = useState<ProviderMap | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);

  useEffect(() => {
    fetch("/api/provider/status")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(setProviders)
      .catch(() => setProviders(null));
    getAnalyticsOverview()
      .then(setOverview)
      .catch(() => setOverview(null));
  }, []);

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
