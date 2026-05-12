import { AlertTriangle, Check, Copy, Heart, MapPinned } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiClientError, getRouteShare, submitFeedback } from "../api/client";
import type { CrowdLevel, RouteRecommendation } from "../api/client";
import { Button } from "../components/Button";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import {
  BuddhaIcon,
  CrowdWaveIcon,
  QrHandoffIcon,
  RoutePathIcon,
  ScenicCameraIcon,
} from "../components/icons/LingshanIcons";

function formatExpiresAt(isoString: string | null | undefined): string {
  if (!isoString) {
    return "到期时间暂不可用";
  }
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) {
      return "到期时间暂不可用";
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  } catch {
    return "到期时间暂不可用";
  }
}

function crowdLabel(level: CrowdLevel) {
  return level === "high" ? "拥挤" : level === "medium" ? "适中" : "舒适";
}

function crowdTone(level: CrowdLevel) {
  return level === "high" ? "warning" : level === "medium" ? "neutral" : "ok";
}

const feedbackTags = ["路线合理", "避开拥挤", "人多拥挤", "讲解清楚", "体验惊喜", "还想了解"];

function errorMessage(code: string) {
  if (code === "CODE_MISSING") {
    return "链接缺少分享码，请回到 Kiosk 重新生成路线。";
  }
  if (code === "ROUTE_SHARE_CODE_INVALID") {
    return "分享码不正确，请确认链接完整，或在 Kiosk 重新生成路线。";
  }
  if (code === "ROUTE_SHARE_NOT_FOUND") {
    return "没有找到这条路线。mock 分享只在当前后端进程内有效，请重新生成。";
  }
  if (code === "ROUTE_SHARE_EXPIRED") {
    return "这条路线分享已过期，请在 Kiosk 重新生成。";
  }
  return "路线分享暂时无法打开，请稍后重试。";
}

