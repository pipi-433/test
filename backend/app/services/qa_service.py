from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from app.repositories.content_repository import (
    get_attraction,
    list_all_knowledge_chunks,
    list_attractions,
    list_knowledge_chunks,
)
from app.services.crowd_service import get_crowd_snapshot
from app.services.operation_service import list_operation_events
from app.services.query_understanding_service import build_gate_answer, understand_query
from app.services.recommendation_service import compare_targets, recommend_attractions
from app.services.scenic_area_service import build_scenic_area_intro


DEFAULT_TOP_K = 5
STOPWORDS = {
    "什么",
    "怎么",
    "哪里",
    "如何",
    "一下",
    "介绍",
    "讲解",
    "景点",
    "景区",
    "适合",
    "游览",
    "推荐",
    "资料",
    "这个",
    "那个",
    "请问",
    "可以",
    "有没有",
}


@dataclass
class ScoredChunk:
    chunk: dict[str, Any]
    score: float
    reasons: list[str]


def _norm(text: Any) -> str:
    return str(text or "").lower()


def _windows(text: str, size: int) -> set[str]:
    compact = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9-]+", "", text)
    return {compact[index : index + size].lower() for index in range(max(0, len(compact) - size + 1))}


def _extract_terms(question: str, visitor_profile: dict[str, Any] | None, attractions: list[dict[str, Any]]) -> list[str]:
    terms: set[str] = set()
    raw = _norm(question)

    for item in re.findall(r"[A-Za-z]+-\d+|[A-Za-z0-9_-]+|[\u4e00-\u9fff]{2,}", question):
        value = item.lower()
        if value not in STOPWORDS and len(value) >= 2:
            terms.add(value)

    for size in (2, 3, 4):
        terms.update(token for token in _windows(question, size) if token not in STOPWORDS)

    for attraction in attractions:
        name = _norm(attraction.get("name"))
        if name and name in raw:
            terms.add(name)
        for tag in attraction.get("tags", []):
            tag_norm = _norm(tag)
            if tag_norm and tag_norm in raw:
                terms.add(tag_norm)

    profile = visitor_profile or {}
    for interest in profile.get("interests", []) or []:
        value = _norm(interest).strip()
        if value:
            terms.add(value)

    return sorted(terms, key=lambda value: (-len(value), value))[:80]


def _score_chunk(chunk: dict[str, Any], terms: list[str], attraction: dict[str, Any] | None) -> ScoredChunk:
    title = _norm(chunk.get("title"))
    content = _norm(chunk.get("content"))
    tags = [_norm(tag) for tag in chunk.get("tags", [])]
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    chunk_type = _norm(chunk.get("chunk_type"))
    is_admin_chunk = chunk_type.startswith("admin_") or bool(metadata.get("admin_source"))
    attraction_terms: set[str] = set()
    if attraction:
        attraction_name = _norm(attraction.get("name"))
        if attraction_name:
            attraction_terms.add(attraction_name)
            for size in (2, 3, 4):
                attraction_terms.update(_windows(attraction_name, size))
    has_admin_specific_hit = is_admin_chunk and any(
        term not in attraction_terms and (term in title or term in tags or term in content) for term in terms
    )
    haystack = f"{title} {content} {' '.join(tags)}"
    score = 0.0
    reasons: list[str] = []

    priority = float(chunk.get("priority") or 0)
    score += min(priority, 100.0) / 100.0 * 0.18

    if has_admin_specific_hit:
        # Admin-published chunks are curated local updates. Boost only after
        # lexical matching filters run, so generic queries still cannot leak in.
        score += 1.15
        reasons.append("admin_dynamic_chunk")

    if attraction and chunk.get("attraction_id") == attraction.get("id"):
        score += 1.2
        reasons.append("attraction_filter")

    if attraction and not (is_admin_chunk and not has_admin_specific_hit):
        name = _norm(attraction.get("name"))
        if name and name in haystack:
            score += 0.7
            reasons.append("attraction_name")

    for term in terms:
        if len(term) < 2:
            continue
        if is_admin_chunk and not has_admin_specific_hit and term in attraction_terms:
            continue
        if term in title:
            score += 1.0 if len(term) >= 3 else 0.55
            reasons.append(f"title:{term}")
        if term in tags:
            score += 0.8
            reasons.append(f"tag:{term}")
        if term in content:
            score += 0.65 if len(term) >= 3 else 0.28
            reasons.append(f"content:{term}")

    # Keep repeated generic bigram hits from dominating.
    score = round(min(score, 20.0), 4)
    return ScoredChunk(chunk=chunk, score=score, reasons=reasons[:8])


