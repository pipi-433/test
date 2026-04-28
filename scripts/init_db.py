"""Initialize the local SQLite database from data/processed JSON artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
PROCESSED_DIR = ROOT / "data" / "processed"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.db import initialize_database  # noqa: E402


def main() -> int:
    required = {
        "attractions": PROCESSED_DIR / "attractions.json",
        "knowledge_chunks": PROCESSED_DIR / "knowledge_chunks.json",
        "behavior_summary": PROCESSED_DIR / "behavior_summary.json",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        print("Missing processed data files:", json.dumps(missing, ensure_ascii=False), file=sys.stderr)
        return 1

    counts = initialize_database(
        attractions_path=required["attractions"],
        chunks_path=required["knowledge_chunks"],
        behavior_summary_path=required["behavior_summary"],
        reset=True,
    )
    print(json.dumps({"database": str(get_settings().sqlite_path()), **counts}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
