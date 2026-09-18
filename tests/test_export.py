from app.models.domain import Article, QualityReport
from app.services.export import markdown, plain_text, word_document


def article() -> Article:
    return Article(topic="测试", title="测试标题", body="第一段。\n\n第二段。", quality=QualityReport(information_density=1, readability=1, duplication_risk="低", fact_risk="低", sensitivity_risk="低", template_risk="低"))


def test_all_export_formats_contain_article_content() -> None:
    item = article()
    assert "测试标题" in markdown(item)
    assert "第一段" in plain_text(item)
    assert word_document(item).startswith(b"PK")
