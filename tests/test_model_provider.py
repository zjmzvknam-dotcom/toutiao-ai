from unittest.mock import Mock, patch

import httpx

from app.providers.openai_compatible import OpenAICompatibleProvider


def provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider("not-a-real-secret", "https://api.example.test/v1")


def test_provider_extracts_text_without_logging_key() -> None:
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "  generated  "}}], "usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10}}
    response.raise_for_status.return_value = None
    with patch("app.providers.openai_compatible.httpx.post", return_value=response) as request:
        assert provider().generate("prompt", model="test-model") == "generated"
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer not-a-real-secret"
    assert provider().last_usage == {}


def test_provider_captures_usage_when_returned() -> None:
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "generated"}}], "usage": {"total_tokens": 10}}
    response.raise_for_status.return_value = None
    item = provider()
    with patch("app.providers.openai_compatible.httpx.post", return_value=response):
        item.generate("prompt", model="test-model")
    assert item.last_usage == {"total_tokens": 10}


def test_connection_hides_http_error_details() -> None:
    with patch("app.providers.openai_compatible.httpx.post", side_effect=httpx.TimeoutException("internal endpoint details")):
        ok, message = provider().test_connection(model="test-model")
    assert ok is False
    assert "internal endpoint details" not in message


def test_connection_handles_empty_or_malformed_responses() -> None:
    empty = Mock()
    empty.json.return_value = {"choices": [{"message": {"content": ""}}]}
    empty.raise_for_status.return_value = None
    malformed = Mock()
    malformed.json.return_value = {}
    malformed.raise_for_status.return_value = None
    with patch("app.providers.openai_compatible.httpx.post", return_value=empty):
        assert provider().test_connection(model="test-model")[0] is False
    with patch("app.providers.openai_compatible.httpx.post", return_value=malformed):
        assert provider().test_connection(model="test-model")[0] is False
