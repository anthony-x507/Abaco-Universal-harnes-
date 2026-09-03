"""Streaming stays on accept → channel → agent → provider. No OpenAI clone."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.providers.demo import EchoProvider
from universal.server import create_app
from tests.conftest import FakeProvider


def test_complete_stream_yields_text_and_remembers() -> None:
    provider = FakeProvider(reply="abcdef")
    agent = Agent(name="g", provider=provider, template_id="general")
    chunks = list(agent.complete_stream("hi"))
    assert "".join(chunks) == "abcdef"
    assert [turn.content for turn in agent.history] == ["hi", "abcdef"]


def test_accept_stream_goes_through_channel(platform: Universal) -> None:
    agent = platform.factory.create("general", name="streamed")
    platform.factory.start(agent.id)
    chunks = list(agent.accept_stream("ping"))
    assert "".join(chunks).startswith("echo:")
    assert agent.history[-1].role == "assistant"


def test_echo_provider_streams_chunks() -> None:
    provider = EchoProvider()
    from universal.core.types import Message

    pieces = list(provider.stream([Message(role="user", content="abcd")]))
    assert "".join(pieces) == "(demo) abcd"
    assert len(pieces) > 1


def test_http_ask_stream_uses_same_registry(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post("/v1/agents", json={"template": "general", "name": "sse"})
    agent_id = created.json()["id"]
    with client.stream(
        "POST",
        f"/v1/agents/{agent_id}/ask",
        json={"prompt": "hello", "stream": True},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = "".join(response.iter_text())
    assert "hello" in body
    assert '"done": true' in body or '"done":true' in body
    listed = client.get(f"/v1/agents/{agent_id}").json()
    assert listed["history"]
    assert platform.registry.get(agent_id).id == agent_id


def test_stream_does_not_add_chat_completions(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    assert client.post("/v1/chat/completions", json={"stream": True}).status_code == 404
