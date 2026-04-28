"""Evaluate Task 06.6 route share handoff flow."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "evals" / "reports" / "route_share_latest.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.errors import ApiError  # noqa: E402
from app.services.route_service import ROUTE_CACHE, get_route_share, recommend_route  # noqa: E402


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _expect_error(code: str, fn) -> dict[str, Any]:
    try:
        fn()
    except ApiError as exc:
        actual = exc.payload.code
        return {"passed": actual == code, "expected": code, "actual": actual}
    except Exception as exc:  # pragma: no cover - surfaced in report
        return {"passed": False, "expected": code, "actual": type(exc).__name__}
    return {"passed": False, "expected": code, "actual": "NO_ERROR"}


def main() -> int:
    route = recommend_route(
        theme="family",
        time_budget_minutes=240,
        group_type="family",
        intensity="easy",
        interests=["亲子轻松", "佛教文化"],
        start_attraction_id="lingshan-ls-011",
        avoid_crowd=True,
        crowd_tolerance="medium",
    )
    share = route["share"]
    shared_route = get_route_share(route["id"], share["share_code"])

    results = [
        {
            "id": "share-code-and-url-created",
            "passed": bool(share.get("share_code")) and bool(share.get("share_url")),
            "share_code": share.get("share_code"),
            "share_url": share.get("share_url"),
        },
        {
            "id": "valid-code-returns-full-route",
            "passed": shared_route["id"] == route["id"]
            and shared_route["title"] == route["title"]
            and "recommendation_score" in shared_route
            and "decision_trace" in shared_route
            and "crowd_policy" in shared_route,
        },
        {
            "id": "stops-count-stable",
            "passed": len(shared_route.get("stops", [])) == len(route.get("stops", [])),
            "original": len(route.get("stops", [])),
            "shared": len(shared_route.get("stops", [])),
        },
        {
            "id": "does-not-expose-session-id",
            "passed": not _contains_key(shared_route, "session_id"),
        },
        {
            "id": "bad-code-rejected",
            **_expect_error(
                "ROUTE_SHARE_CODE_INVALID",
                lambda: get_route_share(route["id"], "BAD_CODE"),
            ),
        },
        {
            "id": "unknown-route-rejected",
            **_expect_error(
                "ROUTE_SHARE_NOT_FOUND",
                lambda: get_route_share("route-not-exist", "LJ-NOPE"),
            ),
        },
    ]
    ROUTE_CACHE[route["id"]]["share"]["expires_at"] = "2000-01-01T00:00:00+00:00"
    results.append(
        {
            "id": "expired-share-rejected",
            **_expect_error(
                "ROUTE_SHARE_EXPIRED",
                lambda: get_route_share(route["id"], share["share_code"]),
            ),
        }
    )

    passed = sum(1 for result in results if result["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "route_id": route["id"],
        "share_code": share["share_code"],
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "total", "passed", "failed", "accuracy"]}, ensure_ascii=False))
    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
