export type Attraction = {
  id: string;
  attraction_id?: string;
  scenic_area: string;
  name: string;
  category?: string;
  summary?: string;
  description?: string;
  visitor_tips?: string[];
  tags?: string[];
  source_file?: string;
};

export type Source = {
  chunk_id: string;
  title: string;
  source_file: string;
  source_section: string;
  attraction_id: string | null;
  score: number;
};

export type QAResponse = {
  answer: string;
  type?: "qa" | "scenic_area_intro" | "recommendation" | "comparison" | "crowd_status" | "route" | "clarification" | "out_of_scope" | string;
  sources: Source[];
  mode: string;
  latency_ms: number;
  understanding?: QueryUnderstandingResult;
  recommendations?: RecommendationItem[];
  scenic_area_intro?: ScenicAreaIntro;
  comparison?: ComparisonResult;
  crowd_status?: CrowdStatusResult;
  suggested_questions?: string[];
};

export type QueryUnderstandingDomain = "scenic_guide" | "route_planning" | "recommendation" | "operations" | "out_of_scope" | "unclear";

export type QueryUnderstandingIntent =
  | "fact_qa"
  | "attraction_intro"
  | "scenic_area_intro"
  | "interest_recommendation"
  | "attraction_compare"
  | "crowd_status"
  | "operation_status"
  | "route_request"
  | "route_replan"
  | "unknown";

export type QueryUnderstandingEntity = {
  type: "attraction" | "scenic_area";
  id: string;
  name: string;
  matched_text: string;
};

export type QueryUnderstandingHandler =
  | "qa_rag"
  | "scenic_area_intro"
  | "interest_recommendation"
  | "comparison"
  | "crowd_status"
  | "route_planner"
  | "clarification"
  | "out_of_scope";

export type QueryUnderstandingSlots = {
  scenic_area: string | null;
  interests: string[];
  group_type: "family" | "elderly" | "friends" | null;
  time_budget_minutes: number | null;
  compare_targets: QueryUnderstandingEntity[];
};

export type QueryUnderstandingResult = {
  domain: QueryUnderstandingDomain;
  intent: QueryUnderstandingIntent;
  entities: QueryUnderstandingEntity[];
  slots?: QueryUnderstandingSlots;
  confidence: number;
  should_retrieve: boolean;
  should_route: boolean;
  handler?: QueryUnderstandingHandler;
  needs_clarification: boolean;
  clarification_question: string | null;
  clarification_options: string[];
  reasons: string[];
  mode: "mock_rule_gate" | string;
};

export type RecommendationItem = {
  attraction_id: string;
  name: string;
  scenic_area: string;
  score: number;
  reason: string;
  matched_interests: string[];
  suggested_question: string;
};

export type ScenicAreaIntro = {
  title: string;
  summary: string;
  highlights: string[];
  suggested_questions: string[];
  source: string;
  disclaimer: string;
  sections?: Array<{
    scenic_area: string;
    attraction_count: number;
    highlights: string[];
    suggested_questions: string[];
  }>;
};

export type ComparisonResult = {
  compare_targets: Array<{ type: string; id: string; name: string; score: number; strengths: string[] }>;
  dimensions: string[];
  recommendation: string;
  reasons: string[];
  suggested_next_questions: string[];
};

export type CrowdStatusResult = {
  items: Array<{
    attraction_id: string;
    name: string;
    scenic_area?: string;
    crowd_level: CrowdLevel;
    crowd_score: number;
    wait_minutes: number;
    source: string;
    note: string;
  }>;
  operation_events: OperationEvent[];
  source_note: string;
};

export type GuideQueryResponse = QAResponse & {
  items?: RecommendationItem[];
  route?: RouteRecommendation | null;
};

export type VisionCandidate = {
  attraction: Attraction;
  confidence: number;
  reason: string;
  match_signals: string[];
};

export type VisionResponse = {
  matched_attraction: Attraction | null;
  confidence: number;
  candidates: VisionCandidate[];
  needs_confirmation: boolean;
  confirmation_reason: string;
  selected_attraction_id: string | null;
  explanation: string;
  suggested_questions: string[];
  mode: string;
  latency_ms: number;
};

