from __future__ import annotations

import httpx

from app.providers.trends import DouyinPublicHotSource, GoogleTrendsRssSource, MultiSourceTrendProvider


def test_google_trends_rss_maps_titles(monkeypatch):
    xml = """<rss><channel><item><title>AI还能够这样</title><ht:approx_traffic xmlns:ht='https://trends.google.com/trending/rss'>100K+</ht:approx_traffic></item></channel></rss>""".encode("utf-8")

    def fake_get(*args, **kwargs):
        return httpx.Response(200, content=xml, request=httpx.Request("GET", args[0]))

    monkeypatch.setattr("app.providers.trends.httpx.get", fake_get)
    result = GoogleTrendsRssSource().fetch(limit=5)
    assert result[0].title == "AI还能够这样"
    assert result[0].source.startswith("Google Trends")


def test_douyin_payload_is_defensively_parsed(monkeypatch):
    def fake_get(*args, **kwargs):
        return httpx.Response(200, json={"data": [{"word": "抖音热点", "hot": 900000}]}, request=httpx.Request("GET", args[0]))

    monkeypatch.setattr("app.providers.trends.httpx.get", fake_get)
    result = DouyinPublicHotSource().fetch(limit=5)
    assert result[0].title == "抖音热点"
    assert result[0].source == "抖音公开热榜接口"


def test_multi_source_retains_partial_success():
    class Good:
        name = "good"

        def fetch(self, *, limit=20):
            from app.models.domain import Topic

            return [Topic(title="保留我", source="good")]

    class Bad:
        name = "bad"

        def fetch(self, *, limit=20):
            raise TimeoutError("offline")

    topics, warnings, refreshed = MultiSourceTrendProvider([Good(), Bad()]).fetch()
    assert topics[0].title == "保留我"
    assert warnings and "bad" in warnings[0]
    assert refreshed.tzinfo is not None
