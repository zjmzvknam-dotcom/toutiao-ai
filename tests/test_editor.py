from app.models.domain import Article, QualityReport
from app.services.editor import revise


def test_editor_expands_without_claiming_new_facts() -> None:
    article = Article(topic="测试", title="测试", body="第一段。\n\n第二段。\n\n第三段。", quality=QualityReport(information_density=1, readability=1, duplication_risk="低", fact_risk="低", sensitivity_risk="低", template_risk="低"))
    revised = revise(article, "扩写")
    assert len(revised.body) > len(article.body)
    assert any("未新增或改写任何外部事实" in note for note in revised.quality.notes)
