from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class AvatarMockBridgeHandler(BaseHTTPRequestHandler):
    server_version = "LingjingAvatarMockBridge/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/liveness" or self.path == "/readiness":
            self._send_json(200, {"status": "ok", "adapter": "mock_bridge"})
            return
        self._send_json(404, {"accepted": False, "message": "not found"})

    def do_POST(self) -> None:
        if self.path != "/lingjing/avatar/speak":
            self._send_json(404, {"accepted": False, "message": "not found"})
            return
        content_length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"accepted": False, "message": "invalid json"})
            return
        text = str(payload.get("text") or "")
        if not text.strip():
            self._send_json(422, {"accepted": False, "message": "empty text"})
            return
        self._send_json(
            200,
            {
                "accepted": True,
                "adapter": "mock_bridge",
                "text_chars": len(text),
                "policy": payload.get("policy"),
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a local HTTP JSON mock bridge for /api/avatar/speak adapter smoke tests."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8021, help="Bind port.")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AvatarMockBridgeHandler)
    print(f"avatar mock bridge listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
