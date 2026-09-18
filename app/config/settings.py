from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path("data/content_workbench.sqlite3")
    request_timeout_seconds: float = 20.0
    max_retries: int = 2


settings = Settings()
