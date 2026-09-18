import pytest

from app.models.domain import Article, ContentType, QualityReport
from app.services.platforms import ToutiaoArticleAdapter, UnsupportedPlatformAdapter


def article() -> Article:
    return Article(topic="测试", title="标题", body="正文", quality=QualityReport(information_density=1, readability=1, duplication_risk="低", fact_risk="低", sensitivity_risk="低", template_risk="低"))


def test_article_adapter_preserves_content() -> None:
    assert "正文" in ToutiaoArticleAdapter().adapt(article())


def test_future_platform_is_explicitly_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        UnsupportedPlatformAdapter(ContentType.WECHAT).adapt(article())
