from __future__ import annotations

import httpx

from app.providers.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    name = "OpenAI Compatible"

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 20.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self.last_usage: dict[str, int] = {}

    def generate(self, prompt: str, *, model: str) -> str:
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage", {})
        self.last_usage = {key: int(value) for key, value in usage.items() if key in {"prompt_tokens", "completion_tokens", "total_tokens"} and isinstance(value, int)} if isinstance(usage, dict) else {}
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
        return content.strip()

    def test_connection(self, *, model: str) -> tuple[bool, str]:
        try:
            self.generate("请只回复 OK", model=model)
            return True, "连接成功。"
        except (httpx.HTTPError, KeyError, ValueError):
            return False, "无法连接或模型返回异常；请检查 Provider、Base URL、模型名和密钥。"
