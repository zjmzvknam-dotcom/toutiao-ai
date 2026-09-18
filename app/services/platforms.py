from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import Article, ContentType


class PlatformAdapter(ABC):
    content_type: ContentType

    @abstractmethod
    def adapt(self, article: Article) -> str:
        """Transform a verified source article into a platform-specific draft."""


class ToutiaoArticleAdapter(PlatformAdapter):
    content_type = ContentType.ARTICLE

    def adapt(self, article: Article) -> str:
        return f"{article.title}\n\n{article.body}"


class UnsupportedPlatformAdapter(PlatformAdapter):
    def __init__(self, content_type: ContentType) -> None:
        self.content_type = content_type

    def adapt(self, article: Article) -> str:
        raise NotImplementedError(f"{self.content_type} 适配模块尚未实现；不会错误地将今日头条文章直接当作该平台成品。")
