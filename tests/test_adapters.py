"""Provider adapter dialects: auth, payload, parse, shared HTTP client."""

from __future__ import annotations

import json

import httpx
import pytest

from universal.core.agent import Agent
from universal.core.types import Message
from universal.exceptions import ProviderError
from universal.providers.factory import PROVIDER_MAP, detect_adapter_type, get_provider_adapter
from universal.providers.openai_compat import OpenAICompatProvider


def test_provider_map_covers_required_hosts() -> None:
    for key in (
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "zhipu",
        "minimax",
        "moonshot",
        "baidu",
        "alibaba",
        "tencent",
        "doubao",
        "sensenova",
        "yi",
        "ollama",
        "lmstudio",
        "vllm",
        "mistral",
        "cohere",
    ):
        assert key in PROVIDER_MAP


def test_detect_from_url_and_explicit_type() -> None:
    assert detect_adapter_type("https://api.openai.com/v1", provider_type="openai") == "openai"
    assert detect_adapter_type("https://api.deepseek.com/v1", provider_type="deepseek") == "deepseek"
    assert detect_adapter_type("https://api.anthropic.com", provider_type="anthropic") == "anthropic"
    assert (
        detect_adapter_type("https://generativelanguage.googleapis.com/v1beta", provider_type="google")
        == "google"
    )
    assert detect_adapter_type("https://open.bigmodel.cn/api/paas/v4") == "zhipu"
    assert (
        detect_adapter_type(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            provider_type="google",
        )
        == "openai"
    )
    assert detect_adapter_type("https://openrouter.ai/api/v1", provider_type="anthropic") == "openai"


def _openai_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer test-key"
    assert str(request.url).endswith("/chat/completions")
    return httpx.Response(
        200,
        json={
            "model": "gpt-test",
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok-openai"}}],
        },
    )


def _anthropic_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["x-api-key"] == "claude-key"
    assert str(request.url).endswith("/v1/messages")
    body = json.loads(request.content)
    assert "messages" in body
    return httpx.Response(
        200,
        json={
            "model": "claude-test",
            "content": [{"type": "text", "text": "ok-anthropic"}],
            "stop_reason": "end_turn",
        },
    )


def _google_handler(request: httpx.Request) -> httpx.Response:
    assert "key=gem-key" in str(request.url)
    assert "generateContent" in str(request.url)
    assert "Authorization" not in request.headers
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": "ok-google"}]}, "finishReason": "STOP"}]},
    )


def _zhipu_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer glm-key"
    return httpx.Response(
        200,
        json={
            "model": "glm-5.2",
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok-zhipu"}}],
        },
    )


def _deepseek_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer ds-key"
    return httpx.Response(
        200,
        json={
            "model": "deepseek-v4-pro",
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok-deepseek"}}],
        },
    )


@pytest.mark.parametrize(
    ("kind", "base", "key", "model", "handler", "text"),
    [
        ("openai", "https://api.openai.com/v1", "test-key", "gpt-test", _openai_handler, "ok-openai"),
        ("deepseek", "https://api.deepseek.com/v1", "ds-key", "deepseek-v4-pro", _deepseek_handler, "ok-deepseek"),
        ("anthropic", "https://api.anthropic.com", "claude-key", "claude-test", _anthropic_handler, "ok-anthropic"),
        ("google", "https://generativelanguage.googleapis.com/v1beta", "gem-key", "gemini-test", _google_handler, "ok-google"),
        ("zhipu", "https://open.bigmodel.cn/api/paas/v4", "glm-key", "glm-5.2", _zhipu_handler, "ok-zhipu"),
    ],
)
def test_five_provider_dialects(kind: str, base: str, key: str, model: str, handler, text: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(
        base, key, model, client=client, adapter_type=kind
    )
    assert provider.adapter_type == kind
    response = provider.complete([Message(role="user", content="ping")])
    assert response.text == text
    provider.close()


def test_errors_are_normalized() -> None:
    provider = OpenAICompatProvider(
        "https://api.openai.com/v1",
        "bad",
        "m",
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="nope"))),
    )
    with pytest.raises(ProviderError, match="Invalid API key") as caught:
        provider.complete([Message(role="user", content="ping")])
    assert caught.value.status_code == 401


def test_agent_set_model_uses_adapter() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("x-api-key", ""))
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "from-adapter"}], "model": "claude-test"},
        )

    agent = Agent(name="w", provider=OpenAICompatProvider(
        "https://api.openai.com/v1",
        "old",
        "gpt",
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
    ), template_id="general")
    agent.set_model(
        "anthropic",
        "https://api.anthropic.com",
        api_key="claude-key",
        model="claude-test",
    )
    agent.provider._client = httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[attr-defined]
    assert agent.complete("hi") == "from-adapter"
    assert seen == ["claude-key"]
    assert get_provider_adapter("zhipu", "https://open.bigmodel.cn/api/paas/v4").name == "zhipu"
