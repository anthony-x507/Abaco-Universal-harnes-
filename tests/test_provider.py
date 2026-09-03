"""OpenAI-compatible HTTP client against a recorded (httpx mock) endpoint."""

from __future__ import annotations

import httpx
import pytest

from universal.core.types import Message
from universal.exceptions import ProviderError
from universal.providers.openai_compat import OpenAICompatProvider


def test_openai_compat_parses_chat_completion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://example.test/v1/chat/completions")
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "model": "fake-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "recorded-answer"},
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAICompatProvider(
        "https://example.test/v1",
        "test-key",
        "fake-model",
        client=client,
    )
    response = provider.complete([Message(role="user", content="ping")])
    assert response.text == "recorded-answer"
    assert response.model == "fake-model"
    provider.close()


def test_openai_compat_http_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="nope"))
    provider = OpenAICompatProvider(
        "https://example.test/v1",
        "test-key",
        "fake-model",
        client=httpx.Client(transport=transport),
    )
    with pytest.raises(ProviderError, match="Invalid API key") as caught:
        provider.complete([Message(role="user", content="ping")])
    assert caught.value.status_code == 401


def test_openai_compat_refuses_empty_key() -> None:
    provider = OpenAICompatProvider("https://example.test/v1", "", "fake-model")
    with pytest.raises(ProviderError, match="API_KEY"):
        provider.complete([Message(role="user", content="ping")])


def test_completions_url_normalization() -> None:
    provider = OpenAICompatProvider(
        "https://example.test/v1/chat/completions", "k", "m"
    )
    assert provider.completions_url == "https://example.test/v1/chat/completions"
    other = OpenAICompatProvider("https://example.test/v1/", "k", "m")
    assert other.completions_url == "https://example.test/v1/chat/completions"
