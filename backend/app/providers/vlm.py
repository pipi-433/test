from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


SUPPORTED_VLM_PROVIDERS = {"mock", "dashscope", "openai"}


@dataclass
class VisionProviderResult:
    provider: str
    observations: str | None
    candidate_names: list[str]
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
        return "qwen-vl-plus"
    if provider == "openai":
        return "gpt-4o-mini"
    return "mock"


def _endpoint(provider: str) -> str:
    if provider == "dashscope":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    if provider == "openai":
        return "https://api.openai.com/v1/chat/completions"
    raise ValueError(f"Unsupported VLM provider: {provider}")


def _json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    payload = json.loads(stripped)
    return payload if isinstance(payload, dict) else {}


def _chat_completion(
    *,
    provider: str,
    model: str,
    key: str,
    image_bytes: bytes,
    content_type: str,
    hint: str | None,
    text_hint: str | None,
    timeout_seconds: float,
) -> str:
    mime = content_type or "image/jpeg"
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    prompt = (
        "你是灵境导游的视觉候选识别器。只做画面观察和候选名称提取，不能回答景区事实。"
        "请把图片可能对应的景点名称映射成最多 5 个候选名称；如果不确定也要说明。"
        "输出严格 JSON：{\"observations\":\"...\",\"candidates\":[{\"name\":\"...\",\"reason\":\"...\"}]}。"
        f"\n用户提示 hint={hint or ''}; text_hint={text_hint or ''}"
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
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


def recognize_visual_candidates(
    *,
    image_bytes: bytes,
    content_type: str,
    hint: str | None = None,
    text_hint: str | None = None,
) -> VisionProviderResult:
    settings = get_settings()
    provider = settings.vlm_provider.lower().strip() or "mock"
    if provider not in SUPPORTED_VLM_PROVIDERS:
        return VisionProviderResult(
            provider="fallback",
            observations=None,
            candidate_names=[],
            fallback_reason=f"unsupported_vlm_provider:{provider}",
            provider_latency_ms=None,
        )
    if provider == "mock":
        return VisionProviderResult(
            provider="mock",
            observations=None,
            candidate_names=[],
            fallback_reason=None,
            provider_latency_ms=None,
        )

    key = _provider_key(provider)
    if not key:
        return VisionProviderResult(
            provider="fallback",
            observations=None,
            candidate_names=[],
            fallback_reason=f"{provider}_api_key_missing",
            provider_latency_ms=None,
        )

    start = time.perf_counter()
    try:
        raw_text = _chat_completion(
            provider=provider,
            model=_provider_model(provider, settings.vlm_model),
            key=key,
            image_bytes=image_bytes,
            content_type=content_type,
            hint=hint,
            text_hint=text_hint,
            timeout_seconds=max(1.0, settings.vlm_timeout_seconds),
        )
        payload = _json_from_text(raw_text)
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return VisionProviderResult(
            provider="fallback",
            observations=None,
            candidate_names=[],
            fallback_reason=f"{provider}_request_failed:{exc.__class__.__name__}",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    names: list[str] = []
    for item in candidates[:5]:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
        elif isinstance(item, str):
            names.append(item)
    observations = str(payload.get("observations") or "").strip() or None
    return VisionProviderResult(
        provider=provider,
        observations=observations,
        candidate_names=names,
        fallback_reason=None,
        provider_latency_ms=int((time.perf_counter() - start) * 1000),
    )
