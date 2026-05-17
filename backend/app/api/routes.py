import urllib.parse
from typing import Any

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, Field

from app.core.errors import ApiError
from app.core.config import get_settings
from app.providers import ProviderStatus, get_provider_status
from app.services.analytics_service import analytics_overview, record_feedback, record_interaction_event
from app.services.avatar_clip_player import play_avatar_clip
from app.services.avatar_speaker import enqueue_avatar_speech, get_avatar_status
from app.services.avatar_webrtc import proxy_avatar_webrtc_offer
from app.services.content_service import (
    get_attraction_or_error,
    get_attractions,
    get_behavior_summary_or_error,
    get_chunks,
)
from app.services.crowd_service import get_crowd_snapshot
from app.services.operation_service import (
    create_operation_event,
    list_operation_events,
    update_operation_event,
)
from app.services.knowledge_gap_service import (
    add_gap_to_eval,
    create_knowledge_gap,
    generate_faq_draft,
    list_knowledge_gaps,
    safe_record_knowledge_gap,
    update_knowledge_gap_status,
)
from app.services.eval_report_service import eval_reports_overview
from app.services.qa_service import answer_question
from app.services.query_understanding_service import build_gate_answer, understand_query
from app.services.route_intent_service import parse_route_intent
from app.services.route_memory_service import apply_intent_to_memory, get_route_memory, update_memory_after_route
from app.services.route_service import (
    CONSTRAINT_CLARIFICATION_OPTIONS,
    detect_constraint_conflicts,
    get_route_share,
    normalize_route_constraints,
    recommend_route,
    route_theme_options,
)
from app.services.vision_service import recognize_image_mock

router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str


class ProviderStatusResponse(BaseModel):
    llm: ProviderStatus
    embedding: ProviderStatus
    vlm: ProviderStatus
    tts: ProviderStatus


class QARequest(BaseModel):
    question: str
    attraction_id: str | None = None
    visitor_profile: dict[str, Any] | None = None
    top_k: int = 5
    channel: str = "mobile"


class RouteRecommendRequest(BaseModel):
    theme: str | None = None
    time_budget_minutes: int | None = 240
    group_type: str | None = None
    intensity: str | None = None
    interests: list[str] | None = None
    start_attraction_id: str | None = None
    avoid_crowd: bool = True
    crowd_tolerance: str = "medium"
    must_visit_attraction_ids: list[str] | None = None
    optional_attraction_ids: list[str] | None = None
    avoid_attraction_ids: list[str] | None = None
    channel: str = "mobile"


class RouteIntentRequest(BaseModel):
    message: str
    selected_attraction_id: str | None = None
    current_route_id: str | None = None
    memory: dict[str, Any] | None = None
    channel: str = "mobile"


class RouteConversationRequest(BaseModel):
    message: str
    session_id: str | None = None
    current_route_id: str | None = None
    selected_attraction_id: str | None = None
    must_visit_attraction_ids: list[str] | None = None
    optional_attraction_ids: list[str] | None = None
    avoid_attraction_ids: list[str] | None = None
    channel: str = "mobile"


class QueryUnderstandRequest(BaseModel):
    message: str
    selected_attraction_id: str | None = None
    current_route_id: str | None = None
    channel: str = "mobile"


class GuideQueryRequest(BaseModel):
    message: str
    selected_attraction_id: str | None = None
    visitor_profile: dict[str, Any] | None = None
    top_k: int = 5
    channel: str = "mobile"


class FeedbackRequest(BaseModel):
    channel: str = "mobile"
    route_id: str | None = None
    attraction_id: str | None = None
    rating: int
    tags: list[str] = []
    comment: str | None = None


class OperationEventCreateRequest(BaseModel):
    attraction_id: str
    event_type: str
    severity: str = "info"
    message: str
    start_at: str | None = None
    end_at: str | None = None
    source: str = "manual_admin"
    created_by: str = "admin"
    active: bool = True


class OperationEventUpdateRequest(BaseModel):
    attraction_id: str | None = None
    event_type: str | None = None
    severity: str | None = None
    message: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    source: str | None = None
    created_by: str | None = None
    active: bool | None = None


class KnowledgeGapCreateRequest(BaseModel):
    query: str
    trigger_type: str = "manual"
    matched_sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = None
    suggested_faq: str | None = None
    status: str = "open"


class KnowledgeGapUpdateRequest(BaseModel):
    status: str | None = None


