"""HTTP factory control plane uses the injected Universal root."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.server import create_app
from tests.conftest import FakeProvider


def _client(platform: Universal, *, demo: bool = False) -> TestClient:
    return TestClient(create_app(platform, demo=demo))


def test_health_and_templates(platform: Universal) -> None:
    client = _client(platform)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["agents"] == 0
    templates = client.get("/v1/templates").json()["templates"]
    ids = {row["id"] for row in templates}
    assert ids == {"general", "researcher", "coder"}


def test_create_list_start_ask_stop_delete(platform: Universal) -> None:
    client = _client(platform, demo=True)
    created = client.post("/v1/agents", json={"template": "general", "name": "http-one"})
    assert created.status_code == 200
    agent_id = created.json()["id"]
    assert created.json()["channel"] == "cli"
    assert created.json()["state"] == "created"

    listed = client.get("/v1/agents").json()["agents"]
    assert len(listed) == 1
    assert listed[0]["id"] == agent_id

    started = client.post(f"/v1/agents/{agent_id}/start")
    assert started.json()["state"] == "running"

    asked = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "ping"})
    assert asked.status_code == 200
    assert asked.json()["answer"].startswith("echo:")
    assert asked.json()["history"]

    stopped = client.post(f"/v1/agents/{agent_id}/stop")
    assert stopped.json()["state"] == "stopped"

    deleted = client.delete(f"/v1/agents/{agent_id}")
    assert deleted.status_code == 200
    assert client.get("/v1/agents").json()["agents"] == []
    assert agent_id not in {info.id for info in platform.factory.list()}


def test_server_uses_the_same_registry(platform: Universal) -> None:
    client = _client(platform)
    created = client.post("/v1/agents", json={"template": "coder", "name": "same-root"})
    agent_id = created.json()["id"]
    assert platform.registry.get(agent_id).name == "same-root"
    assert platform.factory.generator.registry is platform.registry
    assert platform.factory.manager.registry is platform.registry


def test_unknown_channel_is_404(platform: Universal) -> None:
    client = _client(platform)
    response = client.post("/v1/agents", json={"template": "general", "channel": "telegram"})
    assert response.status_code == 404
    assert "telegram" in response.json()["error"]


def test_settings_update_stays_in_memory(platform: Universal) -> None:
    client = _client(platform)
    before = client.get("/v1/settings").json()
    assert before["llm_api_key"] == "***"
    updated = client.put(
        "/v1/settings",
        json={"llm_model": "gpt-test", "default_channel": "cli"},
    )
    assert updated.status_code == 200
    assert updated.json()["llm_model"] == "gpt-test"
    assert platform.settings.llm_model == "gpt-test"


def test_no_chat_completions_clone(platform: Universal) -> None:
    client = _client(platform)
    assert client.post("/v1/chat/completions", json={}).status_code == 404
