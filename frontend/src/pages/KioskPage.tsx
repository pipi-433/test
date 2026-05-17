import { AlertTriangle, Camera, MapPinned, Mic, QrCode, Route, Sparkles, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import { getAvatarStatus, getCrowdSnapshot, getOperationEvents, playAvatarClip, recommendRoute, speakAvatarText } from "../api/client";
import type { AvatarClipId, AvatarStatusResponse, CrowdSnapshotItem, OperationEvent, RouteRecommendation } from "../api/client";
import { Button } from "../components/Button";
import type { DigitalHumanState } from "../components/DigitalHumanMock";
import { IconButton } from "../components/IconButton";
import { PageShell } from "../components/Shell";
import { RouteStep } from "../components/RouteStep";
import { StatusBadge } from "../components/StatusBadge";
import { AvatarLivePanel } from "../components/visitor/AvatarLivePanel";
import { quickQuestions, routeSteps } from "../data/mock";

const kioskAvatarClips: Array<{ clipId: AvatarClipId; label: string }> = [
  { clipId: "lingshan_buddha_intro_45s", label: "灵山大佛" },
  { clipId: "fan_gong_intro_45s", label: "灵山梵宫" },
  { clipId: "jiulong_guanyu_intro_30s", label: "九龙灌浴" },
];

const kioskAvatarClipLockMs: Record<AvatarClipId, number> = {
  fan_gong_intro_45s: 10_000,
  jiulong_guanyu_intro_30s: 10_000,
  lingshan_buddha_intro_45s: 8_000,
};

function kioskRouteSpeakSummary(route: RouteRecommendation) {
  const firstStop = route.stops[0]?.name ? `首站是${route.stops[0].name}。` : "";
  const crowdStop = route.stops.find((stop) => stop.crowd_level === "high");
  const crowdText = crowdStop ? `${crowdStop.name}为模拟高拥挤点，建议按页面提示错峰。` : "路线节奏较舒缓。";
  return `您好，我是灵境导游。${route.title}已生成，共${route.stops.length}站，预计${route.estimated_duration_minutes}分钟。${firstStop}${crowdText}请扫码带走或在终端查看路线摘要。`;
}

export function KioskPage() {
  const [crowdItems, setCrowdItems] = useState<CrowdSnapshotItem[]>([]);
  const [operationEvents, setOperationEvents] = useState<OperationEvent[]>([]);
  const [routeResult, setRouteResult] = useState<RouteRecommendation | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState("");
  const [avatarActionLoading, setAvatarActionLoading] = useState<"route" | AvatarClipId | null>(null);
  const [avatarActionMessage, setAvatarActionMessage] = useState("");
  const [avatarStatus, setAvatarStatus] = useState<AvatarStatusResponse | null>(null);
  const [avatarPlaybackLockedUntil, setAvatarPlaybackLockedUntil] = useState(0);
  const [avatarPlaybackTick, setAvatarPlaybackTick] = useState(0);

  useEffect(() => {
    if (!avatarPlaybackLockedUntil) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setAvatarPlaybackTick(Date.now());
      if (Date.now() >= avatarPlaybackLockedUntil) {
        setAvatarPlaybackLockedUntil(0);
        setAvatarActionLoading(null);
      }
    }, 500);
    return () => window.clearInterval(timer);
  }, [avatarPlaybackLockedUntil]);

  useEffect(() => {
    getCrowdSnapshot()
      .then((snapshot) => setCrowdItems(snapshot.items.filter((item) => item.crowd_level === "high")))
      .catch(() => setCrowdItems([]));
    getOperationEvents()
      .then((payload) => setOperationEvents(payload.items.slice(0, 4)))
      .catch(() => setOperationEvents([]));
    getAvatarStatus()
      .then((status) => setAvatarStatus(status))
      .catch(() =>
        setAvatarStatus({
          mode: "mock",
          sidecar_ready: false,
          sidecar_url: "",
          active_session_id: null,
          fallback_available: true,
          message: "avatar status unavailable",
        }),
      );
  }, []);

  const shareUrl = routeResult ? `${window.location.origin}${routeResult.share.share_url}` : "";
  const avatarPlaybackRemainingMs = Math.max(0, avatarPlaybackLockedUntil - Math.max(Date.now(), avatarPlaybackTick));
  const avatarPlaybackLocked = avatarPlaybackRemainingMs > 0;
  const avatarPlaybackRemainingSeconds = Math.ceil(avatarPlaybackRemainingMs / 1000);
  const kioskHumanState: DigitalHumanState = avatarActionLoading || avatarPlaybackLocked ? "speaking" : routeLoading ? "thinking" : routeError ? "error" : routeResult ? "happy" : "welcome";
  const kioskHumanCaption = routeLoading
    ? "正在根据亲子轻松偏好和模拟拥挤度生成路线。"
    : avatarActionLoading || avatarPlaybackLocked
      ? "数字人正在讲解，请稍候再发送新的播报。"
    : routeError
      ? "路线生成遇到问题，终端仍可展示热门问题和重新尝试。"
      : routeResult
        ? `已生成${routeResult.title}，扫码可在手机继续查看。`
        : "欢迎来到灵境导游终端，生成路线后可以扫码带走。";

  function lockAvatarPlayback(kind: "route" | AvatarClipId, durationMs: number) {
    setAvatarActionLoading(kind);
    setAvatarPlaybackLockedUntil(Date.now() + durationMs);
    setAvatarPlaybackTick(Date.now());
  }

  function unlockAvatarPlaybackSoon(delayMs = 900) {
    window.setTimeout(() => {
      setAvatarPlaybackLockedUntil(0);
      setAvatarActionLoading(null);
      setAvatarPlaybackTick(Date.now());
    }, delayMs);
  }

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
        channel: "kiosk",
      });
      setRouteResult(result);
      setAvatarActionMessage("");
    } catch (cause) {
      setRouteError(cause instanceof Error ? cause.message : "路线生成失败，请稍后重试。");
    } finally {
      setRouteLoading(false);
    }
  }

  async function speakKioskRoute() {
    if (!routeResult) {
      setAvatarActionMessage("请先生成推荐路线，再发送给数字人播报。");
      return;
    }
    if (avatarPlaybackLocked) {
      setAvatarActionMessage(`数字人正在讲解，请 ${avatarPlaybackRemainingSeconds} 秒后再试。`);
      return;
    }
    lockAvatarPlayback("route", 5_000);
    setAvatarActionMessage("");
    try {
      const result = await speakAvatarText({
        text: kioskRouteSpeakSummary(routeResult),
        emotion: "happy",
        source: "route",
        interrupt: true,
      });
      setAvatarActionMessage(result.accepted ? "已发送给数字人播报。" : "已切换为文本播报/稍后重试。");
      if (!result.accepted) {
        unlockAvatarPlaybackSoon();
      }
    } catch {
      setAvatarActionMessage("已切换为文本播报/稍后重试。");
      unlockAvatarPlaybackSoon();
    }
  }

  async function playKioskClip(clipId: AvatarClipId, label: string) {
    if (avatarPlaybackLocked) {
      setAvatarActionMessage(`数字人正在讲解，请 ${avatarPlaybackRemainingSeconds} 秒后再试。`);
      return;
    }
    lockAvatarPlayback(clipId, kioskAvatarClipLockMs[clipId] || 10_000);
    setAvatarActionMessage("");
    try {
      const result = await playAvatarClip({
        clip_id: clipId,
        source: "attraction",
        interrupt: true,
      });
      setAvatarActionMessage(result.accepted ? `已发送${label}数字人讲解。` : "已切换为文本播报/稍后重试。");
      if (!result.accepted) {
        unlockAvatarPlaybackSoon();
      }
    } catch {
      setAvatarActionMessage("已切换为文本播报/稍后重试。");
      unlockAvatarPlaybackSoon();
    }
  }

  function stopKioskAvatarBroadcast() {
    setAvatarPlaybackLockedUntil(0);
    setAvatarActionLoading(null);
    setAvatarPlaybackTick(Date.now());
    setAvatarActionMessage("已停止页面播报状态。");
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
          <AvatarLivePanel
            broadcastDisabled={avatarActionLoading !== null || (!routeResult && avatarPlaybackLocked)}
            broadcasting={avatarPlaybackLocked || avatarActionLoading !== null}
            caption={kioskHumanCaption}
            onStartBroadcast={() => (routeResult ? void speakKioskRoute() : void playKioskClip("lingshan_buddha_intro_45s", "灵山大佛"))}
            onStopBroadcast={stopKioskAvatarBroadcast}
            sidecarUrl={avatarStatus?.sidecar_url || undefined}
            state={kioskHumanState}
            status={avatarStatus}
            title="灵境数字人"
            variant="kiosk"
          />
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

          <section className="kiosk-section kiosk-avatar-actions" aria-label="数字人讲解">
            <div className="section-title-row">
              <h2>数字人讲解</h2>
              <Volume2 aria-hidden="true" />
            </div>
            <div className="kiosk-clip-grid">
              {kioskAvatarClips.map((clip) => (
                <button
                  className="kiosk-avatar-button"
                  disabled={avatarPlaybackLocked || avatarActionLoading !== null}
                  key={clip.clipId}
                  onClick={() => void playKioskClip(clip.clipId, clip.label)}
                  type="button"
                >
                  <Volume2 aria-hidden="true" size={24} />
                  {avatarActionLoading === clip.clipId ? `讲解中 ${avatarPlaybackRemainingSeconds}s` : `${clip.label}讲解`}
                </button>
              ))}
            </div>
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
              当前为模拟拥挤度/运营事件演示数据，不代表真实硬件客流。
            </p>
            {operationEvents.length ? (
              <div className="kiosk-operation-list" aria-label="当前运营提醒">
                {operationEvents.map((event) => (
                  <div className="kiosk-operation-row" key={event.id}>
                    <strong>{event.attraction_name || event.attraction_id}</strong>
                    <span>{event.message} · source={event.source}</span>
                  </div>
                ))}
              </div>
            ) : null}
            {routeResult?.operation_policy?.active_event_count ? (
              <p className="kiosk-operation-applied">
                路线已考虑 {routeResult.operation_policy.active_event_count} 条运营事件，扫码后手机端可查看逐站影响说明。
              </p>
            ) : null}
            {crowdItems.slice(0, 2).map((item) => (
              <div className="kiosk-crowd-row" key={item.attraction_id}>
                <strong>{item.name}</strong>
                <span>拥挤 {item.crowd_score} · 等待约 {item.wait_minutes} 分钟，建议错峰或先游览低拥挤点。</span>
              </div>
            ))}
            {routeError ? <p className="inline-alert">{routeError}</p> : null}
            <button
              className="kiosk-avatar-button kiosk-avatar-button--route"
              disabled={avatarPlaybackLocked || avatarActionLoading !== null || !routeResult}
              onClick={() => void speakKioskRoute()}
              type="button"
            >
              <Volume2 aria-hidden="true" size={26} />
              {avatarActionLoading === "route" ? `讲解中 ${avatarPlaybackRemainingSeconds}s` : "播报推荐路线"}
            </button>
            {avatarActionMessage ? <p className="kiosk-avatar-status">{avatarActionMessage}</p> : null}
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
