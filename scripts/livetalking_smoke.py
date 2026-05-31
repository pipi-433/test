"""Small LiveTalking sidecar smoke helper.

This script talks only to a local LiveTalking sidecar. It does not call model
vendors and does not generate answers. Use /human with type=echo for trusted
backend text, never type=chat.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _read_url(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def _post_json(url: str, payload: dict, timeout: float) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(raw)


def _post_multipart_file(
    url: str,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
    timeout: float,
) -> tuple[int, dict]:
    boundary = f"----lingjing-livetalking-{int(time.time() * 1000)}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
        )
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        url,
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke a local LiveTalking sidecar.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--session-id", default="")
    parser.add_argument(
        "--text",
        default="您好，我是灵境导游，现在测试 LiveTalking 数字人口型播报。",
    )
    parser.add_argument(
        "--audio-path",
        default=r"D:\py\dota\external\avatar-clips\lingshan_buddha_intro_45s.wav",
    )
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--skip-text", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results: dict[str, object] = {"base_url": base_url}

    try:
        status, body = _read_url(f"{base_url}/dashboard.html", args.timeout)
        results["dashboard"] = {"status": status, "bytes": len(body)}
    except Exception as exc:
        results["dashboard"] = {"error": repr(exc)}

    if not args.session_id:
        results["session_required"] = "Pass --session-id after WebRTC page creates a session."
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 2

    if not args.skip_text:
        try:
            status, payload = _post_json(
                f"{base_url}/human",
                {
                    "sessionid": args.session_id,
                    "type": "echo",
                    "text": args.text,
                    "interrupt": True,
                },
                args.timeout,
            )
            results["text_echo"] = {"status": status, "response": payload}
        except (urllib.error.URLError, TimeoutError, Exception) as exc:
            results["text_echo"] = {"error": repr(exc)}

    if not args.skip_audio:
        audio_path = Path(args.audio_path)
        if not audio_path.exists():
            results["audio"] = {"error": f"audio not found: {audio_path}"}
        else:
            try:
                status, payload = _post_multipart_file(
                    f"{base_url}/humanaudio",
                    {"sessionid": args.session_id},
                    "file",
                    audio_path,
                    args.timeout,
                )
                results["audio"] = {"status": status, "response": payload}
            except (urllib.error.URLError, TimeoutError, Exception) as exc:
                results["audio"] = {"error": repr(exc)}

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
