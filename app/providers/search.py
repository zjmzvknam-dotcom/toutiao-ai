from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from time import monotonic, sleep

import httpx

from app.models.domain import Evidence, ResearchResult


class SearchProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        """Return source metadata only. Search results are leads, not verified facts."""


class GDELTDocumentProvider(SearchProvider):
    """Adapter for the documented GDELT DOC 2.0 ArticleList JSON endpoint."""

    name = "GDELT DOC 2.0"
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        params = {"query": query, "mode": "artlist", "format": "json", "timespan": timespan, "maxrecords": min(max(limit, 1), 250), "sort": "datedesc"}
        response = httpx.get(self.endpoint, params=params, timeout=self.timeout_seconds, headers={"User-Agent": "ContentWorkbench/0.1"})
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        if not isinstance(articles, list):
            raise ValueError("unexpected search response")
        evidence = []
        for item in articles:
            if not isinstance(item, dict) or not item.get("title") or not item.get("url"):
                continue
            date = _parse_date(item.get("seendate"))
            evidence.append(Evidence(claim=str(item["title"]), source_name=str(item.get("domain") or "GDELT indexed source"), source_url=str(item["url"]), published_at=date, confidence="待人工核验"))
        return ResearchResult(provider=self.name, evidence=evidence)


def _parse_date(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(raw, pattern)
        except ValueError:
            pass
    return None


class CachedSearchProvider(SearchProvider):
    """Small process-local TTL cache; caller may replace it with a distributed cache later."""

    def __init__(self, backend: SearchProvider, ttl_seconds: float = 600.0) -> None:
        self.name = f"Cached {backend.name}"
        self.backend = backend
        self.ttl_seconds = ttl_seconds
        self._cache: dict[tuple[str, str, int], tuple[float, ResearchResult]] = {}

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        key = (query.strip().lower(), timespan, limit)
        cached = self._cache.get(key)
        if cached and monotonic() < cached[0]:
            return cached[1].model_copy(update={"warning": "使用未过期的搜索缓存；发布前仍需核验来源时效。"})
        result = self.backend.search(query, timespan=timespan, limit=limit)
        self._cache[key] = (monotonic() + self.ttl_seconds, result)
        return result


class ResilientSearchProvider(SearchProvider):
    """Retries bounded failures and opens a short circuit after repeated errors."""

    def __init__(self, backend: SearchProvider, attempts: int = 2, cool_down_seconds: float = 45.0) -> None:
        self.name = f"Resilient {backend.name}"
        self.backend = backend
        self.attempts = attempts
        self.cool_down_seconds = cool_down_seconds
        self._opened_until = 0.0

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        if monotonic() < self._opened_until:
            raise RuntimeError("search circuit is open")
        last_error: Exception | None = None
        for index in range(self.attempts):
            try:
                return self.backend.search(query, timespan=timespan, limit=limit)
            except Exception as exc:
                last_error = exc
                if index + 1 < self.attempts:
                    sleep(0.1 * (index + 1))
        self._opened_until = monotonic() + self.cool_down_seconds
        raise RuntimeError("search provider failed after bounded retries") from last_error
