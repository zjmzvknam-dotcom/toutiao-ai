from app.services.similarity import highest_similarity


def test_similarity_detects_near_duplicate() -> None:
    text = "这是一篇具有独特内容的测试文章，用于检测重复。"
    assert highest_similarity(text, [text]) == 1.0
    assert highest_similarity(text, ["完全不同的内容。"]) < 0.2


def test_shared_boilerplate_does_not_block_distinct_topic() -> None:
    first = "主题甲的具体事实和影响。\n\n目前这项选题的热度、增长和竞争度是系统基于离线启发式生成的初步判断。\n\n主题甲的限制条件。"
    second = "主题乙的具体事实和影响。\n\n目前这项选题的热度、增长和竞争度是系统基于离线启发式生成的初步判断。\n\n主题乙的限制条件。"
    assert highest_similarity(second, [first]) < 0.82
