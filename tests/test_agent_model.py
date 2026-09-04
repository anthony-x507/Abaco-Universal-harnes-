"""Per-agent model selection. Shared provider stays unless a live host changes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.server import create_app


def test_patch_changes_only_that_agent_model(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    first = client.post("/v1/agents", json={"template": "general", "name": "one"}).json()
    second = client.post("/v1/agents", json={"template": "general", "name": "two"}).json()
    updated = client.patch(f"/v1/agents/{first['id']}", json={"provider": "DeepSeek (V4 Pro)"})
    assert updated.status_code == 200
    assert updated.json()["model"] == "deepseek-v4-pro"
    other = client.get(f"/v1/agents/{second['id']}").json()
    assert other["model"] != "deepseek-v4-pro"
    assert platform.registry.get(first["id"]).provider is platform.registry.get(second["id"]).provider


def test_create_keeps_preset_on_the_new_agent(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "general", "name": "groq-face", "provider": "Groq (Compound)"},
    ).json()
    assert created["model"] == "groq/compound"
