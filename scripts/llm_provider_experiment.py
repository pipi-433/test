from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.qa_service import answer_question  # noqa: E402


QUESTIONS = [
    "灵山大佛有什么看点？",
    "梵宫适合怎么游览？",
    "讲一个和灵山大佛有关的小故事",
    "佛教里的莲花有什么文化寓意？",
    "带老人孩子两小时怎么玩？",
    "现在人多吗？",
    "帮我规划半天路线，避开人多的地方",
    "灵山大佛今天开放到几点？",
]

SCENARIOS = [
    {
        "name": "A mock/local only",
        "env": {
            "LLM_PROVIDER": "mock",
            "LLM_MODEL": "",
            "LLM_FALLBACK_MODEL": "",
            "LLM_ENABLE_SEARCH": "false",
            "LLM_SEARCH_POLICY": "gap_only",
            "LLM_THINKING_MODE": "off",
            "LLM_THINKING_BUDGET": "",
            "LLM_MAX_OUTPUT_TOKENS": "300",
        },
    },
    {
        "name": "B qwen-plus local",
        "env": {
            "LLM_PROVIDER": "dashscope",
            "LLM_MODEL": "qwen-plus",
            "LLM_FALLBACK_MODEL": "",
            "LLM_ENABLE_SEARCH": "false",
            "LLM_SEARCH_POLICY": "gap_only",
            "LLM_THINKING_MODE": "off",
            "LLM_THINKING_BUDGET": "",
            "LLM_MAX_OUTPUT_TOKENS": "300",
        },
    },
    {
        "name": "C qwen-max local",
        "env": {
            "LLM_PROVIDER": "dashscope",
            "LLM_MODEL": "qwen-max",
            "LLM_FALLBACK_MODEL": "",
            "LLM_ENABLE_SEARCH": "false",
            "LLM_SEARCH_POLICY": "gap_only",
            "LLM_THINKING_MODE": "off",
            "LLM_THINKING_BUDGET": "",
            "LLM_MAX_OUTPUT_TOKENS": "300",
        },
    },
    {
        "name": "D qwen+gap search",
        "env": {
            "LLM_PROVIDER": "dashscope",
            "LLM_MODEL": "qwen-plus",
            "LLM_FALLBACK_MODEL": "qwen-max",
            "LLM_ENABLE_SEARCH": "true",
            "LLM_SEARCH_POLICY": "gap_only",
            "LLM_THINKING_MODE": "off",
            "LLM_THINKING_BUDGET": "",
            "LLM_MAX_OUTPUT_TOKENS": "300",
        },
    },
]


@contextmanager
def scenario_env(values: dict[str, str]) -> Iterator[None]:
    keys = set(values) | {
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_FALLBACK_MODEL",
        "LLM_ENABLE_SEARCH",
        "LLM_SEARCH_POLICY",
        "LLM_THINKING_MODE",
        "LLM_THINKING_BUDGET",
        "LLM_MAX_OUTPUT_TOKENS",
    }
    previous = {key: os.environ.get(key) for key in keys}
    for key, value in values.items():
        os.environ[key] = value
    try:
        get_settings.cache_clear()
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


def answer_chars(answer: Any) -> int:
    text = str(answer or "")
    return len("".join(text.split()))


def format_cell(value: Any, width: int) -> str:
    text = str(value if value is not None else "-")
    if len(text) > width:
        text = text[: max(0, width - 3)] + "..."
    return text.ljust(width)


def main() -> int:
    print("LLM provider experiment: local-first + Qwen rewrite + gap-only search + low/no thinking")
    print(f"DASHSCOPE_API_KEY present: {bool(os.getenv('DASHSCOPE_API_KEY', '').strip())}")
    print("Keys are never printed by this script.\n")

    header = [
        ("scenario", 18),
        ("question", 18),
        ("provider", 20),
        ("model", 12),
        ("grounding_mode", 26),
        ("provider_ms", 11),
        ("total_ms", 8),
        ("sources", 7),
        ("fallback_reason", 34),
        ("chars", 6),
        ("search", 6),
    ]
    print(" | ".join(format_cell(name, width) for name, width in header))
    print("-+-".join("-" * width for _, width in header))

    for scenario in SCENARIOS:
        with scenario_env(scenario["env"]):
            for question in QUESTIONS:
                started = time.perf_counter()
                result = answer_question(question=question, top_k=5)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                grounding_mode = result.get("grounding_mode")
                row = [
                    (scenario["name"], 18),
                    (question, 18),
                    (result.get("provider") or result.get("mode"), 20),
                    (result.get("model"), 12),
                    (grounding_mode, 26),
                    (result.get("provider_latency_ms"), 11),
                    (elapsed_ms, 8),
                    (len(result.get("sources") or []), 7),
                    (result.get("fallback_reason"), 34),
                    (answer_chars(result.get("answer")), 6),
                    ("yes" if grounding_mode == "dashscope_search_gap_fill" else "no", 6),
                ]
                print(" | ".join(format_cell(value, width) for value, width in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
