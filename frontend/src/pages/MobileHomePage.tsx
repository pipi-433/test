import { type ChangeEvent, type FormEvent, type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Clock3,
  Camera,
  ExternalLink,
  FileImage,
  Heart,
  Layers,
  Map,
  Mic,
  Navigation,
  Route as RouteIcon,
  Send,
  ShieldCheck,
  Volume2,
  VolumeX,
} from "lucide-react";

import { askQuestion, fetchAttractions, recognizeImage, recommendRoute, sendRouteConversation, submitFeedback } from "../api/client";
import type { Attraction, CrowdLevel, QAResponse, RouteConversationResponse, RouteRecommendation, VisionResponse } from "../api/client";
import { Button } from "../components/Button";
import { DigitalHumanMock, type DigitalHumanState } from "../components/DigitalHumanMock";
import { IconButton } from "../components/IconButton";
import { PageShell } from "../components/Shell";
import { SpotCard } from "../components/SpotCard";
import { StatusBadge } from "../components/StatusBadge";
import { useDigitalHumanState } from "../hooks/useDigitalHumanState";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";

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
const feedbackTags = ["讲解清楚", "路线合理", "避开拥挤", "人多拥挤", "信息不准", "体验惊喜"];
const routeIntentKeywords = [
  "路线",
  "怎么玩",
  "安排",
  "几小时",
  "小时",
  "半天",
  "全天",
  "老人",
  "孩子",
  "太累",
  "人多",
  "必去",
  "一定要去",
  "必须看",
  "必须去",
  "不能错过",
  "不想去",
  "不去",
  "跳过",
  "取消",
  "缩短",
  "换一个",
  "少走",
  "讲给孩子听",
  "30 秒",
  "三十秒",
  "讲深入",
];
const mustVisitOptions = [
  { id: "lingshan-ls-011", label: "灵山大佛" },
  { id: "lingshan-ls-006", label: "九龙灌浴" },
  { id: "lingshan-ls-013", label: "灵山梵宫" },
  { id: "lingshan-ls-010", label: "祥符禅寺" },
  { id: "lingshan-ls-014", label: "五印坛城" },
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

function isRouteIntentQuestion(value: string) {
  return routeIntentKeywords.some((keyword) => value.includes(keyword));
}

function constraintLabel(value: string | undefined) {
  return value === "must_visit" ? "必去" : value === "optional" ? "可选" : value === "alternative" ? "替代" : "推荐";
}

function crowdActionLabel(value: string | undefined) {
  const labels: Record<string, string> = {
    delay: "已错峰",
    keep_with_warning: "保留提醒",
    replace: "已替代",
    avoid: "已避开",
    skip: "已跳过",
  };
  return value ? labels[value] || "保留" : "保留";
}

function speechExcerpt(value: string | undefined, limit = 420) {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  return normalized.length > limit ? `${normalized.slice(0, limit)}。后续内容请看页面文字。` : normalized;
}

function routeSpeechSummary(route: RouteRecommendation) {
  const highStops = route.stops.filter((stop) => stop.crowd_level === "high").map((stop) => stop.name);
  const crowdText = highStops.length ? `高拥挤点有${highStops.slice(0, 2).join("、")}，已在路线里提示错峰。` : "当前路线整体拥挤压力较低。";
  return `${route.title}已生成，综合评分 ${route.recommendation_score} 分，预计 ${route.estimated_duration_minutes} 分钟。${crowdText} 当前拥挤度为模拟演示数据，不代表真实客流。`;
}

function visionSpeechSummary(result: VisionResponse) {
  if (result.matched_attraction) {
    return `识景完成，我识别到${result.matched_attraction.name}，置信度约 ${Math.round(result.confidence * 100)}%。你可以继续问我这个景点的看点或游览建议。`;
  }
  return "这张图暂时没有匹配到确定景点，我不会编造结果。你可以换一张样例图，或手动选择当前讲解景点。";
}

export function MobileHomePage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const routePanelRef = useRef<HTMLElement | null>(null);
  const answerPanelRef = useRef<HTMLElement | null>(null);
  const composerInputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);
  const [attractions, setAttractions] = useState<Attraction[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [question, setQuestion] = useState("灵山大佛适合怎么游览？");
  const [qaResult, setQaResult] = useState<QAResponse | null>(null);
  const [visionResult, setVisionResult] = useState<VisionResponse | null>(null);
  const [routeTheme, setRouteTheme] = useState("family");
  const [routeBudget, setRouteBudget] = useState(240);
  const [avoidCrowd, setAvoidCrowd] = useState(true);
  const [crowdTolerance, setCrowdTolerance] = useState<CrowdLevel>("medium");
  const [mustVisitIds, setMustVisitIds] = useState<string[]>([]);
  const [routeResult, setRouteResult] = useState<RouteRecommendation | null>(null);
  const [routeSessionId, setRouteSessionId] = useState("");
  const [routeConversation, setRouteConversation] = useState<RouteConversationResponse | null>(null);
  const [clarificationOptions, setClarificationOptions] = useState<string[]>([]);
  const [loadingAttractions, setLoadingAttractions] = useState(true);
  const [qaLoading, setQaLoading] = useState(false);
  const [visionLoading, setVisionLoading] = useState(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [selectedFeedbackTags, setSelectedFeedbackTags] = useState<string[]>(["路线合理"]);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState("");
  const [error, setError] = useState("");
  const { caption: humanCaption, resetHuman, setHumanState, state: humanState } = useDigitalHumanState();
  const speech = useSpeechSynthesis();
  const recognition = useSpeechRecognition();

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

  function scrollAnswerIntoView(block: ScrollLogicalPosition = "start") {
    window.setTimeout(() => {
      answerPanelRef.current?.scrollIntoView({ behavior: "smooth", block });
    }, 0);
  }

  function speakWithHuman(
    text: string,
    options: { caption?: string; endState?: DigitalHumanState; maxChars?: number } = {},
  ) {
    const caption = options.caption || speechExcerpt(text, 96);
    const didStart = speech.speak(text, {
      maxChars: options.maxChars,
      onEnd: () => {
        if (options.endState) {
          setHumanState(options.endState, caption);
        } else {
          resetHuman("播报结束。你可以继续用文本提问，也可以生成路线。");
        }
      },
      onError: (message) => {
        setHumanState("error", message);
      },
      onStart: () => {
        setHumanState("speaking", caption);
      },
    });
    if (!didStart) {
      setHumanState("error", "当前浏览器不支持语音播报，文本内容仍可正常使用。");
    }
    return didStart;
  }

  function speakLatestAnswer() {
    if (qaResult?.answer) {
      speakWithHuman(qaResult.answer);
      return;
    }
    if (routeResult) {
      speakWithHuman(routeSpeechSummary(routeResult));
      return;
    }
    if (visionResult) {
      speakWithHuman(visionSpeechSummary(visionResult));
    }
  }

  function stopSpeaking() {
    speech.stop();
    resetHuman("播报已停止，文本内容还在页面里。");
  }

  function toggleVoiceInput() {
    if (recognition.listening) {
      recognition.stopListening();
      resetHuman("语音输入已停止。你可以检查文本后发送。");
      return;
    }
    const started = recognition.startListening({
      onEnd: () => {
        setHumanState("welcome", "语音输入结束。请确认文本后发送。");
      },
      onError: (message) => {
        setError(message);
        setHumanState("error", message);
      },
      onResult: (text) => {
        setQuestion(text);
        setHumanState("welcome", "已把语音识别结果填入输入框，请确认后发送。");
        composerInputRef.current?.focus();
      },
      onStart: () => {
        setError("");
        setHumanState("listening", "我正在听，请说出你想问的景点或路线需求。");
      },
    });
    if (!started) {
      setError("当前浏览器不支持语音输入，请使用文本提问。");
      setHumanState("error", "当前浏览器不支持语音输入，请使用文本提问。");
    }
  }

  async function submitQuestion(nextQuestion = question) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion) {
      setError("请先输入一个问题。");
      return;
    }
    setQaLoading(true);
    setError("");
    setQuestion(cleanQuestion);
    setQaResult(null);
    setClarificationOptions([]);
    speech.stop();
    setHumanState("thinking", "我正在检索本地资料，并判断是否需要规划路线。");
    const matchedAttraction = attractions.find((item) => cleanQuestion.includes(item.name));
    const queryAttractionId = matchedAttraction?.id || selectedId;
    if (matchedAttraction && matchedAttraction.id !== selectedId) {
      setSelectedId(matchedAttraction.id);
    }
    scrollAnswerIntoView();
    try {
      if (isRouteIntentQuestion(cleanQuestion)) {
        const result = await sendRouteConversation({
          message: cleanQuestion,
          sessionId: routeSessionId || undefined,
          currentRouteId: routeResult?.id,
          selectedAttractionId: queryAttractionId,
        });
        setRouteConversation(result);
        setRouteSessionId(result.session_id);
        setQaResult({ answer: result.reply, sources: [], mode: "route_memory", latency_ms: 0 });
        setClarificationOptions(result.clarification_options || []);
        if (result.route) {
          setRouteResult(result.route);
          setRouteTheme(result.route.theme);
          setRouteBudget(result.route.time_budget_minutes);
          setAvoidCrowd(result.route.crowd_policy.avoid_crowd);
          setCrowdTolerance(result.route.crowd_policy.crowd_tolerance);
          setMustVisitIds(result.memory.constraints.must_visit_attraction_ids || []);
          window.setTimeout(() => routePanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 250);
        }
        if (result.needs_clarification) {
          setHumanState("comforting", result.reply);
          speakWithHuman(result.reply, { endState: "comforting", maxChars: 220 });
        } else if (result.route) {
          speakWithHuman(`${result.reply} ${routeSpeechSummary(result.route)}`, { maxChars: 360 });
        } else {
          speakWithHuman(result.reply, { maxChars: 260 });
        }
        scrollAnswerIntoView("nearest");
        return;
      }
      const result = await askQuestion({ attractionId: queryAttractionId, question: cleanQuestion });
      setQaResult(result);
      if (result.sources.length === 0) {
        setHumanState("comforting", "本地资料没有明确命中，我会避免编造。");
        speakWithHuman(result.answer, { endState: "comforting", maxChars: 300 });
      } else {
        speakWithHuman(result.answer, { maxChars: 420 });
      }
      scrollAnswerIntoView("nearest");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "问答请求失败，请稍后重试。";
      setError(message);
      setHumanState("error", message);
      speakWithHuman(message, { endState: "error", maxChars: 120 });
      scrollAnswerIntoView("nearest");
    } finally {
      setQaLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion();
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter" || event.shiftKey || composingRef.current) {
      return;
    }
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
    speech.stop();
    setHumanState("thinking", "我正在用 mock 识景规则分析图片文件和提示词。");
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
      const nextState = result.matched_attraction ? "happy" : "comforting";
      setHumanState(nextState, visionSpeechSummary(result));
      speakWithHuman(visionSpeechSummary(result), { endState: nextState, maxChars: 240 });
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "识景请求失败，请稍后重试。";
      setError(message);
      setHumanState("error", message);
      speakWithHuman(message, { endState: "error", maxChars: 120 });
    } finally {
      setVisionLoading(false);
    }
  }

  async function generateRoute(nextTheme = routeTheme) {
    setRouteLoading(true);
    setError("");
    setRouteTheme(nextTheme);
    speech.stop();
    setHumanState("thinking", "我正在根据主题、时间和模拟拥挤度规划路线。");
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
        mustVisitAttractionIds: mustVisitIds,
      });
      setRouteResult(result);
      setHumanState("happy", routeSpeechSummary(result));
      speakWithHuman(routeSpeechSummary(result), { endState: "happy", maxChars: 320 });
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "路线推荐失败，请稍后重试。";
      setError(message);
      setHumanState("error", message);
      speakWithHuman(message, { endState: "error", maxChars: 120 });
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

  function toggleFeedbackTag(tag: string) {
    setSelectedFeedbackTags((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  function toggleMustVisit(attractionId: string) {
    setMustVisitIds((current) =>
      current.includes(attractionId) ? current.filter((item) => item !== attractionId) : [...current, attractionId],
    );
  }

  async function sendFeedback() {
    setFeedbackLoading(true);
    setFeedbackDone("");
    setError("");
    try {
      const result = await submitFeedback({
        channel: "mobile",
        route_id: routeResult?.id,
        attraction_id: selectedId || undefined,
        rating: feedbackRating,
        tags: selectedFeedbackTags,
        comment: feedbackComment || undefined,
      });
      setFeedbackDone(`反馈已记录：${result.id}`);
      setFeedbackComment("");
      setHumanState("happy", "谢谢反馈，我会把这条本地演示记录交给后台洞察。");
      speakWithHuman("谢谢你的反馈，我已经记录到本地演示日志里。", { endState: "happy", maxChars: 80 });
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "反馈提交失败，请稍后重试。";
      setError(message);
      setHumanState("error", message);
    } finally {
      setFeedbackLoading(false);
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

      <DigitalHumanMock caption={humanCaption} state={humanState} className="mobile-avatar" />

      <section className="mobile-greeting" aria-labelledby="mobile-greeting-title">
        <span className="eyebrow">AI 导游待命</span>
        <h2 id="mobile-greeting-title">你好，我是灵境。直接问我景点故事、游览建议或避峰路线。</h2>
      </section>

      <section className="ask-composer" aria-labelledby="ask-composer-title">
        <div className="ask-composer__header">
          <div>
            <span className="eyebrow">文本提问优先</span>
            <h2 id="ask-composer-title">问灵境</h2>
          </div>
          <StatusBadge tone={qaLoading ? "neutral" : "ok"}>{qaLoading ? "检索中" : "可直接提问"}</StatusBadge>
        </div>

        <form className="composer-form" aria-label="文本提问" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="mobile-question">
            输入你的问题
          </label>
          <div className="composer-input-row">
            <input
              aria-describedby="composer-helper"
              className="composer-input"
              disabled={qaLoading}
              id="mobile-question"
              onChange={(event) => setQuestion(event.target.value)}
              onCompositionEnd={() => {
                composingRef.current = false;
              }}
              onCompositionStart={() => {
                composingRef.current = true;
              }}
              onKeyDown={handleComposerKeyDown}
              placeholder="问灵境：九龙灌浴几点表演？"
              ref={composerInputRef}
              type="text"
              value={question}
            />
            <button
              aria-label={recognition.listening ? "停止语音输入" : "开始语音输入"}
              aria-pressed={recognition.listening}
              className={`composer-voice ${recognition.listening ? "composer-voice--active" : ""}`}
              onClick={toggleVoiceInput}
              title={recognition.supported ? "语音识别会填入文本框，发送前可确认" : "当前浏览器不支持语音输入时会降级为文本"}
              type="button"
            >
              <Mic aria-hidden="true" size={18} />
            </button>
            <Button
              aria-label="发送问题"
              className="composer-send"
              disabled={!question.trim() || qaLoading}
              icon={<Send size={18} />}
              loading={qaLoading}
              type="submit"
              variant="primary"
            >
              发送
            </Button>
          </div>
          <p className="composer-helper" id="composer-helper">
            按 Enter 发送；语音会先填入文本框，确认后再发送。
          </p>
          <div className="speech-control-row" aria-label="数字人语音控制">
            <Button
              className="speech-control-button"
              disabled={!qaResult && !routeResult && !visionResult}
              icon={speech.speaking ? <VolumeX size={18} /> : <Volume2 size={18} />}
              onClick={speech.speaking ? stopSpeaking : speakLatestAnswer}
              type="button"
              variant={speech.speaking ? "quiet" : "secondary"}
            >
              {speech.speaking ? "停止播报" : "播报最新回答"}
            </Button>
            <span>
              {speech.supported ? "TTS 使用浏览器 SpeechSynthesis" : "此浏览器不支持 TTS，文本可用"}
              {recognition.listening ? " · 正在听取" : ""}
            </span>
          </div>
        </form>

        {error ? (
          <p className="inline-alert inline-alert--composer" role="alert">
            {error}
          </p>
        ) : null}

        <div className="quick-question-row" aria-label="快捷问题">
          {starterQuestions.map((item) => (
            <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
              {item}
            </button>
          ))}
        </div>

        <div className="attraction-context">
          <label className="field-label" htmlFor="attraction-select">
            当前讲解景点
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
        </div>
      </section>

      <section className="mobile-chat" aria-label="问答讲解" ref={answerPanelRef}>
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

      {qaResult && qaResult.sources.length > 0 ? (
        <section className="source-panel" aria-label="回答来源">
          <div className="section-title-row">
            <h2>来源依据</h2>
            <StatusBadge tone="neutral">{qaResult.latency_ms} ms</StatusBadge>
          </div>
          <div className="source-list">
            {qaResult.sources.map((source) => (
              <div className="source-item" key={source.chunk_id}>
                <strong>{source.title}</strong>
                <span>{source.source_file}</span>
                <span>分数 {source.score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {clarificationOptions.length > 0 ? (
        <section className="clarification-panel" aria-label="澄清选项">
          <strong>{routeConversation?.intent.clarification_question || "请选择一个更明确的方向"}</strong>
          <div className="quick-question-row">
            {clarificationOptions.map((option) => (
              <button className="quick-question" key={option} onClick={() => void submitQuestion(`${question}，${option}`)} type="button">
                {option}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {selectedAttraction ? (
        <div className="mobile-spot-summary">
          <SpotCard
            description={shortText(selectedAttraction.summary || selectedAttraction.description)}
            meta={`${selectedAttraction.category || "景点"} · ${
              (selectedAttraction.tags || []).slice(0, 2).join(" / ") || "本地知识库"
            }`}
            title={selectedAttraction.name}
          />
        </div>
      ) : (
        <p className="empty-state mobile-empty">正在等待景点数据，确认后端启动后会自动加载。</p>
      )}

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
          <div className="must-visit-picker" aria-label="必去景点约束">
            <span className="field-label">必去景点</span>
            <div className="must-visit-chip-row">
              {mustVisitOptions.map((item) => (
                <button
                  className={mustVisitIds.includes(item.id) ? "must-visit-chip must-visit-chip--active" : "must-visit-chip"}
                  key={item.id}
                  onClick={() => toggleMustVisit(item.id)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
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
              {routeResult.constraint_summary?.warning ? (
                <p className="constraint-warning">
                  <ShieldCheck aria-hidden="true" size={16} />
                  {routeResult.constraint_summary.warning}
                </p>
              ) : null}
              {routeResult.constraint_conflicts?.length ? (
                <p className="constraint-warning">
                  <AlertTriangle aria-hidden="true" size={16} />
                  {routeResult.constraint_conflicts[0].message}
                </p>
              ) : null}
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
                    <div className="constraint-badge-row">
                      <StatusBadge tone={stop.constraint_type === "must_visit" ? "ok" : "neutral"}>
                        {constraintLabel(stop.constraint_type)}
                      </StatusBadge>
                      <StatusBadge tone={stop.crowd_action === "delay" || stop.crowd_action === "keep_with_warning" ? "warning" : "neutral"}>
                        {crowdActionLabel(stop.crowd_action)}
                      </StatusBadge>
                    </div>
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
                    {stop.constraint_reason ? <p className="constraint-note">{stop.constraint_reason}</p> : null}
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

      <section className="feedback-panel" aria-label="游客反馈">
        <div className="section-title-row">
          <div>
            <h2>体验反馈</h2>
            <p>本地演示日志，不记录个人身份。</p>
          </div>
          <Heart aria-hidden="true" />
        </div>
        <div className="rating-row" role="group" aria-label="满意度评分">
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
        <div className="feedback-tag-grid" aria-label="反馈标签">
          {feedbackTags.map((tag) => (
            <button
              className={selectedFeedbackTags.includes(tag) ? "feedback-tag feedback-tag--active" : "feedback-tag"}
              key={tag}
              onClick={() => toggleFeedbackTag(tag)}
              type="button"
            >
              {tag}
            </button>
          ))}
        </div>
        <label className="field-label" htmlFor="mobile-feedback-comment">
          补充说明（可选）
        </label>
        <textarea
          className="text-area"
          id="mobile-feedback-comment"
          onChange={(event) => setFeedbackComment(event.target.value)}
          placeholder="例如：路线避开了拥挤点，讲解还可以更短一点。"
          rows={3}
          value={feedbackComment}
        />
        <Button icon={<Heart size={18} />} loading={feedbackLoading} onClick={() => void sendFeedback()} type="button" variant="secondary">
          提交反馈
        </Button>
        {feedbackDone ? <p className="success-note">{feedbackDone}</p> : null}
      </section>

      <nav className="mobile-actions" aria-label="游客主操作">
        <IconButton icon={Mic} label={recognition.listening ? "停止听取" : "语音"} onClick={toggleVoiceInput} />
        <IconButton icon={Camera} label="拍照" onClick={() => fileInputRef.current?.click()} />
        <IconButton icon={Map} label="路线" onClick={focusRoutePanel} />
        <IconButton icon={Navigation} label="终端" onClick={() => window.location.assign("/kiosk")} />
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
