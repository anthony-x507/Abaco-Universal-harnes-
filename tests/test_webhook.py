"""Webhook channel: catalog, accept path, factory inbound, optional outbound."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.channels.webhook import WebhookChannel
from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.server import create_app
from tests.conftest import FakeProvider


def test_webhook_accept_goes_through_handle_text() -> None:
    posts: list[tuple[str, dict[str, object]]] = []

    def poster(url: str, payload: dict[str, object]) -> None:
        posts.append((url, payload))

    channel = WebhookChannel(outbound_url="http://example.test/hook", poster=poster)
    provider = FakeProvider(reply="via-webhook")
    agent = Agent(name="w", provider=provider, template_id="general", channel=channel)
    channel.agent_id = agent.id
    agent.bind_channel()
    channel.start()
    answer = agent.accept("ping")
    assert answer == "via-webhook"
    assert posts == [("http://example.test/hook", {"agent_id": agent.id, "text": "via-webhook"})]


def test_webhook_empty_outbound_skips_post() -> None:
    posts: list[object] = []
    channel = WebhookChannel(outbound_url="", poster=lambda url, payload: posts.append(payload))
    agent = Agent(name="w", provider=FakeProvider(reply="ok"), template_id="general", channel=channel)
    agent.bind_channel()
    channel.start()
    assert agent.accept("hi") == "ok"
    assert posts == []


def test_factory_creates_webhook_agent(platform: Universal) -> None:
    agent = platform.factory.create(
        "general",
        name="hooked",
        channel="webhook",
        outbound_url="http://example.test/cb",
    )
    assert agent.channel is not None
    assert agent.channel.name == "webhook"
    assert isinstance(agent.channel, WebhookChannel)
    assert agent.channel.outbound_url == "http://example.test/cb"
    assert agent.channel.agent_id == agent.id


def test_http_webhook_inbound_uses_accept(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "general", "name": "in", "channel": "webhook"},
    )
    assert created.status_code == 200
    agent_id = created.json()["id"]
    assert created.json()["channel"] == "webhook"

    listed = client.get("/v1/channels").json()
    assert "webhook" in listed["channels"]

    inbound = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "hello"})
    assert inbound.status_code == 200
    assert inbound.json()["answer"].startswith("echo:")
    assert inbound.json()["history"]


def test_http_webhook_rejects_cli_agent(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "general", "channel": "cli"}).json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "nope"})
    assert response.status_code == 400
    assert "webhook" in str(response.json()).lower()


def test_settings_lists_webhook(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    settings = client.get("/v1/settings").json()
    assert "webhook" in settings["channels"]
    assert "webhook" not in settings["channels_coming"]


def test_http_create_stores_outbound_url(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={
            "template": "general",
            "name": "out",
            "channel": "webhook",
            "outbound_url": "http://example.test/cb",
        },
    )
    assert created.status_code == 200
    assert created.json()["outbound_url"] == "http://example.test/cb"


def test_http_webhook_busy_is_409(platform: Universal) -> None:
    app = create_app(platform, demo=True)
    client = TestClient(app)
    agent_id = client.post(
        "/v1/agents",
        json={"template": "general", "channel": "webhook"},
    ).json()["id"]
    app.state.universal.asking.add(agent_id)
    response = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "two"})
    assert response.status_code == 409
