"""CLI channel implements BaseCommunication and can drive an agent."""

from __future__ import annotations

from io import StringIO

from universal.channels.base import BaseCommunication
from universal.channels.cli import CLIChannel
from universal.core.agent import Agent
from tests.conftest import FakeProvider


def test_cli_channel_is_base_communication() -> None:
    assert issubclass(CLIChannel, BaseCommunication)


def test_cli_channel_round_trip() -> None:
    out = StringIO()
    channel = CLIChannel(stdout=out)
    channel.bind(lambda inbound: f"heard:{inbound.text}")
    channel.start()
    channel.deliver("hello")
    reply = channel.serve_once()
    assert reply == "heard:hello"
    assert "heard:hello" in out.getvalue()
    channel.stop()
    assert channel.running is False


def test_agent_bound_to_cli_channel() -> None:
    out = StringIO()
    channel = CLIChannel(stdout=out)
    agent = Agent(
        name="cli",
        provider=FakeProvider(reply="pong"),
        template_id="general",
        channel=channel,
    )
    agent.bind_channel()
    channel.start()
    channel.deliver("ping")
    assert channel.serve_once() == "pong"
    assert "pong" in out.getvalue()


def test_channel_capture_swallows_send() -> None:
    out = StringIO()
    channel = CLIChannel(stdout=out)
    channel.bind(lambda inbound: f"cap:{inbound.text}")
    with channel.capture() as chunks:
        reply = channel.handle_text("z")
    assert reply == "cap:z"
    assert chunks == ["cap:z"]
    assert out.getvalue() == ""
