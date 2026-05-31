from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import IncompleteRead
from typing import Any

from app.core.config import get_settings


SUPPORTED_LLM_PROVIDERS = {"mock", "dashscope"}
DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_MAX_OUTPUT_TOKENS = 300
DASHSCOPE_CHAT_COMPLETIONS_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

SAFE_SEARCH_SCENIC_TERMS = (
    "灵山",
    "灵山大佛",
    "梵宫",
    "九龙灌浴",
    "拈花湾",
    "五印坛城",
    "祥符禅寺",
    "无锡",
    "佛教",
    "禅意",
    "文化",
    "历史",
    "故事",
    "典故",
    "背景",
    "由来",
    "寓意",
)
BLOCKED_SEARCH_TERMS = (
    "今天",
    "现在",
    "当前",
    "实时",
    "开放",
    "闭园",
    "营业",
    "几点",
    "票价",
    "门票",
    "优惠",
    "人多",
    "客流",
    "拥挤",
    "排队",
    "路线",
    "导航",
    "gps",
    "定位",
    "地图",
    "硬件",
    "设备",
    "闸机",
    "摄像头",
    "停车",
    "交通",
    "表演时间",
    "演出时间",
    "场次",
)
FALLBACK_EXPRESSION_TERMS = (
    "story",
    "history",
    "culture",
    "background",
    "why",
    "故事",
    "典故",
    "历史",
    "文化",
    "背景",
    "深入",
    "为什么",
)
LOW_CONFIDENCE_SOURCE_THRESHOLD = 1.2


@dataclass
class GroundedAnswerResult:
    answer: str
    provider: str
    model: str | None
    grounding_mode: str
    fallback_reason: str | None
    provider_latency_ms: int | None


def _provider_key(provider: str) -> str:
    if provider == "dashscope":
        return os.getenv("DASHSCOPE_API_KEY", "").strip()
    return ""


def _provider_model(provider: str, configured_model: str) -> str:
    if configured_model:
        return configured_model
    if provider == "dashscope":
        return DEFAULT_QWEN_MODEL
    return "mock"


def _provider_fallback_model(provider: str, configured_model: str) -> str:
    disabled = {"", "none", "off", "disabled", "false"}
    if configured_model.strip().lower() in disabled:
        return ""
    if provider == "dashscope":
        return configured_model
    return ""


def _provider_label(provider: str, model: str) -> str:
    if provider == "dashscope" and model:
        return f"{provider}:{model}"
    return provider


def _source_text(source: dict[str, Any], index: int) -> str:
    title = str(source.get("title") or f"source-{index}")
    source_file = str(source.get("source_file") or "local knowledge")
    section = str(source.get("source_section") or "")
    content = str(source.get("content") or "")
    if len(content) > 700:
        content = content[:700] + "..."
    return f"[{index}] title={title}\nsource_file={source_file}\nsection={section}\ncontent={content}"


def _build_messages(question: str, sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    source_block = "\n\n".join(_source_text(source, index) for index, source in enumerate(sources[:5], start=1))
    return [
        {
            "role": "system",
            "content": (
                "You are Lingjing Guide's trusted scenic QA generator. "
                "Answer scenic facts only from the provided SOURCES. "
                "Do not add opening hours, ticket prices, route commitments, realtime crowd status, "
                "GPS/navigation, hardware status, or facts that are not present in SOURCES. "
                "If SOURCES are insufficient, say the local knowledge base does not include enough information. "
                "Use short sentences in a warm tour-guide voice. Reply in Chinese, suitable for avatar speech, "
                "preferably 120-300 Chinese characters. Do not write a long encyclopedia answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"QUESTION:\n{question}\n\nSOURCES:\n{source_block}\n\n"
                "Please answer in 2-5 concise Chinese sentences. Do not output JSON. "
                "Do not include facts without source support."
            ),
        },
    ]


def _build_search_messages(question: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是灵境导游的安全背景知识补充器。只允许补充非时效性的景区背景、佛教文化常识、"
                "无锡或灵山相关公开文化背景。不要采用今日开放时间、实时票价、实时客流、GPS/地图导航、"
                "硬件事件、实时演出场次或路线点位决策信息。若无法可靠确认，请回答："
                "本地资料暂未收录，建议以景区官方公告为准。中文短句，适合数字人口播，120-300 中文字以内。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"QUESTION:\n{question}\n\n"
                "请只做安全的非时效背景补充。不要输出 JSON，不要编造实时信息。"
            ),
        },
    ]


def _max_output_tokens(value: int | None) -> int:
    try:
        return max(64, min(int(value or DEFAULT_MAX_OUTPUT_TOKENS), 1200))
    except (TypeError, ValueError):
        return DEFAULT_MAX_OUTPUT_TOKENS


