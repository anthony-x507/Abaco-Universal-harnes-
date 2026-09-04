"""Wiring contracts: shared provider, channel inbound path, plugin catalog."""

from __future__ import annotations

from io import StringIO

from universal.channels.cli import CLIChannel
from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.exceptions import PluginError
from universal.plugins.catalog import default_plugin_catalog
from tests.conftest import FakeProvider


def test_two_agents_share_the_same_provider(platform: Universal) -> None:
    first = platform.factory.create("general", name="one")
    second = platform.factory.create("coder", name="two")
    assert first.provider is second.provider
    assert first.provider is platform.provider()


def test_accept_goes_through_the_bound_channel() -> None:
    out = StringIO()
    channel = CLIChannel(stdout=out)
    provider = FakeProvider(reply="via-channel")
    agent = Agent(name="w", provider=provider, template_id="general", channel=channel)
    agent.bind_channel()
    channel.start()
    answer = agent.accept("ping")
    assert answer == "via-channel"
    assert "via-channel" in out.getvalue()


def test_accept_without_channel_uses_complete() -> None:
    agent = Agent(name="w", provider=FakeProvider(reply="direct"), template_id="general")
    assert agent.accept("x") == "direct"


def test_plugin_catalog_creates_known_ids() -> None:
    catalog = default_plugin_catalog()
    assert set(catalog.ids()) == {
        "system_prompt",
        "transcript",
        "tools",
        "terminal",
        "tts",
        "stt",
        "vision",
        "web_search",
        "scraper",
        "rule_enforcer",
    }
    prompt = catalog.create("system_prompt", system_prompt="Stay brief.")
    assert prompt.name == "system_prompt"


def test_plugin_catalog_unknown_id() -> None:
    catalog = default_plugin_catalog()
    try:
        catalog.create("not-a-plugin")
    except PluginError:
        return
    raise AssertionError("expected PluginError")


def test_serve_once_stops_on_eof() -> None:
    channel = CLIChannel(reader=lambda: (_ for _ in ()).throw(EOFError()))
    channel.start()
    assert channel.serve_once() == ""
    assert channel.running is False
