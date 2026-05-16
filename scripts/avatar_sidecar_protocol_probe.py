from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8282"
SEND_HUMAN_TEXT_SAMPLE = {
    "header": {
        "name": "SendHumanText",
        "request_id": "probe-request-id",
    },
    "payload": {
        "request_id": "probe-payload-id",
        "stream_key": "probe-stream-key",
        "mode": "full_text",
        "text": "为您规划好了礼佛文化路线，全程约 45 分钟。",
        "end_of_speech": True,
    },
}


@dataclass
class ProbeResult:
    base_url: str
    liveness: str
    readiness: str
    initconfig_status: str
    chat_mode: str | None
    injection_surface: str
    trusted_speaker_adapter: str
    note: str
    latency_ms: int


def fetch_json(base_url: str, path: str, timeout: float) -> tuple[str, dict[str, Any] | None]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return f"{response.status}", {}
            return f"{response.status}", json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        return f"http_{exc.code}", None
    except URLError as exc:
        return f"unreachable:{exc.reason}", None
    except TimeoutError:
        return "timeout", None
    except OSError as exc:
        return f"error:{exc}", None
    except json.JSONDecodeError:
        return "invalid_json", None


def probe(base_url: str, timeout: float) -> ProbeResult:
    started_at = time.perf_counter()
    liveness_status, _ = fetch_json(base_url, "/liveness", timeout)
    readiness_status, _ = fetch_json(base_url, "/readiness", timeout)
    init_status, init_config = fetch_json(base_url, "/openavatarchat/initconfig", timeout)
    chat_mode = None
    injection_surface = "unknown"
    trusted_adapter = "none"
    note = "OpenAvatarChat sidecar was not reachable or did not expose initconfig."

    if isinstance(init_config, dict):
        chat_mode = str(init_config.get("chat_mode") or "webrtc")
        if chat_mode == "ws":
            ws_route = init_config.get("ws_session_route") or (init_config.get("avatar_config") or {}).get("ws_session_route")
            injection_surface = f"websocket:{ws_route or '/ws/session/{session_id}'}"
            note = (
                "WebSocket SendHumanText is a user-input protocol for the chat engine. "
                "It is not a trusted direct speaker endpoint unless OpenAvatarChat is started "
                "with a custom no-LLM text-to-avatar bridge."
            )
        else:
            injection_surface = "webrtc:/webrtc/offer + RTCDataChannel(text).SendHumanText"
            note = (
                "WebUI sends SendHumanText over an established RTC data channel. "
                "In the current LiteAvatar config that text enters HUMAN_TEXT and can flow "
                "through LLM/TTS/avatar, so it must not be used as /api/avatar/speak directly."
            )
        trusted_adapter = "http_json_bridge_required"

    latency_ms = round((time.perf_counter() - started_at) * 1000)
    return ProbeResult(
        base_url=base_url,
        liveness=liveness_status,
        readiness=readiness_status,
        initconfig_status=init_status,
        chat_mode=chat_mode,
        injection_surface=injection_surface,
        trusted_speaker_adapter=trusted_adapter,
        note=note,
        latency_ms=latency_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe OpenAvatarChat sidecar protocol surfaces without sending text, "
            "downloading models, or touching vendor APIs."
        )
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAvatarChat base URL.")
    parser.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--print-send-human-text-sample",
        action="store_true",
        help="Print the WebUI SendHumanText data-channel payload shape for documentation only.",
    )
    args = parser.parse_args()

    if args.print_send_human_text_sample:
        print(json.dumps(SEND_HUMAN_TEXT_SAMPLE, ensure_ascii=False, indent=2))
        return 0

    result = probe(args.base_url, args.timeout)
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(f"base_url: {result.base_url}")
        print(f"liveness: {result.liveness}")
        print(f"readiness: {result.readiness}")
        print(f"initconfig_status: {result.initconfig_status}")
        print(f"chat_mode: {result.chat_mode}")
        print(f"injection_surface: {result.injection_surface}")
        print(f"trusted_speaker_adapter: {result.trusted_speaker_adapter}")
        print(f"latency_ms: {result.latency_ms}")
        print(f"note: {result.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
