from app.services.similarity import highest_similarity


def test_similarity_detects_near_duplicate() -> None:
    text = "这是一篇具有独特内容的测试文章，用于检测重复。"
    assert highest_similarity(text, [text]) == 1.0
    assert highest_similarity(text, ["完全不同的内容。"]) < 0.2
