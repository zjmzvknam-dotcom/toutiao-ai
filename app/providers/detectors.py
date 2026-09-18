from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import DetectorResult


class ExternalDetectorProvider(ABC):
    @abstractmethod
    def inspect(self, text: str) -> DetectorResult:
        """External detector outputs are advisory only, never proof of human authorship."""


class UnconfiguredDetector(ExternalDetectorProvider):
    def inspect(self, text: str) -> DetectorResult:
        return DetectorResult(provider="External detector", available=False, message="外部检测服务暂未配置；本地质量检测仍已完成。")
