from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.providers.vlm import recognize_visual_candidates
from app.repositories.content_repository import list_attractions


ALIAS_MAP: dict[str, list[str]] = {
    "lingshan-ls-011": ["灵山大佛", "大佛", "lingshan dafo", "dafo", "ls-011", "ls011", "big buddha"],
    "lingshan-ls-006": ["九龙灌浴", "九龙", "灌浴", "jiulong guanyu", "jiulong", "ls-006", "ls006"],
    "lingshan-ls-013": ["灵山梵宫", "梵宫", "fangong", "fan gong", "lingshan palace", "ls-013", "ls013"],
    "lingshan-ls-014": ["五印坛城", "坛城", "wuyin tancheng", "wuyin", "tancheng", "ls-014", "ls014"],
    "nianhuawan-nh-003": ["香月花街", "花街", "xiangyue huajie", "xiangyue", "huajie", "nh-003", "nh003"],
}


@dataclass
class VisionMatch:
    attraction: dict[str, Any]
    score: float
    reasons: list[str]
    match_signals: list[str]


SIGNAL_LABELS = {
    "filename": "文件名",
    "hint": "提示词",
    "text_hint": "补充描述",
    "tag": "标签",
    "scenic_area": "景区名",
}

SIGNAL_WEIGHTS = {
    "filename": 0.42,
    "hint": 0.52,
    "text_hint": 0.4,
}

CANDIDATE_SCORE_THRESHOLD = 0.12
MATCH_CONFIDENCE_THRESHOLD = 0.62
CONFIRMATION_CONFIDENCE_THRESHOLD = 0.76
CONFIRMATION_GAP_THRESHOLD = 0.15