export type CrowdLevel = "low" | "medium" | "high";

export type CrowdSnapshotItem = {
  attraction_id: string;
  name: string;
  scenic_area?: string;
  crowd_level: CrowdLevel;
  crowd_score: number;
  wait_minutes: number;
  source: "mock_simulation";
  updated_at: string;
  note: string;
};

export type CrowdSnapshotResponse = {
  items: CrowdSnapshotItem[];
  count: number;
  source: "mock_simulation";
  updated_at: string;
  caveat: string;
};

export type OperationEventType = "crowd" | "closed" | "show" | "recommendation";
export type OperationEventSeverity = "info" | "warning" | "critical";
export type OperationEventSource = "manual_admin" | "mock_simulation";

export type OperationEvent = {
  id: string;
  attraction_id: string;
  attraction_name?: string;
  scenic_area?: string;
  event_type: OperationEventType;
  severity: OperationEventSeverity;
  message: string;
  start_at: string;
  end_at: string;
  source: OperationEventSource;
  created_by: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type OperationEventCreateRequest = {
  attraction_id: string;
  event_type: OperationEventType;
  severity: OperationEventSeverity;
  message: string;
  start_at?: string;
  end_at?: string;
  source?: OperationEventSource;
  created_by?: string;
  active?: boolean;
};

export type OperationEventUpdateRequest = Partial<OperationEventCreateRequest> & {
  active?: boolean;
};

export type OperationEventsResponse = {
  items: OperationEvent[];
  count: number;
  mode: string;
  source_note: string;
};

export type KnowledgeGapTrigger = "low_confidence" | "no_source" | "negative_feedback" | "manual";
export type KnowledgeGapStatus = "open" | "drafted" | "resolved" | "ignored";

export type KnowledgeGap = {
  id: string;
  query: string;
  trigger_type: KnowledgeGapTrigger;
  matched_sources: Source[];
  confidence: number | null;
  suggested_faq: string | null;
  status: KnowledgeGapStatus;
  eval_case_id: string | null;
  created_at: string;
  updated_at: string;
  deduped?: boolean;
};

export type KnowledgeGapsResponse = {
  items: KnowledgeGap[];
  count: number;
  mode: string;
  source_note: string;
};

export type KnowledgeGapEvalResponse = {
  gap: KnowledgeGap;
  eval_case_id: string;
  created: boolean;
};

export type EvalReportStatus = "pass" | "fail" | "missing";

export type EvalFailureSample = {
  id: string;
  message: string;
  expected?: unknown;
  actual?: unknown;
  mismatches?: unknown;
  [key: string]: unknown;
};

export type EvalReportItem = {
  id: string;
  title: string;
  status: EvalReportStatus;
  total: number;
  passed: number;
  failed: number;
  accuracy: number | null;
  avg_latency_ms: number | null;
  generated_at: string | null;
  mode: string;
  summary: string;
  failure_samples: EvalFailureSample[];
};

export type EvalDerivedMetric = {
  value: number | null;
  passed: number | null;
  total: number | null;
  reason: string | null;
};

export type EvalReportsOverview = {
  reports: EvalReportItem[];
  overall: {
    total_reports: number;
    available_reports: number;
    passing_reports: number;
    total_cases: number;
    passed_cases: number;
    failed_cases: number;
    overall_accuracy: number | null;
    latest_generated_at: string | null;
  };
  derived_metrics: {
    must_visit_preservation_rate: EvalDerivedMetric;
    crowd_explanation_rate: EvalDerivedMetric;
    clarification_pass_rate: EvalDerivedMetric;
    knowledge_gap_workflow_rate: EvalDerivedMetric;
  };
  source_note: string;
  mode: string;
};

export type RouteStop = {
  order: number;
  attraction_id: string;
  name: string;
  scenic_area: string;
  category?: string;
  tags?: string[];
  stay_minutes: number;
  walk_minutes_from_previous: number;
  focus: string;
  reason: string;
  narration_question: string;
  crowd_level: CrowdLevel;
  crowd_score: number;
  wait_minutes: number;
  crowd_note: string;
  crowd_source?: string;
  operation_events?: OperationEvent[];
  operation_note?: string | null;
  constraint_type?: "must_visit" | "optional" | "recommended" | "alternative";
  constraint_reason?: string;
  crowd_action?: "keep" | "delay" | "replace" | "avoid" | "skip" | "keep_with_warning";
  decision_reason?: string;
  selection_source?: "must_visit" | "template_seed" | "full_pool" | "optional_boost" | "start_context" | string;
  profile_match_reason?: string;
  theme_score?: number;
  topology_line_id?: string | null;
  topology_line_name?: string | null;
  topology_node_id?: string | null;
  topology_order_index?: number | null;
  walking_minutes_to_next?: number | null;
  next_attraction_id?: string | null;
  transport_hint?: string | null;
  backtrack_risk?: "low" | "medium" | "high" | "transfer" | string | null;
  topology_note?: string | null;
  smoothness_reason?: string | null;
  route_profile_scores?: {
    family_score?: number;
    history_score?: number;
    nature_score?: number;
    blessing_score?: number;
    photo_score?: number;
    route_priority?: number;
    default_stay_minutes?: number;
    is_core_landmark?: boolean;
  };
};

export type RouteConstraintConflict = {
  code: string;
  attraction_id?: string;
  name?: string;
  message: string;
  options?: string[];
};

export type RouteConstraintSummary = {
  priority: string[];
  must_visit_attraction_ids: string[];
  optional_attraction_ids: string[];
  avoid_attraction_ids: string[];
  invalid_attraction_ids: string[];
  conflict_attraction_ids: string[];
  start_context_only: boolean;
  skipped_avoid_attraction_ids: string[];
  optional_not_selected_attraction_ids: string[];
  full_pool_selected_attraction_ids?: string[];
  full_pool_not_selected_attraction_ids?: string[];
  trimmed_attraction_ids: string[];
  warning: string | null;
  notes: string[];
};

export type RouteOperationPolicy = {
  active_event_count: number;
  affected_event_count: number;
  skipped_closed_attraction_ids: string[];
  event_types: Record<string, number>;
  sources: string[];
  caveat: string;
  affected_events: OperationEvent[];
};

export type RouteTopology = {
  source: string;
  source_note: string;
  line_ids: string[];
  line_names: string[];
  route_smoothness_score: number;
  total_walking_minutes: number;
  backtrack_count: number;
  sightseeing_bus_suggestion: string | null;
  topology_explanation: string[];
};

export type RouteRecommendation = {
  id: string;
  title: string;
  theme: string;
  theme_label: string;
  summary: string;
  suitable_for: string[];
  constraints?: {
    must_visit_attraction_ids: string[];
    optional_attraction_ids: string[];
    avoid_attraction_ids: string[];
    rules?: Record<string, unknown>;
  };
  constraint_summary?: RouteConstraintSummary;
  constraint_conflicts?: RouteConstraintConflict[];
  estimated_duration_minutes: number;
  time_budget_minutes: number;
  recommendation_score: number;
  score_breakdown: {
    theme_match: number;
    time_fit: number;
    group_fit: number;
    crowd_comfort: number;
    stop_quality: number;
  };
  decision_trace: string[];
  route_topology?: RouteTopology;
  operation_policy?: RouteOperationPolicy;
  operation_events_summary?: RouteOperationPolicy;
  crowd_policy: {
    avoid_crowd: boolean;
    crowd_tolerance: CrowdLevel;
    source: "mock_simulation";
    caveat: string;
  };
  stops: RouteStop[];
  assumptions: string[];
  performance_tips: string[];
  share: {
    share_code: string;
    share_url: string;
    qr_payload: string;
    expires_at: string;
    expires_in_minutes: number;
  };
  mode: string;
  latency_ms: number;
};

export type RouteIntentResult = {
  intent: "route_recommend" | "route_replan" | "explanation_style" | "clarification" | "unknown";
  operation:
    | "shorten"
    | "avoid_crowd"
    | "less_walking"
    | "more_photo"
    | "more_history"
    | "start_here"
    | "set_must_visit"
    | "remove_must_visit"
    | "none";
  theme: string | null;
  time_budget_minutes: number | null;
  group_type: string | null;
  intensity: string | null;
  interests: string[];
  must_visit_attraction_ids: string[];
  optional_attraction_ids: string[];
  avoid_attraction_ids: string[];
  avoid_crowd: boolean;
  crowd_tolerance: CrowdLevel;
  style: "child" | "deep_history" | "short_30s" | "photo" | "comfort" | "default";
  intent_confidence: number;
  needs_clarification: boolean;
  clarification_question: string | null;
  clarification_options: string[];
  mode: string;
  metadata?: Record<string, unknown>;
};

export type RouteMemory = {
  session_id: string;
  preferences: {
    theme?: string | null;
    time_budget_minutes?: number;
    group_type?: string | null;
    intensity?: string | null;
    interests?: string[];
    avoid_crowd?: boolean;
    crowd_tolerance?: CrowdLevel;
    start_attraction_id?: string | null;
  };
  constraints: {
    must_visit_attraction_ids: string[];
    optional_attraction_ids: string[];
    avoid_attraction_ids: string[];
  };
  current_route_id?: string | null;
  current_stop_index: number;
  removed_stops: string[];
  delayed_stops: string[];
  high_crowd_stops: string[];
  last_operation?: string | null;
  last_reason?: string | null;
  turn_count: number;
};

export type RouteConversationResponse = {
  session_id: string;
  intent: RouteIntentResult;
  memory: RouteMemory;
  route: RouteRecommendation | null;
  reply: string;
  confidence: number;
  needs_clarification: boolean;
  clarification_options: string[];
  understanding?: QueryUnderstandingResult;
  mode: string;
};

export type FeedbackRequest = {
  channel: "mobile" | "kiosk" | "share" | "admin" | "api";
  route_id?: string;
  attraction_id?: string;
  rating: number;
  tags: string[];
  comment?: string;
};

export type FeedbackResponse = {
  id: string;
  status: string;
  created_at: string;
};

export type AnalyticsOverview = {
  service_count: number;
  qa_count: number;
  vision_count: number;
  route_count: number;
  share_open_count: number;
  feedback_count: number;
  knowledge_gap_count: number;
  open_knowledge_gap_count: number;
  drafted_knowledge_gap_count: number;
  average_rating: number | null;
  popular_questions: Array<{ question: string; count: number }>;
  low_confidence_questions: Array<{ question: string; answer_preview?: string; confidence?: number; created_at: string }>;
  route_theme_distribution: Array<{ theme: string; theme_label: string; count: number }>;
  crowd_avoidance_count: number;
  high_crowd_attractions: Array<{
    attraction_id: string;
    name: string;
    scenic_area?: string;
    crowd_level: CrowdLevel;
    crowd_score: number;
    wait_minutes: number;
    source: string;
  }>;
  feedback_tags: Array<{ tag: string; count: number }>;
  recent_events: Array<{
    id: string;
    event_type: string;
    channel: string;
    question?: string | null;
    answer_preview?: string | null;
    attraction_id?: string | null;
    route_id?: string | null;
    share_code?: string | null;
    confidence?: number | null;
    success: boolean;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
  source_note: string;
  mode: string;
};

type ApiErrorPayload = {
  code?: string;
  message?: string;
  cause?: string;
  fix?: string;
};

export class ApiClientError extends Error {
  code?: string;
  causeText?: string;
  fix?: string;

  constructor(payload: ApiErrorPayload, fallback: string) {
    super(payload.message || payload.cause || fallback);
    this.name = "ApiClientError";
    this.code = payload.code;
    this.causeText = payload.cause;
    this.fix = payload.fix;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = {};
    }
    throw new ApiClientError(payload, `请求失败：${response.status}`);
  }

  return (await response.json()) as T;
}

export async function fetchAttractions(): Promise<Attraction[]> {
  const payload = await requestJson<{ items: Attraction[] }>("/api/attractions");
  return payload.items;
}

export async function getCrowdSnapshot(): Promise<CrowdSnapshotResponse> {
  return requestJson<CrowdSnapshotResponse>("/api/crowd/snapshot");
}

export async function getOperationEvents(attractionId?: string): Promise<OperationEventsResponse> {
  const params = new URLSearchParams();
  if (attractionId) {
    params.set("attraction_id", attractionId);
  }
  const query = params.toString();
  return requestJson<OperationEventsResponse>(`/api/operations/events${query ? `?${query}` : ""}`);
}

export async function getAdminOperationEvents(activeOnly = false): Promise<OperationEventsResponse> {
  const params = new URLSearchParams({ active_only: String(activeOnly) });
  return requestJson<OperationEventsResponse>(`/api/admin/operations/events?${params.toString()}`);
}

export async function createOperationEvent(payload: OperationEventCreateRequest): Promise<OperationEvent> {
  return requestJson<OperationEvent>("/api/admin/operations/events", {
    body: JSON.stringify(payload),
    method: "POST",
  });
}

export async function updateOperationEvent(eventId: string, payload: OperationEventUpdateRequest): Promise<OperationEvent> {
  return requestJson<OperationEvent>(`/api/admin/operations/events/${encodeURIComponent(eventId)}`, {
    body: JSON.stringify(payload),
    method: "PATCH",
  });
}

export async function getKnowledgeGaps(status?: KnowledgeGapStatus): Promise<KnowledgeGapsResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  const query = params.toString();
  return requestJson<KnowledgeGapsResponse>(`/api/admin/knowledge/gaps${query ? `?${query}` : ""}`);
}

