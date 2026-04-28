from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def _score_attraction(attraction: dict[str, Any], text: str) -> VisionMatch:
    compact_text = _compact(text)
    reasons: list[str] = []
    score = 0.0

    stable_id = attraction["id"]
    legacy_id = attraction.get("attraction_id", "")
    name = attraction.get("name", "")
    aliases = [stable_id, legacy_id, name, *ALIAS_MAP.get(stable_id, [])]

    for alias in aliases:
        alias_norm = _normalize(alias)
        alias_compact = _compact(alias_norm)
        if not alias_compact:
            continue
        if alias_norm and alias_norm in text:
            score += 0.82 if alias_norm in {stable_id, legacy_id.lower(), name.lower()} else 0.7
            reasons.append(f"alias:{alias}")
        elif alias_compact and alias_compact in compact_text:
            score += 0.72
            reasons.append(f"compact_alias:{alias}")

    for tag in attraction.get("tags", []):
        tag_compact = _compact(tag)
        if tag_compact and tag_compact in compact_text:
            score += 0.18
            reasons.append(f"tag:{tag}")

    if attraction.get("scenic_area") and _compact(attraction["scenic_area"]) in compact_text:
        score += 0.1
        reasons.append("scenic_area")

    return VisionMatch(attraction=attraction, score=round(min(score, 1.0), 4), reasons=reasons[:6])


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


def recognize_image_mock(
    *,
    filename: str | None = None,
    hint: str | None = None,
    text_hint: str | None = None,
    file_size: int | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    text = _candidate_text(filename=filename, hint=hint, text_hint=text_hint)
    matches = [_score_attraction(attraction, text) for attraction in list_attractions()]
    matches.sort(key=lambda item: (-item.score, item.attraction["id"]))
    best = matches[0] if matches else None

    if best is None or best.score < 0.45:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "matched_attraction": None,
            "confidence": 0.0,
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
            },
        }

    confidence = round(min(0.99, 0.52 + best.score * 0.43), 2)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "matched_attraction": best.attraction,
        "confidence": confidence,
        "explanation": (
            f"mock 识景根据文件名/提示词命中 {best.attraction['name']}。"
            f"匹配依据：{', '.join(best.reasons) if best.reasons else '样例映射'}。"
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
        },
    }
