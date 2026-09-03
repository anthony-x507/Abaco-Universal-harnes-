"""Ephemeral tool / delegate SSE events stay off the chat history."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.server import create_app
from tests.conftest import FakeProvider


def test_complete_stream_events_emit_tool_before_tokens() -> None:
    provider = FakeProvider(
        reply="time noted",
        tool_script=[[ToolCall(id="c1", name="utc_now", arguments="{}")]],
    )
    agent = Agent(name="r", provider=provider, template_id="researcher")
    from universal.plugins.tools import ToolBeltPlugin, utc_now_tool

    belt = ToolBeltPlugin()
    belt.add(utc_now_tool())
    agent.attach_plugin(belt)
    events = list(agent.complete_stream_events("What time is it?"))
    kinds = [event.get("type") for event in events]
    assert "tool_execution" in kinds
    assert events[0] == {"type": "tool_execution", "tool": "utc_now"}
    assert any(event.get("type") == "token" and "time noted" in str(event.get("text")) for event in events)
    assert all("Executing tool" not in turn.content for turn in agent.history)


def test_http_stream_includes_tool_execution(settings: object) -> None:
    provider = FakeProvider(
        reply="clocked",
        tool_script=[[ToolCall(id="c1", name="utc_now", arguments="{}")]],
    )
    root = Universal(settings, provider=provider)  # type: ignore[arg-type]
    client = TestClient(create_app(root, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "researcher", "name": "clock"}).json()["id"]
    with client.stream(
        "POST",
        f"/v1/agents/{agent_id}/ask",
        json={"prompt": "What time is it?", "stream": True},
    ) as response:
        body = "".join(response.iter_text())
    assert '"type": "tool_execution"' in body or '"type":"tool_execution"' in body
    assert "utc_now" in body
    assert '"type": "token"' in body or '"type":"token"' in body or '"text"' in body
    history = client.get(f"/v1/agents/{agent_id}").json()["history"]
    blob = " ".join(turn["content"] for turn in history)
    assert "Executing tool" not in blob


def test_delegate_tool_emits_delegating_event() -> None:
    provider = FakeProvider(
        reply="handed off",
        tool_script=[[ToolCall(id="d1", name="call_agent", arguments='{"name":"Researcher_2"}')]],
    )
    agent = Agent(name="lead", provider=provider, template_id="general")

    class DelegatePlugin:
        name = "delegate_stub"

        def tools(self):
            from universal.core.types import ToolSpec

            return [ToolSpec(name="call_agent", description="Send work to another agent.")]

        def invoke_tool(self, call: ToolCall) -> str | None:
            return "ok" if call.name == "call_agent" else None

        def before_complete(self, agent, messages):  # type: ignore[no-untyped-def]
            return messages

        def after_complete(self, agent, messages, response):  # type: ignore[no-untyped-def]
            return response

        def on_attach(self, agent) -> None:  # type: ignore[no-untyped-def]
            return None

        def on_detach(self, agent) -> None:  # type: ignore[no-untyped-def]
            return None

    agent.attach_plugin(DelegatePlugin())  # type: ignore[arg-type]
    events = list(agent.complete_stream_events("ask the other one"))
    assert {"type": "delegating", "target": "Researcher_2"} in events
