"""Tool-call payloads must be OpenAI-shaped so live hosts do not 400."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.core.agent import TOOL_LIMIT_MESSAGE, Agent
from universal.core.plugin import Plugin
from universal.core.platform import Universal
from universal.core.types import Message, ToolCall, ToolSpec
from universal.server import create_app
from tests.conftest import FakeProvider


def test_to_openai_uses_null_content_with_tool_calls() -> None:
    payload = Message(
        role="assistant",
        content="",
        tool_calls=[ToolCall(id="", name="utc_now", arguments={"when": "now"})],  # type: ignore[arg-type]
    ).to_openai()
    assert payload["content"] is None
    assert payload["tool_calls"] == [
        {
            "id": "call_0",
            "type": "function",
            "function": {"name": "utc_now", "arguments": '{"when": "now"}'},
        }
    ]


def test_to_openai_skips_nameless_calls() -> None:
    payload = Message(
        role="assistant",
        content="hello",
        tool_calls=[ToolCall(id="x", name="", arguments="{}")],
    ).to_openai()
    assert "tool_calls" not in payload
    assert payload["content"] == "hello"


def test_tool_message_includes_tool_call_id() -> None:
    payload = Message(role="tool", content="ok", tool_call_id="call_1").to_openai()
    assert payload["tool_call_id"] == "call_1"


def test_tool_crash_becomes_error_message_not_http_500() -> None:
    class BoomPlugin(Plugin):
        @property
        def name(self) -> str:
            return "boom"

        def tools(self) -> list[ToolSpec]:
            return [ToolSpec(name="explode", description="fails on purpose")]

        def invoke_tool(self, call: ToolCall) -> str | None:
            if call.name != "explode":
                return None
            raise RuntimeError("kaboom")

    provider = FakeProvider(
        reply="recovered",
        tool_script=[[ToolCall(id="", name="explode", arguments="{}")]],
    )
    agent = Agent(name="safe", provider=provider, template_id="general")
    agent.attach_plugin(BoomPlugin())
    assert agent.complete("go") == "recovered"
    tool_msgs = [message for message in provider.calls[1] if message.role == "tool"]
    assert tool_msgs
    assert "explode" in tool_msgs[0].content
    assert "kaboom" in tool_msgs[0].content
    assert tool_msgs[0].tool_call_id == "call_0"


def test_http_run_stays_on_python_when_node_is_up(platform: Universal, monkeypatch) -> None:
    class FakeRuntime:
        def healthy(self) -> bool:
            return True

        def think(self, **_kwargs: object) -> str:
            raise AssertionError("Node must not handle POST /v1/agents/{id}/run")

    monkeypatch.setattr("universal.server.default_manager", lambda: FakeRuntime())
    client = TestClient(create_app(platform, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "general", "name": "py-run"}).json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/run", json={"prompt": "hello"})
    assert response.status_code == 200
    assert response.json()["answer"].startswith("echo:")
    assert "runtime" not in response.json()


class _NamedTools(Plugin):
    def __init__(self, *names: str) -> None:
        self._names = names

    @property
    def name(self) -> str:
        return "named-tools"

    def tools(self) -> list[ToolSpec]:
        return [ToolSpec(name=item, description=item) for item in self._names]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name not in self._names:
            return None
        return f"ok:{call.name}"


def test_same_tool_three_times_forces_a_final_answer() -> None:
    from universal.core.types import CompletionResponse

    class RepeatThenAnswer(FakeProvider):
        def __init__(self) -> None:
            super().__init__(reply="unused")
            self.invocations = 0

        def complete(self, messages, *, tools=None, model=None):  # type: ignore[no-untyped-def]
            self.calls.append(list(messages))
            if not tools:
                return CompletionResponse(text="12:00 UTC", model=self.model, finish_reason="stop")
            self.invocations += 1
            return CompletionResponse(
                text="",
                tool_calls=[ToolCall(id=f"c{self.invocations}", name="utc_now", arguments="{}")],
                finish_reason="tool_calls",
                model=self.model,
            )

    provider = RepeatThenAnswer()
    agent = Agent(name="loop", provider=provider, template_id="researcher")
    agent.attach_plugin(_NamedTools("utc_now"))
    assert agent.complete("what time is it?") == "12:00 UTC"
    assert provider.invocations == 3
    assert any(message.content.startswith("You already called this tool") for message in provider.calls[-1])


def test_tool_limit_returns_a_final_message_not_an_error() -> None:
    from universal.core.types import CompletionResponse

    class FlipTools(FakeProvider):
        def __init__(self) -> None:
            super().__init__(reply="unused")
            self.n = 0

        def complete(self, messages, *, tools=None, model=None):  # type: ignore[no-untyped-def]
            self.calls.append(list(messages))
            if not tools:
                return CompletionResponse(text="", model=self.model, finish_reason="stop")
            self.n += 1
            name = "alpha" if self.n % 2 else "beta"
            return CompletionResponse(
                text="",
                tool_calls=[ToolCall(id=f"c{self.n}", name=name, arguments="{}")],
                finish_reason="tool_calls",
                model=self.model,
            )

    provider = FlipTools()
    agent = Agent(name="flip", provider=provider, template_id="general", max_tool_iters=4)
    agent.attach_plugin(_NamedTools("alpha", "beta"))
    assert agent.complete("keep going") == TOOL_LIMIT_MESSAGE
