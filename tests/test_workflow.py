from app.models.domain import TaskStatus
from app.providers.router import ModelRouter
from app.services.topics import analyze_topic
from app.workflows.article import ArticleWorkflow, RiskConfirmationRequired
from app.models.domain import Evidence, ResearchResult


class FakeSearch:
    name = "Fake Search"

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        return ResearchResult(provider=self.name, evidence=[Evidence(claim="可核验的报道线索", source_name="示例来源", source_url="https://example.com", confidence="待人工核验")])


class FailingSearch:
    name = "Failing Search"

    def search(self, query: str, *, timespan: str, limit: int = 8) -> ResearchResult:
        raise TimeoutError("network timeout")


def test_workflow_uses_model_response() -> None:
    article = ArticleWorkflow(fake_router()).run(analyze_topic("小米汽车"), length=600, persona="理性分析型", with_images=True)
    assert article.status == TaskStatus.PARTIAL_SUCCESS
    assert len(article.titles) == 5
    assert "小米汽车" in article.body
    assert article.image.verified is False
    assert article.metadata["plan"]["persona"] == "理性分析型"
    assert article.metadata["image_requested"] is True


def test_sensitive_topic_is_flagged() -> None:
    assert analyze_topic("医疗治疗新消息").risk in {"中", "高"}


def test_high_risk_topic_requires_explicit_confirmation() -> None:
    topic = analyze_topic("医疗治疗新消息")
    try:
        ArticleWorkflow(fake_router()).run(topic, length=600, persona="理性分析型")
    except RiskConfirmationRequired:
        pass
    else:
        raise AssertionError("expected confirmation gate")
    article = ArticleWorkflow(fake_router()).run(topic, length=600, persona="理性分析型", confirmed_high_risk=True)
    assert article.status in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}


def test_one_topic_can_create_five_structurally_distinct_variants() -> None:
    articles = ArticleWorkflow(fake_router()).run_many(analyze_topic("新能源汽车"), length=600, persona="行业观察型")
    assert len(articles) == 5
    assert len({item.metadata["variant_angle"] for item in articles}) == 5
    assert len({item.body for item in articles}) == 5


def test_workflow_keeps_research_as_unverified_evidence() -> None:
    article = ArticleWorkflow(fake_router(), FakeSearch()).run(analyze_topic("测试"), length=600, persona="理性分析型", use_research=True)
    assert article.evidence[0].confidence == "待人工核验"
    assert article.metadata["research_provider"] == "Fake Search"


def test_workflow_isolated_from_search_failure() -> None:
    article = ArticleWorkflow(fake_router(), FailingSearch()).run(analyze_topic("测试"), length=600, persona="理性分析型", use_research=True)
    assert article.status == TaskStatus.PARTIAL_SUCCESS
    assert "搜索服务暂时不可用" in article.metadata["warning"]


def test_workflow_warns_but_keeps_near_duplicate_available() -> None:
    topic = analyze_topic("小米汽车")
    first = ArticleWorkflow(fake_router()).run(topic, length=600, persona="理性分析型")
    second = ArticleWorkflow(fake_router()).run(topic, length=600, persona="理性分析型", existing_bodies=[first.body])
    assert any("相似度较高" in note for note in second.quality.notes)
    assert second.body

class FakeWriter:
    def generate(self, prompt, *, model):
        return "测试模型正文，仅用于测试流程。\n\n" + prompt


def fake_router():
    return ModelRouter(FakeWriter(), {"writing": "fake-test-model"})


def test_missing_model_never_returns_template():
    import pytest
    with pytest.raises(ValueError, match="尚未连接写作模型"):
        ArticleWorkflow(ModelRouter(None)).run(analyze_topic("中年人的心酸"), length=900, persona="温和观察型")


def test_failed_model_never_returns_template():
    import pytest
    class Broken:
        def generate(self, *args, **kwargs):
            raise TimeoutError("private provider details")
    with pytest.raises(ValueError, match="未能返回完整文章"):
        ArticleWorkflow(ModelRouter(Broken(), {"writing": "test"})).run(analyze_topic("中年人的心酸"), length=900, persona="温和观察型")
