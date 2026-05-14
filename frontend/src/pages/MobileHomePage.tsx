import { type CSSProperties, type ChangeEvent, type FormEvent, type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Heart, Layers, Map as MapIcon, Mic, Send, ShieldCheck, Volume2, VolumeX } from "lucide-react";

import { askQuestion, fetchAttractions, recognizeImage, recommendRoute, sendRouteConversation, submitFeedback, understandQuery } from "../api/client";
import type {
  Attraction,
  CrowdLevel,
  QAResponse,
  QueryUnderstandingResult,
  RouteConversationResponse,
  RouteRecommendation,
  VisionCandidate,
  VisionResponse,
} from "../api/client";
import { Button } from "../components/Button";
import { DigitalHumanMock, type DigitalHumanState } from "../components/DigitalHumanMock";
import {
  RouteConstraintChip,
  ScenicActionTile,
  ScenicBottomNav,
  SourceChip,
  type ScenicNavKey,
} from "../components/ScenicControls";
import { PageShell } from "../components/Shell";
import { StatusBadge } from "../components/StatusBadge";
import { ImageIcon, type LingshanImageIconName } from "../components/icons/LingshanImageIcons";
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
  { value: 180, label: "3 小时" },
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
  "想去",
  "想看",
  "避开",
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
type RouteConstraintKind = "must" | "optional" | "avoid";

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

function shouldUseCurrentAttractionContext(value: string) {
  return ["这里", "这个景点", "当前景点", "从这里", "我在"].some((keyword) => value.includes(keyword));
}

function isRouteIntentQuestion(value: string) {
  return routeIntentKeywords.some((keyword) => value.includes(keyword));
}

function understandingLabel(value: QueryUnderstandingResult | undefined) {
  if (!value) {
    return "";
  }
  const labels: Record<string, string> = {
    scenic_guide: "景区问答",
    route_planning: "路线规划",
    recommendation: "推荐/对比",
    operations: "拥挤运营",
    out_of_scope: "资料外",
    unclear: "需要澄清",
  };
  const handlerLabels: Record<string, string> = {
    qa_rag: "本地 RAG",
    scenic_area_intro: "景区总览",
    interest_recommendation: "兴趣推荐",
    comparison: "景点对比",
    crowd_status: "拥挤运营",
    route_planner: "路线规划",
    clarification: "澄清",
    out_of_scope: "资料外",
  };
  return handlerLabels[value.handler || ""] || labels[value.domain] || value.domain;
}

