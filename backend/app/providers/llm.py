from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


SUPPORTED_LLM_PROVIDERS = {"mock", "dashscope", "openai"}


@dataclass
class GroundedAnswerResult:
    answer: str
    provider: str
    grounding_mode: str
    fallback_reason: str | None
    provider_latency_ms: int | None


def _provider_key(provider: str) -> str:
    if provider == "dashscope":
        return os.getenv("DASHSCOPE_API_KEY", "").strip()
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "").strip()
    return ""


def _provider_model(provider: str, configured_model: str) -> str:
    if configured_model:
        return configured_model
    if provider == "dashscope":
        return "qwen-plus"
    if provider == "openai":
        return "gpt-4o-mini"
    return "mock"


def _endpoint(provider: str) -> str:
    if provider == "dashscope":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    if provider == "openai":
        return "https://api.openai.com/v1/chat/completions"
    raise ValueError(f"Unsupported LLM provider: {provider}")


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
                "你是灵境导游的可信问答生成器。必须只根据用户提供的 SOURCES 回答景区事实问题。"
                "不要补充 SOURCES 之外的开放时间、票价、历史细节、路线承诺或实时信息。"
                "如果 SOURCES 不足以回答，就明确说本地资料库未收录。"
                "回答使用简洁、可信、适合游客端数字人的中文导游口吻。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"QUESTION:\n{question}\n\nSOURCES:\n{source_block}\n\n"
                "请给出 2-5 句中文回答。不要输出 JSON，不要列出没有来源的事实。"
            ),
        },
    ]


def _chat_completion(provider: str, model: str, key: str, messages: list[dict[str, str]], timeout_seconds: float) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 700,
    }
    request = urllib.request.Request(
        _endpoint(provider),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    return str((message or {}).get("content") or "").strip()


def generate_grounded_answer(
    *,
    question: str,
    sources: list[dict[str, Any]],
    fallback_answer: str,
) -> GroundedAnswerResult:
    """Generate a grounded answer from local RAG sources with strict fallback.

    The provider is never allowed to answer when sources are empty. Callers should
    only invoke this function after retrieval succeeds.
    """

    settings = get_settings()
    provider = settings.llm_provider.lower().strip() or "mock"
    if provider not in SUPPORTED_LLM_PROVIDERS:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            grounding_mode="rag_sources_only",
            fallback_reason=f"unsupported_llm_provider:{provider}",
            provider_latency_ms=None,
        )
    if provider == "mock":
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="mock",
            grounding_mode="rag_sources_only",
            fallback_reason=None,
            provider_latency_ms=None,
        )
    if not sources:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            grounding_mode="rag_sources_only",
            fallback_reason="no_rag_sources",
            provider_latency_ms=None,
        )

    key = _provider_key(provider)
    if not key:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            grounding_mode="rag_sources_only",
            fallback_reason=f"{provider}_api_key_missing",
            provider_latency_ms=None,
        )

    start = time.perf_counter()
    try:
        answer = _chat_completion(
            provider=provider,
            model=_provider_model(provider, settings.llm_model),
            key=key,
            messages=_build_messages(question, sources),
            timeout_seconds=max(1.0, settings.llm_timeout_seconds),
        )
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            grounding_mode="rag_sources_only",
            fallback_reason=f"{provider}_request_failed:{exc.__class__.__name__}",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if not answer:
        return GroundedAnswerResult(
            answer=fallback_answer,
            provider="fallback",
            grounding_mode="rag_sources_only",
            fallback_reason=f"{provider}_empty_response",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    return GroundedAnswerResult(
        answer=answer,
        provider=provider,
        grounding_mode="rag_sources_only",
        fallback_reason=None,
        provider_latency_ms=int((time.perf_counter() - start) * 1000),
    )
