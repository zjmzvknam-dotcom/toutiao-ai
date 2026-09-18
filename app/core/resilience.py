from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceResult:
    value: T | None
    warning: str | None = None


def with_fallback(action: Callable[[], T], fallback: Callable[[], T], service: str, attempts: int = 2) -> ServiceResult[T]:
    for attempt in range(attempts):
        try:
            return ServiceResult(value=action())
        except Exception as exc:  # provider boundary: never expose secrets or stack traces to UI
            logger.warning("service=%s attempt=%s error=%s", service, attempt + 1, type(exc).__name__)
            if attempt + 1 < attempts:
                sleep(0.15 * (attempt + 1))
    return ServiceResult(value=fallback(), warning=f"{service} 暂时不可用，已使用本地降级结果。")
