from __future__ import annotations

from app.models.domain import ArticlePlan, Evidence, Topic
from app.services.personas import resolve_persona


def build_plan(topic: Topic, *, persona: str, evidence: list[Evidence]) -> ArticlePlan:
    profile = resolve_persona(persona)
    source_constraints = ["区分官方信息、媒体报道、观点与网传内容。", "没有可核验来源时，不写成确定事实。"]
    if evidence:
        source_constraints.append("仅将资料来源作为待核验线索；发布前打开原始链接复核时间、主体和上下文。")
    return ArticlePlan(
        audience=f"关心{profile.focus}的移动端读者",
        core_question=f"谈{topic.title}时，{profile.focus}中哪个具体问题值得展开？",
        thesis=profile.judgment,
        angle=topic.angle,
        persona=persona,
        outline=[profile.opening, profile.examples, profile.transition, profile.ending],
        source_constraints=source_constraints,
    )
