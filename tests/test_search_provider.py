from unittest.mock import Mock, patch

from app.models.domain import ResearchResult
from app.providers.search import CachedSearchProvider, GDELTDocumentProvider, ResilientSearchProvider


def test_gdelt_maps_article_response_to_evidence() -> None:
    response = Mock()
    response.json.return_value = {"articles": [{"title": "Example", "url": "https://example.com/story", "domain": "example.com", "seendate": "20260914T090000Z"}]}
    response.raise_for_status.return_value = None
    with patch("app.providers.search.httpx.get", return_value=response) as request:
        result = GDELTDocumentProvider().search("test", timespan="24h")
    assert result.evidence[0].source_name == "example.com"
    assert result.evidence[0].confidence == "待人工核验"
    assert request.call_args.kwargs["params"]["mode"] == "artlist"


class CountingSearch:
    name = "Counting"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        self.calls += 1
        return ResearchResult(provider=self.name)


class BrokenSearch:
    name = "Broken"

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        raise TimeoutError()


def test_cached_provider_deduplicates_same_request() -> None:
    backend = CountingSearch()
    provider = CachedSearchProvider(backend)
    provider.search("test", timespan="24h")
    cached = provider.search("test", timespan="24h")
    assert backend.calls == 1
    assert cached.warning is not None


def test_resilient_provider_opens_circuit_after_bounded_failures() -> None:
    provider = ResilientSearchProvider(BrokenSearch(), attempts=1)
    try:
        provider.search("test", timespan="24h")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected provider failure")
    try:
        provider.search("test", timespan="24h")
    except RuntimeError as exc:
        assert "circuit" in str(exc)
    else:
        raise AssertionError("expected open circuit")
