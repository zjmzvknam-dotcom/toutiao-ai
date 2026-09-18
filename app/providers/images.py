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


class WikimediaCommonsImageProvider(ImageProvider):
    """Keyless Commons search with source-page attribution."""

    name = "Wikimedia Commons"
    endpoint = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    def find(self, query: str, *, limit: int = 5) -> list[ImageCandidate]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": min(max(limit, 1), 10),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1200,
            "format": "json",
            "formatversion": 2,
        }
        response = httpx.get(self.endpoint, params=params, timeout=self._timeout_seconds, headers={"User-Agent": "ContentWorkbench/1.0 (image candidates)"})
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
        candidates: list[ImageCandidate] = []
        for page in pages if isinstance(pages, list) else []:
            info = page.get("imageinfo", [{}])[0] if isinstance(page, dict) else {}
            url = info.get("thumburl") or info.get("url")
            page_url = f"https://commons.wikimedia.org/?curid={page.get('pageid')}" if isinstance(page, dict) else ""
            title = str(page.get("title", "")) if isinstance(page, dict) else ""
            if isinstance(url, str) and url and page_url:
                candidates.append(ImageCandidate(url=url, source=f"Wikimedia Commons · {title} · {page_url}", label="真实来源候选", verified=False, reason=f"Commons 检索候选，查询词：{query}。尚未完成语义与许可核验。"))
        return candidates