class AvatarSpeakRequest(BaseModel):
    text: str
    emotion: str = "happy"
    source: str = "system"
    interrupt: bool = True


class AvatarPlayClipRequest(BaseModel):
    clip_id: str
    source: str = "demo"
    interrupt: bool = True


class AvatarWebrtcOfferRequest(BaseModel):
    sdp: str | None = None
    type: str
    webrtc_id: str | None = None
    client_id: str | None = None
    candidate: dict[str, Any] | None = None


def _dump_model(payload: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=exclude_unset)


def _merge_unique(current: list[str], incoming: list[str]) -> list[str]:
    result = list(current)
    for item in incoming:
        if item and item not in result:
            result.append(item)
    return result


def _remove_many(current: list[str], values: list[str]) -> list[str]:
    remove = set(values)
    return [item for item in current if item not in remove]


def _preview_route_constraints(memory: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    constraints = memory.get("constraints", {})
    must_visit = list(constraints.get("must_visit_attraction_ids", []))
    optional = list(constraints.get("optional_attraction_ids", []))
    avoid = list(constraints.get("avoid_attraction_ids", []))
    operation = intent.get("operation") or "none"
    if operation == "remove_must_visit":
        remove_ids = intent.get("avoid_attraction_ids") or []
        must_visit = _remove_many(must_visit, remove_ids)
        optional = _remove_many(optional, remove_ids)
        avoid = _merge_unique(avoid, remove_ids)
    else:
        must_visit = _merge_unique(must_visit, intent.get("must_visit_attraction_ids") or [])
        optional = _merge_unique(optional, intent.get("optional_attraction_ids") or [])
        avoid = _merge_unique(avoid, intent.get("avoid_attraction_ids") or [])
    return normalize_route_constraints(
        must_visit_attraction_ids=must_visit,
        optional_attraction_ids=optional,
        avoid_attraction_ids=avoid,
        start_attraction_id=(memory.get("preferences") or {}).get("start_attraction_id"),
    )


def _merge_route_constraint_payload(intent: dict[str, Any], payload: RouteConversationRequest) -> dict[str, Any]:
    return {
        **intent,
        "must_visit_attraction_ids": _merge_unique(
            list(intent.get("must_visit_attraction_ids") or []),
            payload.must_visit_attraction_ids or [],
        ),
        "optional_attraction_ids": _merge_unique(
            list(intent.get("optional_attraction_ids") or []),
            payload.optional_attraction_ids or [],
        ),
        "avoid_attraction_ids": _merge_unique(
            list(intent.get("avoid_attraction_ids") or []),
            payload.avoid_attraction_ids or [],
        ),
    }


def _route_intent_from_understanding(understanding: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": "clarification" if understanding.get("needs_clarification") else "unknown",
        "operation": "none",
        "theme": None,
        "time_budget_minutes": None,
        "group_type": None,
        "intensity": None,
        "interests": [],
        "must_visit_attraction_ids": [],
        "optional_attraction_ids": [],
        "avoid_attraction_ids": [],
        "avoid_crowd": False,
        "crowd_tolerance": "medium",
        "style": "default",
        "intent_confidence": understanding.get("confidence", 0),
        "needs_clarification": bool(understanding.get("needs_clarification")),
        "clarification_question": understanding.get("clarification_question"),
        "clarification_options": understanding.get("clarification_options", []),
        "mode": "mock_rule_gate",
        "metadata": {"query_understanding": understanding},
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        mode=settings.mode,
    )


@router.get("/provider/status", response_model=ProviderStatusResponse)
def provider_status() -> dict[str, ProviderStatus]:
    return get_provider_status()


@router.post("/avatar/speak")
def avatar_speak(payload: AvatarSpeakRequest) -> dict[str, object]:
    return enqueue_avatar_speech(
        text=payload.text,
        emotion=payload.emotion,
        source=payload.source,
        interrupt=payload.interrupt,
    )


@router.post("/avatar/play-clip")
def avatar_play_clip(payload: AvatarPlayClipRequest) -> dict[str, object]:
    return play_avatar_clip(
        clip_id=payload.clip_id,
        source=payload.source,
        interrupt=payload.interrupt,
    )


@router.get("/avatar/status")
def avatar_status() -> dict[str, object]:
    return get_avatar_status()


@router.post("/avatar/webrtc/offer")
def avatar_webrtc_offer(payload: AvatarWebrtcOfferRequest) -> dict[str, object]:
    return proxy_avatar_webrtc_offer(_dump_model(payload, exclude_unset=True))


@router.get("/attractions")
def attractions() -> dict[str, object]:
    items = get_attractions()
    return {"items": items, "count": len(items)}


@router.get("/attractions/{attraction_id}")
def attraction_detail(attraction_id: str) -> dict:
    return get_attraction_or_error(attraction_id)


@router.get("/knowledge/chunks")
def knowledge_chunks(attraction_id: str | None = None) -> dict[str, object]:
    items = get_chunks(attraction_id)
    return {"items": items, "count": len(items)}


@router.get("/analytics/behavior-summary")
def behavior_summary() -> dict:
    return get_behavior_summary_or_error()


@router.get("/analytics/overview")
def analytics() -> dict[str, object]:
    return analytics_overview()


@router.post("/query/understand")
def query_understand(payload: QueryUnderstandRequest) -> dict[str, object]:
    message = payload.message.strip()
    if not message:
        raise ApiError(
            code="EMPTY_QUERY",
            message="请先输入一个问题或路线需求。",
            cause="POST /api/query/understand received an empty message.",
            fix="在 message 字段中传入游客文本。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return understand_query(
        message,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id,
    )


@router.post("/guide/query")
def guide_query(payload: GuideQueryRequest) -> dict[str, object]:
    message = payload.message.strip()
    if not message:
        raise ApiError(
            code="EMPTY_GUIDE_QUERY",
            message="请先输入一个导览问题或路线需求。",
            cause="POST /api/guide/query received an empty message.",
            fix="在 message 字段中传入游客自然语言问题。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    result = answer_question(
        question=message,
        attraction_id=payload.selected_attraction_id,
        visitor_profile=payload.visitor_profile,
        top_k=max(1, min(payload.top_k, 10)),
    )
    return {
        "answer": result.get("answer"),
        "type": result.get("type") or "qa",
        "understanding": result.get("understanding"),
        "sources": result.get("sources", []),
        "items": result.get("recommendations", []),
        "recommendations": result.get("recommendations", []),
        "scenic_area_intro": result.get("scenic_area_intro"),
        "comparison": result.get("comparison"),
        "crowd_status": result.get("crowd_status"),
        "route": None,
        "suggested_questions": result.get("suggested_questions", []),
        "mode": result.get("mode") or "mock",
        "latency_ms": result.get("latency_ms", 0),
    }


@router.post("/qa")
def qa(payload: QARequest) -> dict[str, object]:
    question = payload.question.strip()
    if not question:
        raise ApiError(
            code="EMPTY_QUESTION",
            message="请先输入一个问题。",
            cause="POST /api/qa received an empty question.",
            fix="在 question 字段中传入游客想问的景点、文化或游览问题。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    top_k = max(1, min(payload.top_k, 10))
    result = answer_question(
        question=question,
        attraction_id=payload.attraction_id,
        visitor_profile=payload.visitor_profile,
        top_k=top_k,
    )
    source_scores = [float(source.get("score") or 0) for source in result.get("sources", [])]
    confidence = min(1.0, max(source_scores) / 4.0) if source_scores else 0.0
    result_type = str(result.get("type") or "qa")
    success = bool(result.get("sources")) or result_type in {"scenic_area_intro", "recommendation", "comparison", "crowd_status"}
    record_interaction_event(
        event_type="qa",
        channel=payload.channel,
        question=question,
        answer_preview=str(result.get("answer") or ""),
        attraction_id=payload.attraction_id,
        confidence=round(confidence, 4),
        success=success,
        metadata={
            "source_count": len(result.get("sources", [])),
            "fallback": len(result.get("sources", [])) == 0 and result_type in {"qa", "out_of_scope", "clarification"},
            "latency_ms": result.get("latency_ms"),
            "mode": result.get("mode"),
            "type": result_type,
            "understanding": result.get("understanding"),
            "understanding_domain": (result.get("understanding") or {}).get("domain")
            if isinstance(result.get("understanding"), dict)
            else None,
        },
    )
    sources = result.get("sources", [])
    if not sources and result_type in {"qa", "out_of_scope", "clarification"}:
        safe_record_knowledge_gap(
            query=question,
            trigger_type="no_source",
            matched_sources=[],
            confidence=confidence,
        )
    elif confidence < 0.35:
        safe_record_knowledge_gap(
            query=question,
            trigger_type="low_confidence",
            matched_sources=sources if isinstance(sources, list) else [],
            confidence=confidence,
        )
    return result


@router.get("/routes/themes")
def route_themes() -> dict[str, object]:
    items = route_theme_options()
    return {"items": items, "count": len(items)}


@router.get("/crowd/snapshot")
def crowd_snapshot() -> dict[str, object]:
    return get_crowd_snapshot()


@router.get("/operations/events")
def operation_events(attraction_id: str | None = None) -> dict[str, object]:
    items = list_operation_events(active_only=True, attraction_id=attraction_id)
    return {
        "items": items,
        "count": len(items),
        "mode": "mock",
        "source_note": "运营事件来自 manual_admin / mock_simulation 演示配置，不代表真实硬件客流或实时设备数据。",
    }


@router.get("/admin/operations/events")
def admin_operation_events(active_only: bool = Query(default=False)) -> dict[str, object]:
    items = list_operation_events(active_only=active_only)
    return {
        "items": items,
        "count": len(items),
        "mode": "mock",
        "source_note": "运营事件控制台为本地演示配置，事件来源仅 manual_admin / mock_simulation。",
    }


@router.post("/admin/operations/events", status_code=status.HTTP_201_CREATED)
def admin_create_operation_event(payload: OperationEventCreateRequest) -> dict[str, object]:
    return create_operation_event(_dump_model(payload))


@router.patch("/admin/operations/events/{event_id}")
def admin_update_operation_event(event_id: str, payload: OperationEventUpdateRequest) -> dict[str, object]:
    return update_operation_event(event_id, _dump_model(payload, exclude_unset=True))


@router.get("/admin/knowledge/gaps")
def admin_knowledge_gaps(status: str | None = Query(default=None)) -> dict[str, object]:
    status_filter = status if isinstance(status, str) else None
    items = list_knowledge_gaps(status_filter=status_filter)
    return {
        "items": items,
        "count": len(items),
        "mode": "mock",
        "source_note": "知识缺口来自本地演示日志、低置信问答和游客反馈；FAQ 草稿为规则生成，需管理员确认后发布。",
    }


@router.post("/admin/knowledge/gaps", status_code=status.HTTP_201_CREATED)
def admin_create_knowledge_gap(payload: KnowledgeGapCreateRequest) -> dict[str, object]:
    return create_knowledge_gap(
        query=payload.query,
        trigger_type=payload.trigger_type,
        matched_sources=payload.matched_sources,
        confidence=payload.confidence,
        suggested_faq=payload.suggested_faq,
        status_value=payload.status,
    )


@router.post("/admin/knowledge/gaps/{gap_id}/draft-faq")
def admin_draft_knowledge_gap_faq(gap_id: str) -> dict[str, object]:
    return generate_faq_draft(gap_id)


@router.patch("/admin/knowledge/gaps/{gap_id}")
def admin_update_knowledge_gap(gap_id: str, payload: KnowledgeGapUpdateRequest) -> dict[str, object]:
    updates = _dump_model(payload, exclude_unset=True)
    if "status" in updates:
        return update_knowledge_gap_status(gap_id, str(updates["status"]))
    raise ApiError(
        code="KNOWLEDGE_GAP_EMPTY_UPDATE",
        message="没有可更新的知识缺口字段。",
        cause=f"PATCH /api/admin/knowledge/gaps/{gap_id} received no supported fields.",
        fix="当前接口支持更新 status 字段。",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@router.post("/admin/knowledge/gaps/{gap_id}/add-eval")
def admin_add_knowledge_gap_to_eval(gap_id: str) -> dict[str, object]:
    return add_gap_to_eval(gap_id)


@router.get("/admin/evals/overview")
def admin_eval_reports_overview() -> dict[str, object]:
    return eval_reports_overview()


@router.post("/routes/recommend")
def routes_recommend(payload: RouteRecommendRequest) -> dict[str, object]:
    result = recommend_route(
        theme=payload.theme,
        time_budget_minutes=payload.time_budget_minutes,
        group_type=payload.group_type,
        intensity=payload.intensity,
        interests=payload.interests,
        start_attraction_id=payload.start_attraction_id,
        avoid_crowd=payload.avoid_crowd,
        crowd_tolerance=payload.crowd_tolerance,
        must_visit_attraction_ids=payload.must_visit_attraction_ids,
        optional_attraction_ids=payload.optional_attraction_ids,
        avoid_attraction_ids=payload.avoid_attraction_ids,
    )
    high_stops = [stop for stop in result.get("stops", []) if stop.get("crowd_level") == "high"]
    record_interaction_event(
        event_type="route_recommend",
        channel=payload.channel,
        attraction_id=payload.start_attraction_id,
        route_id=str(result.get("id")),
        share_code=(result.get("share") or {}).get("share_code"),
        confidence=float(result.get("recommendation_score") or 0) / 100,
        success=True,
        metadata={
            "theme": result.get("theme"),
            "theme_label": result.get("theme_label"),
            "score": result.get("recommendation_score"),
            "avoid_crowd": payload.avoid_crowd,
            "crowd_tolerance": payload.crowd_tolerance,
            "high_crowd_stops": [stop.get("name") for stop in high_stops],
            "stop_count": len(result.get("stops", [])),
            "must_visit_attraction_ids": payload.must_visit_attraction_ids or [],
            "avoid_attraction_ids": payload.avoid_attraction_ids or [],
            "operation_event_count": (result.get("operation_policy") or {}).get("active_event_count", 0),
            "operation_sources": (result.get("operation_policy") or {}).get("sources", []),
        },
    )
    if payload.avoid_crowd or high_stops:
        record_interaction_event(
            event_type="crowd_avoidance",
            channel=payload.channel,
            attraction_id=payload.start_attraction_id,
            route_id=str(result.get("id")),
            share_code=(result.get("share") or {}).get("share_code"),
            confidence=float(result.get("recommendation_score") or 0) / 100,
            success=True,
            metadata={
                "source": "mock_simulation",
                "high_crowd_stops": [stop.get("name") for stop in high_stops],
                "decision_trace": result.get("decision_trace", [])[:4],
            },
        )
    return result


@router.post("/routes/intent")
def routes_intent(payload: RouteIntentRequest) -> dict[str, object]:
    message = payload.message.strip()
    if not message:
        raise ApiError(
            code="EMPTY_ROUTE_MESSAGE",
            message="请先输入路线需求。",
            cause="POST /api/routes/intent received an empty message.",
            fix="在 message 字段中传入游客的自然语言路线需求。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    result = parse_route_intent(
        message=message,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id,
        memory=payload.memory,
    )
    record_interaction_event(
        event_type="route_intent_parse",
        channel=payload.channel,
        question=message,
        attraction_id=payload.selected_attraction_id,
        confidence=float(result.get("intent_confidence") or 0),
        success=not bool(result.get("needs_clarification")),
        metadata={
            "intent": result.get("intent"),
            "operation": result.get("operation"),
            "style": result.get("style"),
            "needs_clarification": result.get("needs_clarification"),
        },
    )
    if result.get("needs_clarification"):
        record_interaction_event(
            event_type="clarification",
            channel=payload.channel,
            question=message,
            attraction_id=payload.selected_attraction_id,
            confidence=float(result.get("intent_confidence") or 0),
            success=True,
            metadata={"clarification_options": result.get("clarification_options", [])},
        )
    return result


@router.post("/routes/conversation")
def routes_conversation(payload: RouteConversationRequest) -> dict[str, object]:
    message = payload.message.strip()
    if not message:
        raise ApiError(
            code="EMPTY_ROUTE_MESSAGE",
            message="请先输入路线需求。",
            cause="POST /api/routes/conversation received an empty message.",
            fix="在 message 字段中传入游客的自然语言路线需求或重规划指令。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    memory = get_route_memory(payload.session_id)
    understanding = understand_query(
        message,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id or memory.get("current_route_id"),
    )
    intent_probe = parse_route_intent(
        message=message,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id or memory.get("current_route_id"),
        memory=memory,
    )
    intent_probe = _merge_route_constraint_payload(intent_probe, payload)
    has_explicit_route_constraints = bool(
        payload.must_visit_attraction_ids or payload.optional_attraction_ids or payload.avoid_attraction_ids
    )
    if (understanding.get("domain") == "out_of_scope" and not has_explicit_route_constraints) or (
        not understanding.get("should_route")
        and intent_probe.get("intent") != "explanation_style"
        and not has_explicit_route_constraints
    ):
        reply = build_gate_answer(understanding)
        gate_intent = _route_intent_from_understanding(understanding)
        record_interaction_event(
            event_type="clarification" if understanding.get("needs_clarification") else "route_conversation",
            channel=payload.channel,
            question=message,
            answer_preview=reply,
            attraction_id=payload.selected_attraction_id,
            confidence=float(understanding.get("confidence") or 0),
            success=False,
            metadata={"understanding": understanding, "blocked_by_query_gate": True},
        )
        return {
            "session_id": memory["session_id"],
            "intent": gate_intent,
            "memory": memory,
            "route": None,
            "reply": reply,
            "confidence": understanding.get("confidence", 0),
            "needs_clarification": bool(understanding.get("needs_clarification")),
            "clarification_options": understanding.get("clarification_options", []),
            "understanding": understanding,
            "mode": "mock",
        }
    intent = parse_route_intent(
        message=message,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id or memory.get("current_route_id"),
        memory=memory,
    )
    intent = _merge_route_constraint_payload(intent, payload)
    record_interaction_event(
        event_type="route_intent_parse",
        channel=payload.channel,
        question=message,
        attraction_id=payload.selected_attraction_id,
        confidence=float(intent.get("intent_confidence") or 0),
        success=not bool(intent.get("needs_clarification")),
        metadata={"intent": intent.get("intent"), "operation": intent.get("operation"), "style": intent.get("style")},
    )
    if intent.get("needs_clarification"):
        reply = intent.get("clarification_question") or "我需要再确认一下你的路线需求。"
        record_interaction_event(
            event_type="clarification",
            channel=payload.channel,
            question=message,
            answer_preview=reply,
            attraction_id=payload.selected_attraction_id,
            confidence=float(intent.get("intent_confidence") or 0),
            success=True,
            metadata={"options": intent.get("clarification_options", [])},
        )
        return {
            "session_id": memory["session_id"],
            "intent": intent,
            "memory": memory,
            "route": None,
            "reply": reply,
            "confidence": intent.get("intent_confidence", 0),
            "needs_clarification": True,
            "clarification_options": intent.get("clarification_options", []),
            "understanding": understanding,
            "mode": "mock",
        }

    preview_constraints = _preview_route_constraints(memory, intent)
    constraint_conflicts = detect_constraint_conflicts(preview_constraints)
    if constraint_conflicts:
        conflict_names = "、".join(str(item.get("name") or item.get("attraction_id")) for item in constraint_conflicts)
        reply = f"{conflict_names} 同时被标记为必去和避开，我先不生成路线，避免把你的必去点误删。"
        intent = {
            **intent,
            "needs_clarification": True,
            "clarification_question": reply,
            "clarification_options": CONSTRAINT_CLARIFICATION_OPTIONS,
            "metadata": {
                **(intent.get("metadata") or {}),
                "constraint_conflicts": constraint_conflicts,
            },
        }
        record_interaction_event(
            event_type="clarification",
            channel=payload.channel,
            question=message,
            answer_preview=reply,
            attraction_id=payload.selected_attraction_id,
            confidence=float(intent.get("intent_confidence") or 0),
            success=True,
            metadata={"constraint_conflicts": constraint_conflicts, "options": CONSTRAINT_CLARIFICATION_OPTIONS},
        )
        return {
            "session_id": memory["session_id"],
            "intent": intent,
            "memory": memory,
            "route": None,
            "reply": reply,
            "confidence": intent.get("intent_confidence", 0),
            "needs_clarification": True,
            "clarification_options": CONSTRAINT_CLARIFICATION_OPTIONS,
            "understanding": understanding,
            "mode": "mock",
        }

    if intent.get("intent") == "explanation_style":
        style = intent.get("style") or "default"
        attraction = get_attraction_or_error(payload.selected_attraction_id) if payload.selected_attraction_id else None
        name = attraction.get("name") if attraction else "当前景点"
        summary = str((attraction or {}).get("summary") or "我会基于本地资料，用更适合当前场景的方式讲解。")
        if style == "child":
            reply = f"我会用亲子版讲解：{name}可以先抓住一个简单故事来听，别急着记术语。{summary[:80]}"
        elif style == "short_30s":
            reply = f"30 秒版：{name}的重点是先看核心地标，再听一个最关键的文化背景。{summary[:70]}"
        elif style == "deep_history":
            reply = f"历史深度版：{name}可以从历史脉络、建筑象征和佛教文化三层理解。{summary[:90]}"
        else:
            reply = f"已切换讲解风格：{style}。{summary[:90]}"
        record_interaction_event(
            event_type="route_conversation",
            channel=payload.channel,
            question=message,
            answer_preview=reply,
            attraction_id=payload.selected_attraction_id,
            confidence=float(intent.get("intent_confidence") or 0),
            success=True,
            metadata={"intent": "explanation_style", "style": style},
        )
        return {
            "session_id": memory["session_id"],
            "intent": intent,
            "memory": memory,
            "route": None,
            "reply": reply,
            "confidence": intent.get("intent_confidence", 0),
            "needs_clarification": False,
            "clarification_options": [],
            "understanding": understanding,
            "mode": "mock",
        }

    memory = apply_intent_to_memory(
        memory=memory,
        intent=intent,
        selected_attraction_id=payload.selected_attraction_id,
        current_route_id=payload.current_route_id,
    )
    preferences = memory["preferences"]
    constraints = memory["constraints"]
    route = recommend_route(
        theme=preferences.get("theme"),
        time_budget_minutes=preferences.get("time_budget_minutes"),
        group_type=preferences.get("group_type"),
        intensity=preferences.get("intensity"),
        interests=preferences.get("interests"),
        start_attraction_id=preferences.get("start_attraction_id") or payload.selected_attraction_id,
        avoid_crowd=bool(preferences.get("avoid_crowd")),
        crowd_tolerance=preferences.get("crowd_tolerance") or "medium",
        must_visit_attraction_ids=constraints.get("must_visit_attraction_ids"),
        optional_attraction_ids=constraints.get("optional_attraction_ids"),
        avoid_attraction_ids=constraints.get("avoid_attraction_ids"),
    )
    memory = update_memory_after_route(memory, route)
    must_names = [stop["name"] for stop in route.get("stops", []) if stop.get("constraint_type") == "must_visit"]
    reply = (
        f"已按你的自然语言需求更新路线：{route['title']}，综合评分 {route['recommendation_score']} 分。"
        f"{' 必去点已保留：' + '、'.join(must_names) + '。' if must_names else ''}"
        "当前拥挤度为 mock_simulation 演示数据，不代表真实客流。"
    )
    event_type = "route_replan" if intent.get("intent") == "route_replan" else "route_conversation"
    record_interaction_event(
        event_type=event_type,
        channel=payload.channel,
        question=message,
        answer_preview=reply,
        attraction_id=payload.selected_attraction_id,
        route_id=str(route.get("id")),
        share_code=(route.get("share") or {}).get("share_code"),
        confidence=float(intent.get("intent_confidence") or 0),
        success=True,
        metadata={
            "intent": intent.get("intent"),
            "operation": intent.get("operation"),
            "theme": route.get("theme"),
            "theme_label": route.get("theme_label"),
            "score": route.get("recommendation_score"),
            "must_visit_attraction_ids": constraints.get("must_visit_attraction_ids", []),
            "avoid_attraction_ids": constraints.get("avoid_attraction_ids", []),
        },
    )
    return {
        "session_id": memory["session_id"],
        "intent": intent,
        "memory": memory,
        "route": route,
        "reply": reply,
        "confidence": intent.get("intent_confidence", 0),
        "needs_clarification": False,
        "clarification_options": [],
        "understanding": understanding,
        "mode": "mock",
    }


@router.get("/routes/{route_id}/share")
def route_share(route_id: str, code: str | None = Query(default=None)) -> dict[str, object]:
    result = get_route_share(route_id, code)
    record_interaction_event(
        event_type="route_share_open",
        channel="share",
        route_id=route_id,
        share_code=code,
        success=True,
        metadata={
            "theme": result.get("theme"),
            "theme_label": result.get("theme_label"),
            "score": result.get("recommendation_score"),
            "stop_count": len(result.get("stops", [])),
        },
    )
    return result


@router.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, object]:
    if payload.rating < 1 or payload.rating > 5:
        raise ApiError(
            code="INVALID_FEEDBACK_RATING",
            message="反馈评分需要在 1 到 5 分之间。",
            cause=f"Invalid rating: {payload.rating}",
            fix="请在 rating 字段传入 1、2、3、4 或 5。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    result = record_feedback(
        channel=payload.channel,
        route_id=payload.route_id,
        attraction_id=payload.attraction_id,
        rating=payload.rating,
        tags=payload.tags,
        comment=payload.comment,
    )
    tag_text = " ".join(payload.tags or [])
    if "信息不准" in tag_text or "不准" in tag_text or "incorrect" in tag_text.lower():
        query = (payload.comment or "").strip()
        if not query:
            query = f"反馈提示信息不准：route={payload.route_id or '-'} attraction={payload.attraction_id or '-'}"
        safe_record_knowledge_gap(
            query=query,
            trigger_type="negative_feedback",
            matched_sources=[],
            confidence=0.0,
        )
    return result


def _parse_content_disposition(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        result[key.strip().lower()] = raw.strip().strip('"')
    # Support RFC 5987 filename*=UTF-8''... when filename= is missing
    if "filename*" in result and "filename" not in result:
        filename_star = result["filename*"]
        # RFC 5987 format: charset'lang'value
        if "'" in filename_star:
            charset, _, encoded_value = filename_star.partition("'")
            # Skip language tag if present (second ')
            if "'" in encoded_value:
                _, encoded_value = encoded_value.split("'", 1)
            if charset.lower() == "utf-8":
                result["filename"] = urllib.parse.unquote(encoded_value)
    return result


def _parse_multipart_form(content_type: str, body: bytes) -> dict[str, object]:
    marker = "boundary="
    if marker not in content_type:
        raise ApiError(
            code="INVALID_MULTIPART",
            message="请使用 multipart/form-data 上传图片。",
            cause=f"Content-Type missing boundary: {content_type}",
            fix="表单字段使用 file 上传文件，可选 hint 或 text_hint 提供识别提示。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = f"--{boundary}".encode("utf-8")
    fields: dict[str, object] = {}
    for part in body.split(delimiter):
        part = part.strip()
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip()
        # Support both CRLF (\r\n\r\n) and LF-only (\n\n) header/body separator
        header_sep = b"\r\n\r\n" if b"\r\n\r\n" in part else b"\n\n"
        if header_sep not in part:
            continue
        raw_headers, value = part.split(header_sep, 1)
        # Strip trailing line endings from value (support both CRLF and LF)
        if value.endswith(b"\r\n"):
            value = value[:-2]
        elif value.endswith(b"\n"):
            value = value[:-1]
        # Parse headers - support both CRLF and LF line endings
        headers = {}
        header_text = raw_headers.decode("utf-8", errors="ignore")
        # Normalize line endings to \n then split
        header_lines = header_text.replace("\r\n", "\n").split("\n")
        for line in header_lines:
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            headers[key.strip().lower()] = raw.strip()
        disposition = _parse_content_disposition(headers.get("content-disposition", ""))
        name = disposition.get("name")
        if not name:
            continue
        if "filename" in disposition:
            fields[name] = {
                "filename": disposition.get("filename", ""),
                "content_type": headers.get("content-type", "application/octet-stream"),
                "content": value,
            }
        else:
            fields[name] = value.decode("utf-8", errors="ignore").strip()
    return fields


@router.post("/vision/recognize")
async def vision_recognize(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    fields = _parse_multipart_form(content_type, body)
    file_info = fields.get("file")
    if not isinstance(file_info, dict):
        raise ApiError(
            code="IMAGE_FILE_REQUIRED",
            message="请上传一张图片文件。",
            cause="POST /api/vision/recognize did not include form field 'file'.",
            fix="用 multipart/form-data 提交 file 字段，可附加 hint 或 text_hint。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    content = file_info.get("content", b"")
    file_size = len(content) if isinstance(content, bytes) else None
    result = recognize_image_mock(
        filename=str(file_info.get("filename") or ""),
        hint=str(fields.get("hint") or ""),
        text_hint=str(fields.get("text_hint") or ""),
        file_size=file_size,
    )
    matched = result.get("matched_attraction")
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    record_interaction_event(
        event_type="vision",
        channel=str(fields.get("channel") or "mobile"),
        attraction_id=matched.get("id") if isinstance(matched, dict) else None,
        confidence=float(result.get("confidence") or 0),
        success=matched is not None,
        metadata={
            "filename": file_info.get("filename"),
            "mode": result.get("mode"),
            "matched_attraction_name": matched.get("name") if isinstance(matched, dict) else None,
            "latency_ms": result.get("latency_ms"),
            "strategy": metadata.get("strategy"),
            "candidates_count": metadata.get("candidates_count"),
            "needs_confirmation": metadata.get("needs_confirmation"),
            "top1_attraction_id": metadata.get("top1_attraction_id"),
        },
    )
    return result
