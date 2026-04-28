import { type ChangeEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Clock3,
  Camera,
  ExternalLink,
  FileImage,
  Layers,
  Map,
  MessageSquareText,
  Mic,
  Navigation,
  Route as RouteIcon,
  Send,
  ShieldCheck,
} from "lucide-react";

import { askQuestion, fetchAttractions, recognizeImage, recommendRoute } from "../api/client";
import type { Attraction, CrowdLevel, QAResponse, RouteRecommendation, VisionResponse } from "../api/client";
import { Button } from "../components/Button";
import { DigitalHumanMock, type DigitalHumanState } from "../components/DigitalHumanMock";
import { IconButton } from "../components/IconButton";
import { PageShell } from "../components/Shell";
import { SpotCard } from "../components/SpotCard";
import { StatusBadge } from "../components/StatusBadge";

const starterQuestions = ["灵山大佛适合怎么游览？", "九龙灌浴有什么看点？", "梵宫背后有什么文化故事？"];
const routeThemes = [
  { id: "family", label: "亲子" },
  { id: "history", label: "历史" },
  { id: "nature", label: "自然" },
  { id: "blessing", label: "祈福" },
  { id: "photo", label: "拍照" },
];
const routeBudgets = [
  { value: 120, label: "2 小时" },
  { value: 240, label: "4 小时" },
  { value: 360, label: "6 小时" },
  { value: 480, label: "全天" },
];
const crowdToleranceOptions: Array<{ value: CrowdLevel; label: string }> = [
  { value: "low", label: "舒适优先" },
  { value: "medium", label: "普通" },
  { value: "high", label: "可接受排队" },
];

