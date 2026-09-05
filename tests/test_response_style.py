"""Response-style native plugin: preference, hooks, and concise enforcement."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from universal.audit import repo_root
from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import CompletionResponse, Message, ToolCall
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.plugins.response_style import (
    DEFAULT_STYLE,
    ResponseStylePlugin,
    enforce_concise_text,
    load_response_style,
    preference_path,
    requests_detail,
    save_response_style,
    style_instruction,
)
from universal.server import create_app
from tests.conftest import FakeProvider


def _call(style: str) -> ToolCall:
    return ToolCall(id="t1", name="set_response_style", arguments=json.dumps({"style": style}))


def test_response_style_is_last_native_plugin() -> None:
    assert "response_style" in NATIVE_PLUGIN_NAMES
    assert NATIVE_PLUGIN_NAMES[-1] == "response_style"
    assert "identity" in NATIVE_PLUGIN_NAMES


def test_every_created_agent_gets_response_style(platform: Universal) -> None:
    for template_id in ("general", "researcher", "coder"):
        agent = platform.factory.create(template_id, name=f"rs-{template_id}")
        assert "response_style" in agent.plugins
        assert "identity" in agent.plugins
        tools = {spec.name for spec in agent.plugins.collect_tools()}
        assert "set_response_style" in tools
        names = agent.plugins.names()
        assert names.index("response_style") == len(NATIVE_PLUGIN_NAMES) - 1
        assert names.index("identity") < names.index("response_style")
        if template_id != "researcher":
            assert names[-1] == "response_style"


def test_default_preference_is_concise(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    assert load_response_style() == DEFAULT_STYLE == "concise"
    assert not preference_path().exists()


def test_set_response_style_persists_safely(tmp_path: Path, monkeypatch) -> None:
    data = tmp_path / "data"
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(data))
    plugin = ResponseStylePlugin()

    out = plugin.invoke_tool(_call("detailed"))
    assert out is not None
    body = json.loads(out)
    assert body["style"] == "detailed"
    path = preference_path()
    assert path.is_file()
    assert path.parent == data
    assert load_response_style() == "detailed"
    assert json.loads(path.read_text(encoding="utf-8"))["style"] == "detailed"
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600 or os.name == "nt"

    assert plugin.invoke_tool(_call("default")) is not None
    assert load_response_style() == "default"
    assert plugin.invoke_tool(_call("concise")) is not None
    assert load_response_style() == "concise"


def test_set_response_style_rejects_unknown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    plugin = ResponseStylePlugin()
    err = plugin.invoke_tool(_call("verbose"))
    assert err is not None and err.startswith("Error:")
    assert load_response_style() == "concise"


def test_runtime_route_and_node_stub_set_response_style(
    platform: Universal, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    client = TestClient(create_app(platform, demo=True))
    response = client.post("/v1/response-style", json={"style": "detailed"})
    assert response.status_code == 200
    assert response.json() == {"style": "detailed"}
    assert load_response_style() == "detailed"

    stub = (repo_root() / "agent_runtime" / "plugins" / "response_style.js").read_text()
    runtime = (repo_root() / "agent_runtime" / "runtime.js").read_text()
    assert "set_response_style" in stub
    assert "/v1/response-style" in stub
    assert "candidate.get_tool_definition()?.name === call.name" in runtime


def test_before_complete_injects_style_instruction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    save_response_style("detailed")
    plugin = ResponseStylePlugin()
    agent = Agent(name="rs", provider=FakeProvider(), template_id="general")
    messages = [
        Message(role="system", content="You are helpful."),
        Message(role="user", content="hi"),
    ]
    out = plugin.before_complete(agent, messages)
    assert out[0].role == "system"
    assert out[0].content == "You are helpful.\n\n" + style_instruction("detailed")
    assert out[1].role == "user"
    assert sum(message.role == "system" for message in out) == 1


def test_after_complete_truncates_concise_and_preserves_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    save_response_style("concise")
    plugin = ResponseStylePlugin()
    agent = Agent(name="rs", provider=FakeProvider(), template_id="general")
    long_text = "one\ntwo\nthree\nfour\nfive"
    raw = {"id": "resp-1"}
    calls = [ToolCall(id="c1", name="run_command", arguments="{}")]
    response = CompletionResponse(
        text=long_text,
        tool_calls=calls,
        model="demo",
        finish_reason="tool_calls",
        raw=raw,
    )
    out = plugin.after_complete(agent, [], response)
    assert out.text == "one\ntwo\nthree"
    assert out.tool_calls == calls
    assert out.model == "demo"
    assert out.finish_reason == "tool_calls"
    assert out.raw == raw


def test_after_complete_does_not_truncate_detailed_or_default(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    plugin = ResponseStylePlugin()
    agent = Agent(name="rs", provider=FakeProvider(), template_id="general")
    long_text = "one\ntwo\nthree\nfour\nfive"
    for style in ("detailed", "default"):
        save_response_style(style)
        response = CompletionResponse(text=long_text, model="demo")
        out = plugin.after_complete(agent, [], response)
        assert out.text == long_text
        assert out.model == "demo"


def test_concise_style_honors_explicit_detail_request(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    save_response_style("concise")
    plugin = ResponseStylePlugin()
    agent = Agent(name="rs", provider=FakeProvider(), template_id="general")
    messages = [Message(role="user", content="Explícalo paso a paso y con detalle")]
    response = CompletionResponse(text="one\ntwo\nthree\nfour\nfive", model="demo")

    assert requests_detail(messages) is True
    assert plugin.after_complete(agent, messages, response).text == response.text


def test_enforce_concise_text_helper() -> None:
    assert enforce_concise_text("a\n\nb\nc\nd") == "a\n\nb\nc"
    assert enforce_concise_text("only") == "only"
    assert enforce_concise_text("") == ""


def test_agent_complete_applies_concise_enforcement(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    save_response_style("concise")
    provider = FakeProvider(reply="line1\nline2\nline3\nline4\nline5")
    agent = Agent(name="rs", provider=provider, template_id="general")
    agent.attach_plugin(ResponseStylePlugin())
    assert agent.complete("ping") == "line1\nline2\nline3"