export async function draftKnowledgeGapFaq(gapId: string): Promise<KnowledgeGap> {
  return requestJson<KnowledgeGap>(`/api/admin/knowledge/gaps/${encodeURIComponent(gapId)}/draft-faq`, {
    method: "POST",
  });
}

export async function updateKnowledgeGapStatus(gapId: string, status: KnowledgeGapStatus): Promise<KnowledgeGap> {
  return requestJson<KnowledgeGap>(`/api/admin/knowledge/gaps/${encodeURIComponent(gapId)}`, {
    body: JSON.stringify({ status }),
    method: "PATCH",
  });
}

export async function addKnowledgeGapToEval(gapId: string): Promise<KnowledgeGapEvalResponse> {
  return requestJson<KnowledgeGapEvalResponse>(`/api/admin/knowledge/gaps/${encodeURIComponent(gapId)}/add-eval`, {
    method: "POST",
  });
}

export async function getEvalReportsOverview(): Promise<EvalReportsOverview> {
  return requestJson<EvalReportsOverview>("/api/admin/evals/overview");
}

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return requestJson<AnalyticsOverview>("/api/analytics/overview");
}

export async function askQuestion({
  attractionId,
  question,
}: {
  attractionId?: string;
  question: string;
}): Promise<QAResponse> {
  return requestJson<QAResponse>("/api/qa", {
    body: JSON.stringify({
      attraction_id: attractionId || null,
      question,
      top_k: 5,
      channel: "mobile",
      visitor_profile: {
        group_type: "family",
        time_budget_minutes: 120,
        interests: ["佛教文化", "拍照打卡"],
      },
    }),
    method: "POST",
  });
}

