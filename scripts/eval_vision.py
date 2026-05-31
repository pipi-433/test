"""Run the Task 04.5 vision recognition evaluation set."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
EVAL_PATH = ROOT / "evals" / "vision_samples.jsonl"
REPORT_PATH = ROOT / "evals" / "reports" / "vision_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.providers.vlm import VisionProviderResult  # noqa: E402
from app.services.vision_service import recognize_image, recognize_image_mock, recognize_image_with_vlm_context  # noqa: E402


SUPPORTED_PROVIDERS = {"mock", "dashscope"}


def load_dotenv_if_present() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(EVAL_PATH.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return cases


def is_cover_case(case: dict[str, Any]) -> bool:
    image_path = Path(str(case.get("image_path") or ""))
    return "__1" in image_path.stem and str(case.get("id") or "").startswith("vision_real_")


def filtered_cases(cases: list[dict[str, Any]], *, only_cover: bool, limit: int | None) -> list[dict[str, Any]]:
    selected = [case for case in cases if is_cover_case(case)] if only_cover else list(cases)
    if limit is not None:
        return selected[: max(0, limit)]
    return selected


def _safe_eval_filename(case: dict[str, Any], image_path: Path, *, provider: str) -> str:
    if provider == "mock":
        return image_path.name
    return f"{case['id']}{image_path.suffix.lower() or '.jpg'}"


def check_case(case: dict[str, Any], *, provider: str, use_hints: bool) -> dict[str, Any]:
    image_path = ROOT / case["image_path"]
    content = image_path.read_bytes()
    filename = _safe_eval_filename(case, image_path, provider=provider)
    hint = case.get("hint") if provider == "mock" or use_hints else None
    text_hint = case.get("text_hint") if provider == "mock" or use_hints else None
    if provider == "mock":
        response = recognize_image_mock(
            filename=filename,
            hint=hint,
            text_hint=text_hint,
            file_size=len(content),
        )
    else:
        response = recognize_image(
            filename=filename,
            hint=hint,
            text_hint=text_hint,
            file_size=len(content),
            image_bytes=content,
            content_type="image/jpeg",
        )
    matched = response["matched_attraction"]
    matched_id = matched["id"] if matched else None
    candidates = response.get("candidates", [])
    candidate_ids = [item["attraction"]["id"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    candidate_names = [item["attraction"]["name"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    candidate_confidences = [float(item.get("confidence") or 0.0) for item in candidates if isinstance(item, dict)]
    expect_match = case.get("expect_match", True)
    id_ok = matched_id == case.get("expected_attraction_id")
    match_ok = (matched is not None) if expect_match else (matched is None)
    old_fields_ok = all(key in response for key in ["matched_attraction", "confidence", "suggested_questions"])
    candidates_present_ok = (len(candidates) >= 1) if expect_match else len(candidates) == 0
    top1_ok = (candidate_ids[0] == case.get("expected_attraction_id")) if expect_match and candidate_ids else not expect_match
    top3_ok = (case.get("expected_attraction_id") in candidate_ids[:3]) if expect_match else not candidate_ids
    max3_ok = len(candidates) <= 3
    sorted_ok = candidate_confidences == sorted(candidate_confidences, reverse=True)
    needs_confirmation_ok = isinstance(response.get("needs_confirmation"), bool)
    passed = top3_ok and old_fields_ok and candidates_present_ok and max3_ok and sorted_ok and needs_confirmation_ok
    return {
        "id": case["id"],
        "image_path": case["image_path"],
        "expected_attraction_id": case.get("expected_attraction_id"),
        "expected_attraction_name": case.get("expected_attraction_name"),
        "matched_attraction_id": matched_id,
        "top1_attraction_id": candidate_ids[0] if candidate_ids else None,
        "candidate_ids": candidate_ids,
        "candidate_names": candidate_names,
        "candidates_count": len(candidates),
        "confidence": response["confidence"],
        "passed": passed,
        "match_ok": match_ok,
        "id_ok": id_ok,
        "old_fields_ok": old_fields_ok,
        "candidates_present_ok": candidates_present_ok,
        "top1_ok": top1_ok,
        "top3_ok": top3_ok,
        "max3_ok": max3_ok,
        "sorted_ok": sorted_ok,
        "needs_confirmation_ok": needs_confirmation_ok,
        "needs_confirmation": response.get("needs_confirmation"),
        "latency_ms": response["latency_ms"],
        "provider": response.get("provider") or provider,
        "provider_latency_ms": response.get("provider_latency_ms"),
        "fallback_reason": response.get("fallback_reason"),
        "vlm_candidate_ids": (response.get("metadata") or {}).get("vlm_candidate_ids") if isinstance(response.get("metadata"), dict) else None,
        "strategy": (response.get("metadata") or {}).get("strategy") if isinstance(response.get("metadata"), dict) else None,
        "explanation": response["explanation"],
    }


def check_ambiguous_case() -> dict[str, Any]:
    response = recognize_image_mock(
        filename="ambiguous_mock.jpg",
        hint="大佛 九龙",
        text_hint="",
        file_size=12,
    )
    candidates = response.get("candidates", [])
    candidate_ids = [item["attraction"]["id"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    passed = (
        len(candidates) >= 2
        and len(candidates) <= 3
        and response.get("needs_confirmation") is True
        and {"lingshan-ls-011", "lingshan-ls-006"}.issubset(set(candidate_ids))
    )
    return {
        "id": "vision_ambiguous_confirmation",
        "image_path": "synthetic",
        "expected_attraction_id": None,
        "matched_attraction_id": (response.get("matched_attraction") or {}).get("id")
        if isinstance(response.get("matched_attraction"), dict)
        else None,
        "candidate_ids": candidate_ids,
        "candidates_count": len(candidates),
        "confidence": response.get("confidence"),
        "passed": passed,
        "match_ok": True,
        "id_ok": True,
        "old_fields_ok": all(key in response for key in ["matched_attraction", "confidence", "suggested_questions"]),
        "candidates_present_ok": len(candidates) >= 2,
        "top1_ok": True,
        "max3_ok": len(candidates) <= 3,
        "sorted_ok": True,
        "needs_confirmation_ok": response.get("needs_confirmation") is True,
        "needs_confirmation": response.get("needs_confirmation"),
        "latency_ms": response["latency_ms"],
        "explanation": response["explanation"],
    }


def check_vlm_background_buddha_case() -> dict[str, Any]:
    provider_result = VisionProviderResult(
        provider="dashscope",
        observations="画面主体是圆形水池、九龙喷泉和灌浴广场，远处背景可见巨大佛像。",
        primary_subject="圆形水池中央的九龙灌浴喷泉和广场水景",
        background_landmarks=["远处巨大佛像", "背景佛像"],
        visual_features=["水池", "九龙", "灌浴", "喷泉", "圆形广场", "远处佛像"],
        candidate_names=["灵山大佛", "九龙灌浴"],
        uncertainty_reason="远处佛像明显但不是画面主体",
        fallback_reason=None,
        provider_latency_ms=1200,
        candidate_ids=[],
    )
    response = recognize_image_with_vlm_context(
        filename="vlm_scene_with_background_buddha.jpg",
        hint="",
        text_hint="",
        file_size=128,
        provider_result=provider_result,
    )
    candidates = response.get("candidates", [])
    candidate_ids = [item["attraction"]["id"] for item in candidates if isinstance(item, dict) and isinstance(item.get("attraction"), dict)]
    candidate_confidences = [float(item.get("confidence") or 0.0) for item in candidates if isinstance(item, dict)]
    matched = response.get("matched_attraction")
    matched_id = matched["id"] if isinstance(matched, dict) else None
    passed = (
        len(candidates) >= 1
        and candidate_ids[0] == "lingshan-ls-006"
        and "lingshan-ls-011" in candidate_ids
        and len(candidates) <= 3
        and candidate_confidences == sorted(candidate_confidences, reverse=True)
        and "mock 识景根据文件名/提示词" not in str(response.get("explanation") or "")
    )
    return {
        "id": "vision_vlm_jiulong_background_buddha_rerank",
        "image_path": "synthetic",
        "expected_attraction_id": "lingshan-ls-006",
        "matched_attraction_id": matched_id,
        "candidate_ids": candidate_ids,
        "candidates_count": len(candidates),
        "confidence": response.get("confidence"),
        "passed": passed,
        "match_ok": matched_id == "lingshan-ls-006",
        "id_ok": candidate_ids[0] == "lingshan-ls-006" if candidate_ids else False,
        "old_fields_ok": all(key in response for key in ["matched_attraction", "confidence", "suggested_questions"]),
        "candidates_present_ok": len(candidates) >= 1,
        "top1_ok": candidate_ids[0] == "lingshan-ls-006" if candidate_ids else False,
        "top3_ok": "lingshan-ls-006" in candidate_ids[:3],
        "max3_ok": len(candidates) <= 3,
        "sorted_ok": candidate_confidences == sorted(candidate_confidences, reverse=True),
        "needs_confirmation_ok": isinstance(response.get("needs_confirmation"), bool),
        "needs_confirmation": response.get("needs_confirmation"),
        "latency_ms": response["latency_ms"],
        "explanation": response["explanation"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate local scenic image recognition.")
    parser.add_argument("--provider", choices=sorted(SUPPORTED_PROVIDERS), default="mock")
    parser.add_argument("--only-cover", action="store_true", help="Evaluate only real cover samples named attraction-id__1.jpg.")
    parser.add_argument("--limit", type=int, default=None, help="Limit cases after filtering.")
    parser.add_argument("--use-hints", action="store_true", help="Pass sample hint/text_hint to non-mock providers.")
    parser.add_argument("--skip-synthetic", action="store_true", help="Skip synthetic regression checks.")
    parser.add_argument("--report-path", default=str(REPORT_PATH), help="JSON report output path.")
    return parser


def summarize_results(results: list[dict[str, Any]], *, provider: str) -> dict[str, Any]:
    real_results = [result for result in results if result.get("expected_attraction_id")]
    total = len(results)
    top1_count = sum(1 for result in real_results if result.get("top1_ok"))
    top3_count = sum(1 for result in real_results if result.get("top3_ok"))
    latency_values = [int(result.get("latency_ms") or 0) for result in results]
    provider_latency_values = [
        int(result["provider_latency_ms"])
        for result in results
        if isinstance(result.get("provider_latency_ms"), (int, float))
    ]
    fallback_count = sum(1 for result in results if result.get("fallback_reason") or result.get("provider") == "fallback")
    no_candidate_count = sum(1 for result in results if not result.get("candidate_ids"))
    confusion_counter: Counter[tuple[str, str | None]] = Counter()
    for result in real_results:
        expected = str(result.get("expected_attraction_id") or "")
        top1 = result.get("top1_attraction_id")
        if expected and top1 != expected:
            confusion_counter[(expected, str(top1) if top1 else None)] += 1
    confusion_pairs = [
        {"expected": expected, "top1": top1, "count": count}
        for (expected, top1), count in confusion_counter.most_common()
    ]
    return {
        "mode": provider,
        "total": total,
        "passed": sum(1 for result in results if result.get("passed")),
        "failed": sum(1 for result in results if not result.get("passed")),
        "top1_accuracy": round(top1_count / len(real_results), 4) if real_results else 0.0,
        "top3_accuracy": round(top3_count / len(real_results), 4) if real_results else 0.0,
        "avg_latency_ms": round(sum(latency_values) / len(latency_values), 2) if latency_values else 0.0,
        "avg_provider_latency_ms": round(sum(provider_latency_values) / len(provider_latency_values), 2)
        if provider_latency_values
        else 0.0,
        "fallback_count": fallback_count,
        "no_candidate_count": no_candidate_count,
        "confusion_pairs": confusion_pairs,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv_if_present()
    os.environ["VLM_PROVIDER"] = args.provider
    if args.provider == "dashscope":
        os.environ.setdefault("VLM_MODEL", "qwen-vl-plus")
    get_settings.cache_clear()

    cases = filtered_cases(load_cases(), only_cover=args.only_cover, limit=args.limit)
    results = [check_case(case, provider=args.provider, use_hints=args.use_hints) for case in cases]
    if args.provider == "mock" and not args.only_cover and not args.skip_synthetic:
        results.append(check_ambiguous_case())
        results.append(check_vlm_background_buddha_case())
    passed = sum(1 for result in results if result["passed"])
    summary = summarize_results(results, provider=args.provider)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": args.provider,
        "only_cover": args.only_cover,
        "limit": args.limit,
        "use_hints": args.use_hints or args.provider == "mock",
        "total": summary["total"],
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "top1_accuracy": summary["top1_accuracy"],
        "top3_accuracy": summary["top3_accuracy"],
        "avg_latency_ms": summary["avg_latency_ms"],
        "avg_provider_latency_ms": summary["avg_provider_latency_ms"],
        "fallback_count": summary["fallback_count"],
        "no_candidate_count": summary["no_candidate_count"],
        "confusion_pairs": summary["confusion_pairs"],
        "results": results,
    }
    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_keys = [
        "mode",
        "total",
        "passed",
        "failed",
        "accuracy",
        "top1_accuracy",
        "top3_accuracy",
        "avg_latency_ms",
        "avg_provider_latency_ms",
        "fallback_count",
        "no_candidate_count",
        "confusion_pairs",
    ]
    print(json.dumps({key: report[key] for key in summary_keys}, ensure_ascii=False))
    if report["failed"]:
        for result in results:
            if not result["passed"]:
                print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
