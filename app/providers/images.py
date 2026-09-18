from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.models.domain import ImageCandidate


class ImageProvider(ABC):
    """Only returns candidates with origin metadata; it never claims verification by itself."""

    @abstractmethod
    def find(self, query: str, *, limit: int = 5) -> list[ImageCandidate]:
        pass


class UnconfiguredImageProvider(ImageProvider):
    def find(self, query: str, *, limit: int = 5) -> list[ImageCandidate]:
        return []


class PexelsImageProvider(ImageProvider):
    """Pexels photo search adapter. Returned media are candidates, not semantic verification."""

    name = "Pexels"
    endpoint = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def find(self, query: str, *, limit: int = 5) -> list[ImageCandidate]:
        response = httpx.get(self.endpoint, headers={"Authorization": self._api_key}, params={"query": query, "per_page": min(max(limit, 1), 80), "locale": "zh-CN"}, timeout=self._timeout_seconds)
        response.raise_for_status()
        candidates: list[ImageCandidate] = []
        for item in response.json().get("photos", []):
            if not isinstance(item, dict):
                continue
            image_url = item.get("src", {}).get("large") if isinstance(item.get("src"), dict) else None
            page_url = item.get("url")
            photographer = item.get("photographer", "未知摄影师")
            if isinstance(image_url, str) and isinstance(page_url, str):
                candidates.append(ImageCandidate(url=image_url, source=f"Pexels · {photographer} · {page_url}", label="真实来源候选", verified=False, reason=f"Pexels 检索候选，查询词：{query}。尚未完成事件、人物、时间和产品语义核验。"))
        return candidates
