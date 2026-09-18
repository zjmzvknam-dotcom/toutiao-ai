from __future__ import annotations

from app.models.domain import ResearchResult, Topic, utcnow


def refresh_topic(topic: Topic, research: ResearchResult) -> Topic:
    """Update a transparent source-coverage signal, not a claim of platform-wide popularity."""
    count = len(research.evidence)
    heat = min(100, 20 + count * 10)
    growth = min(100, 15 + count * 8)
    lifecycle = "近期资料来源扫描" if count else "近期未发现来源；不代表事件不存在"
    return topic.model_copy(update={"heat": heat, "growth": growth, "source": research.provider, "lifecycle": lifecycle, "updated_at": utcnow()})