function shortText(value: string | undefined, limit = 88) {
  if (!value) {
    return "本地资料暂未提供详细简介，可先向灵境提问获取讲解。";
  }
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

function crowdLabel(level: CrowdLevel) {
  return level === "high" ? "拥挤" : level === "medium" ? "适中" : "舒适";
}

function crowdTone(level: CrowdLevel) {
  return level === "high" ? "warning" : level === "medium" ? "neutral" : "ok";
}

export function MobileHomePage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const routePanelRef = useRef<HTMLElement | null>(null);
  const [attractions, setAttractions] = useState<Attraction[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [question, setQuestion] = useState("灵山大佛适合怎么游览？");
  const [qaResult, setQaResult] = useState<QAResponse | null>(null);
  const [visionResult, setVisionResult] = useState<VisionResponse | null>(null);
  const [routeTheme, setRouteTheme] = useState("family");
  const [routeBudget, setRouteBudget] = useState(240);
  const [avoidCrowd, setAvoidCrowd] = useState(true);
  const [crowdTolerance, setCrowdTolerance] = useState<CrowdLevel>("medium");
  const [routeResult, setRouteResult] = useState<RouteRecommendation | null>(null);
  const [loadingAttractions, setLoadingAttractions] = useState(true);
  const [qaLoading, setQaLoading] = useState(false);
  const [visionLoading, setVisionLoading] = useState(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    fetchAttractions()
      .then((items) => {
        if (!mounted) {
          return;
        }
        setAttractions(items);
        setSelectedId(items.find((item) => item.id === "lingshan-ls-011")?.id || items[0]?.id || "");
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(cause instanceof Error ? cause.message : "景点数据加载失败，请确认后端已启动。");
        }
      })
      .finally(() => {
        if (mounted) {
          setLoadingAttractions(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const selectedAttraction = useMemo(
    () => attractions.find((item) => item.id === selectedId) || null,
    [attractions, selectedId],
  );

  const humanState: DigitalHumanState = qaLoading || visionLoading || routeLoading ? "thinking" : qaResult ? "speaking" : "welcome";

  async function submitQuestion(nextQuestion = question) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion) {
      setError("请先输入一个问题。");
      return;
    }
    setQaLoading(true);
    setError("");
    setQuestion(cleanQuestion);
    try {
      const result = await askQuestion({ attractionId: selectedId, question: cleanQuestion });
      setQaResult(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "问答请求失败，请稍后重试。");
    } finally {
      setQaLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion();
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setVisionLoading(true);
    setError("");
    try {
      const result = await recognizeImage({
        file,
        hint: selectedAttraction?.name,
        textHint: question,
      });
      setVisionResult(result);
      if (result.matched_attraction) {
        setSelectedId(result.matched_attraction.id);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "识景请求失败，请稍后重试。");
    } finally {
      setVisionLoading(false);
    }
  }

  async function generateRoute(nextTheme = routeTheme) {
    setRouteLoading(true);
    setError("");
    setRouteTheme(nextTheme);
    try {
      const result = await recommendRoute({
        theme: nextTheme,
        timeBudgetMinutes: routeBudget,
        groupType: nextTheme === "family" ? "family" : "friends",
        intensity: routeBudget <= 120 ? "easy" : "balanced",
        interests: selectedAttraction?.tags?.slice(0, 3) || [nextTheme],
        startAttractionId: selectedId,
        avoidCrowd,
        crowdTolerance,
      });
      setRouteResult(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "路线推荐失败，请稍后重试。");
    } finally {
      setRouteLoading(false);
    }
  }

  function focusRoutePanel() {
    routePanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (!routeResult) {
      void generateRoute();
    }
  }

  return (
    <PageShell className="mobile-page">
      <header className="mobile-header">
        <div>
          <span className="eyebrow">灵山胜境 / 拈花湾</span>
          <h1>灵境导游</h1>
        </div>
        <StatusBadge tone={error ? "warning" : "ok"}>{error ? "需要处理" : "mock 在线"}</StatusBadge>
      </header>

      <DigitalHumanMock state={humanState} className="mobile-avatar" />

      <section className="mobile-greeting" aria-labelledby="mobile-greeting-title">
        <span className="eyebrow">当前讲解</span>
        <h2 id="mobile-greeting-title">
          你好，我是灵境。选择景点后可以直接提问，也可以上传样例图片完成 mock 识景。
        </h2>
      </section>

      <section className="mobile-control-panel" aria-label="景点与提问">
        <label className="field-label" htmlFor="attraction-select">
          景点选择
        </label>
        <select
          className="select-input"
          disabled={loadingAttractions || attractions.length === 0}
          id="attraction-select"
          onChange={(event) => setSelectedId(event.target.value)}
          value={selectedId}
        >
          {attractions.map((item) => (
            <option key={item.id} value={item.id}>
              {item.scenic_area} · {item.name}
            </option>
          ))}
        </select>

        <div className="quick-question-row" aria-label="快捷问题">
          {starterQuestions.map((item) => (
            <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
              {item}
            </button>
          ))}
        </div>
      </section>

      {selectedAttraction ? (
        <SpotCard
          description={shortText(selectedAttraction.summary || selectedAttraction.description)}
          meta={`${selectedAttraction.category || "景点"} · ${
            (selectedAttraction.tags || []).slice(0, 2).join(" / ") || "本地知识库"
          }`}
          title={selectedAttraction.name}
        />
      ) : (
        <p className="empty-state mobile-empty">正在等待景点数据，确认后端启动后会自动加载。</p>
      )}

      {error ? (
        <p className="inline-alert" role="alert">
          {error}
        </p>
      ) : null}

      <section className="mobile-chat" aria-label="问答讲解">
        <div className="chat-row chat-row--visitor">
          <strong>游客</strong>
          <p>{question || "还没有输入问题"}</p>
        </div>
        <div className="chat-row chat-row--guide">
          <strong>灵境</strong>
          {qaLoading ? (
            <p>正在检索本地知识库...</p>
          ) : qaResult ? (
            <p>{qaResult.answer}</p>
          ) : (
            <p>你可以问景点看点、文化故事或适合怎么游览，回答会带上本地资料来源。</p>
          )}
        </div>
      </section>

      {qaResult ? (
        <section className="source-panel" aria-label="回答来源">
          <div className="section-title-row">
            <h2>来源依据</h2>
            <StatusBadge tone="neutral">{qaResult.latency_ms} ms</StatusBadge>
          </div>
          {qaResult.sources.length > 0 ? (
            <div className="source-list">
              {qaResult.sources.map((source) => (
                <div className="source-item" key={source.chunk_id}>
                  <strong>{source.title}</strong>
                  <span>{source.source_file}</span>
                  <span>分数 {source.score.toFixed(2)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state mobile-empty">本次没有可靠命中，灵境已避免编造答案。</p>
          )}
        </section>
      ) : null}

      <section className="vision-panel" aria-label="图片识景">
        <div className="section-title-row">
          <div>
            <h2>拍照识景</h2>
            <p>上传样例图，mock 识景会根据文件名和提示词匹配景点。</p>
          </div>
          <Button
            icon={<FileImage size={18} />}
            loading={visionLoading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
            variant="secondary"
          >
            上传
          </Button>
        </div>
        <input
          accept="image/*,.jpg,.jpeg,.png"
          className="sr-only"
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />
        {visionResult ? (
          <div className="vision-result">
            <div className="vision-result__top">
              <StatusBadge tone={visionResult.matched_attraction ? "ok" : "warning"}>
                {visionResult.matched_attraction ? `置信度 ${Math.round(visionResult.confidence * 100)}%` : "未命中"}
              </StatusBadge>
              <span>
                {visionResult.latency_ms} ms · {visionResult.mode}
              </span>
            </div>
            <p>{visionResult.explanation}</p>
            {visionResult.matched_attraction ? (
              <strong>
                {visionResult.matched_attraction.scenic_area} · {visionResult.matched_attraction.name}
              </strong>
            ) : null}
            <div className="suggested-question-list" aria-label="识景建议问题">
              {visionResult.suggested_questions.map((item) => (
                <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="empty-state mobile-empty">还没有上传图片。可用 evals/vision_samples 下的样例文件演示。</p>
        )}
      </section>

      <section className="route-panel" aria-label="路线推荐" ref={routePanelRef}>
        <div className="section-title-row">
          <div>
            <h2>路线推荐</h2>
            <p>根据兴趣、时长、当前景点和模拟拥挤度生成可解释路线。</p>
          </div>
          <Button
            icon={<RouteIcon size={18} />}
            loading={routeLoading}
            onClick={() => void generateRoute()}
            type="button"
            variant="secondary"
          >
            生成
          </Button>
        </div>
        <div className="route-preferences" aria-label="路线偏好">
          <div className="route-theme-grid" role="group" aria-label="路线主题">
            {routeThemes.map((theme) => (
              <button
                className={`route-theme ${routeTheme === theme.id ? "route-theme--active" : ""}`}
                key={theme.id}
                onClick={() => void generateRoute(theme.id)}
                type="button"
              >
                {theme.label}
              </button>
            ))}
          </div>
          <label className="field-label" htmlFor="route-budget">
            游玩时长
          </label>
          <select
            className="select-input"
            id="route-budget"
            onChange={(event) => setRouteBudget(Number(event.target.value))}
            value={routeBudget}
          >
            {routeBudgets.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <label className="crowd-switch">
            <input checked={avoidCrowd} onChange={(event) => setAvoidCrowd(event.target.checked)} type="checkbox" />
            <span>
              <ShieldCheck aria-hidden="true" size={18} />
              避开拥挤
            </span>
          </label>
          <label className="field-label" htmlFor="crowd-tolerance">
            拥挤容忍度
          </label>
          <select
            className="select-input"
            id="crowd-tolerance"
            onChange={(event) => setCrowdTolerance(event.target.value as CrowdLevel)}
            value={crowdTolerance}
          >
            {crowdToleranceOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        {routeResult ? (
          <div className="route-result">
            <div className="route-summary">
              <div className="route-score-row">
                <StatusBadge tone="ok">{routeResult.theme_label}</StatusBadge>
                <strong>{routeResult.recommendation_score} 分</strong>
              </div>
              <h3>{routeResult.title}</h3>
              <p>{routeResult.summary}</p>
              <span>
                <Clock3 aria-hidden="true" size={16} />
                约 {routeResult.estimated_duration_minutes} 分钟 · 分享码 {routeResult.share.share_code}
              </span>
              <a className="route-share-link" href={routeResult.share.share_url}>
                <ExternalLink aria-hidden="true" size={16} />
                打开手机路线带走页
              </a>
              <div className="score-grid" aria-label="路线评分拆解">
                {Object.entries(routeResult.score_breakdown).map(([key, value]) => (
                  <span key={key}>
                    {key === "theme_match"
                      ? "主题"
                      : key === "time_fit"
                        ? "时长"
                        : key === "group_fit"
                          ? "同行"
                          : key === "crowd_comfort"
                            ? "舒适"
                            : "质量"}
                    <strong>{value}</strong>
                  </span>
                ))}
              </div>
              <p className="simulation-note">
                <AlertTriangle aria-hidden="true" size={16} />
                {routeResult.crowd_policy.caveat}
              </p>
            </div>
            <div className="decision-trace" aria-label="路线决策说明">
              <strong>决策说明</strong>
              <ul>
                {routeResult.decision_trace.slice(0, 4).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="route-stop-list" aria-label="逐站路线">
              {routeResult.stops.map((stop) => (
                <article className="route-stop" key={`${routeResult.id}-${stop.attraction_id}`}>
                  <div className="route-stop__index">{stop.order}</div>
                  <div>
                    <strong>{stop.name}</strong>
                    <span>
                      {stop.scenic_area} · 停留 {stop.stay_minutes} 分钟
                      {stop.walk_minutes_from_previous ? ` · 步行约 ${stop.walk_minutes_from_previous} 分钟` : ""}
                    </span>
                    <div className="crowd-inline">
                      <StatusBadge tone={crowdTone(stop.crowd_level)}>
                        {crowdLabel(stop.crowd_level)} · {stop.crowd_score}
                      </StatusBadge>
                      <span>等待约 {stop.wait_minutes} 分钟</span>
                    </div>
                    <p>{stop.focus}：{stop.reason}</p>
                    <p className="crowd-note">{stop.crowd_note}</p>
                    <button className="quick-question" type="button" onClick={() => void submitQuestion(stop.narration_question)}>
                      进入本站讲解
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        ) : (
          <p className="empty-state mobile-empty">还没有生成路线。选择主题和时长后，灵境会给出逐站讲解顺序。</p>
        )}
      </section>

      <form className="mobile-input" aria-label="文本提问" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="mobile-question">
          输入问题
        </label>
        <input
          className="text-input"
          id="mobile-question"
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="问灵境，例如：梵宫怎么游览？"
          type="text"
          value={question}
        />
        <Button type="submit" aria-label="发送问题" icon={<Send size={18} />} loading={qaLoading} variant="primary">
          发送
        </Button>
      </form>

      <nav className="mobile-actions" aria-label="游客主操作">
        <IconButton disabled icon={Mic} label="语音" />
        <IconButton icon={MessageSquareText} label="文本" onClick={() => document.getElementById("mobile-question")?.focus()} />
        <IconButton icon={Camera} label="拍照" onClick={() => fileInputRef.current?.click()} />
        <IconButton icon={Map} label="路线" onClick={focusRoutePanel} />
      </nav>

      <a className="route-link" href="/kiosk">
        <Navigation aria-hidden="true" size={18} />
        查看景区终端演示
      </a>

      <div className="mobile-mode-note">
        <Layers aria-hidden="true" size={16} />
        当前为 mock 模式：前端只调用后端 API，不接触模型厂商 Key。
      </div>
    </PageShell>
  );
}
