import {
  Activity,
  AlertTriangle,
  Bot,
  ChartNoAxesCombined,
  Database,
  Gauge,
  Heart,
  HelpCircle,
  Search,
  Settings,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";

import { getCrowdSnapshot } from "../api/client";
import type { CrowdSnapshotItem } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { hotQuestions, providerRows } from "../data/mock";

type ProviderMap = Record<string, { provider: string; status: string }>;

export function AdminPage() {
  const [providers, setProviders] = useState<ProviderMap | null>(null);
  const [crowdItems, setCrowdItems] = useState<CrowdSnapshotItem[]>([]);

  useEffect(() => {
    fetch("/api/provider/status")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(setProviders)
      .catch(() => setProviders(null));
    getCrowdSnapshot()
      .then((snapshot) => setCrowdItems(snapshot.items))
      .catch(() => setCrowdItems([]));
  }, []);

  const providerEntries = providers
    ? Object.entries(providers).map(([name, value]) => [name, value.provider, value.status])
    : providerRows;
  const highCrowdItems = crowdItems.filter((item) => item.crowd_level === "high");

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
          <MetricCard icon={<Users />} label="今日服务人次" trend="+12.4%" value="1,286" />
          <MetricCard icon={<Heart />} label="满意度" trend="近 7 日" value="4.72" />
          <MetricCard icon={<Gauge />} label="平均延迟" trend="mock" value="620ms" />
          <MetricCard icon={<HelpCircle />} label="低置信度问题" trend="需补知识" value="18" />
        </section>

        <section className="admin-content-grid">
          <article className="admin-panel admin-panel--wide">
            <div className="section-title-row">
              <div>
                <h2>满意度与服务量趋势</h2>
                <p>单位：人次 / 评分，时间范围：近 7 日</p>
              </div>
              <StatusBadge tone="neutral">演示数据</StatusBadge>
            </div>
            <div className="mock-chart" role="img" aria-label="近七日服务量上升，满意度保持在 4.6 分以上">
              {[42, 56, 48, 68, 74, 82, 88].map((value, index) => (
                <span key={index} style={{ height: `${value}%` }} />
              ))}
            </div>
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
                <h2>拥挤点预警</h2>
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
                <p className="empty-state">当前没有 high 拥挤点。模拟数据加载失败时会显示空状态。</p>
              )}
            </div>
          </article>

          <article className="admin-panel admin-panel--wide">
            <div className="section-title-row">
              <div>
                <h2>热门问题</h2>
                <p>用于发现讲解需求与知识缺口</p>
              </div>
            </div>
            <div className="question-list">
              {hotQuestions.map((item) => (
                <div className="question-row" key={item.text}>
                  <span>{item.text}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          </article>

          <article className="admin-panel">
            <h2>空状态预留</h2>
            <p className="empty-state">
              真实交互日志、知识切片和行为画像会在后续任务接入；当前页面使用 mock 数据保证无 API Key 可演示。
            </p>
          </article>
        </section>
      </section>
    </PageShell>
  );
}
