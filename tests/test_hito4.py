"""Hito 4: ZIP labels, autonomous run, registry sidecar, usage stats."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from universal.config import Settings
from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import AgentState, ToolCall
from universal.core.usage import estimate_cost
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.server import create_app
from tests.conftest import FakeProvider
from tests.native_expect import NATIVE_LABELS, RESEARCHER_LABELS, RESEARCHER_PLUGIN_NAMES


def test_plugin_labels_are_readable(platform: Universal) -> None:
    researcher = platform.factory.create("researcher", name="labels")
    assert researcher.plugin_labels() == RESEARCHER_LABELS
    general = platform.factory.create("general", name="plain")
    assert general.plugin_labels() == NATIVE_LABELS
    payload = create_app(platform, demo=True)
    client = TestClient(payload)
    listed = client.get("/v1/agents").json()["agents"]
    row = next(item for item in listed if item["name"] == "labels")
    assert row["plugin_labels"] == RESEARCHER_LABELS


def test_run_loops_tools_without_a_second_complete_path() -> None:
    provider = FakeProvider(
        reply="summary: sky is clear",
        tool_script=[[ToolCall(id="c1", name="utc_now", arguments="{}")]],
    )
    agent = Agent(name="auto", provider=provider, template_id="researcher")
    belt = ToolBeltPlugin()
    belt.add(utc_now_tool())
    agent.attach_plugin(belt)
    answer = agent.run("investigate the time and summarize", max_iterations=5)
    assert answer == "summary: sky is clear"
    assert len(provider.calls) == 2
    assert agent.max_tool_iters == 8


def test_run_is_a_layer_above_accept(platform: Universal) -> None:
    agent = platform.factory.create("researcher", name="runner")
    platform.factory.start(agent.id)
    answer = agent.run("What time is it?")
    assert answer.startswith("echo:")
    assert agent.history[-1].role == "assistant"


def test_http_run_uses_accept_not_complete(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "researcher", "name": "http-run"}).json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/run", json={"prompt": "investigate and summarize"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("echo:")
    assert "usage" in body
    assert body["usage"]["calls"] >= 1


def test_registry_sidecar_reloads_identities_stopped(tmp_path: Path, settings: Settings, provider: FakeProvider) -> None:
    path = tmp_path / "registry.json"
    first = Universal(settings, provider=provider, persist_path=path)
    created = first.factory.create("researcher", name="keep-me", channel="cli")
    first.factory.start(created.id)
    assert first.lifecycle.state_of(created.id) is AgentState.RUNNING
    agent_id = created.id
    created.complete("hello there")
    assert created.history

    data = json.loads(path.read_text())
    assert data["agents"][0]["id"] == agent_id
    assert data["agents"][0]["name"] == "keep-me"
    assert data["agents"][0]["plugins"] == list(RESEARCHER_PLUGIN_NAMES)
    assert "history" not in data["agents"][0]
    assert "api_key" not in json.dumps(data)

    second = Universal(settings, provider=FakeProvider(reply="fresh"), persist_path=path)
    restored = second.registry.get(agent_id)
    assert restored.name == "keep-me"
    assert restored.template_id == "researcher"
    assert restored.plugins.names() == list(RESEARCHER_PLUGIN_NAMES)
    assert [turn.content for turn in restored.history] == ["hello there", "echo:hello there"]
    assert second.lifecycle.state_of(agent_id) is AgentState.STOPPED
    assert restored.channel is not None and not restored.channel.running


def test_no_persist_path_stays_in_memory(tmp_path: Path, settings: Settings, provider: FakeProvider) -> None:
    platform = Universal(settings, provider=provider)
    platform.factory.create("general", name="ephemeral")
    assert not (tmp_path / "registry.json").exists()
    assert platform.registry.persist_path is None


def test_usage_records_tokens_and_fixed_cost() -> None:
    provider = FakeProvider(reply="abcd" * 8, model="gpt-4o-mini")
    agent = Agent(name="meter", provider=provider, template_id="general")
    agent.complete("hello world")
    assert agent.usage.calls == 1
    assert agent.usage.prompt_tokens > 0
    assert agent.usage.completion_tokens > 0
    assert agent.usage.last_model == "gpt-4o-mini"
    expected = estimate_cost("gpt-4o-mini", agent.usage.prompt_tokens, agent.usage.completion_tokens)
    assert abs(agent.usage.estimated_cost - expected) < 1e-9


def test_echo_usage_is_free() -> None:
    provider = FakeProvider(reply="ok", model="fake-model")
    agent = Agent(name="free", provider=provider, template_id="general")
    agent.complete("ping")
    assert agent.usage.estimated_cost == 0.0


def test_zip_includes_usage_summary(platform: Universal, tmp_path: Path) -> None:
    agent = platform.factory.create("general", name="usage-box")
    agent.complete("count me")
    dest = tmp_path / "usage.zip"
    written = platform.factory.deploy(agent.id, dest)
    with zipfile.ZipFile(written) as archive:
        usage = json.loads(archive.read("usage.json"))
    assert usage["calls"] == 1
    assert usage["prompt_tokens"] >= 0
