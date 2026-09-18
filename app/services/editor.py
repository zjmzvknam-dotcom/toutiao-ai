from __future__ import annotations

from app.models.domain import Article, utcnow
from app.services.quality import assess


def revise(article: Article, instruction: str) -> Article:
    """Local, fact-preserving edits for common requests; does not invent new facts."""
    instruction = instruction.strip()
    body = article.body
    if instruction == "缩写":
        paragraphs = [item for item in body.split("\n\n") if item.strip()]
        body = "\n\n".join(paragraphs[:max(3, len(paragraphs) - 1)])
    elif instruction == "更口语":
        body = body.replace("正式发布前，应", "发布前最好").replace("更好的表达是", "更稳妥的说法是")
    elif instruction == "增加观点":
        body += "\n\n观点补充：信息越不完整，越需要把结论放在证据之后。与其追逐确定感，不如让读者看见判断依据和仍待观察的部分。"
    elif instruction == "扩写":
        body += "\n\n补充阅读角度：可以继续对比不同来源的表述、发布时间和利益相关方。出现明显矛盾时，应保留分歧，而不是选择更吸引眼球的版本。"
    else:
        raise ValueError("不支持的本地修改指令")
    quality = assess(body, article.quality.sensitivity_risk)
    quality.notes.append("本地修改助手仅调整表达；未新增或改写任何外部事实。")
    return article.model_copy(update={"body": body, "quality": quality, "updated_at": utcnow()})
