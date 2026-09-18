from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from app.models.domain import Topic


class TrendSource(ABC):
    """A public trend source. Results are signals, not verified facts."""

    name: str

    @abstractmethod
    def fetch(self, *, limit: int = 20) -> list[Topic]:
        raise NotImplementedError


class GoogleTrendsRssSource(TrendSource):
    # Google does not expose a stable mainland-China RSS feed; HK is the
    # closest Chinese-language regional feed and is labelled transparently.
    name = "Google Trends 香港中文 RSS"
    endpoint = "https://trends.google.com/trending/rss?geo=HK&hl=zh-HK"

    def __init__(self, timeout_seconds: float = 3.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, *, limit: int = 20) -> list[Topic]:
        response = httpx.get(self.endpoint, timeout=self.timeout_seconds, headers={"User-Agent": "ContentWorkbench/1.0"})
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        rows: list[Topic] = []
        for index, item in enumerate(root.findall(".//item")[:limit]):
            title = _text(item.find("title"))
            if not title:
                continue
            traffic = _text(item.find("{https://trends.google.com/trending/rss}approx_traffic"))
            heat = _traffic_score(traffic, index)
            rows.append(_topic(title, self.name, heat=heat, growth=min(98, heat + 8), angle="搜索趋势解读"))
        return rows


class DouyinPublicHotSource(TrendSource):
    """Adapter for the public JSON feed documented by douyinhuo.cn.

    The endpoint is treated as an unverified lead source and parsed defensively
    because public aggregators may change their response envelope.
    """

    name = "抖音公开热榜接口"
    endpoint = "https://douyinhuo.cn/api/data"

    def __init__(self, timeout_seconds: float = 3.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, *, limit: int = 20) -> list[Topic]:
        response = httpx.get(self.endpoint, timeout=self.timeout_seconds, headers={"User-Agent": "ContentWorkbench/1.0"})
        response.raise_for_status()
        return _parse_douyin_payload(response.json(), limit=limit, source=self.name)


class MultiSourceTrendProvider:
    """Fetch several sources independently, retaining partial success."""

    def __init__(self, sources: list[TrendSource] | None = None) -> None:
        self.sources = sources or [GoogleTrendsRssSource(), DouyinPublicHotSource()]

    def fetch(self, *, limit: int = 30) -> tuple[list[Topic], list[str], datetime]:
        source_rows: list[list[Topic]] = []
        warnings: list[str] = []
        for source in self.sources:
            try:
                source_rows.append(source.fetch(limit=limit))
            except Exception as exc:
                warnings.append(f"{source.name} 暂时不可用：{type(exc).__name__}")
        topics: list[Topic] = []
        for index in range(limit):
            for rows in source_rows:
                if index < len(rows):
                    topics.append(rows[index])
        deduped: dict[str, Topic] = {}
        for topic in topics:
            key = re.sub(r"\s+", "", topic.title).lower()
            existing = deduped.get(key)
            if existing is None or topic.heat > existing.heat:
                deduped[key] = topic
            elif existing.source != topic.source:
                deduped[key] = existing.model_copy(update={"source": f"{existing.source} + {topic.source}"})
        return list(deduped.values())[:limit], warnings, datetime.now(timezone.utc)


def _text(node: ElementTree.Element | None) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def _traffic_score(raw: str, index: int) -> int:
    digits = re.sub(r"[^0-9]", "", raw)
    if not digits:
        return max(55, 92 - index * 2)
    value = int(digits)
    if "万" in raw:
        value *= 10000
    return max(40, min(99, 50 + round(value / 2_000_000)))


def _topic(title: str, source: str, *, heat: int, growth: int, angle: str) -> Topic:
    return Topic(title=title[:120], source=source, heat=heat, growth=growth, competition=55, content_value=70, monetization=45, lifecycle="实时信号（需核验）", angle=angle, updated_at=datetime.now(timezone.utc))


def _parse_douyin_payload(payload: object, *, limit: int, source: str) -> list[Topic]:
    if isinstance(payload, dict) and isinstance(payload.get("platforms"), list):
        platform_names = {"douyin": "抖音", "toutiao": "今日头条", "weibo": "微博", "baidu": "百度", "zhihu": "知乎", "bilibili": "哔哩哔哩"}
        rows: list[Topic] = []
        for platform in payload["platforms"]:
            if not isinstance(platform, dict) or platform.get("id") not in platform_names:
                continue
            items = platform.get("items", [])
            if not isinstance(items, list):
                continue
            platform_source = f"{platform_names[platform['id']]}公开热榜（{source}）"
            rows.extend(_parse_items(items, limit=max(1, limit // len(platform_names)), source=platform_source))
        return rows[:limit]
    items: list[object] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("data", "list", "result", "hot_list", "hotList"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
            if isinstance(candidate, dict):
                items = candidate.get("list", []) if isinstance(candidate.get("list"), list) else []
                if items:
                    break
    return _parse_items(items, limit=limit, source=source)


def _parse_items(items: list[object], *, limit: int, source: str) -> list[Topic]:
    rows: list[Topic] = []
    for index, item in enumerate(items[:limit]):
        if isinstance(item, str):
            title, value = item, ""
        elif isinstance(item, dict):
            title = str(item.get("title") or item.get("word") or item.get("name") or item.get("keyword") or "").strip()
            value = str(item.get("hot") or item.get("hotValue") or item.get("热度") or "")
        else:
            continue
        if title:
            rows.append(_topic(title, source, heat=_traffic_score(value, index), growth=max(45, 90 - index * 2), angle="短视频热榜解读"))
    return rows


def parse_published_at(raw: str) -> datetime | None:
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return None
