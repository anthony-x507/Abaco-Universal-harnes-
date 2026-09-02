"""Hot-swap plugins on a live agent."""

from __future__ import annotations

from universal.core.agent import Agent
from universal.core.types import CompletionResponse, Message
from universal.exceptions import PluginError
from universal.plugins.transcript import TranscriptPlugin
from tests.conftest import FakeProvider


class PrefixPlugin:
    name = "prefix"

    def __init__(self, token: str) -> None:
        self.token = token
        self.attached = 0
        self.detached = 0

    def on_attach(self, agent: Agent) -> None:
        self.attached += 1

    def on_detach(self, agent: Agent) -> None:
        self.detached += 1

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        return messages

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        return CompletionResponse(text=f"{self.token}:{response.text}", model=response.model)

    def tools(self) -> list:
        return []

    def invoke_tool(self, call: object) -> None:
        return None


def test_hot_swap_changes_behavior() -> None:
    provider = FakeProvider(reply="raw")
    agent = Agent(name="p", provider=provider, template_id="general")
    first = PrefixPlugin("A")
    agent.attach_plugin(first)
    assert agent.complete("x") == "A:raw"
    assert first.attached == 1

    second = PrefixPlugin("B")
    agent.attach_plugin(second)  # replace by same name
    assert first.detached == 1
    assert agent.complete("y") == "B:raw"
    assert "prefix" in agent.plugins

    agent.detach_plugin("prefix")
    assert agent.complete("z") == "raw"
    assert "prefix" not in agent.plugins


def test_uninstall_missing_raises() -> None:
    agent = Agent(name="p", provider=FakeProvider(), template_id="general")
    try:
        agent.detach_plugin("nope")
    except PluginError:
        return
    raise AssertionError("expected PluginError")


def test_transcript_plugin_records_events() -> None:
    agent = Agent(name="p", provider=FakeProvider(reply="ok"), template_id="general")
    log = TranscriptPlugin()
    agent.attach_plugin(log)
    agent.complete("hi")
    kinds = [event.kind for event in log.events]
    assert kinds == ["before", "after"]
