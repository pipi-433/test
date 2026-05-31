from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings


SUPPORTED_VLM_PROVIDERS = {"mock", "dashscope"}

LOCAL_ATTRACTION_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("lingshan-ls-001", "灵山大照壁"),
    ("lingshan-ls-002", "五明桥"),
    ("lingshan-ls-003", "佛足坛"),
    ("lingshan-ls-004", "五智门"),
    ("lingshan-ls-005", "菩提大道"),
    ("lingshan-ls-006", "九龙灌浴"),
    ("lingshan-ls-007", "降魔浮雕"),
    ("lingshan-ls-008", "阿育王柱"),
    ("lingshan-ls-009", "百子戏弥勒"),
    ("lingshan-ls-010", "祥符禅寺"),
    ("lingshan-ls-011", "灵山大佛"),
    ("lingshan-ls-012", "佛教文化博览馆"),
    ("lingshan-ls-013", "灵山梵宫"),
    ("lingshan-ls-014", "五印坛城"),
    ("lingshan-ls-015", "曼飞龙塔"),
    ("lingshan-ls-016", "无尽意斋"),
    ("nianhuawan-nh-001", "拈花广场"),
    ("nianhuawan-nh-002", "梵天花海"),
    ("nianhuawan-nh-003", "香月花街"),
    ("nianhuawan-nh-004", "拈花堂"),
    ("nianhuawan-nh-005", "五灯湖"),
    ("nianhuawan-nh-006", "鹿鸣谷"),
)


@dataclass
class VisionProviderResult:
    provider: str
    observations: str | None
    primary_subject: str | None
    background_landmarks: list[str]
    visual_features: list[str]
    candidate_names: list[str]
    uncertainty_reason: str | None
    fallback_reason: str | None
    provider_latency_ms: int | None
    candidate_ids: list[str] = field(default_factory=list)


def _provider_key(provider: str) -> str:
    if provider == "dashscope":
        return os.getenv("DASHSCOPE_API_KEY", "").strip()
    return ""


def _provider_model(provider: str, configured_model: str) -> str:
    if configured_model:
        return configured_model
    if provider == "dashscope":
        return "qwen-vl-plus"
    return "mock"


def _endpoint(provider: str) -> str:
    if provider == "dashscope":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
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
    candidate_lines = "\n".join(f"- {attraction_id}: {name}" for attraction_id, name in LOCAL_ATTRACTION_CANDIDATES)
    prompt = (
        "你是灵境导游的视觉候选识别器，只做视觉观察和本地景点候选识别。"
        "不要生成景点事实讲解，不要编造开放时间、票价、演出时间、实时客流或游览建议。"
        "确认后的讲解会由后端本地 RAG sources 负责。"
        "请优先识别画面主体，不要把背景/远处地标当作 Top1。"
        "例如巨大佛像只是远处背景时，不要强行把灵山大佛排为 Top1；"
        "应优先判断前景主体建筑、水景、桥、广场、街巷、花海或湖面。"
        "只能从下面 22 个本地候选中选择 candidate_attraction_ids，不能输出列表外 id：\n"
        f"{candidate_lines}\n"
        "不确定时 candidate_attraction_ids 和 candidate_attraction_names 返回空数组，"
        "或只返回低把握候选并在 uncertainty_reason 说明原因。"
        "输出必须是严格 JSON 对象，不要 Markdown，不要代码块，不要额外文字。JSON schema："
        "{\"primary_subject\":\"画面主体\","
        "\"visual_features\":[\"可见特征\"],"
        "\"background_landmarks\":[\"背景/远处地标\"],"
        "\"candidate_attraction_ids\":[\"lingshan-ls-011\"],"
        "\"candidate_attraction_names\":[\"灵山大佛\"],"
        "\"uncertainty_reason\":\"不确定原因\","
        "\"observations\":\"一句视觉观察\"}。"
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
            primary_subject=None,
            background_landmarks=[],
            visual_features=[],
            candidate_names=[],
            uncertainty_reason=None,
            fallback_reason=f"unsupported_vlm_provider:{provider}",
            provider_latency_ms=None,
        )
    if provider == "mock":
        return VisionProviderResult(
            provider="mock",
            observations=None,
            primary_subject=None,
            background_landmarks=[],
            visual_features=[],
            candidate_names=[],
            uncertainty_reason=None,
            fallback_reason=None,
            provider_latency_ms=None,
        )

    key = _provider_key(provider)
    if not key:
        return VisionProviderResult(
            provider="fallback",
            observations=None,
            primary_subject=None,
            background_landmarks=[],
            visual_features=[],
            candidate_names=[],
            uncertainty_reason=None,
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
            primary_subject=None,
            background_landmarks=[],
            visual_features=[],
            candidate_names=[],
            uncertainty_reason=None,
            fallback_reason=f"{provider}_request_failed:{exc.__class__.__name__}",
            provider_latency_ms=int((time.perf_counter() - start) * 1000),
        )

    allowed_ids = {attraction_id for attraction_id, _ in LOCAL_ATTRACTION_CANDIDATES}
    candidate_ids_payload = payload.get("candidate_attraction_ids")
    candidate_ids: list[str] = []
    if isinstance(candidate_ids_payload, list):
        for item in candidate_ids_payload[:5]:
            value = str(item.get("id") if isinstance(item, dict) else item).strip()
            if value in allowed_ids and value not in candidate_ids:
                candidate_ids.append(value)

    candidates = payload.get("candidate_attraction_names")
    if not isinstance(candidates, list):
        candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    names: list[str] = []
    for item in candidates[:5]:
        if isinstance(item, dict):
            candidate_id = str(item.get("id") or item.get("attraction_id") or "").strip()
            if candidate_id in allowed_ids and candidate_id not in candidate_ids:
                candidate_ids.append(candidate_id)
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
        elif isinstance(item, str):
            names.append(item)
    observations = str(payload.get("observations") or "").strip() or None
    primary_subject = str(payload.get("primary_subject") or "").strip() or None
    background_landmarks = [
        str(item).strip()
        for item in (payload.get("background_landmarks") if isinstance(payload.get("background_landmarks"), list) else [])
        if str(item).strip()
    ]
    visual_features = [
        str(item).strip()
        for item in (payload.get("visual_features") if isinstance(payload.get("visual_features"), list) else [])
        if str(item).strip()
    ]
    uncertainty_reason = str(payload.get("uncertainty_reason") or "").strip() or None
    return VisionProviderResult(
        provider=provider,
        observations=observations,
        primary_subject=primary_subject,
        background_landmarks=background_landmarks[:8],
        visual_features=visual_features[:12],
        candidate_names=names,
        uncertainty_reason=uncertainty_reason,
        fallback_reason=None,
        provider_latency_ms=int((time.perf_counter() - start) * 1000),
        candidate_ids=candidate_ids,
    )