def _post_json(
    endpoint: str,
    payload: dict[str, Any],
    key: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "lingjing-guide/0.1 qwen-client",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _chat_completion(
    *,
    model: str,
    key: str,
    messages: list[dict[str, str]],
    timeout_seconds: float,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    enable_search: bool = False,
    thinking_mode: str = "off",
    thinking_budget: int | None = None,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": _max_output_tokens(max_output_tokens),
    }
    if enable_search:
        payload["enable_search"] = True

    thinking_mode = (thinking_mode or "off").strip().lower()
    if thinking_mode in {"off", "none", "no", "false", "0"}:
        payload["enable_thinking"] = False
    elif thinking_mode in {"on", "auto", "low"}:
        payload["enable_thinking"] = True
        if thinking_budget:
            payload["thinking_budget"] = max(0, int(thinking_budget))

    data = _post_json(DASHSCOPE_CHAT_COMPLETIONS_URL, payload, key, timeout_seconds)
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    return str((message or {}).get("content") or "").strip()


def _retrieval_confidence(sources: list[dict[str, Any]]) -> float:
    scores = []
    for source in sources:
        try:
            scores.append(float(source.get("score") or 0))
        except (TypeError, ValueError):
            continue
    return max(scores) if scores else 0.0


def _fallback_reason_for_question(question: str, sources: list[dict[str, Any]]) -> str | None:
    compact = re.sub(r"\s+", "", question.lower())
    if sources and _retrieval_confidence(sources) < LOW_CONFIDENCE_SOURCE_THRESHOLD:
        return "low_retrieval_confidence"
    if 0 < len(sources) < 2:
        return "limited_local_sources"
    if any(term in compact for term in FALLBACK_EXPRESSION_TERMS):
        return "complex_expression"
    return None


def _search_gap_reason(question: str, sources: list[dict[str, Any]]) -> str | None:
    if not sources:
        return "no_local_sources"
    if _retrieval_confidence(sources) < LOW_CONFIDENCE_SOURCE_THRESHOLD:
        return "low_retrieval_confidence"
    return None


def _is_safe_search_gap_question(question: str) -> bool:
    compact = re.sub(r"\s+", "", question.lower())
    if any(term in compact for term in BLOCKED_SEARCH_TERMS):
        return False
    return any(term in compact for term in SAFE_SEARCH_SCENIC_TERMS)


def _should_use_search_gap(question: str, sources: list[dict[str, Any]]) -> tuple[bool, str | None]:
    settings = get_settings()
    policy = (settings.llm_search_policy or "gap_only").strip().lower()
    gap_reason = _search_gap_reason(question, sources)
    if not settings.llm_enable_search or policy != "gap_only" or not gap_reason:
        return False, gap_reason
    return _is_safe_search_gap_question(question), gap_reason


def _provider_failure_reason(provider: str, exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{provider}_http_{exc.code}"
    if isinstance(exc, IncompleteRead):
        return f"{provider}_gateway_incomplete_response"
    if exc.__class__.__name__ == "RemoteDisconnected":
        return f"{provider}_gateway_disconnected"
    return f"{provider}_request_failed:{exc.__class__.__name__}"


def _safe_search_fallback_answer() -> str:
    return "本地资料暂未收录，建议以景区官方公告为准。我也可以继续基于本地资料介绍景点看点、文化背景或游览建议。"


def _search_gap_fill(
    *,
    question: str,
    model: str,
    key: str,
    timeout_seconds: float,
    max_output_tokens: int,
    thinking_mode: str,
    thinking_budget: int | None,
) -> GroundedAnswerResult:
    start = time.perf_counter()
    try:
        answer = _chat_completion(
            model=model,
            key=key,
            messages=_build_search_messages(question),
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            enable_search=True,
            thinking_mode=thinking_mode,
            thinking_budget=thinking_budget,
        )
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, IncompleteRead) as exc:
        return GroundedAnswerResult(
            answer=_safe_search_fallback_answer(),
            provider="fallback",
            model=None,
            grounding_mode="no_sources",
            fallback_reason=f"dashscope_search_gap_fill_failed:{_provider_failure_reason('dashscope', exc)}",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )
    if not answer:
        return GroundedAnswerResult(
            answer=_safe_search_fallback_answer(),
            provider="fallback",
            model=None,
            grounding_mode="no_sources",
            fallback_reason="dashscope_search_gap_fill_empty_response",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )
    return GroundedAnswerResult(
        answer=answer,
        provider=_provider_label("dashscope", model),
        model=model,
        grounding_mode="dashscope_search_gap_fill",
        fallback_reason="gap_only_search_used",
        provider_latency_ms=int((time.perf_counter() - start) * 1000),
    )


def generate_grounded_answer(
    *,
    question: str,
    sources: list[dict[str, Any]],
    fallback_answer: str,
) -> GroundedAnswerResult:
    """Generate a Qwen grounded answer from local RAG sources with safe fallback."""

    settings = get_settings()
    provider = settings.llm_provider.lower().strip() or "mock"
    timeout_seconds = max(1.0, settings.llm_timeout_seconds)
    max_output_tokens = _max_output_tokens(settings.llm_max_output_tokens)

    if provider not in SUPPORTED_LLM_PROVIDERS:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=f"unsupported_llm_provider:{provider}",
            provider_latency_ms=None,
        )
    if provider == "mock":
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="mock",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=None,
            provider_latency_ms=None,
        )

    main_model = _provider_model(provider, settings.llm_model)
    fallback_model = _provider_fallback_model(provider, settings.llm_fallback_model)
    has_fallback_model = bool(fallback_model and fallback_model != main_model)
    key = _provider_key(provider)

    if not sources:
        should_search, gap_reason = _should_use_search_gap(question, sources)
        if should_search and key:
            return _search_gap_fill(
                question=question,
                model=fallback_model or main_model,
                key=key,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
                thinking_mode=settings.llm_thinking_mode,
                thinking_budget=settings.llm_thinking_budget,
            )
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=gap_reason or "no_rag_sources",
            provider_latency_ms=None,
        )

    if not key:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=f"{provider}_api_key_missing",
            provider_latency_ms=None,
        )

    should_search, gap_reason = _should_use_search_gap(question, sources)
    if should_search:
        return _search_gap_fill(
            question=question,
            model=fallback_model or main_model,
            key=key,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            thinking_mode=settings.llm_thinking_mode,
            thinking_budget=settings.llm_thinking_budget,
        )

    escalation_reason = _fallback_reason_for_question(question, sources) if has_fallback_model else None
    requested_model = fallback_model if escalation_reason else main_model
    requested_fallback_reason = f"used_fallback_model:{escalation_reason}" if escalation_reason else None
    messages = _build_messages(question, sources)
    start = time.perf_counter()

    try:
        answer = _chat_completion(
            model=requested_model,
            key=key,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            thinking_mode=settings.llm_thinking_mode,
            thinking_budget=settings.llm_thinking_budget,
        )
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, IncompleteRead) as exc:
        first_failure = _provider_failure_reason(provider, exc)
        if has_fallback_model and requested_model != fallback_model:
            try:
                answer = _chat_completion(
                    model=fallback_model,
                    key=key,
                    messages=messages,
                    timeout_seconds=timeout_seconds,
                    max_output_tokens=max_output_tokens,
                    thinking_mode=settings.llm_thinking_mode,
                    thinking_budget=settings.llm_thinking_budget,
                )
            except (
                TimeoutError,
                urllib.error.URLError,
                urllib.error.HTTPError,
                json.JSONDecodeError,
                OSError,
                IncompleteRead,
            ) as fallback_exc:
                return GroundedAnswerResult(
                    answer=fallback_answer,
                    provider="fallback",
                    model=None,
                    grounding_mode="rag_sources_only",
                    fallback_reason=f"{first_failure};fallback_model_failed:{_provider_failure_reason(provider, fallback_exc)}",
                    provider_latency_ms=int((time.perf_counter() - start) * 1000),
                )
            if answer:
                return GroundedAnswerResult(
                    answer=answer,
                    provider=_provider_label(provider, fallback_model),
                    model=fallback_model,
                    grounding_mode="rag_sources_only",
                    fallback_reason=f"{first_failure};used_fallback_model:request_failed",
                    provider_latency_ms=int((time.perf_counter() - start) * 1000),
                )
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=first_failure,
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if not answer:
        if has_fallback_model and requested_model != fallback_model:
            try:
                answer = _chat_completion(
                    model=fallback_model,
                    key=key,
                    messages=messages,
                    timeout_seconds=timeout_seconds,
                    max_output_tokens=max_output_tokens,
                    thinking_mode=settings.llm_thinking_mode,
                    thinking_budget=settings.llm_thinking_budget,
                )
            except (
                TimeoutError,
                urllib.error.URLError,
                urllib.error.HTTPError,
                json.JSONDecodeError,
                OSError,
                IncompleteRead,
            ) as fallback_exc:
                return GroundedAnswerResult(
                    answer=fallback_answer,
                    provider="fallback",
                    model=None,
                    grounding_mode="rag_sources_only",
                    fallback_reason=f"{provider}_empty_response;fallback_model_failed:{_provider_failure_reason(provider, fallback_exc)}",
                    provider_latency_ms=int((time.perf_counter() - start) * 1000),
                )
            if answer:
                return GroundedAnswerResult(
                    answer=answer,
                    provider=_provider_label(provider, fallback_model),
                    model=fallback_model,
                    grounding_mode="rag_sources_only",
                    fallback_reason=f"{provider}_empty_response;used_fallback_model:empty_response",
                    provider_latency_ms=int((time.perf_counter() - start) * 1000),
                )
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            model=None,
            grounding_mode="rag_sources_only",
            fallback_reason=f"{provider}_empty_response",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    return GroundedAnswerResult(
        answer=answer,
        provider=_provider_label(provider, requested_model),
        model=requested_model,
        grounding_mode="rag_sources_only",
        fallback_reason=requested_fallback_reason,
        provider_latency_ms=int((time.perf_counter() - start) * 1000),
    )
