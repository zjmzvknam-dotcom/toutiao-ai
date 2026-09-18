from app.services.topics import analyze_topic


def test_topic_potential_and_tracking_are_available() -> None:
    topic = analyze_topic("新能源汽车")
    assert 0 <= topic.potential <= 100
    assert topic.tracked is False
    assert topic.model_copy(update={"tracked": True}).tracked is True
