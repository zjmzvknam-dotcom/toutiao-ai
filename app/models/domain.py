from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PublicationStatus(StrEnum):
    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ContentType(StrEnum):
    ARTICLE = "ARTICLE"
    VIDEO_SCRIPT = "VIDEO_SCRIPT"
    XIAOHONGSHU = "XIAOHONGSHU"
    WECHAT = "WECHAT"
    BAIJIAHAO = "BAIJIAHAO"
    DOUYIN = "DOUYIN"


class TaskEvent(BaseModel):
    task_id: str
    step: str
    status: str
    created_at: datetime = Field(default_factory=utcnow)


class Topic(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    source: str = "用户关键词"
    heat: int = Field(default=50, ge=0, le=100)
    growth: int = Field(default=50, ge=0, le=100)
    competition: int = Field(default=50, ge=0, le=100)
    content_value: int = Field(default=50, ge=0, le=100)
    monetization: int = Field(default=50, ge=0, le=100)
    lifecycle: str = "待评估"
    risk: str = "低"
    angle: str = "信息解读"
    tracked: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def potential(self) -> int:
        return round((self.heat + self.growth + self.content_value + self.monetization + (100 - self.competition)) / 5)


class TitleOption(BaseModel):
    title: str
    strategy: str
    attraction: int = Field(ge=0, le=100)
    accuracy: int = Field(ge=0, le=100)
    information_value: int = Field(ge=0, le=100)
    exaggeration_risk: str
    recommended: bool = False


class ArticlePlan(BaseModel):
    audience: str
    core_question: str
    thesis: str
    angle: str
    persona: str
    outline: list[str]
    source_constraints: list[str]


class Evidence(BaseModel):
    claim: str
    source_name: str
    source_url: str | None = None
    confidence: str = "未核实"
    published_at: datetime | None = None
    excerpt: str | None = None


class ImageCandidate(BaseModel):
    url: str | None = None
    source: str = ""
    label: str = "未使用"
    verified: bool = False
    reason: str = "未配置或无法验证图片来源，遵循宁缺毋滥原则。"


class QualityReport(BaseModel):
    information_density: int
    readability: int
    duplication_risk: str
    fact_risk: str
    sensitivity_risk: str
    template_risk: str
    notes: list[str] = Field(default_factory=list)


class PublicationReadiness(BaseModel):
    status: PublicationStatus
    checks: list[str]
    blockers: list[str] = Field(default_factory=list)


class Article(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    title: str
    body: str
    model: str = "本地降级模板"
    status: TaskStatus = TaskStatus.SUCCESS
    titles: list[TitleOption] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    image: ImageCandidate = Field(default_factory=ImageCandidate)
    quality: QualityReport
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_type: ContentType = ContentType.ARTICLE


class ResearchResult(BaseModel):
    provider: str
    evidence: list[Evidence] = Field(default_factory=list)
    warning: str | None = None


class DetectorResult(BaseModel):
    provider: str
    available: bool
    score: float | None = None
    message: str
