from app.models.domain import Evidence, ResearchResult
from app.services.topics import analyze_topic
from app.services.tracking import refresh_topic


def test_tracking_refresh_uses_source_coverage_not_unfounded_claims() -> None:
    topic = analyze_topic("新能源汽车")
    refreshed = refresh_topic(topic, ResearchResult(provider="Test source", evidence=[Evidence(claim="a", source_name="s"), Evidence(claim="b", source_name="s")]))
    assert refreshed.source == "Test source"
    assert refreshed.heat == 40
    assert refreshed.lifecycle == "近期资料来源扫描"