export function RouteSharePage() {
  const routeId = useMemo(() => {
    const match = window.location.pathname.match(/^\/route\/([^/]+)\/share/);
    return match ? decodeURIComponent(match[1]) : "";
  }, []);
  const code = useMemo(() => new URLSearchParams(window.location.search).get("code") || "", []);
  const [route, setRoute] = useState<RouteRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState("");
  const [copiedStopId, setCopiedStopId] = useState("");
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackTagsSelected, setFeedbackTagsSelected] = useState<string[]>(["路线合理"]);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState("");
  const [feedbackError, setFeedbackError] = useState("");
  const [checkedIn, setCheckedIn] = useState(false);

  useEffect(() => {
    if (!code) {
      setErrorCode("CODE_MISSING");
      setLoading(false);
      return;
    }
    let mounted = true;
    setLoading(true);
    getRouteShare(routeId, code)
      .then((result) => {
        if (mounted) {
          setRoute(result);
          setErrorCode("");
        }
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setErrorCode(cause instanceof ApiClientError && cause.code ? cause.code : "UNKNOWN_ERROR");
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [code, routeId]);

  async function copyQuestion(stopId: string, question: string) {
    try {
      await navigator.clipboard.writeText(question);
      setCopiedStopId(stopId);
      window.setTimeout(() => setCopiedStopId(""), 1800);
    } catch {
      setCopiedStopId("");
    }
  }

  function toggleFeedbackTag(tag: string) {
    setFeedbackTagsSelected((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  async function sendFeedback() {
    if (!route) {
      return;
    }
    setFeedbackLoading(true);
    setFeedbackDone("");
    setFeedbackError("");
    try {
      const result = await submitFeedback({
        channel: "share",
        route_id: route.id,
        rating: feedbackRating,
        tags: feedbackTagsSelected,
        comment: feedbackComment || undefined,
      });
      setFeedbackDone(`反馈已记录：${result.id}`);
      setFeedbackComment("");
    } catch (cause) {
      setFeedbackError(cause instanceof Error ? cause.message : "反馈提交失败，请稍后重试。");
    } finally {
      setFeedbackLoading(false);
    }
  }

  if (loading) {
    return (
      <PageShell className="mobile-page route-share-page">
        <section className="share-loading" aria-live="polite">
          <RoutePathIcon />
          <h1>正在打开路线</h1>
          <p>正在校验短码并读取 Kiosk 生成的路线。</p>
        </section>
      </PageShell>
    );
  }

  if (!route) {
    return (
      <PageShell className="mobile-page route-share-page">
        <section className="share-error" role="alert">
          <AlertTriangle aria-hidden="true" size={30} />
          <span className="eyebrow">路线带走</span>
          <h1>分享链接不可用</h1>
          <p>{errorMessage(errorCode)}</p>
          <a className="share-link-button" href="/kiosk">
            回到 Kiosk 演示页
          </a>
        </section>
      </PageShell>
    );
  }

  const currentStop = route.stops[0];
  const nextStop = route.stops[1];

  return (
    <PageShell className="mobile-page route-share-page">
      <header className="share-header">
        <div>
          <span className="eyebrow">Kiosk 路线带走</span>
          <h1>{route.title}</h1>
          <p>{route.summary}</p>
        </div>
        <div className="share-ticket" aria-label="路线小票">
          <div className="share-ticket__main">
            <span>凭证码</span>
            <strong>{route.share.share_code}</strong>
            <small>生成后 30 分钟有效</small>
          </div>
          <div className="share-ticket__qr">
            <QrHandoffIcon />
            <span>扫码带走</span>
          </div>
        </div>
      </header>

      <section className="share-notice">
        <AlertTriangle aria-hidden="true" size={18} />
        <div>
          <p>{route.crowd_policy.caveat} 分享码 {route.share.share_code}，默认 30 分钟有效。</p>
          <p className="expires-at">到期时间：{formatExpiresAt(route.share.expires_at)}</p>
        </div>
      </section>

      <section className="share-journey-card" aria-label="当前路线进度">
        <div className="share-journey-card__score">
          <span>{route.theme_label}</span>
          <strong>{route.recommendation_score}</strong>
          <small>/100 舒适度评分</small>
        </div>
        <div className="share-progress-line" aria-label={`当前第 1 站，共 ${route.stops.length} 站`}>
          {route.stops.map((stop, index) => (
            <span className={index === 0 ? "share-progress-line__dot share-progress-line__dot--active" : "share-progress-line__dot"} key={stop.attraction_id} />
          ))}
        </div>
        {currentStop ? (
          <div className="share-current-stop">
            <span>当前站</span>
            <strong>{currentStop.name}</strong>
            <p>{currentStop.scenic_area} · 停留 {currentStop.stay_minutes} 分钟</p>
          </div>
        ) : null}
        {nextStop ? (
          <div className="share-current-stop share-current-stop--next">
            <span>下一站</span>
            <strong>{nextStop.name}</strong>
            <p>等待约 {nextStop.wait_minutes} 分钟 · {crowdLabel(nextStop.crowd_level)}</p>
          </div>
        ) : null}
        <div className="share-action-grid" aria-label="路线快捷操作">
          <button type="button" onClick={() => currentStop && void copyQuestion(currentStop.attraction_id, currentStop.narration_question)}>
            <BuddhaIcon />
            听本站讲解
          </button>
          <a href="/">
            <ScenicCameraIcon />
            拍照识景
          </a>
          <button type="button" onClick={() => void navigator.clipboard?.writeText("人太多，换一个")}>
            <CrowdWaveIcon />
            人太多换一个
          </button>
          <button className={checkedIn ? "share-action-grid__done" : ""} type="button" onClick={() => setCheckedIn((value) => !value)}>
            <Check aria-hidden="true" size={19} />
            {checkedIn ? "已打卡" : "完成打卡"}
          </button>
        </div>
      </section>

      <section className="decision-trace" aria-label="路线决策摘要">
        <strong>为什么这样走</strong>
        <ul>
          {route.decision_trace.slice(0, 4).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="share-timeline" aria-label="手机路线时间线">
        {route.stops.map((stop) => (
          <article className="share-stop" key={stop.attraction_id}>
            <div className="route-stop__index">{stop.order}</div>
            <div className="share-stop__body">
              <div className="share-stop__top">
                <div>
                  <h2>{stop.name}</h2>
                  <p>
                    {stop.scenic_area} · 停留 {stop.stay_minutes} 分钟
                    {stop.walk_minutes_from_previous ? ` · 步行约 ${stop.walk_minutes_from_previous} 分钟` : ""}
                  </p>
                </div>
                <StatusBadge tone={crowdTone(stop.crowd_level)}>
                  {crowdLabel(stop.crowd_level)} {stop.crowd_score}
                </StatusBadge>
              </div>
              <p>{stop.focus}：{stop.reason}</p>
              <div className="share-crowd-row">
                <MapPinned aria-hidden="true" size={16} />
                <span>等待约 {stop.wait_minutes} 分钟。{stop.crowd_note}</span>
              </div>
              <Button
                icon={copiedStopId === stop.attraction_id ? <Check size={17} /> : <Copy size={17} />}
                onClick={() => void copyQuestion(stop.attraction_id, stop.narration_question)}
                type="button"
                variant="secondary"
              >
                {copiedStopId === stop.attraction_id ? "已复制" : "复制本站讲解问题"}
              </Button>
            </div>
          </article>
        ))}
      </section>

      <section className="feedback-panel share-feedback" aria-label="路线反馈">
        <div className="section-title-row">
          <div>
            <h2>这条路线有帮助吗？</h2>
            <p>反馈只写入本地演示日志。</p>
          </div>
          <Heart aria-hidden="true" />
        </div>
        <div className="rating-row" role="group" aria-label="路线满意度评分">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              className={feedbackRating === value ? "rating-button rating-button--active" : "rating-button"}
              key={value}
              onClick={() => setFeedbackRating(value)}
              type="button"
            >
              {value} 分
            </button>
          ))}
        </div>
        <div className="feedback-tag-grid" aria-label="路线反馈标签">
          {feedbackTags.map((tag) => (
            <button
              className={feedbackTagsSelected.includes(tag) ? "feedback-tag feedback-tag--active" : "feedback-tag"}
              key={tag}
              onClick={() => toggleFeedbackTag(tag)}
              type="button"
            >
              {tag}
            </button>
          ))}
        </div>
        <textarea
          className="text-area"
          onChange={(event) => setFeedbackComment(event.target.value)}
          placeholder="可选：告诉我们哪里有帮助，哪里需要调整。"
          rows={3}
          value={feedbackComment}
        />
        <Button icon={<Heart size={18} />} loading={feedbackLoading} onClick={() => void sendFeedback()} type="button" variant="secondary">
          提交路线反馈
        </Button>
        {feedbackError ? <p className="inline-alert">{feedbackError}</p> : null}
        {feedbackDone ? <p className="success-note">{feedbackDone}</p> : null}
      </section>
    </PageShell>
  );
}
