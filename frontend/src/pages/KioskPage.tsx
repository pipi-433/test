import { AlertTriangle, Camera, MapPinned, Mic, QrCode, Route, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import { getCrowdSnapshot, recommendRoute } from "../api/client";
import type { CrowdSnapshotItem, RouteRecommendation } from "../api/client";
import { Button } from "../components/Button";
import { DigitalHumanMock } from "../components/DigitalHumanMock";
import { IconButton } from "../components/IconButton";
import { PageShell } from "../components/Shell";
import { RouteStep } from "../components/RouteStep";
import { StatusBadge } from "../components/StatusBadge";
import { quickQuestions, routeSteps } from "../data/mock";

export function KioskPage() {
  const [crowdItems, setCrowdItems] = useState<CrowdSnapshotItem[]>([]);
  const [routeResult, setRouteResult] = useState<RouteRecommendation | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState("");

  useEffect(() => {
    getCrowdSnapshot()
      .then((snapshot) => setCrowdItems(snapshot.items.filter((item) => item.crowd_level === "high")))
      .catch(() => setCrowdItems([]));
  }, []);

  const shareUrl = routeResult ? `${window.location.origin}${routeResult.share.share_url}` : "";

  async function generateKioskRoute() {
    setRouteLoading(true);
    setRouteError("");
    try {
      const result = await recommendRoute({
        theme: "family",
        timeBudgetMinutes: 240,
        groupType: "family",
        intensity: "easy",
        interests: ["亲子轻松", "佛教文化"],
        startAttractionId: "lingshan-ls-011",
        avoidCrowd: true,
        crowdTolerance: "medium",
      });
      setRouteResult(result);
    } catch (cause) {
      setRouteError(cause instanceof Error ? cause.message : "路线生成失败，请稍后重试。");
    } finally {
      setRouteLoading(false);
    }
  }

  return (
    <PageShell className="kiosk-page">
      <header className="kiosk-header">
        <div>
          <span className="eyebrow">游客中心触控终端</span>
          <h1>灵境导游欢迎你</h1>
        </div>
        <StatusBadge tone="ok">匿名会话 · 闲时自动清空</StatusBadge>
      </header>

      <section className="kiosk-grid">
        <div className="kiosk-avatar-panel">
          <DigitalHumanMock state="welcome" className="kiosk-avatar" />
          <div className="kiosk-primary-actions" aria-label="终端主要操作">
            <Button size="kiosk" icon={<Mic size={26} />}>
              开始语音咨询
            </Button>
            <Button
              size="kiosk"
              variant="accent"
              icon={<Route size={26} />}
              loading={routeLoading}
              onClick={() => void generateKioskRoute()}
              type="button"
            >
              生成推荐路线
            </Button>
          </div>
        </div>

        <aside className="kiosk-side" aria-label="快捷咨询">
          <section className="kiosk-section">
            <div className="section-title-row">
              <h2>热门问题</h2>
              <Sparkles aria-hidden="true" />
            </div>
            <div className="question-grid">
              {quickQuestions.map((question) => (
                <button className="question-button" key={question} type="button">
                  {question}
                </button>
              ))}
            </div>
          </section>

          <section className="kiosk-section kiosk-tools">
            <IconButton icon={Camera} label="拍照识景" size="kiosk" />
            <IconButton icon={MapPinned} label="路线推荐" size="kiosk" />
            <IconButton icon={Mic} label="语音讲解" size="kiosk" />
          </section>

          <section className="kiosk-section kiosk-route" aria-label="推荐路线摘要">
            <div className="section-title-row">
              <h2>{routeResult?.title || "亲子轻松路线"}</h2>
              <StatusBadge tone={routeResult ? "ok" : "warning"}>
                {routeResult ? `${routeResult.recommendation_score} 分` : "mock 推荐"}
              </StatusBadge>
            </div>
            <p className="kiosk-crowd-note">
              <AlertTriangle aria-hidden="true" size={20} />
              当前为模拟拥挤度/演示数据，不代表真实客流。
            </p>
            {crowdItems.slice(0, 2).map((item) => (
              <div className="kiosk-crowd-row" key={item.attraction_id}>
                <strong>{item.name}</strong>
                <span>拥挤 {item.crowd_score} · 等待约 {item.wait_minutes} 分钟，建议错峰或先游览低拥挤点。</span>
              </div>
            ))}
            {routeError ? <p className="inline-alert">{routeError}</p> : null}
            {routeResult
              ? routeResult.stops.slice(0, 3).map((stop) => (
                  <RouteStep
                    description={`${stop.focus} · ${stop.crowd_note}`}
                    index={stop.order}
                    key={stop.attraction_id}
                    time={`停留 ${stop.stay_minutes} 分钟`}
                    title={stop.name}
                  />
                ))
              : routeSteps.map((step, index) => (
                  <RouteStep
                    description={step.description}
                    index={index + 1}
                    key={step.title}
                    time={step.time}
                    title={step.title}
                  />
                ))}
          </section>

          <section className="kiosk-qr" aria-label="扫码带走路线">
            <div className="qr-placeholder" aria-label={routeResult ? "路线分享二维码" : "路线二维码占位"}>
              {routeResult ? <QRCodeSVG value={shareUrl} size={132} level="M" includeMargin /> : <QrCode aria-hidden="true" size={84} />}
            </div>
            <div>
              <h2>扫码带走路线</h2>
              {routeResult ? (
                <div className="kiosk-share-details">
                  <strong>短码 {routeResult.share.share_code}</strong>
                  <a href={routeResult.share.share_url}>{shareUrl}</a>
                  <p>扫码后在手机继续查看路线，分享码 30 分钟后失效。</p>
                </div>
              ) : (
                <p>点击“生成推荐路线”后展示二维码、短码和手机打开链接；终端不会保留上一位游客的私人状态。</p>
              )}
            </div>
          </section>
        </aside>
      </section>
    </PageShell>
  );
}