def _has_query_term_hit(item: ScoredChunk) -> bool:
    return any(reason.startswith(("title:", "tag:", "content:")) for reason in item.reasons)


def _answer_sources(sources: list[ScoredChunk]) -> list[ScoredChunk]:
    picked = list(sources[:3])
    admin_source = next(
        (
            item
            for item in sources
            if _norm(item.chunk.get("chunk_type")).startswith("admin_")
            or (isinstance(item.chunk.get("metadata"), dict) and item.chunk["metadata"].get("admin_source"))
        ),
        None,
    )
    if admin_source and all(item.chunk.get("id") != admin_source.chunk.get("id") for item in picked):
        if "admin_dynamic_chunk" in admin_source.reasons:
            picked = [admin_source, *picked[:2]]
    return picked


def _is_generic_attraction_question(question: str) -> bool:
    compact = re.sub(r"[\s，。！？；、,.!?;:：]+", "", question)
    guide_markers = ("怎么游览", "如何游览", "怎么玩", "介绍", "讲解", "看点", "亮点", "适合", "推荐")
    context_markers = ("这个景点", "这个地方", "这里", "当前景点", "该景点", "它")
    if any(marker in compact for marker in context_markers) and any(marker in compact for marker in guide_markers):
        return True
    bare_generic_questions = {
        "介绍",
        "介绍一下",
        "讲解",
        "讲解一下",
        "有什么看点",
        "有啥看点",
        "看点",
        "亮点",
        "游览建议",
        "怎么游览",
        "如何游览",
        "怎么玩",
        "适合怎么游览",
        "推荐怎么玩",
    }
    return compact in bare_generic_questions


def _selected_attraction_context_chunks(chunks: list[dict[str, Any]], top_k: int) -> list[ScoredChunk]:
    scored = [
        ScoredChunk(
            chunk=chunk,
            score=round(1.0 + min(float(chunk.get("priority") or 0), 100.0) / 100.0, 4),
            reasons=["selected_attraction_context"],
        )
        for chunk in chunks
    ]
    scored.sort(key=lambda item: (-item.score, item.chunk.get("id", "")))
    return scored[: max(1, min(top_k, 10))]