export async function guideQuery({
  message,
  selectedAttractionId,
}: {
  message: string;
  selectedAttractionId?: string;
}): Promise<GuideQueryResponse> {
  return requestJson<GuideQueryResponse>("/api/guide/query", {
    body: JSON.stringify({
      message,
      selected_attraction_id: selectedAttractionId || null,
      top_k: 5,
      channel: "mobile",
      visitor_profile: {
        group_type: "family",
        time_budget_minutes: 120,
        interests: ["佛教文化", "拍照打卡"],
      },
    }),
    method: "POST",
  });
}

export async function understandQuery({
  message,
  selectedAttractionId,
  currentRouteId,
}: {
  message: string;
  selectedAttractionId?: string;
  currentRouteId?: string;
}): Promise<QueryUnderstandingResult> {
  return requestJson<QueryUnderstandingResult>("/api/query/understand", {
    body: JSON.stringify({
      message,
      selected_attraction_id: selectedAttractionId || null,
      current_route_id: currentRouteId || null,
      channel: "mobile",
    }),
    method: "POST",
  });
}

export async function recognizeImage({
  file,
  hint,
  textHint,
}: {
  file: File;
  hint?: string;
  textHint?: string;
}): Promise<VisionResponse> {
  const body = new FormData();
  body.append("file", file);
  if (hint) {
    body.append("hint", hint);
  }
  if (textHint) {
    body.append("text_hint", textHint);
  }
  body.append("channel", "mobile");
  return requestJson<VisionResponse>("/api/vision/recognize", {
    body,
    method: "POST",
  });
}