function understandingTone(value: QueryUnderstandingResult | undefined) {
  if (!value) {
    return "neutral" as const;
  }
  return value.domain === "out_of_scope" || value.domain === "unclear" ? "warning" : "ok";
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

function selectionSourceLabel(value: string | undefined) {
  const labels: Record<string, string> = {
    must_visit: "必去约束",
    optional_boost: "可选加权",
    template_seed: "经典 seed",
    full_pool: "全量候选池",
    start_context: "起点上下文",
  };
  return value ? labels[value] || value : "系统推荐";
}

function operationImpactSummary(route: RouteRecommendation) {
  const policy = route.operation_policy || route.operation_events_summary;
  if (!policy || policy.active_event_count === 0) {
    return "";
  }
  const affected = policy.affected_event_count > 0 ? `影响 ${policy.affected_event_count} 个站点` : "当前路线无直接受影响站点";
  return `已读取 ${policy.active_event_count} 条运营事件，${affected}；来源 ${policy.sources.join(" / ") || "mock"}。`;
}

function attractionSearchText(item: Attraction) {
  return [item.name, item.scenic_area, item.category, ...(item.tags || [])].join(" ").toLowerCase();
}

function routeAttractionIconName(name: string): LingshanImageIconName {
  if (name.includes("梵宫")) {
    return "brahma-palace";
  }
  if (name.includes("桥")) {
    return "bridge";
  }
  if (name.includes("九龙")) {
    return "crowd-wave";
  }
  return "buddha";
}

function crowdStatusTone(level: CrowdLevel) {
  return level === "high" ? "warning" : level === "medium" ? "neutral" : "ok";
}

function speechExcerpt(value: string | undefined, limit = 420) {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  return normalized.length > limit ? `${normalized.slice(0, limit)}。后续内容请看页面文字。` : normalized;
}

function routeSpeechSummary(route: RouteRecommendation) {
  const highStops = route.stops.filter((stop) => stop.crowd_level === "high").map((stop) => stop.name);
  const crowdText = highStops.length ? `高拥挤点有${highStops.slice(0, 2).join("、")}，已在路线里提示错峰。` : "当前路线整体拥挤压力较低。";
  const operationText = operationImpactSummary(route);
  return `${route.title}已生成，综合评分 ${route.recommendation_score} 分，预计 ${route.estimated_duration_minutes} 分钟。${crowdText}${operationText ? operationText : ""} 当前拥挤度与运营事件为模拟演示数据，不代表真实客流。`;
}

function visionSpeechSummary(result: VisionResponse) {
  const topCandidate = result.candidates[0];
  if (topCandidate) {
    const prefix = result.needs_confirmation ? "我找到几个可能的景点，需要你确认。" : "识景候选已生成。";
    return `${prefix}Top1 是${topCandidate.attraction.name}，置信度约 ${Math.round(topCandidate.confidence * 100)}%。确认后我再进入讲解。`;
  }
  return "这张图暂时没有匹配到确定景点，我不会编造结果。你可以换一张样例图，或手动选择当前讲解景点。";
}

export function MobileHomePage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const topRef = useRef<HTMLDivElement | null>(null);
  const routePanelRef = useRef<HTMLElement | null>(null);
  const answerPanelRef = useRef<HTMLElement | null>(null);
  const visionPanelRef = useRef<HTMLElement | null>(null);
  const feedbackPanelRef = useRef<HTMLElement | null>(null);
  const composerInputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);
  const [attractions, setAttractions] = useState<Attraction[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [question, setQuestion] = useState("灵山大佛适合怎么游览？");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [qaResult, setQaResult] = useState<QAResponse | null>(null);
  const [visionResult, setVisionResult] = useState<VisionResponse | null>(null);
  const [confirmedVisionId, setConfirmedVisionId] = useState<string | null>(null);
  const [visionFileName, setVisionFileName] = useState("");
  const [routeTheme, setRouteTheme] = useState("family");
  const [routeBudget, setRouteBudget] = useState(180);
  const [routeLessWalk, setRouteLessWalk] = useState(true);
  const [routeFamilyFriendly, setRouteFamilyFriendly] = useState(true);
  const [routeNoBacktrack, setRouteNoBacktrack] = useState(false);
  const [avoidCrowd, setAvoidCrowd] = useState(true);
  const [crowdTolerance, setCrowdTolerance] = useState<CrowdLevel>("medium");
  const [mustVisitIds, setMustVisitIds] = useState<string[]>([]);
  const [optionalAttractionIds, setOptionalAttractionIds] = useState<string[]>([]);
  const [avoidAttractionIds, setAvoidAttractionIds] = useState<string[]>([]);
  const [routeConstraintQuery, setRouteConstraintQuery] = useState("");
  const [routeInstruction, setRouteInstruction] = useState("我带老人孩子，3小时，灵山大佛一定要去，别太挤");
  const [routePreferencesOpen, setRoutePreferencesOpen] = useState(false);
  const [routeAllAttractionsOpen, setRouteAllAttractionsOpen] = useState(false);
  const [routeEvidenceOpen, setRouteEvidenceOpen] = useState(false);
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
  const [activeNav, setActiveNav] = useState<ScenicNavKey>("recommend");
  const [answerDetailOpen, setAnswerDetailOpen] = useState(false);
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
  const recommendedAttractions = useMemo(() => {
    const seeded = selectedAttraction ? [selectedAttraction, ...attractions.filter((item) => item.id !== selectedAttraction.id)] : attractions;
    return seeded.slice(0, 3);
  }, [attractions, selectedAttraction]);
  const activeUnderstanding = qaResult?.understanding || routeConversation?.understanding;
  const currentAnswer = qaResult?.answer || "";
  const answerIsLong = currentAnswer.length > 120;
  const routePrimaryCrowdText =
    routeResult?.stops.find((stop) => stop.crowd_level === "high")?.crowd_note ||
    routeResult?.decision_trace.find((item) => item.includes("拥挤")) ||
    "根据实时客流为您生成错峰顺序。";

  const attractionById = useMemo(() => new Map(attractions.map((item) => [item.id, item])), [attractions]);
  const lingshanDafoId = useMemo(
    () => attractions.find((item) => item.id === "lingshan-ls-011" || item.name.includes("灵山大佛"))?.id || "",
    [attractions],
  );
  const routeAttractionMatches = useMemo(() => {
    const query = routeConstraintQuery.trim().toLowerCase();
    return attractions.filter((item) => !query || attractionSearchText(item).includes(query));
  }, [attractions, routeConstraintQuery]);
  const routePreviewAttractions = useMemo(() => routeAttractionMatches.slice(0, 7), [routeAttractionMatches]);
  const hasMoreRouteAttractions = routeAttractionMatches.length > routePreviewAttractions.length;

  function scrollAnswerIntoView(block: ScrollLogicalPosition = "start") {
    void block;
    window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: "smooth" });
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
    setActiveNav("guide");
    setQaLoading(true);
    setError("");
    setQuestion(cleanQuestion);
    setSubmittedQuestion(cleanQuestion);
    setQaResult(null);
    setAnswerDetailOpen(false);
    setRouteConversation(null);
    setClarificationOptions([]);
    speech.stop();
    setHumanState("thinking", "我正在先理解问题边界，再决定是否检索资料或规划路线。");
    const matchedAttraction = attractions.find((item) => cleanQuestion.includes(item.name));
    const explicitAttractionId = matchedAttraction?.id || undefined;
    const routeContextAttractionId =
      explicitAttractionId || (shouldUseCurrentAttractionContext(cleanQuestion) ? selectedId || undefined : undefined);
    if (matchedAttraction && matchedAttraction.id !== selectedId) {
      setSelectedId(matchedAttraction.id);
    }
    scrollAnswerIntoView();
    try {
      const understanding = await understandQuery({
        message: cleanQuestion,
        selectedAttractionId: routeContextAttractionId,
        currentRouteId: routeResult?.id,
      });
      if (understanding.should_route || (isRouteIntentQuestion(cleanQuestion) && understanding.domain === "route_planning")) {
        const result = await sendRouteConversation({
          message: cleanQuestion,
          sessionId: routeSessionId || undefined,
          currentRouteId: routeResult?.id,
          selectedAttractionId: routeContextAttractionId,
        });
        setRouteConversation(result);
        setRouteSessionId(result.session_id);
        setQaResult({ answer: result.reply, sources: [], mode: "route_memory", latency_ms: 0, understanding: result.understanding || understanding });
        setClarificationOptions(result.clarification_options || []);
        if (result.route) {
          setRouteResult(result.route);
          setRouteTheme(result.route.theme);
          setRouteBudget(result.route.time_budget_minutes);
          setAvoidCrowd(result.route.crowd_policy.avoid_crowd);
          setCrowdTolerance(result.route.crowd_policy.crowd_tolerance);
          setMustVisitIds(result.memory.constraints.must_visit_attraction_ids || []);
          setOptionalAttractionIds(result.memory.constraints.optional_attraction_ids || []);
          setAvoidAttractionIds(result.memory.constraints.avoid_attraction_ids || []);
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
      const queryAttractionId = understanding.entities.length === 1 ? understanding.entities[0].id : explicitAttractionId;
      const result = await askQuestion({ attractionId: understanding.should_retrieve ? queryAttractionId : undefined, question: cleanQuestion });
      setQaResult(result);
      setClarificationOptions(result.understanding?.clarification_options || []);
      if (["scenic_area_intro", "recommendation", "comparison", "crowd_status"].includes(result.type || "")) {
        setHumanState("happy", "已按问题类型生成结构化导览结果。");
        speakWithHuman(result.answer, { maxChars: 360 });
      } else if (result.sources.length === 0) {
        setHumanState(
          "comforting",
          result.understanding?.domain === "out_of_scope"
            ? "这个问题不在本地景区知识库范围内，我不会编造。"
            : "本地资料没有明确命中，我会避免编造。",
        );
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
    setActiveNav("vision");
    setVisionFileName(file.name);
    setVisionLoading(true);
    setError("");
    speech.stop();
    setHumanState("thinking", "我正在用 mock 识景规则分析图片文件和提示词。");
    try {
      const result = await recognizeImage({
        file,
      });
      setVisionResult(result);
      setConfirmedVisionId(null);
      const nextState = result.candidates.length ? (result.needs_confirmation ? "comforting" : "happy") : "comforting";
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

  function confirmVisionCandidate(candidate: VisionCandidate) {
    setSelectedId(candidate.attraction.id);
    setConfirmedVisionId(candidate.attraction.id);
    const questionText = `${candidate.attraction.name}有什么看点？`;
    setQuestion(questionText);
    setHumanState("happy", `已确认${candidate.attraction.name}。我可以继续讲解这个景点。`);
    speakWithHuman(`已确认${candidate.attraction.name}。你可以点一键讲解，或继续问我游览建议。`, {
      endState: "happy",
      maxChars: 120,
    });
  }

  function confirmedVisionCandidate() {
    if (!visionResult || !confirmedVisionId) {
      return null;
    }
    return visionResult.candidates.find((candidate) => candidate.attraction.id === confirmedVisionId) || null;
  }

  function visionSuggestedQuestions() {
    const confirmed = confirmedVisionCandidate();
    if (!confirmed) {
      return visionResult?.suggested_questions || [];
    }
    return [
      `${confirmed.attraction.name}有什么看点？`,
      `${confirmed.attraction.name}适合怎么游览？`,
      `${confirmed.attraction.name}背后有什么文化故事？`,
    ];
  }

  function syncRouteStateFromConversation(result: RouteConversationResponse) {
    setRouteConversation(result);
    setRouteSessionId(result.session_id);
    setClarificationOptions(result.clarification_options || []);
    if (!result.route) {
      return;
    }
    setRouteResult(result.route);
    setRouteTheme(result.route.theme);
    setRouteBudget(result.route.time_budget_minutes);
    setAvoidCrowd(result.route.crowd_policy.avoid_crowd);
    setCrowdTolerance(result.route.crowd_policy.crowd_tolerance);
    setMustVisitIds(result.memory.constraints.must_visit_attraction_ids || []);
    setOptionalAttractionIds(result.memory.constraints.optional_attraction_ids || []);
    setAvoidAttractionIds(result.memory.constraints.avoid_attraction_ids || []);
  }

  async function submitRouteInstructionText(nextInstruction = routeInstruction) {
    const cleanInstruction = nextInstruction.trim();
    if (!cleanInstruction) {
      void generateRoute();
      return;
    }
    setActiveNav("route");
    setRouteLoading(true);
    setError("");
    setRouteInstruction(cleanInstruction);
    speech.stop();
    setHumanState("thinking", "我正在把路线需求解析成时长、必去点和避峰策略。");
    const matchedAttraction = attractions.find((item) => cleanInstruction.includes(item.name));
    try {
      const result = await sendRouteConversation({
        message: cleanInstruction,
        sessionId: routeSessionId || undefined,
        currentRouteId: routeResult?.id,
        selectedAttractionId: matchedAttraction?.id || selectedId || undefined,
      });
      syncRouteStateFromConversation(result);
      if (result.route) {
        speakWithHuman(`${result.reply} ${routeSpeechSummary(result.route)}`, { endState: "happy", maxChars: 360 });
      } else {
        speakWithHuman(result.reply, { endState: result.needs_clarification ? "comforting" : "welcome", maxChars: 240 });
      }
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "路线指令解析失败，请稍后重试。";
      setError(message);
      setHumanState("error", message);
      speakWithHuman(message, { endState: "error", maxChars: 120 });
    } finally {
      setRouteLoading(false);
    }
  }

  function handleRouteInstructionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitRouteInstructionText();
  }

  function clearRoutePlan() {
    setRouteInstruction("");
    setRouteTheme("family");
    setRouteBudget(180);
    setRouteLessWalk(false);
    setRouteFamilyFriendly(false);
    setRouteNoBacktrack(false);
    setAvoidCrowd(false);
    setCrowdTolerance("medium");
    setMustVisitIds([]);
    setOptionalAttractionIds([]);
    setAvoidAttractionIds([]);
    setRouteConstraintQuery("");
    setRoutePreferencesOpen(false);
    setRouteAllAttractionsOpen(false);
    setRouteEvidenceOpen(false);
    setRouteResult(null);
    setRouteConversation(null);
    setRouteSessionId("");
    setClarificationOptions([]);
    setError("");
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
        groupType: routeFamilyFriendly || nextTheme === "family" ? "family" : "friends",
        intensity: routeLessWalk || routeBudget <= 120 ? "easy" : "balanced",
        interests: [
          ...(selectedAttraction?.tags?.slice(0, 3) || [nextTheme]),
          ...(routeNoBacktrack ? ["no_backtracking"] : []),
        ],
        startAttractionId: selectedId,
        avoidCrowd,
        crowdTolerance,
        mustVisitAttractionIds: mustVisitIds,
        optionalAttractionIds,
        avoidAttractionIds,
      });
      setRouteResult(result);
      setActiveNav("route");
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
    setActiveNav("route");
    if (!routeResult) {
      void generateRoute();
    }
  }

  function handleScenicNavSelect(next: ScenicNavKey) {
    setActiveNav(next);
    if (next !== "route") {
      setRouteAllAttractionsOpen(false);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (next === "guide") {
      composerInputRef.current?.focus();
    }
  }

  function toggleFeedbackTag(tag: string) {
    setSelectedFeedbackTags((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  function addRouteConstraint(kind: RouteConstraintKind, attractionId: string) {
    if (kind === "must") {
      setMustVisitIds((current) => (current.includes(attractionId) ? current : [...current, attractionId]));
      setOptionalAttractionIds((current) => current.filter((item) => item !== attractionId));
      setAvoidAttractionIds((current) => current.filter((item) => item !== attractionId));
      return;
    }
    if (kind === "optional") {
      setOptionalAttractionIds((current) => (current.includes(attractionId) ? current : [...current, attractionId]));
      setMustVisitIds((current) => current.filter((item) => item !== attractionId));
      setAvoidAttractionIds((current) => current.filter((item) => item !== attractionId));
      return;
    }
    setAvoidAttractionIds((current) => (current.includes(attractionId) ? current : [...current, attractionId]));
    setMustVisitIds((current) => current.filter((item) => item !== attractionId));
    setOptionalAttractionIds((current) => current.filter((item) => item !== attractionId));
  }

  function removeRouteConstraint(kind: RouteConstraintKind, attractionId: string) {
    if (kind === "must") {
      setMustVisitIds((current) => current.filter((item) => item !== attractionId));
    } else if (kind === "optional") {
      setOptionalAttractionIds((current) => current.filter((item) => item !== attractionId));
    } else {
      setAvoidAttractionIds((current) => current.filter((item) => item !== attractionId));
    }
  }

  function toggleMustVisitConstraint(attractionId: string) {
    if (!attractionId) {
      return;
    }
    if (mustVisitIds.includes(attractionId)) {
      removeRouteConstraint("must", attractionId);
    } else {
      addRouteConstraint("must", attractionId);
    }
  }

  function selectedConstraintIds(kind: RouteConstraintKind) {
    return kind === "must" ? mustVisitIds : kind === "optional" ? optionalAttractionIds : avoidAttractionIds;
  }

  function isConstraintSelected(kind: RouteConstraintKind, attractionId: string) {
    return selectedConstraintIds(kind).includes(attractionId);
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
    <PageShell className={`mobile-page mobile-page--${activeNav}`}>
      <div className="mobile-top-anchor" ref={topRef} />
      <header className="mobile-header">
        <div>
          <span className="eyebrow">无锡灵山胜境</span>
          <h1>灵境导游</h1>
          <p>AI 智能导游 · 灵山胜境</p>
        </div>
        <div className="mobile-header__status">
          <StatusBadge tone={error ? "warning" : "ok"}>{error ? "需要处理" : "mock 在线"}</StatusBadge>
          <span className="weather-pill">26°C 多云</span>
        </div>
      </header>

      {activeNav === "recommend" ? (
        <>
          <section className="mobile-home-hero scenic-image-placeholder" aria-labelledby="mobile-home-hero-title">
            <div className="mobile-home-hero__mountains" aria-hidden="true" />
            <DigitalHumanMock caption={humanCaption} state={humanState} className="mobile-home-hero__human" />
            <div className="mobile-home-hero__bubble">
              <h2 id="mobile-home-hero-title">您好，我是灵境导游小灵</h2>
              <p>很高兴为您服务，想了解什么呢？</p>
            </div>
          </section>

          <form className="home-ask-bar" aria-label="首页提问" onSubmit={handleSubmit}>
            <input
              aria-label="输入您的问题"
              disabled={qaLoading}
              onChange={(event) => setQuestion(event.target.value)}
              onCompositionEnd={() => {
                composingRef.current = false;
              }}
              onCompositionStart={() => {
                composingRef.current = true;
              }}
              onKeyDown={handleComposerKeyDown}
              placeholder="输入您的问题..."
              type="text"
              value={question}
            />
            <button
              aria-label={recognition.listening ? "停止语音输入" : "开始语音输入"}
              aria-pressed={recognition.listening}
              className={recognition.listening ? "home-ask-bar__voice home-ask-bar__voice--active" : "home-ask-bar__voice"}
              onClick={toggleVoiceInput}
              type="button"
            >
              <Mic aria-hidden="true" size={20} />
            </button>
            <button aria-label="发送问题" className="home-ask-bar__send" disabled={!question.trim() || qaLoading} type="submit">
              <Send aria-hidden="true" size={22} />
            </button>
          </form>

          <div className="scenic-action-grid scenic-action-grid--home" aria-label="景区文化功能入口">
            <ScenicActionTile
              icon={<ImageIcon name="lotus" size={56} />}
              onClick={() => {
                setActiveNav("guide");
                composerInputRef.current?.focus();
              }}
            >
              问景点
            </ScenicActionTile>
            <ScenicActionTile
              icon={<ImageIcon name="scenic-camera" size={56} />}
              onClick={() => {
                setActiveNav("vision");
                window.setTimeout(() => fileInputRef.current?.click(), 200);
              }}
            >
              拍照识景
            </ScenicActionTile>
            <ScenicActionTile icon={<ImageIcon name="route-path" size={56} />} onClick={focusRoutePanel}>
              规划路线
            </ScenicActionTile>
            <ScenicActionTile
              icon={<ImageIcon name="crowd-wave" size={56} />}
              onClick={() => {
                setAvoidCrowd(true);
                focusRoutePanel();
              }}
            >
              避开拥挤
            </ScenicActionTile>
          </div>

          <section className="recommend-spots" aria-labelledby="recommend-spots-title">
            <div className="recommend-spots__header">
              <h2 id="recommend-spots-title">为你推荐</h2>
              <button type="button" onClick={() => setSelectedId(recommendedAttractions[1]?.id || recommendedAttractions[0]?.id || selectedId)}>
                换一批
              </button>
            </div>
            {recommendedAttractions.length ? (
              <div className="recommend-spot-list">
                {recommendedAttractions.map((item, index) => (
                  <article className="recommend-spot-card" key={item.id}>
                    <div className="recommend-spot-card__image scenic-image-placeholder" aria-hidden="true">
                      <ImageIcon name={index === 1 ? "lotus" : index === 2 ? "brahma-palace" : "buddha"} size={34} />
                    </div>
                    <div className="recommend-spot-card__body">
                      <div className="recommend-spot-card__title">
                        <h3>{item.name}</h3>
                        <span>{item.category || "核心地标"}</span>
                      </div>
                      <p>{shortText(item.summary || item.description, 44)}</p>
                      <small>客流：{index === 1 ? "中等" : "舒适"}　预计停留：{index === 1 ? "40" : index === 2 ? "30-40" : "15-20"} 分钟</small>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty-state mobile-empty">正在等待景点数据，确认后端启动后会自动加载。</p>
            )}
          </section>
        </>
      ) : null}

      {activeNav === "guide" ? (
      <div className="guide-tab">
      <section className="guide-status-panel" aria-labelledby="guide-status-title">
        <div>
          <span className="eyebrow">AI 导游讲解</span>
          <h2 id="guide-status-title">游灵山</h2>
          <p>问景点、故事、路线与拥挤状态。</p>
        </div>
        <div className="guide-status-card" aria-label="导游状态">
          <ImageIcon name="buddha" size={32} />
          <div>
            <strong>
              {qaLoading ? "检索中" : clarificationOptions.length ? "需要澄清" : speech.speaking ? "正在讲解" : submittedQuestion ? "待追问" : "待提问"}
            </strong>
            <span>{speech.speaking ? "TTS 播报中" : speech.supported ? "TTS 可用" : "TTS 不可用"}</span>
          </div>
        </div>
      </section>

      <section className="guide-live-stage" aria-label="沉浸式数字人直播讲解">
        <div className="guide-live-stage__top">
          <span className="guide-live-stage__badge">
            小灵 · {qaLoading ? "检索中" : recognition.listening ? "正在听" : speech.speaking ? "口型同步讲解" : "在线待命"}
          </span>
          <span className="guide-live-stage__signal">
            {speech.speaking ? "TTS 播报中" : recognition.supported ? "语音可用" : "文本可用"}
          </span>
        </div>
        <div className={`guide-live-avatar-slot guide-live-avatar-slot--${humanState}`} aria-label="数字人渲染接口位">
          <div className="guide-live-avatar-slot__figure" aria-hidden="true">
            <span />
            <i />
          </div>
          <div className="guide-live-avatar-slot__waves" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
        <div className="guide-live-stage__caption">
          <strong>{speech.speaking ? "正在讲解" : recognition.listening ? "我在听" : qaLoading ? "正在查资料" : "可以语音或文字提问"}</strong>
          <span>{humanCaption}</span>
        </div>
      </section>

      <section className="ask-composer guide-composer" aria-labelledby="ask-composer-title">
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
          <p className="composer-helper" id="composer-helper">Enter 发送，语音只辅助填入文本。</p>
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

      </section>

      <section className="mobile-chat guide-chat" aria-label="问答讲解" ref={answerPanelRef}>
        {activeUnderstanding ? (
          <div className="understanding-strip" aria-label="问题理解结果">
            <StatusBadge tone={understandingTone(activeUnderstanding)}>识别为：{understandingLabel(activeUnderstanding)}</StatusBadge>
            <span>
              置信度 {Math.round(activeUnderstanding.confidence * 100)}%
              {activeUnderstanding.reasons.length ? ` · ${activeUnderstanding.reasons.slice(0, 2).join(" / ")}` : ""}
            </span>
          </div>
        ) : null}
        <div className="chat-row chat-row--visitor">
          <strong>游客</strong>
          <p>{submittedQuestion || "还没有发送问题"}</p>
        </div>
        <div className="chat-row chat-row--guide">
          <div className="chat-row__speaker">
            <strong>灵境</strong>
            {qaResult?.understanding?.domain === "out_of_scope" ? <StatusBadge tone="warning">资料外</StatusBadge> : null}
            {clarificationOptions.length > 0 ? <StatusBadge tone="warning">需要澄清</StatusBadge> : null}
          </div>
          {qaLoading ? (
            <p className="guide-answer-text">正在检索本地资料，并判断是否需要澄清...</p>
          ) : qaResult ? (
            <>
              <p className={`guide-answer-text ${answerIsLong ? "guide-answer-text--clamped" : ""}`}>{qaResult.answer}</p>
              {answerIsLong ? (
                <button className="guide-answer-expand" onClick={() => setAnswerDetailOpen(true)} type="button">
                  展开完整讲解
                </button>
              ) : null}
              <div className="guide-answer-proof" aria-label="来源参考与回答置信度">
                {qaResult.sources.length > 0 ? (
                  <>
                    <strong>来源参考</strong>
                    <div className="guide-answer-proof__chips">
                      {qaResult.sources.slice(0, 2).map((source) => (
                        <SourceChip icon={<ImageIcon name="source-doc" size={16} />} key={source.chunk_id}>
                          {source.title || source.source_file}
                        </SourceChip>
                      ))}
                    </div>
                  </>
                ) : (
                  <strong>资料外 / 需要澄清</strong>
                )}
                <div className="guide-confidence-row">
                  <span>回答置信度：{Math.round(Math.min(0.99, qaResult.sources[0]?.score || 0.72) * 100)}%</span>
                  <i style={{ "--confidence": `${Math.round(Math.min(0.99, qaResult.sources[0]?.score || 0.72) * 100)}%` } as CSSProperties} />
                  <span>{qaResult.sources.length > 0 ? "数据来源充足" : "暂无本地来源"}</span>
                </div>
              </div>
              <section className="guide-action-grid" aria-label="讲解操作">
                <button type="button" onClick={speech.speaking ? stopSpeaking : speakLatestAnswer} disabled={!qaResult && !routeResult && !visionResult}>
                  <Volume2 aria-hidden="true" size={24} />
                  播放讲解
                </button>
                <button type="button" onClick={() => setAnswerDetailOpen(true)} disabled={!qaResult}>
                  <ImageIcon name="source-doc" size={25} />
                  来源依据
                </button>
                <button type="button" onClick={focusRoutePanel}>
                  <MapIcon aria-hidden="true" size={24} />
                  生成路线
                </button>
                <button className="guide-action-grid__danger" type="button" onClick={() => setActiveNav("mine")}>
                  <AlertTriangle aria-hidden="true" size={24} />
                  反馈不准
                </button>
              </section>
            </>
          ) : (
            <p className="guide-answer-text">你可以问景点看点、文化故事或适合怎么游览，回答会带上本地资料来源。</p>
          )}
        </div>
      </section>

      {answerDetailOpen && qaResult ? (
        <div className="guide-answer-drawer" role="dialog" aria-modal="true" aria-label="完整讲解">
          <button className="guide-answer-drawer__scrim" aria-label="关闭完整讲解" onClick={() => setAnswerDetailOpen(false)} type="button" />
          <section className="guide-answer-drawer__panel">
            <div className="guide-answer-drawer__handle" aria-hidden="true" />
            <div className="guide-answer-drawer__header">
              <div>
                <span className="eyebrow">完整讲解</span>
                <h2>小灵的详细回答</h2>
              </div>
              <button onClick={() => setAnswerDetailOpen(false)} type="button">
                收起
              </button>
            </div>
            <p className="guide-answer-drawer__question">{submittedQuestion}</p>
            <div className="guide-answer-drawer__body">
              <p>{qaResult.answer}</p>
            </div>
            <div className="guide-answer-drawer__sources" aria-label="来源依据">
              <strong>来源依据</strong>
              {qaResult.sources.length > 0 ? (
                qaResult.sources.map((source) => (
                  <div className="guide-answer-drawer__source" key={source.chunk_id}>
                    <span>{source.title || source.source_file}</span>
                    <small>
                      {source.source_section || "本地资料"} · 引用分 {Math.round(source.score * 100)}%
                    </small>
                  </div>
                ))
              ) : (
                <p>暂无本地来源，当前回答按资料外或澄清策略展示。</p>
              )}
            </div>
          </section>
        </div>
      ) : null}

      {qaResult?.scenic_area_intro ? (
        <section className="capability-panel" aria-label="景区总览">
          <div className="section-title-row">
            <h2>{qaResult.scenic_area_intro.title}</h2>
            <StatusBadge tone="neutral">{qaResult.scenic_area_intro.source}</StatusBadge>
          </div>
          <p>{qaResult.scenic_area_intro.summary}</p>
          <div className="capability-list">
            {qaResult.scenic_area_intro.highlights.slice(0, 5).map((item) => (
              <div className="capability-list-item" key={item}>
                <CheckCircle2 aria-hidden="true" size={16} />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <p className="simulation-note">
            <ShieldCheck aria-hidden="true" size={16} />
            {qaResult.scenic_area_intro.disclaimer}
          </p>
          <div className="quick-question-row" aria-label="景区总览建议问题">
            {qaResult.scenic_area_intro.suggested_questions.slice(0, 4).map((item) => (
              <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
                {item}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {qaResult?.recommendations?.length ? (
        <section className="capability-panel" aria-label="兴趣推荐">
          <div className="section-title-row">
            <h2>兴趣推荐</h2>
            <StatusBadge tone="ok">{qaResult.recommendations.length} 个候选</StatusBadge>
          </div>
          <div className="recommendation-list">
            {qaResult.recommendations.map((item) => (
              <article className="recommendation-item" key={item.attraction_id}>
                <div>
                  <strong>{item.name}</strong>
                  <span>
                    {item.scenic_area} · 规则分 {item.score}
                  </span>
                  <p>{item.reason}</p>
                  <small>{item.matched_interests.join(" / ") || "本地资料匹配"}</small>
                </div>
                <Button icon={<Send size={16} />} onClick={() => void submitQuestion(item.suggested_question)} type="button" variant="secondary">
                  一键问
                </Button>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {qaResult?.comparison ? (
        <section className="capability-panel" aria-label="景点景区对比">
          <div className="section-title-row">
            <h2>对比建议</h2>
            <StatusBadge tone="neutral">{qaResult.comparison.dimensions.join(" / ") || "综合"}</StatusBadge>
          </div>
          <p>{qaResult.comparison.recommendation}</p>
          <div className="capability-list">
            {qaResult.comparison.reasons.map((item) => (
              <div className="capability-list-item" key={item}>
                <MapIcon aria-hidden="true" size={16} />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <div className="quick-question-row" aria-label="对比后续问题">
            {qaResult.comparison.suggested_next_questions.slice(0, 3).map((item) => (
              <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
                {item}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {qaResult?.crowd_status ? (
        <section className="capability-panel" aria-label="拥挤与运营状态">
          <div className="section-title-row">
            <h2>拥挤与运营状态</h2>
            <StatusBadge tone="warning">演示数据</StatusBadge>
          </div>
          <p className="simulation-note">
            <AlertTriangle aria-hidden="true" size={16} />
            {qaResult.crowd_status.source_note}
          </p>
          <div className="status-list">
            {qaResult.crowd_status.items.map((item) => (
              <div className="status-list-item" key={item.attraction_id}>
                <strong>{item.name}</strong>
                <StatusBadge tone={crowdStatusTone(item.crowd_level)}>
                  {crowdLabel(item.crowd_level)} · {item.crowd_score}
                </StatusBadge>
                <span>等待约 {item.wait_minutes} 分钟 · {item.source}</span>
              </div>
            ))}
            {qaResult.crowd_status.operation_events.map((event) => (
              <div className="status-list-item" key={event.id}>
                <strong>{event.attraction_name || event.attraction_id}</strong>
                <StatusBadge tone={event.severity === "critical" ? "warning" : "neutral"}>{event.event_type}</StatusBadge>
                <span>
                  {event.message} · {event.source}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {qaResult && qaResult.sources.length > 0 ? (
        <section className="source-panel" aria-label="回答来源">
          <div className="section-title-row">
            <h2>来源依据</h2>
            <StatusBadge tone="neutral">{qaResult.latency_ms} ms</StatusBadge>
          </div>
          <div className="source-list">
            {qaResult.sources.map((source) => (
              <div className="source-item" key={source.chunk_id}>
                <SourceChip icon={<ImageIcon name="source-doc" size={18} />}>{source.source_file}</SourceChip>
                <strong>{source.title}</strong>
                <span>来源章节：{source.source_section || "本地资料切片"}</span>
                <span>引用分数 {source.score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {clarificationOptions.length > 0 ? (
        <section className="clarification-panel" aria-label="澄清选项">
          <strong>
            {qaResult?.understanding?.clarification_question || routeConversation?.intent.clarification_question || "请选择一个更明确的方向"}
          </strong>
          <div className="quick-question-row">
            {clarificationOptions.map((option) => (
              <button
                className="quick-question"
                key={option}
                onClick={() => void submitQuestion(`${submittedQuestion || question}，${option}`)}
                type="button"
              >
                {option}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <section className="guide-context-panel" aria-label="讲解上下文">
        <div className="section-title-row">
          <div>
            <h2>讲解上下文</h2>
            <p>普通问题不会自动带入该景点。</p>
          </div>
          <ImageIcon name="source-doc" size={22} />
        </div>
        <div className="attraction-context">
          <label className="field-label" htmlFor="attraction-select">
            当前展示景点
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
          <p className="context-note">需要讲解当前景点时，请在问题里直接写出景点名，或使用识景确认后继续追问。</p>
        </div>
      </section>
      </div>
      ) : null}

      {activeNav === "vision" ? (
      <section className="vision-panel" aria-label="图片识景" ref={visionPanelRef}>
        <div className="vision-hero">
          <div>
            <span className="eyebrow">AI 识景确认</span>
            <h2>拍照识景</h2>
            <p>拍下景点主体，我先给出候选，确认后再讲解。</p>
          </div>
          <StatusBadge
            tone={visionLoading ? "neutral" : confirmedVisionId ? "ok" : visionResult?.candidates.length ? "warning" : visionResult ? "warning" : "neutral"}
          >
            {visionLoading ? "识别中" : confirmedVisionId ? "已确认" : visionResult?.candidates.length ? "需确认" : visionResult ? "未识别" : "待上传"}
          </StatusBadge>
        </div>

        <div className="vision-upload-panel">
          <div className="vision-upload-panel__icon">
            <ImageIcon name="scenic-camera" size={46} />
          </div>
          <div className="vision-upload-panel__copy">
            <strong>{visionLoading ? "正在识别候选景点" : visionFileName || "选择一张景点图片"}</strong>
            <span>{visionFileName ? "已读取图片文件，结果只作为候选确认。" : "支持 jpg / png，mock 模式无 API Key 可运行。"}</span>
          </div>
          <Button
            icon={<ImageIcon name="scenic-camera" size={20} />}
            loading={visionLoading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
            variant="secondary"
          >
            {visionFileName ? "换一张" : "上传图片"}
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
              <StatusBadge tone={visionResult.candidates.length ? (visionResult.needs_confirmation ? "warning" : "ok") : "warning"}>
                {visionResult.candidates.length ? `候选 ${visionResult.candidates.length} 个` : "未命中"}
              </StatusBadge>
              <span>
                {visionResult.latency_ms} ms · {visionResult.mode}
              </span>
            </div>
            <p>{visionResult.explanation}</p>
            {visionResult.confirmation_reason ? (
              <p className={visionResult.needs_confirmation ? "vision-confirm-note vision-confirm-note--warning" : "vision-confirm-note"}>
                {visionResult.confirmation_reason}
              </p>
            ) : null}
            {visionResult.candidates.length > 0 ? (
              <div className="vision-candidate-list" aria-label="识景候选列表">
                {visionResult.candidates.map((candidate, index) => {
                  const confirmed = confirmedVisionId === candidate.attraction.id;
                  const topCandidate = index === 0;
                  return (
                    <article
                      className={[
                        "vision-candidate",
                        topCandidate ? "vision-candidate--top" : "",
                        confirmed ? "vision-candidate--confirmed" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      key={candidate.attraction.id}
                    >
                      <div className="vision-candidate__main">
                        <div className="vision-candidate__title">
                          <span className="vision-candidate__rank">Top{index + 1}</span>
                          <strong>{candidate.attraction.name}</strong>
                          <span className="vision-candidate__score">{Math.round(candidate.confidence * 100)}%</span>
                          {confirmed ? <StatusBadge tone="ok">已确认</StatusBadge> : null}
                        </div>
                        <span>{candidate.attraction.scenic_area} · {candidate.attraction.category || "景点"}</span>
                        <p>{candidate.reason}</p>
                        <small>依据：{candidate.match_signals.map((item) => ({ filename: "文件名", hint: "提示词", text_hint: "描述", tag: "标签", scenic_area: "景区" }[item] || item)).join(" / ") || "弱相关"}</small>
                      </div>
                      <Button
                        icon={confirmed ? <CheckCircle2 size={16} /> : <ImageIcon name="buddha" size={18} />}
                        onClick={() => confirmVisionCandidate(candidate)}
                        type="button"
                        variant={confirmed ? "secondary" : "accent"}
                      >
                        {confirmed ? "已确认" : "确认"}
                      </Button>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="vision-fallback">
                <strong>暂时没有把握识别这个画面</strong>
                <p>请换个角度拍摄景点主体，或直接输入景点名。没有可靠候选时，灵境不会把低置信结果当事实讲解。</p>
              </div>
            )}
            {confirmedVisionId ? (
              <div className="vision-confirmed-panel" aria-label="确认后讲解入口">
                <strong>已确认：{confirmedVisionCandidate()?.attraction.name}</strong>
                <p>接下来会走本地知识库问答，不凭视觉候选编造讲解。</p>
                <div className="suggested-question-list" aria-label="识景建议问题">
                {visionSuggestedQuestions().map((item) => (
                  <button className="quick-question" key={item} onClick={() => void submitQuestion(item)} type="button">
                    {item}
                  </button>
                ))}
                </div>
              </div>
            ) : visionResult.candidates.length > 0 ? (
              <p className="vision-pending-note">请先确认一个候选，再进入该景点讲解或继续追问。</p>
            ) : null}
          </div>
        ) : (
          <p className="empty-state mobile-empty">还没有上传图片。可用 evals/vision_samples 下的样例文件演示。</p>
        )}
      </section>
      ) : null}

      {activeNav === "route" ? (
      <section
        className={routeResult ? "route-panel route-journey route-journey--result" : "route-panel route-journey"}
        aria-label="路线规划"
        ref={routePanelRef}
      >
        <header className="route-journey__header">
          <div>
            <h2>{routeResult ? "路线详情" : "路线规划"}</h2>
          </div>
          {routeResult ? (
            <a className="route-share-icon-link" href={routeResult.share.share_url} aria-label="分享路线">
              ⤴
            </a>
          ) : (
            <button className="route-clear-button" type="button" onClick={clearRoutePlan}>
              清空
            </button>
          )}
        </header>

        {!routeResult ? (
          routeAllAttractionsOpen ? (
          <section className="route-all-attractions-page" aria-label="全部景点选择">
            <div className="route-all-attractions-header">
              <button className="route-detail-back-button" type="button" onClick={() => setRouteAllAttractionsOpen(false)}>
                返回路线规划
              </button>
              <span>已选 {mustVisitIds.length} 个</span>
            </div>
            <div className="route-text-card route-attraction-search-card">
              <div className="route-form-label-row">
                <label htmlFor="route-attraction-search">全部景点</label>
                <span>{routeAttractionMatches.length} 个可选</span>
              </div>
              <input
                id="route-attraction-search"
                onChange={(event) => setRouteConstraintQuery(event.target.value)}
                placeholder="搜索景点名称、景区或标签"
                type="search"
                value={routeConstraintQuery}
              />
            </div>
            <div className="route-scenic-grid route-scenic-grid--all">
              {routeAttractionMatches.map((item) => {
                const selected = mustVisitIds.includes(item.id);
                return (
                  <button
                    className={selected ? "route-scenic-choice route-scenic-choice--active" : "route-scenic-choice"}
                    key={item.id}
                    onClick={() => (selected ? removeRouteConstraint("must", item.id) : addRouteConstraint("must", item.id))}
                    type="button"
                  >
                    <ImageIcon name={routeAttractionIconName(item.name)} size={28} />
                    {item.name}
                  </button>
                );
              })}
              {routeAttractionMatches.length === 0 ? <p className="empty-state mobile-empty">没有匹配景点，请换一个关键词。</p> : null}
            </div>
          </section>
          ) : (
          <form className="route-plan-form" onSubmit={handleRouteInstructionSubmit} aria-label="路线规划表单">
            <div className="route-text-card">
              <div className="route-form-label-row">
                <label htmlFor="route-main-text">文本提问优先</label>
                <span>可直接提问</span>
              </div>
              <textarea
                id="route-main-text"
                onChange={(event) => setRouteInstruction(event.target.value)}
                value={routeInstruction}
                maxLength={200}
              />
              <small>{routeInstruction.length}/200</small>
            </div>

            <div className="route-choice-section">
              <span className="route-choice-title">我的要求 <small>（可多选）</small></span>
              <div className="route-chip-grid route-chip-grid--requirements">
                <button
                  className={lingshanDafoId && mustVisitIds.includes(lingshanDafoId) ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"}
                  disabled={!lingshanDafoId}
                  onClick={() => toggleMustVisitConstraint(lingshanDafoId)}
                  type="button"
                >
                  {lingshanDafoId && mustVisitIds.includes(lingshanDafoId) ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                  必去 灵山大佛
                </button>
                <button className={routeLessWalk ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"} type="button" onClick={() => setRouteLessWalk((value) => !value)}>
                  {routeLessWalk ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                  少走路
                </button>
                <button className={avoidCrowd ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"} type="button" onClick={() => setAvoidCrowd((value) => !value)}>
                  {avoidCrowd ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                  避开拥挤
                </button>
                <button
                  className={routeFamilyFriendly ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"}
                  type="button"
                  onClick={() => {
                    setRouteFamilyFriendly((value) => !value);
                    setRouteTheme("family");
                  }}
                >
                  {routeFamilyFriendly ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                  亲子友好
                </button>
                <button className={routeNoBacktrack ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"} type="button" onClick={() => setRouteNoBacktrack((value) => !value)}>
                  {routeNoBacktrack ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                  不走回头路
                </button>
              </div>
            </div>

            <div className="route-choice-section">
              <span className="route-choice-title">路线主题 <small>（单选）</small></span>
              <div className="route-theme-board" role="group" aria-label="路线主题">
                {[
                  { id: "blessing", label: "祈福", icon: "buddha" as const },
                  { id: "history", label: "历史", icon: "bridge" as const },
                  { id: "family", label: "亲子", icon: "visitor" as const },
                  { id: "photo", label: "拍照", icon: "scenic-camera" as const },
                  { id: "nature", label: "自然", icon: "bodhi-leaf" as const },
                ].map((item) => (
                  <button
                    className={routeTheme === item.id ? "route-theme-card route-theme-card--active" : "route-theme-card"}
                    key={item.id}
                    onClick={() => setRouteTheme(item.id)}
                    type="button"
                  >
                    <ImageIcon name={item.icon} size={26} />
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="route-choice-section">
              <span className="route-choice-title">选择景点 <small>（可多选，至少1个）</small></span>
              <div className="route-scenic-grid">
                {routePreviewAttractions.map((item) => {
                  const selected = mustVisitIds.includes(item.id);
                  return (
                    <button
                      className={selected ? "route-scenic-choice route-scenic-choice--active" : "route-scenic-choice"}
                      key={item.id}
                      onClick={() => (selected ? removeRouteConstraint("must", item.id) : addRouteConstraint("must", item.id))}
                      type="button"
                    >
                      <ImageIcon
                        name={routeAttractionIconName(item.name)}
                        size={28}
                      />
                      {item.name}
                    </button>
                  );
                })}
                {hasMoreRouteAttractions ? (
                  <button className="route-scenic-choice route-scenic-choice--more" onClick={() => setRouteAllAttractionsOpen(true)} type="button">
                    <ImageIcon name="route-path" size={28} />
                    更多景点
                  </button>
                ) : null}
              </div>
            </div>

            <div className="route-choice-section">
              <span className="route-choice-title">时间与节奏</span>
              <div className="route-duration-grid">
                {[
                  { value: 120, label: "2小时内" },
                  { value: 180, label: "3 小时左右" },
                  { value: 240, label: "4小时以上" },
                ].map((item) => (
                  <button className={routeBudget === item.value ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"} key={item.value} onClick={() => setRouteBudget(item.value)} type="button">
                    {routeBudget === item.value ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                    {item.label}
                  </button>
                ))}
                {[
                  { value: "low" as CrowdLevel, label: "舒缓游览" },
                  { value: "medium" as CrowdLevel, label: "适中节奏" },
                  { value: "high" as CrowdLevel, label: "紧凑高效" },
                ].map((item) => (
                  <button className={crowdTolerance === item.value ? "route-choice-chip route-choice-chip--active" : "route-choice-chip"} key={item.value} onClick={() => setCrowdTolerance(item.value)} type="button">
                    {crowdTolerance === item.value ? <CheckCircle2 aria-hidden="true" size={16} /> : null}
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <button className="route-generate-button" disabled={routeLoading} type="submit">
              <ImageIcon name="route-path" size={24} />
              {routeLoading ? "正在生成" : "生成舒适路线"}
            </button>
            <button className="route-reset-button" type="button" onClick={() => void generateRoute()}>
              按当前景点重排
            </button>
          </form>
          )
        ) : (
          <>
            <div className="route-detail-action-row">
              <button className="route-detail-back-button" type="button" onClick={() => setRouteResult(null)}>
                返回路线规划
              </button>
            </div>
            <div className="route-ticket route-ticket--ready">
              <div className="route-ticket__title-row">
                <h3>{routeResult.title}</h3>
                <span>{Math.round(routeResult.estimated_duration_minutes / 60)}小时 | 约5.2公里</span>
              </div>
              <div className="route-ticket__score-row">
                <strong>{routeResult.recommendation_score}</strong>
                <span>/100<br />舒适度评分</span>
                <div className="route-ticket__tags">
                  <em>必去保留</em>
                  <em>{routeResult.crowd_policy.avoid_crowd ? "错峰" : "顺游"}</em>
                  <em>{crowdTolerance === "low" ? "低步行" : crowdTolerance === "high" ? "可排队" : "舒适"}</em>
                </div>
              </div>
              <p>{routePrimaryCrowdText}</p>
              <div className="route-ticket__share">
                <span>根据实时客流为您生成，预计拥挤时段已避开</span>
                <a href={routeResult.share.share_url}>
                  查看地图
                </a>
              </div>
            </div>
          </>
        )}

        {routePreferencesOpen ? (
          <div className="route-constraint-picker route-constraint-picker--sheet" aria-label="全量景点路线约束">
            <div className="route-constraint-picker__header">
              <span className="field-label">景点偏好</span>
              <span>必去优先，避开只作约束说明</span>
            </div>
            <div className="route-theme-grid" aria-label="路线主题">
              {routeThemes.map((theme) => (
                <button
                  className={routeTheme === theme.id ? "route-theme route-theme--active" : "route-theme"}
                  key={theme.id}
                  onClick={() => setRouteTheme(theme.id)}
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
            <label className="field-label" htmlFor="route-constraint-search">
              搜索景点
            </label>
            <input
              className="route-constraint-search"
              id="route-constraint-search"
              onChange={(event) => setRouteConstraintQuery(event.target.value)}
              placeholder="搜香月花街、五灯湖、梵天花海..."
              value={routeConstraintQuery}
            />
            <div className="constraint-selected-groups" aria-label="已选择的路线约束">
              {[
                { kind: "must" as const, label: "必去", ids: mustVisitIds },
                { kind: "optional" as const, label: "可选", ids: optionalAttractionIds },
                { kind: "avoid" as const, label: "避开", ids: avoidAttractionIds },
              ].map((group) => (
                <div className="constraint-selected-group" key={group.kind}>
                  <span>{group.label}</span>
                  {group.ids.length ? (
                    <div className="constraint-selected-chips">
                      {group.ids.map((id) => (
                        <RouteConstraintChip key={`${group.kind}-${id}`} onRemove={() => removeRouteConstraint(group.kind, id)} tone={group.kind}>
                          {attractionById.get(id)?.name || id}
                        </RouteConstraintChip>
                      ))}
                    </div>
                  ) : (
                    <small>未选择</small>
                  )}
                </div>
              ))}
            </div>
            <div className="route-constraint-results" aria-label="景点搜索结果">
              {routeAttractionMatches.map((item) => (
                <div className="route-constraint-row" key={item.id}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>
                      {item.scenic_area}
                      {item.category ? ` · ${item.category}` : ""}
                    </span>
                  </div>
                  <div className="route-constraint-actions">
                    {[
                      { kind: "must" as const, label: "必去" },
                      { kind: "optional" as const, label: "可选" },
                      { kind: "avoid" as const, label: "避开" },
                    ].map((action) => (
                      <button
                        aria-pressed={isConstraintSelected(action.kind, item.id)}
                        className={
                          isConstraintSelected(action.kind, item.id)
                            ? `constraint-action constraint-action--${action.kind} constraint-action--active`
                            : `constraint-action constraint-action--${action.kind}`
                        }
                        key={`${item.id}-${action.kind}`}
                        onClick={() => addRouteConstraint(action.kind, item.id)}
                        type="button"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {routeAttractionMatches.length === 0 ? <p className="empty-state mobile-empty">没有匹配景点，请换一个关键词。</p> : null}
            </div>
          </div>
        ) : null}

        {error ? <p className="inline-error">{error}</p> : null}

        {routeResult ? (
          <div className="route-result route-result--ticketed">
            <section className="route-timeline-card" aria-label="行程安排">
              <div className="route-subtitle-row">
                <strong>行程安排</strong>
                <span>共 {routeResult.stops.length} 站</span>
              </div>
              <div className="route-stop-list route-stop-list--timeline" aria-label="逐站路线">
                {routeResult.stops.map((stop) => (
                  <article className="route-stop route-stop--timeline" key={`${routeResult.id}-${stop.attraction_id}`}>
                    <div className="route-stop__index">{stop.order}</div>
                    <div className="route-stop__body">
                      <div className="route-stop__glyph" aria-hidden="true">
                        <ImageIcon
                          name={
                            stop.name.includes("梵宫")
                              ? "brahma-palace"
                              : stop.name.includes("桥")
                                ? "bridge"
                                : stop.name.includes("九龙")
                                  ? "crowd-wave"
                                  : "buddha"
                          }
                          size={52}
                        />
                      </div>
                      <div className="route-stop__title-row">
                        <div>
                          <strong>{stop.name}</strong>
                          <small>{stop.scenic_area}</small>
                        </div>
                        <span>
                          客流 <em>{crowdLabel(stop.crowd_level).replace("拥挤", "高").replace("适中", "中").replace("舒适", "低")}</em>
                          等待 {stop.wait_minutes}分钟
                        </span>
                      </div>
                      <div className="constraint-badge-row route-stop__badges">
                        <StatusBadge tone={stop.constraint_type === "must_visit" ? "ok" : "neutral"}>
                          {constraintLabel(stop.constraint_type)}
                        </StatusBadge>
                        <StatusBadge tone={stop.crowd_action === "delay" || stop.crowd_action === "keep_with_warning" ? "warning" : "neutral"}>
                          {crowdActionLabel(stop.crowd_action)}
                        </StatusBadge>
                      </div>
                      <p>{stop.focus || stop.reason}</p>
                      <span className="route-stop__duration">停留 {stop.stay_minutes} 分钟{stop.walk_minutes_from_previous ? ` · 步行 ${stop.walk_minutes_from_previous} 分钟` : ""}</span>
                      {stop.operation_note ? <p className="operation-note">{stop.operation_note}</p> : null}
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="decision-trace decision-trace--compact" aria-label="路线决策说明">
              <div className="route-subtitle-row">
                <strong>为什么这样排</strong>
                <button type="button" onClick={() => setRouteEvidenceOpen((value) => !value)}>
                  {routeEvidenceOpen ? "收起依据" : "查看完整依据"}
                </button>
              </div>
              <ul>
                {routeResult.decision_trace.slice(0, routeEvidenceOpen ? routeResult.decision_trace.length : 3).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <div className="score-grid score-grid--compact" aria-label="路线评分拆解">
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
              {operationImpactSummary(routeResult) ? (
                <p className="operation-route-note">
                  <ImageIcon name="event-bell" size={18} />
                  {operationImpactSummary(routeResult)} {(routeResult.operation_policy || routeResult.operation_events_summary)?.caveat}
                </p>
              ) : null}
            </section>
            <div className="route-detail-actions" aria-label="路线操作">
              <button className="route-start-button" type="button" onClick={() => void submitQuestion(routeResult.stops[0]?.narration_question || "开始第一站讲解")}>
                <ImageIcon name="visitor" size={22} />
                开始第一站
              </button>
              <a href={routeResult.share.share_url}>
                <ImageIcon name="qr-handoff" size={22} />
                扫码带走
              </a>
              <button type="button" onClick={() => setRoutePreferencesOpen((value) => !value)}>
                <ImageIcon name="route-path" size={22} />
                调整路线
              </button>
            </div>
          </div>
        ) : null}
      </section>
      ) : null}

      {activeNav === "mine" ? (
      <section className="feedback-panel" aria-label="游客反馈" ref={feedbackPanelRef}>
        <div className="section-title-row">
          <div>
            <h2>我的行程</h2>
            <p>路线小票、游中操作和体验反馈。</p>
          </div>
          <Heart aria-hidden="true" />
        </div>
        {routeResult ? (
          <div className="mobile-route-ticket" aria-label="路线小票">
            <div>
              <span>当前路线</span>
              <strong>{routeResult.title}</strong>
              <small>
                {routeResult.estimated_duration_minutes} 分钟 · {routeResult.stops.length} 站 · 分享码 {routeResult.share.share_code}
              </small>
            </div>
            <div className="mobile-route-ticket__actions">
              <a href={routeResult.share.share_url}>
                <ImageIcon name="qr-handoff" size={20} />
                扫码带走
              </a>
              <button type="button" onClick={() => setActiveNav("guide")}>
                <ImageIcon name="buddha" size={20} />
                听本站讲解
              </button>
              <button type="button" onClick={focusRoutePanel}>
                <ImageIcon name="crowd-wave" size={20} />
                人多换一个
              </button>
            </div>
          </div>
        ) : (
          <div className="mobile-route-ticket mobile-route-ticket--empty">
            <p>还没有路线小票。</p>
            <button type="button" onClick={() => setActiveNav("route")}>
              去路线页生成路线
            </button>
          </div>
        )}
        <div className="section-title-row section-title-row--sub">
          <div>
            <h2>体验反馈</h2>
            <p>本地演示日志，不记录个人身份。</p>
          </div>
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
      ) : null}

      {activeNav !== "guide" ? (
        <button
          aria-label="打开灵境导游"
          className="floating-guide-entry"
          onClick={() => {
            setActiveNav("guide");
            window.setTimeout(() => composerInputRef.current?.focus(), 80);
          }}
          type="button"
        >
          <span className="floating-guide-entry__avatar" aria-hidden="true">
            <ImageIcon name="buddha" size={28} />
          </span>
          <span>问小灵</span>
        </button>
      ) : null}

      <ScenicBottomNav active={activeNav} onSelect={handleScenicNavSelect} />

      <div className="mobile-mode-note">
        <Layers aria-hidden="true" size={16} />
        当前为 mock 模式：前端只调用后端 API，不接触模型厂商 Key。
      </div>
    </PageShell>
  );
}