def retrieve_chunks(
    *,
    question: str,
    attraction_id: str | None = None,
    visitor_profile: dict[str, Any] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[list[ScoredChunk], dict[str, Any] | None, list[str]]:
    attractions = list_attractions()
    attraction = None
    if attraction_id:
        attraction = get_attraction(attraction_id)
        if attraction is None:
            # The endpoint handles this as a friendly fallback rather than a hard error.
            return [], None, []
        chunks = list_knowledge_chunks(attraction["id"])
    else:
        chunks = list_all_knowledge_chunks()

    terms = _extract_terms(question, visitor_profile, attractions)
    scored = [_score_chunk(chunk, terms, attraction) for chunk in chunks]

    if attraction:
        scored = [item for item in scored if item.score >= 0.8 and _has_query_term_hit(item)]
        if not scored and _is_generic_attraction_question(question):
            return _selected_attraction_context_chunks(chunks, top_k), attraction, terms
    else:
        scored = [item for item in scored if item.score >= 0.55 and _has_query_term_hit(item)]

    scored.sort(key=lambda item: (-item.score, -(item.chunk.get("priority") or 0), item.chunk.get("id", "")))
    return scored[: max(1, min(top_k, 10))], attraction, terms


def _snippet(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[。！？；])", text)
    picked = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(picked) + len(sentence) > limit and picked:
            break
        picked += sentence
        if len(picked) >= limit:
            break
    if not picked:
        picked = text[:limit]
    return picked[:limit].rstrip("，；、 ") + ("。" if picked and picked[-1] not in "。！？" else "")


def _profile_hint(visitor_profile: dict[str, Any] | None) -> str:
    profile = visitor_profile or {}
    hints: list[str] = []
    group_type = profile.get("group_type")
    time_budget = profile.get("time_budget_minutes")
    interests = profile.get("interests") or []
    if group_type == "family":
        hints.append("同行有亲子需求，建议节奏放缓，优先选择停留舒适、讲解故事性强的点位")
    elif group_type:
        hints.append(f"已按 {group_type} 同行类型控制讲解重点")
    if time_budget:
        hints.append(f"你的可用时间约 {time_budget} 分钟，建议先抓重点，不要把路线排得太满")
    if interests:
        hints.append(f"我会优先结合 {'、'.join(map(str, interests[:4]))} 来讲")
    return "；".join(hints)


def build_mock_answer(
    *,
    question: str,
    sources: list[ScoredChunk],
    attraction: dict[str, Any] | None,
    attraction_id: str | None,
    visitor_profile: dict[str, Any] | None,
) -> str:
    if attraction_id and attraction is None:
        return (
            "我在本地景区知识库里没有找到这个景点编号。"
            "你可以换成景点名称提问，或先查看景点列表后再继续。"
        )

    if not sources:
        return (
            "这个问题我暂时没有在本地资料里检索到可靠依据，所以先不编造答案。"
            "你可以换成具体景点名、演出名或游览需求再问一次，我会继续用 mock 知识库帮你查。"
        )

    place = attraction["name"] if attraction else "你问到的内容"
    lines = [f"我用本地 mock 知识库为你查到：{place}可以这样理解。"]
    for index, item in enumerate(_answer_sources(sources), start=1):
        lines.append(f"{index}. {_snippet(item.chunk.get('content', ''))}")

    hint = _profile_hint(visitor_profile)
    if hint:
        lines.append(f"结合你的游览偏好，{hint}。")

    lines.append("以上回答来自本地资料切片检索，当前模式为 mock。")
    return "\n".join(lines)


def _answer_scenic_area_intro(understanding: dict[str, Any]) -> dict[str, Any]:
    slots = understanding.get("slots") if isinstance(understanding.get("slots"), dict) else {}
    scenic_area = slots.get("scenic_area")
    intro = build_scenic_area_intro(str(scenic_area) if scenic_area else None)
    answer = f"{intro['title']}：{intro['summary']}\n" + "\n".join(f"{index}. {item}" for index, item in enumerate(intro["highlights"][:4], start=1))
    return {
        "answer": answer,
        "scenic_area_intro": intro,
        "suggested_questions": intro.get("suggested_questions", []),
    }


def _answer_interest_recommendation(understanding: dict[str, Any]) -> dict[str, Any]:
    slots = understanding.get("slots") if isinstance(understanding.get("slots"), dict) else {}
    recommendations = recommend_attractions(
        interests=slots.get("interests") or [],
        scenic_area=slots.get("scenic_area"),
        group_type=slots.get("group_type"),
        limit=5,
    )
    if recommendations:
        lead = "我会先按本地 22 个景点的标签、类别和简介做规则评分，推荐这些点："
        lines = [lead]
        for index, item in enumerate(recommendations[:3], start=1):
            lines.append(f"{index}. {item['name']}（{item['scenic_area']}）：{item['reason']}")
        answer = "\n".join(lines)
    else:
        answer = "本地景点资料里暂时没有匹配到足够明确的推荐项，我不会硬凑结果。你可以补充兴趣，例如历史、拍照、亲子、自然或祈福。"
    return {
        "answer": answer,
        "recommendations": recommendations,
        "suggested_questions": [item["suggested_question"] for item in recommendations[:4]],
    }


def _answer_comparison(understanding: dict[str, Any]) -> dict[str, Any]:
    slots = understanding.get("slots") if isinstance(understanding.get("slots"), dict) else {}
    comparison = compare_targets(
        compare_targets=slots.get("compare_targets") or [],
        interests=slots.get("interests") or ["photo"],
    )
    answer = comparison["recommendation"] + "\n" + "\n".join(comparison.get("reasons", [])[:3])
    return {
        "answer": answer,
        "comparison": comparison,
        "suggested_questions": comparison.get("suggested_next_questions", []),
    }


def _answer_crowd_status(understanding: dict[str, Any]) -> dict[str, Any]:
    slots = understanding.get("slots") if isinstance(understanding.get("slots"), dict) else {}
    scenic_area = slots.get("scenic_area")
    crowd_items = get_crowd_snapshot()["items"]
    if scenic_area:
        crowd_items = [item for item in crowd_items if item.get("scenic_area") == scenic_area]
    high_or_medium = [item for item in crowd_items if item.get("crowd_level") in {"high", "medium"}]
    operation_events = list_operation_events(active_only=True)
    if scenic_area:
        operation_events = [event for event in operation_events if event.get("scenic_area") == scenic_area]
    focus_items = sorted(high_or_medium, key=lambda item: (-int(item.get("crowd_score") or 0), item.get("name") or ""))[:5]
    lines = ["当前为模拟拥挤度和运营事件演示数据，不代表真实硬件客流。"]
    if focus_items:
        lines.append("较需要关注的点位：" + "；".join(f"{item['name']} {item['crowd_score']} 分，等待约 {item['wait_minutes']} 分钟" for item in focus_items[:3]))
    else:
        lines.append("当前模拟拥挤度整体较舒适。")
    if operation_events:
        lines.append("运营提醒：" + "；".join(f"{event['attraction_name']}：{event['message']}（{event['source']}）" for event in operation_events[:3]))
    crowd_status = {
        "items": focus_items,
        "operation_events": operation_events[:5],
        "source_note": "crowd=mock_simulation；operation=manual_admin/mock_simulation，均为演示数据。",
    }
    return {
        "answer": "\n".join(lines),
        "crowd_status": crowd_status,
        "suggested_questions": ["帮我规划一条避开人多的路线", "有哪些临时关闭？", "哪些地方适合现在去？"],
    }


def answer_question(
    *,
    question: str,
    attraction_id: str | None = None,
    visitor_profile: dict[str, Any] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    start = time.perf_counter()
    if attraction_id and get_attraction(attraction_id) is None:
        understanding = understand_query(question, selected_attraction_id=attraction_id)
        answer = build_mock_answer(
            question=question,
            sources=[],
            attraction=None,
            attraction_id=attraction_id,
            visitor_profile=visitor_profile,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "answer": answer,
            "type": "out_of_scope",
            "sources": [],
            "mode": "mock",
            "latency_ms": latency_ms,
            "understanding": {
                **understanding,
                "should_retrieve": False,
                "reasons": [*(understanding.get("reasons") or []), "invalid_attraction_id"],
            },
        }

    understanding = understand_query(question, selected_attraction_id=attraction_id)
    handler = understanding.get("handler")
    if handler == "route_planner":
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "answer": "这是路线规划需求，应交给受约束的 Route Planner 生成路线；不会直接用 RAG 编造行程。",
            "type": "route",
            "sources": [],
            "mode": "mock",
            "latency_ms": latency_ms,
            "understanding": understanding,
        }
    if handler in {"scenic_area_intro", "interest_recommendation", "comparison", "crowd_status"}:
        if handler == "scenic_area_intro":
            extra = _answer_scenic_area_intro(understanding)
            response_type = "scenic_area_intro"
        elif handler == "interest_recommendation":
            extra = _answer_interest_recommendation(understanding)
            response_type = "recommendation"
        elif handler == "comparison":
            extra = _answer_comparison(understanding)
            response_type = "comparison"
        else:
            extra = _answer_crowd_status(understanding)
            response_type = "crowd_status"
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            **extra,
            "type": response_type,
            "sources": [],
            "mode": "mock",
            "latency_ms": latency_ms,
            "understanding": understanding,
        }

    if not understanding.get("should_retrieve"):
        latency_ms = int((time.perf_counter() - start) * 1000)
        response_type = "clarification" if understanding.get("needs_clarification") else "out_of_scope"
        return {
            "answer": build_gate_answer(understanding),
            "type": response_type,
            "sources": [],
            "mode": "mock",
            "latency_ms": latency_ms,
            "understanding": understanding,
        }

    retrieval_attraction_id = attraction_id
    if not retrieval_attraction_id:
        attraction_entities = [
            entity
            for entity in understanding.get("entities", [])
            if isinstance(entity, dict) and entity.get("type") == "attraction" and entity.get("id")
        ]
        if len(attraction_entities) == 1:
            retrieval_attraction_id = str(attraction_entities[0]["id"])

    sources, attraction, _terms = retrieve_chunks(
        question=question,
        attraction_id=retrieval_attraction_id,
        visitor_profile=visitor_profile,
        top_k=top_k,
    )
    answer = build_mock_answer(
        question=question,
        sources=sources,
        attraction=attraction,
        attraction_id=retrieval_attraction_id,
        visitor_profile=visitor_profile,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "answer": answer,
        "type": "qa",
        "sources": [
            {
                "chunk_id": item.chunk["id"],
                "title": item.chunk["title"],
                "source_file": item.chunk["source_file"],
                "source_section": item.chunk["source_section"],
                "attraction_id": item.chunk["attraction_id"],
                "score": item.score,
            }
            for item in sources
        ],
        "mode": "mock",
        "latency_ms": latency_ms,
        "understanding": understanding,
    }
