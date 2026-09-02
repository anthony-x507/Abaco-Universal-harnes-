"""Agent answers via a mocked provider, including the tool loop."""

from __future__ import annotations

from universal.core.agent import Agent
from universal.core.types import ToolCall
from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from tests.conftest import FakeProvider


def test_agent_answers_via_mocked_provider() -> None:
    provider = FakeProvider(reply="four")
    agent = Agent(name="g", provider=provider, template_id="general", system_prompt="Be brief.")
    answer = agent.complete("What is 2+2?")
    assert answer == "four"
    assert provider.calls, "provider.complete must be called"
    roles = [m.role for m in provider.calls[0]]
    assert "user" in roles
    assert provider.calls[0][-1].content == "What is 2+2?"


def test_agent_remembers_turns() -> None:
    provider = FakeProvider(reply=lambda messages: f"n={len(messages)}")
    agent = Agent(name="g", provider=provider, template_id="general")
    agent.complete("one")
    agent.complete("two")
    assert len(agent.history) == 4  # user, assistant, user, assistant


def test_system_prompt_plugin_leads_the_request() -> None:
    provider = FakeProvider(reply="ok")
    agent = Agent(name="g", provider=provider, template_id="general", system_prompt="ignored")
    agent.attach_plugin(SystemPromptPlugin("You are the research face."))
    agent.complete("hello")
    first = provider.calls[0][0]
    assert first.role == "system"
    assert first.content == "You are the research face."
    assert sum(1 for m in provider.calls[0] if m.role == "system") == 1


def test_tool_loop_invokes_plugin_and_returns_final_text() -> None:
    provider = FakeProvider(
        reply="the time was noted",
        tool_script=[[ToolCall(id="call_1", name="utc_now", arguments="{}")]],
    )
    agent = Agent(name="r", provider=provider, template_id="researcher")
    belt = ToolBeltPlugin()
    belt.add(utc_now_tool())
    agent.attach_plugin(belt)
    answer = agent.complete("What time is it?")
    assert answer == "the time was noted"
    assert len(provider.calls) == 2
    tool_msgs = [m for m in provider.calls[1] if m.role == "tool"]
    assert tool_msgs and "T" in tool_msgs[0].content  # ISO-8601
