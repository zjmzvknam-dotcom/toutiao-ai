from __future__ import annotations

from app.models.domain import ArticlePlan, Evidence, Topic


def build_plan(topic: Topic, *, persona: str, evidence: list[Evidence]) -> ArticlePlan:
    source_constraints = ["区分官方信息、媒体报道、观点与网传内容。", "没有可核验来源时，不写成确定事实。"]
    if evidence:
        source_constraints.append("仅将资料来源作为待核验线索；发布前打开原始链接复核时间、主体和上下文。")
    return ArticlePlan(
        audience="希望快速理解事件影响与限制条件的移动端读者",
        core_question=f"{topic.title}究竟意味着什么，普通读者应关注哪些已知信息和未知条件？",
        thesis="高价值解读不是放大不确定性，而是清楚交代证据、影响与仍待观察的部分。",
        angle=topic.angle,
        persona=persona,
        outline=["用读者关切切入，说明讨论背景", "区分已知信息与待核验线索", "解释对普通人或行业的可能影响", "说明限制条件、风险与争议", "给出后续观察信号，而非过度承诺"],
        source_constraints=source_constraints,
    )
