#!/usr/bin/env python
"""Evaluate multipart parser compatibility for mock upload requests."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "evals" / "reports" / "multipart_parser_latest.json"
sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import _parse_content_disposition, _parse_multipart_form


def build_multipart_body(
    boundary: str,
    *,
    line_sep: str,
    file_disposition: str,
    hint: str = "lingshan dafo",
    text_hint: str = "mock scenic spot",
    channel: str = "eval",
) -> bytes:
    lines = [
        f"--{boundary}",
        f"Content-Disposition: {file_disposition}",
        "Content-Type: image/jpeg",
        "",
        "fake-image-content",
        f"--{boundary}",
        'Content-Disposition: form-data; name="hint"',
        "",
        hint,
        f"--{boundary}",
        'Content-Disposition: form-data; name="text_hint"',
        "",
        text_hint,
        f"--{boundary}",
        'Content-Disposition: form-data; name="channel"',
        "",
        channel,
        f"--{boundary}--",
        "",
    ]
    return line_sep.join(lines).encode("utf-8")


def check_content_disposition() -> list[dict[str, object]]:
    cases = [
        (
            "rfc5987_plain",
            'form-data; name="file"; filename*=UTF-8\'\'lingshan-ls-011.jpg',
            "lingshan-ls-011.jpg",
        ),
        (
            "rfc5987_percent_decoded",
            'form-data; name="file"; filename*=UTF-8\'\'lingshan%20dafo.jpg',
            "lingshan dafo.jpg",
        ),
        (
            "rfc5987_with_language",
            'form-data; name="file"; filename*=UTF-8\'en\'lingshan%20dafo.jpg',
            "lingshan dafo.jpg",
        ),
        (
            "filename_takes_precedence",
            'form-data; name="file"; filename="legacy.jpg"; filename*=UTF-8\'\'utf8-name.jpg',
            "legacy.jpg",
        ),
    ]
    results: list[dict[str, object]] = []
    for case_id, header, expected in cases:
        parsed = _parse_content_disposition(header)
        actual = parsed.get("filename")
        results.append(
            {
                "id": case_id,
                "passed": actual == expected,
                "expected": expected,
                "actual": actual,
            }
        )
    return results


def check_multipart_forms() -> list[dict[str, object]]:
    boundary = "boundary1234"
    content_type = f"multipart/form-data; boundary={boundary}"
    file_dispositions = {
        "quoted_filename": 'form-data; name="file"; filename="lingshan-ls-011.jpg"',
        "rfc5987_filename": "form-data; name=\"file\"; filename*=UTF-8''lingshan%20dafo.jpg",
    }
    results: list[dict[str, object]] = []
    for line_label, line_sep in (("crlf", "\r\n"), ("lf_only", "\n")):
        for disposition_label, disposition in file_dispositions.items():
            body = build_multipart_body(
                boundary,
                line_sep=line_sep,
                file_disposition=disposition,
            )
            fields = _parse_multipart_form(content_type, body)
            file_field = fields.get("file")
            filename = file_field.get("filename") if isinstance(file_field, dict) else None
            expected_filename = (
                "lingshan dafo.jpg" if disposition_label == "rfc5987_filename" else "lingshan-ls-011.jpg"
            )
            passed = (
                isinstance(file_field, dict)
                and filename == expected_filename
                and fields.get("hint") == "lingshan dafo"
                and fields.get("text_hint") == "mock scenic spot"
                and fields.get("channel") == "eval"
            )
            results.append(
                {
                    "id": f"{line_label}_{disposition_label}",
                    "passed": passed,
                    "expected_filename": expected_filename,
                    "actual_filename": filename,
                    "field_names": sorted(fields.keys()),
                }
            )
    return results


def main() -> int:
    results = check_content_disposition() + check_multipart_forms()
    passed = sum(1 for item in results if item["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