def _normalize(text: Any) -> str:
    value = str(text or "").lower()
    value = re.sub(r"[_./\\()（）\[\]{}]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text.lower())


def _candidate_text(*, filename: str | None, hint: str | None, text_hint: str | None) -> str:
    filename_stem = Path(filename or "").stem
    return _normalize(" ".join(part for part in [filename_stem, filename, hint, text_hint] if part))


def _source_texts(*, filename: str | None, hint: str | None, text_hint: str | None) -> dict[str, str]:
    filename_stem = Path(filename or "").stem
    return {
        "filename": _normalize(" ".join(part for part in [filename_stem, filename] if part)),
        "hint": _normalize(hint),
        "text_hint": _normalize(text_hint),
    }


def _alias_hit(field_text: str, alias: str) -> bool:
    alias_norm = _normalize(alias)
    alias_compact = _compact(alias_norm)
    field_compact = _compact(field_text)
    return bool(alias_compact and ((alias_norm and alias_norm in field_text) or alias_compact in field_compact))


def _score_attraction(attraction: dict[str, Any], source_texts: dict[str, str]) -> VisionMatch:
    combined_text = _normalize(" ".join(value for value in source_texts.values() if value))
    compact_text = _compact(combined_text)
    reasons: list[str] = []
    match_signals: list[str] = []
    score = 0.0

    stable_id = attraction["id"]
    legacy_id = attraction.get("attraction_id", "")
    name = attraction.get("name", "")
    aliases = [stable_id, legacy_id, name, *ALIAS_MAP.get(stable_id, [])]

    exact_aliases = {_compact(stable_id), _compact(legacy_id), _compact(name)}
    for signal, field_text in source_texts.items():
        if not field_text:
            continue
        best_hit: tuple[float, str] | None = None
        for alias in aliases:
            alias_compact = _compact(_normalize(alias))
            if not alias_compact or not _alias_hit(field_text, alias):
                continue
            weight = SIGNAL_WEIGHTS[signal]
            if alias_compact in exact_aliases:
                weight += 0.16
            if best_hit is None or weight > best_hit[0]:
                best_hit = (weight, str(alias))
        if best_hit:
            score += best_hit[0]
            match_signals.append(signal)
            reasons.append(f"{SIGNAL_LABELS[signal]}命中“{best_hit[1]}”")

    for tag in attraction.get("tags", []):
        tag_compact = _compact(tag)
        if tag_compact and tag_compact in compact_text:
            score += 0.08
            match_signals.append("tag")
            reasons.append(f"标签命中“{tag}”")

    if attraction.get("scenic_area") and _compact(attraction["scenic_area"]) in compact_text:
        score += 0.05
        match_signals.append("scenic_area")
        reasons.append(f"景区名命中“{attraction['scenic_area']}”")

    unique_signals = list(dict.fromkeys(match_signals))
    return VisionMatch(attraction=attraction, score=round(min(score, 1.0), 4), reasons=reasons[:6], match_signals=unique_signals)


def suggested_questions(attraction: dict[str, Any]) -> list[str]:
    name = attraction["name"]
    questions = [
        f"{name}有什么看点？",
        f"{name}适合怎么游览？",
        f"{name}背后有什么文化故事？",
    ]
    if "演艺提醒" in attraction.get("tags", []) or "演出" in attraction.get("opening_info", ""):
        questions.insert(1, f"{name}有哪些演出或开放时间提醒？")
    return questions[:4]


def _confidence_from_score(score: float) -> float:
    if score <= 0:
        return 0.0
    return round(min(0.99, 0.34 + score * 0.62), 2)


def _candidate_reason(match: VisionMatch) -> str:
    if match.reasons:
        return "、".join(match.reasons[:3])
    return "mock 规则给出弱相关候选，需游客确认。"


def _candidate_payload(match: VisionMatch) -> dict[str, Any]:
    return {
        "attraction": match.attraction,
        "confidence": _confidence_from_score(match.score),
        "reason": _candidate_reason(match),
        "match_signals": match.match_signals,
    }


def _confirmation_state(candidates: list[dict[str, Any]]) -> tuple[bool, str]:
    if not candidates:
        return False, "mock 识景没有找到可靠候选，不会编造识别结果。"
    top = candidates[0]
    top_confidence = float(top.get("confidence") or 0.0)
    second_confidence = float(candidates[1].get("confidence") or 0.0) if len(candidates) > 1 else 0.0
    if top_confidence < MATCH_CONFIDENCE_THRESHOLD:
        return True, "Top1 候选置信度偏低，请游客确认后再进入讲解。"
    if len(candidates) > 1 and top_confidence - second_confidence < CONFIRMATION_GAP_THRESHOLD:
        return True, "前两个候选分差较小，请游客确认拍摄的是哪个景点。"
    if top_confidence < CONFIRMATION_CONFIDENCE_THRESHOLD:
        return True, "识景结果可用但仍需确认，避免把低置信候选当作事实讲解。"
    return False, "Top1 候选置信度较高，仍可由游客确认或改选。"


def recognize_image_mock(
    *,
    filename: str | None = None,
    hint: str | None = None,
    text_hint: str | None = None,
    file_size: int | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    source_texts = _source_texts(filename=filename, hint=hint, text_hint=text_hint)
    matches = [_score_attraction(attraction, source_texts) for attraction in list_attractions()]
    matches.sort(key=lambda item: (-item.score, item.attraction["id"]))
    candidate_matches = [match for match in matches if match.score >= CANDIDATE_SCORE_THRESHOLD][:3]
    candidates = [_candidate_payload(match) for match in candidate_matches]
    needs_confirmation, confirmation_reason = _confirmation_state(candidates)
    best = candidate_matches[0] if candidate_matches else None

    if best is None:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "matched_attraction": None,
            "confidence": 0.0,
            "candidates": [],
            "needs_confirmation": False,
            "confirmation_reason": confirmation_reason,
            "selected_attraction_id": None,
            "explanation": (
                "mock 识景没有从文件名或提示词中匹配到可靠景点。"
                "请换用包含景点名称、景点编号或更明确 hint 的样例继续演示。"
            ),
            "suggested_questions": ["这张图可能是哪类景点？", "可以手动选择景点继续讲解吗？"],
            "mode": "mock",
            "latency_ms": latency_ms,
            "metadata": {
                "filename": filename,
                "hint": hint,
                "text_hint": text_hint,
                "file_size": file_size,
                "strategy": "filename_hint_alias_match",
                "candidates_count": 0,
                "needs_confirmation": False,
                "top1_attraction_id": None,
            },
        }

    confidence = float(candidates[0]["confidence"])
    matched_attraction = best.attraction if confidence >= MATCH_CONFIDENCE_THRESHOLD else None
    latency_ms = int((time.perf_counter() - start) * 1000)
    explanation_target = best.attraction["name"] if best else "候选景点"
    return {
        "matched_attraction": matched_attraction,
        "confidence": confidence,
        "candidates": candidates,
        "needs_confirmation": needs_confirmation,
        "confirmation_reason": confirmation_reason,
        "selected_attraction_id": None,
        "explanation": (
            f"mock 识景根据文件名/提示词给出 Top{len(candidates)} 候选，Top1 为 {explanation_target}。"
            f"判断依据：{_candidate_reason(best)}。"
        ),
        "suggested_questions": suggested_questions(best.attraction),
        "mode": "mock",
        "latency_ms": latency_ms,
        "metadata": {
            "filename": filename,
            "hint": hint,
            "text_hint": text_hint,
            "file_size": file_size,
            "strategy": "filename_hint_alias_match",
            "candidates_count": len(candidates),
            "needs_confirmation": needs_confirmation,
            "top1_attraction_id": best.attraction["id"],
        },
    }


def _with_provider_fields(
    result: dict[str, Any],
    *,
    provider: str,
    provider_latency_ms: int | None = None,
    vlm_observations: str | None = None,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    return {
        **result,
        "provider": provider,
        "provider_latency_ms": provider_latency_ms,
        "vlm_observations": vlm_observations,
        "fallback_reason": fallback_reason,
        "source_note": (
            "VLM 只用于识景候选增强；候选仍需映射到本地 22 个景点，确认后的讲解继续走 RAG sources。"
            if provider not in {"mock", "fallback"}
            else "mock/fallback 识景只做候选确认，不生成景区事实讲解。"
        ),
        "metadata": {
            **metadata,
            "provider": provider,
            "provider_latency_ms": provider_latency_ms,
            "vlm_observations_available": bool(vlm_observations),
            "fallback_reason": fallback_reason,
        },
    }


def recognize_image(
    *,
    filename: str | None = None,
    hint: str | None = None,
    text_hint: str | None = None,
    file_size: int | None = None,
    image_bytes: bytes | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    provider_result = recognize_visual_candidates(
        image_bytes=image_bytes or b"",
        content_type=content_type or "image/jpeg",
        hint=hint,
        text_hint=text_hint,
    )
    if provider_result.provider == "mock":
        return _with_provider_fields(
            recognize_image_mock(filename=filename, hint=hint, text_hint=text_hint, file_size=file_size),
            provider="mock",
        )

    if provider_result.provider == "fallback":
        return _with_provider_fields(
            recognize_image_mock(filename=filename, hint=hint, text_hint=text_hint, file_size=file_size),
            provider="fallback",
            provider_latency_ms=provider_result.provider_latency_ms,
            fallback_reason=provider_result.fallback_reason,
        )

    enhanced_text_hint = " ".join(
        part
        for part in [
            text_hint or "",
            provider_result.observations or "",
            " ".join(provider_result.candidate_names),
        ]
        if part
    )
    result = recognize_image_mock(
        filename=filename,
        hint=hint,
        text_hint=enhanced_text_hint,
        file_size=file_size,
    )
    if not result.get("candidates"):
        return _with_provider_fields(
            result,
            provider=provider_result.provider,
            provider_latency_ms=provider_result.provider_latency_ms,
            vlm_observations=provider_result.observations,
            fallback_reason="vlm_candidates_not_mapped_to_local_attractions",
        )
    return _with_provider_fields(
        result,
        provider=provider_result.provider,
        provider_latency_ms=provider_result.provider_latency_ms,
        vlm_observations=provider_result.observations,
    )
