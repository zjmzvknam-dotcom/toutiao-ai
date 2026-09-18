from __future__ import annotations

import json
from pathlib import Path

from app.providers.trends import MultiSourceTrendProvider


def main() -> int:
    topics, warnings, refreshed_at = MultiSourceTrendProvider().fetch(limit=50)
    output = {
        "refreshed_at": refreshed_at.isoformat(),
        "warnings": warnings,
        "topics": [topic.model_dump(mode="json") for topic in topics],
    }
    path = Path("data/hot_topics.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(topics)} topics to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
