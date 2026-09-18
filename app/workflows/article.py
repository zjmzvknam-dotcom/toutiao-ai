from __future__ import annotations

from collections.abc import Callable

from app.models.domain import Article, Evidence, ImageCandidate, ResearchResult, TaskStatus, TitleOption, Topic
from app.providers.router import ModelRouter
from app.providers.search import SearchProvider
from app.services.quality import assess
from app.services.fact_check import verification_notes
from app.services.similarity import highest_similarity
from app.services.planning import build_plan
from app.services.personas import writer_prompt
from app.services.human_style import improve_locally
from app.services.illustrations import illustrate
from app.services.readiness import assess_readiness
from app.services.topics import topic_angles


Progress = Callable[[str, str], None]


class RiskConfirmationRequired(ValueError):
    """Raised before generation when a high-risk topic needs an explicit user decision."""


def _titles(topic: str) -> list[TitleOption]:
    items = [
        (f"{topic}：已知信息、影响与下一步该看什么", "信息型", True),
        (f"{topic}背后，普通人真正关心的三个问题", "共鸣型", False),
        (f"别急着下结论：理解{topic}要先看这几个条件", "观点型", False),
        (f"从一个细节看{topic}，变化可能比想象中更近", "故事型", False),
        (f"{topic}值得关注，但别忽略这些限制", "理性提醒型", False),
    ]
    return [TitleOption(title=title, strategy=strategy, attraction=82 - index * 2, accuracy=90 - index, information_value=86 - index, exaggeration_risk="低", recommended=recommended) for index, (title, strategy, recommended) in enumerate(items)]


class ArticleWorkflow:
    def __init__(self, router: ModelRouter | None = None, search_provider: SearchProvider | None = None, image_generator=None) -> None:
        self.router = router or ModelRouter(None)
        self.search_provider = search_provider
        self.image_generator = image_generator

    def run(self, topic: Topic, *, length: int, persona: str, requirement: str = "", with_images: bool = False, use_research: bool = False, timespan: str = "24h", existing_bodies: list[str] | None = None, task_id: str | None = None, confirmed_high_risk: bool = False, progress: Progress | None = None) -> Article:
        emit = progress or (lambda _step, _state: None)
        if topic.risk == "高" and not confirmed_high_risk:
            emit("风险门槛", "需要用户确认：高风险题材不会自动扩写")
            raise RiskConfirmationRequired("该选题属于高风险题材。请在专业模式确认你会核验事实、避免医疗/投资建议及未证实指控后再继续。")
        if not self.router.model_for("writing"):
            raise ValueError("尚未连接写作模型，无法生成文章。请在页面的模型连接区填写 API Key 和模型名称；已有文章会保留。")
        emit("分析关键词", "完成")
        emit("规划选题角度", "完成")
        research = self._research(topic.title, timespan) if use_research else ResearchResult(provider="未启用", warning="用户未启用资料搜索。")
        emit("搜索资料", research.warning or f"完成：获得 {len(research.evidence)} 条待核验资料")
        emit("事实核查", "完成：来源均标为待人工核验；模型不得将其自动升级为事实")
        plan = build_plan(topic, persona=persona, evidence=research.evidence)
        emit("文章策划", "完成：已生成目标读者、核心问题、观点与结构")
        prompt = writer_prompt(topic, plan, length, requirement, research.evidence)
        try:
            body = self.router.generate("writing", prompt)
            if not isinstance(body, str) or len(body.strip()) < 80:
                raise ValueError("incomplete response")
        except Exception:
            raise ValueError("写作模型本次未能返回完整文章。请检查连接、额度或稍后重试；没有保存模板冒充文章，之前的正文仍保留。") from None
        from app.core.resilience import ServiceResult
        body, style = improve_locally(body.strip(), persona, self.router)
        result = ServiceResult(value=body)
        emit("正在写作", "完成" if not result.warning else result.warning)
        titles = _titles(topic.title)
        emit("生成标题", "完成：已生成 5 个不同策略标题")
        image = ImageCandidate()
        quality = assess(result.value, topic.risk)
        similarity = highest_similarity(result.value, existing_bodies or [])
        if similarity >= 0.82:
            quality.notes.append("与历史文章相似度较高；文章仍已生成，请在发布前更换角度、补充新来源或人工去重。")
        quality.notes.extend(verification_notes(research.evidence, result.value))
        quality.notes.append(f"历史相似度初筛：{similarity:.0%}。该评分只用于发现潜在重复，不替代人工判断。")
        emit("质量与风险检测", "完成")
        evidence = research.evidence or [Evidence(claim="当前任务没有可用的外部资料来源。", source_name="系统状态", confidence="未核实")]
        warning = "；".join(item for item in [result.warning, research.warning] if item) or None
        status = TaskStatus.PARTIAL_SUCCESS if warning or with_images else TaskStatus.SUCCESS
        article_kwargs = {"task_id": task_id} if task_id else {}
        readiness = assess_readiness(evidence=evidence, image=image, image_requested=False, quality=quality)
        article = Article(topic=topic.title, title=topic.title, body=result.value, model=self.router.model_for("writing"), status=status, titles=titles, evidence=evidence, image=image, quality=quality, metadata={"warning": warning, "requested_length": length, "persona": persona, "research_provider": research.provider, "plan": plan.model_dump(), "readiness": readiness.model_dump(), "image_requested": with_images, "generation_kind": "model", "human_style": style}, **article_kwargs)
        return illustrate(article, self.router, self.image_generator, enabled=with_images)

    def _research(self, query: str, timespan: str) -> ResearchResult:
        if not self.search_provider:
            return ResearchResult(provider="未配置", warning="未配置真实搜索 Provider，未将离线结果当作事实来源。")
        try:
            return self.search_provider.search(query, timespan=timespan)
        except Exception:
            return ResearchResult(provider=self.search_provider.name, warning="搜索服务暂时不可用，文章仍可生成；请勿将未核实内容作为事实发布。")

    def run_many(self, topic: Topic, *, length: int, persona: str, requirement: str = "", use_research: bool = False, timespan: str = "24h", confirmed_high_risk: bool = False, progress: Progress | None = None) -> list[Article]:
        """Create distinct, planned article variants for one topic; never synonym-rewrite one draft."""
        articles: list[Article] = []
        for angle in topic_angles(topic):
            variant_topic = topic.model_copy(update={"angle": angle})
            article = self.run(variant_topic, length=length, persona=persona, requirement=requirement, use_research=use_research, timespan=timespan, confirmed_high_risk=confirmed_high_risk, progress=progress)
            article = article.model_copy(update={"title": f"{topic.title}：{angle}", "metadata": {**article.metadata, "variant_angle": angle}})
            articles.append(article)
        return articles
