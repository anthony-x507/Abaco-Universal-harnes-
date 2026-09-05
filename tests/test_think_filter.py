"""``<think>`` reasoning never reaches users, history, SSE, or the LLM bridge."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient

from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import CompletionResponse, Message
from universal.plugins.language_policy import LanguagePolicyPlugin
from universal.providers.base import Provider
from universal.providers.openai import OpenAIAdapter
from universal.server import create_app
from universal.think_filter import ThinkStreamFilter, strip_think_tags
from tests.conftest import FakeProvider


class ChunkProvider(Provider):
    def __init__(self, chunks: list[str], *, model: str = "chunk-model") -> None:
        self._chunks = chunks
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[object] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        return CompletionResponse(text="".join(self._chunks), model=self._model)

    def stream(
        self,
        messages: list[Message],
        *,
        tools: list[object] | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        yield from self._chunks


def test_strip_complete_and_unclosed_blocks() -> None:
    assert strip_think_tags("hello") == "hello"
    assert strip_think_tags("<think>secret</think>visible") == "visible"
    assert strip_think_tags("pre<THINK>x</Think>post") == "prepost"
    assert strip_think_tags("keep <think>hidden") == "keep "
    assert strip_think_tags("<think>only") == ""
    assert (
        strip_think_tags("a<think>1</think>b<think>2</think>c") == "abc"
    )


def test_stream_filter_handles_split_tags() -> None:
    filt = ThinkStreamFilter()
    leaked: list[str] = []
    for piece in ("hello <th", "ink>secret</th", "ink> world"):
        visible = filt.feed(piece)
        leaked.append(visible)
        assert "secret" not in visible
        assert "<think>" not in visible.lower()
        assert "</think>" not in visible.lower()
    leaked.append(filt.flush())
    assert "".join(leaked) == "hello  world"
    assert filt.text == "hello  world"


def test_unclosed_think_at_end_of_stream_is_dropped() -> None:
    filt = ThinkStreamFilter()
    assert filt.feed("ok <think>private chain") == "ok "
    assert filt.flush() == ""
    assert filt.text == "ok "


def test_partial_open_tag_is_held_then_released_if_not_think() -> None:
    filt = ThinkStreamFilter()
    assert filt.feed("value <th") == "value "
    assert filt.feed("ermal>ok") == "<thermal>ok"
    assert filt.flush() == ""
    assert filt.text == "value <thermal>ok"


def test_agent_stream_does_not_emit_or_remember_think() -> None:
    provider = ChunkProvider(
        ["<th", "ink>\nreason\n</th", "ink>Line one\nLine two\nLine three\nLine four"]
    )
    agent = Agent(name="g", provider=provider, template_id="general")
    agent.plugins.install(LanguagePolicyPlugin(), agent)
    chunks = list(agent.complete_stream("hola"))
    text = "".join(chunks)
    assert "reason" not in text
    assert "<think>" not in text.lower()
    stored = agent.history[-1].content
    assert "reason" not in stored
    assert "<think>" not in stored.lower()
    lines = [line for line in stored.splitlines() if line.strip()]
    assert len(lines) <= 3


def test_agent_complete_strips_without_plugins() -> None:
    agent = Agent(
        name="bare",
        provider=FakeProvider(reply="<think>nope</think>Shown"),
        template_id="general",
    )
    assert agent.complete("hi") == "Shown"
    assert agent.history[-1].content == "Shown"


def test_openai_adapter_strips_message_content() -> None:
    adapter = OpenAIAdapter("https://example.test/v1", api_key="k", model="m")
    parsed = adapter.parse_response(
        {
            "model": "m",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "<think>x</think>ok"},
                }
            ],
        }
    )
    assert parsed.text == "ok"


def test_http_stream_and_history_hide_think(platform: Universal) -> None:
    agent = platform.factory.create("general", name="think-sse")
    platform.factory.start(agent.id)
    agent.provider = FakeProvider(reply="<think>hidden chain</think>Respuesta visible")
    client = TestClient(create_app(platform, demo=True))
    with client.stream(
        "POST",
        f"/v1/agents/{agent.id}/ask",
        json={"prompt": "hola", "stream": True},
    ) as response:
        body = "".join(response.iter_text())
    assert "hidden chain" not in body
    listed = client.get(f"/v1/agents/{agent.id}").json()
    assistant = [turn for turn in listed["history"] if turn["role"] == "assistant"][-1]
    assert "hidden chain" not in assistant["content"]
    assert "<think>" not in assistant["content"].lower()
    assert "Respuesta visible" in assistant["content"]


def test_llm_complete_bridge_strips_think(platform: Universal) -> None:
    platform.factory.generator._provider = FakeProvider(reply="<think>bridge</think>out")  # noqa: SLF001
    client = TestClient(create_app(platform, demo=True))
    body = client.post(
        "/v1/llm/complete",
        json={"messages": [{"role": "user", "content": "hi"}]},
    ).json()
    assert body["content"] == "out"
    assert "bridge" not in body["content"]