export async function recommendRoute({
  theme,
  timeBudgetMinutes,
  groupType,
  intensity,
  interests,
  startAttractionId,
  avoidCrowd = true,
  crowdTolerance = "medium",
  mustVisitAttractionIds,
  optionalAttractionIds,
  avoidAttractionIds,
  channel = "mobile",
}: {
  theme?: string;
  timeBudgetMinutes?: number;
  groupType?: string;
  intensity?: string;
  interests?: string[];
  startAttractionId?: string;
  avoidCrowd?: boolean;
  crowdTolerance?: CrowdLevel;
  mustVisitAttractionIds?: string[];
  optionalAttractionIds?: string[];
  avoidAttractionIds?: string[];
  channel?: "mobile" | "kiosk" | "share" | "admin" | "api";
}): Promise<RouteRecommendation> {
  return requestJson<RouteRecommendation>("/api/routes/recommend", {
    body: JSON.stringify({
      theme,
      time_budget_minutes: timeBudgetMinutes,
      group_type: groupType,
      intensity,
      interests,
      start_attraction_id: startAttractionId || null,
      avoid_crowd: avoidCrowd,
      crowd_tolerance: crowdTolerance,
      must_visit_attraction_ids: mustVisitAttractionIds || [],
      optional_attraction_ids: optionalAttractionIds || [],
      avoid_attraction_ids: avoidAttractionIds || [],
      channel,
    }),
    method: "POST",
  });
}

