"""The six polish / intelligence adjustments (notes/60.md)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from universal.channels.cli import CLIChannel
from universal.cli import run_chat_turns
from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import AgentState, ToolCall
from universal.exceptions import ProviderError
from universal.server import create_app
from universal.templates.catalog import get_template
from tests.conftest import FakeProvider


def test_ajuste1_chat_turns_go_through_accept(platform: Universal) -> None:
    agent = platform.factory.create("general", name="chat-cli")
    platform.factory.start(agent.id)
    assert isinstance(agent.channel, CLIChannel)
    with agent.channel.capture():
        answers = run_chat_turns(agent, ["hello there", "/quit"])
    assert answers == ["echo:hello there"]
    assert [turn.content for turn in agent.history] == ["hello there", "echo:hello there"]


def test_ajuste1_researcher_chat_runs_utc_now(settings: object, tmp_path: Path) -> None:
    provider = FakeProvider(
        reply="The current UTC time was fetched.",
        tool_script=[[ToolCall(id="call_1", name="utc_now", arguments="{}")]],
    )
    root = Universal(settings, provider=provider)  # type: ignore[arg-type]
    agent = root.factory.create("researcher", name="chat-r")
    root.factory.start(agent.id)
    assert isinstance(agent.channel, CLIChannel)
    with agent.channel.capture():
        answers = run_chat_turns(agent, ["What time is it?"])
    assert answers == ["The current UTC time was fetched."]
    assert len(provider.calls) == 2
    tool_msgs = [message for message in provider.calls[1] if message.role == "tool"]
    assert tool_msgs and "T" in tool_msgs[0].content


def test_ajuste2_http_maps_invalid_key(platform: Universal) -> None:
    class BadKey(FakeProvider):
        def complete(self, messages, *, tools=None, model=None):  # type: ignore[no-untyped-def]
            raise ProviderError("Invalid API key", status_code=401)

    root = Universal(platform.settings, provider=BadKey())
    client = TestClient(create_app(root, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "general"}).json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "hi"})
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid API key"


def test_ajuste2_http_maps_timeout(platform: Universal) -> None:
    class Slow(FakeProvider):
        def complete(self, messages, *, tools=None, model=None):  # type: ignore[no-untyped-def]
            raise ProviderError("LLM request timed out", status_code=408)

    root = Universal(platform.settings, provider=Slow())
    client = TestClient(create_app(root, demo=True))
    agent_id = client.post("/v1/agents", json={"template": "general"}).json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "hi"})
    assert response.status_code == 408
    assert "timed out" in response.json()["error"].lower()


def test_ajuste3_reset_clears_history_keeps_state(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post("/v1/agents", json={"template": "general", "name": "wipe"})
    agent_id = created.json()["id"]
    client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "remember this"})
    assert client.get(f"/v1/agents/{agent_id}").json()["history"]
    assert platform.lifecycle.state_of(agent_id) is AgentState.RUNNING
    reset = client.post(f"/v1/agents/{agent_id}/reset")
    assert reset.status_code == 200
    assert reset.json()["history"] == []
    assert reset.json()["status"] == "reset"
    assert reset.json()["state"] == "running"
    assert platform.lifecycle.state_of(agent_id) is AgentState.RUNNING
    assert platform.registry.get(agent_id).history == []


def test_ajuste4_memory_reloads_by_agent_name(tmp_path: Path, settings: object) -> None:
    memory_dir = tmp_path / "named-mem"

    def reply(messages: list) -> str:
        blob = " ".join(message.content for message in messages)
        if "What is my name" in blob and "John" in blob:
            return "John"
        return "noted"

    first = Agent(
        name="pat",
        provider=FakeProvider(reply=reply),
        template_id="researcher",
        memory=True,
        memory_dir=memory_dir,
    )
    first.complete("My name is John")
    path = first.memory_path()
    assert path.is_file()
    stored = path.read_text(encoding="utf-8")
    assert "John" in stored

    second = Agent(
        name="pat",
        provider=FakeProvider(reply=reply),
        template_id="researcher",
        memory=True,
        memory_dir=memory_dir,
    )
    assert any("John" in str(fact) for fact in second.memory_data["facts"])
    assert second.complete("What is my name?") == "John"


def test_ajuste4_researcher_template_enables_memory(platform: Universal) -> None:
    agent = platform.factory.create("researcher", name="memo")
    assert get_template("researcher").memory is True
    assert agent.memory_enabled is True
    assert platform.factory.create("general", name="no-mem").memory_enabled is False


def test_ajuste5_provider_sees_only_last_ten_turns(platform: Universal, provider: FakeProvider) -> None:
    agent = platform.factory.create("general", name="window")
    platform.factory.start(agent.id)
    for index in range(15):
        agent.accept(f"turn-{index}")
    assert len(agent.history) == 30
    last = provider.calls[-1]
    user_assistant = [message for message in last if message.role in {"user", "assistant"}]
    assert len(user_assistant) == 21  # 10 prior turns + the new user prompt
    contents = [message.content for message in user_assistant if message.role == "user"]
    assert "turn-0" not in contents
    assert "turn-3" not in contents
    assert contents[0] == "turn-4"
    assert contents[-1] == "turn-14"


def test_ajuste6_prompts_are_the_polished_copy() -> None:
    general = get_template("general").system_prompt
    researcher = get_template("researcher").system_prompt
    coder = get_template("coder").system_prompt
    assert "do not guess" in general.lower() or "do not guess" in general
    assert "utc_now" in researcher
    assert "at most 3 lines" in coder.lower()
    assert "do not call the same tool again" in general.lower()
    assert "do not call the same tool again" in researcher.lower()
    assert "do not call the same tool again" in coder.lower()
