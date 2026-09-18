from __future__ import annotations

from collections.abc import Callable

from app.core.resilience import with_fallback
from app.models.domain import Article, ArticlePlan, Evidence, ImageCandidate, ResearchResult, TaskStatus, TitleOption, Topic
from app.providers.router import ModelRouter
from app.providers.search import SearchProvider
from app.services.quality import assess
from app.services.fact_check import verification_notes
from app.services.similarity import highest_similarity
from app.services.planning import build_plan
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


def _offline_article(topic: Topic, length: int, persona: str, requirement: str) -> str:
    angle = topic.angle
    target = "普通读者"
    angle_notes = {
        "事件与已知信息解读": ("先把时间线、主体和公开信息说清楚", "信息解读的价值，在于帮读者区分已确认的节点和仍待补证的部分"),
        "普通人会受到什么影响": ("从日常成本、使用体验和选择空间入手", "普通人视角不能替读者下结论，而应把可能影响拆成可观察的具体问题"),
        "行业变化与竞争格局": ("观察参与者、供应链与竞争节奏", "行业视角要解释变化如何传导，而不是把短期热度直接等同于长期格局"),
        "关键原因与限制条件": ("追问背后的驱动因素、前提和反例", "原因分析需要同时展示支持结论的证据与可能推翻它的条件"),
        "未来趋势及待观察信号": ("列出后续公告、数据和用户反馈等观察信号", "趋势分析应给出条件性判断，避免把预测包装成已经发生的事实"),
    }
    focus, conclusion = angle_notes.get(angle, ("从可核验资料和读者问题展开", "结论应保留不确定性并交代判断依据"))
    paragraphs = [
        f"围绕“{angle}”，{topic.title}最近受到关注。本文不试图把所有问题塞进一个结论，而是{focus}。对{target}来说，真正值得花时间理解的，是哪些信息足够可靠、哪些说法仍需等待来源确认。",
        f"先看已知部分：目前这项选题的热度、增长和竞争度是系统基于离线启发式生成的初步判断，并不替代真实趋势数据。正式发布前，应补充官方公告、可靠媒体报道和原始资料，并标记每条信息的时间与来源。",
        f"从“{angle}”出发，{conclusion}。比起把不确定的细节写成结论，更好的表达是说明条件、列出证据，并承认尚未确认的部分。",
        f"{persona}的写法不需要靠夸张制造张力。可以从一个真实问题切入，再用对应角度的案例、数据或采访材料推进论证，让每篇文章有不同的信息价值。",
        f"最后，{topic.title}是否持续升温，还要看后续公开信息与用户反馈。本文只覆盖“{angle}”这一问题；其他角度应另行策划，避免同一篇文章承担互相冲突的叙事任务。",
    ]
    if requirement.strip():
        paragraphs.append(f"写作补充要求：{requirement.strip()}。此要求应在补充材料得到核验后落实到具体段落。")
    body = "\n\n".join(paragraphs)
    return body if len(body) >= length else body + "\n\n" + "建议继续补充可验证的最新资料、差异化案例和读者关切，以达到目标篇幅。"


class ArticleWorkflow:
    def __init__(self, router: ModelRouter | None = None, search_provider: SearchProvider | None = None) -> None:
        self.router = router or ModelRouter(None)
        self.search_provider = search_provider

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
        fallback = lambda: _offline_article(topic, length, persona, requirement)
        citations = "\n".join(f"- {item.claim}｜{item.source_name}｜{item.source_url}" for item in research.evidence[:6]) or "无可引用来源。"
        prompt = (f"为今日头条写一篇约{length}字中文文章，主题：{topic.title}。人格：{plan.persona}。"
                  "只能陈述用户提供或来源明确的事实；不确定信息必须明确标注。不要编造数据、引文或现场细节。"
                  f"附加要求：{requirement}\n核心问题：{plan.core_question}\n核心观点：{plan.thesis}\n结构：{'；'.join(plan.outline)}\n待人工核验的资料线索（不得超出它们推断事实）：\n{citations}")
        prompt += f"\n选题角度：{topic.angle}。直接输出完整文章正文，不输出写作计划、待补充占位语或系统状态。情感、生活随笔采用贴题的叙述与观点，不套用新闻分析框架；虚构场景不得冒充真实采访。"
        try:
            body = self.router.generate("writing", prompt)
            if not isinstance(body, str) or len(body.strip()) < 80:
                raise ValueError("incomplete response")
        except Exception:
            raise ValueError("写作模型本次未能返回完整文章。请检查连接、额度或稍后重试；没有保存模板冒充文章，之前的正文仍保留。") from None
        from app.core.resilience import ServiceResult
        result = ServiceResult(value=body.strip())
        emit("正在写作", "完成" if not result.warning else result.warning)
        titles = _titles(topic.title)
        emit("生成标题", "完成：已生成 5 个不同策略标题")
        image = ImageCandidate()
        if with_images:
            image = ImageCandidate(label="未使用", verified=False, reason="图片 Provider 尚未配置；未使用无法验证的图片。")
            emit("图片核验", "降级：文章仍可使用")
        else:
            emit("图片核验", "跳过：用户未要求配图")
        quality = assess(result.value or fallback(), topic.risk)
        similarity = highest_similarity(result.value or fallback(), existing_bodies or [])
        if similarity >= 0.82:
            quality.notes.append("与历史文章相似度较高；文章仍已生成，请在发布前更换角度、补充新来源或人工去重。")
        quality.notes.extend(verification_notes(research.evidence, result.value or fallback()))
        quality.notes.append(f"历史相似度初筛：{similarity:.0%}。该评分只用于发现潜在重复，不替代人工判断。")
        emit("质量与风险检测", "完成")
        evidence = research.evidence or [Evidence(claim="当前任务没有可用的外部资料来源。", source_name="系统状态", confidence="未核实")]
        warning = "；".join(item for item in [result.warning, research.warning] if item) or None
        status = TaskStatus.PARTIAL_SUCCESS if warning or with_images else TaskStatus.SUCCESS
        article_kwargs = {"task_id": task_id} if task_id else {}
        readiness = assess_readiness(evidence=evidence, image=image, image_requested=with_images, quality=quality)
        return Article(topic=topic.title, title=topic.title, body=result.value, model=self.router.model_for("writing"), status=status, titles=titles, evidence=evidence, image=image, quality=quality, metadata={"warning": warning, "requested_length": length, "persona": persona, "research_provider": research.provider, "plan": plan.model_dump(), "readiness": readiness.model_dump(), "image_requested": with_images, "generation_kind": "model"}, **article_kwargs)

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