export async function parseRouteIntent({
  message,
  selectedAttractionId,
  currentRouteId,
}: {
  message: string;
  selectedAttractionId?: string;
  currentRouteId?: string;
}): Promise<RouteIntentResult> {
  return requestJson<RouteIntentResult>("/api/routes/intent", {
    body: JSON.stringify({
      message,
      selected_attraction_id: selectedAttractionId || null,
      current_route_id: currentRouteId || null,
      channel: "mobile",
    }),
    method: "POST",
  });
}

export async function sendRouteConversation({
  message,
  sessionId,
  currentRouteId,
  selectedAttractionId,
}: {
  message: string;
  sessionId?: string;
  currentRouteId?: string;
  selectedAttractionId?: string;
}): Promise<RouteConversationResponse> {
  return requestJson<RouteConversationResponse>("/api/routes/conversation", {
    body: JSON.stringify({
      message,
      session_id: sessionId || null,
      current_route_id: currentRouteId || null,
      selected_attraction_id: selectedAttractionId || null,
      channel: "mobile",
    }),
    method: "POST",
  });
}

export async function getRouteShare(routeId: string, code: string): Promise<RouteRecommendation> {
  const params = new URLSearchParams({ code });
  return requestJson<RouteRecommendation>(`/api/routes/${encodeURIComponent(routeId)}/share?${params.toString()}`);
}

export async function submitFeedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
  return requestJson<FeedbackResponse>("/api/feedback", {
    body: JSON.stringify(payload),
    method: "POST",
  });
}
