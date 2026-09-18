from __future__ import annotations

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str, *, model: str) -> str:
        """Generate text. Provider implementations must never log credentials or prompts wholesale."""

    @abstractmethod
    def test_connection(self, *, model: str) -> tuple[bool, str]:
        """Return a safe, user-facing connectivity result."""
