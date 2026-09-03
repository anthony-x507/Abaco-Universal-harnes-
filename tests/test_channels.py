"""Channel catalog: create chooses a channel; unknown ids fail."""

from __future__ import annotations

from universal.channels.catalog import default_channel_catalog
from universal.core.platform import Universal
from universal.exceptions import ChannelNotFound


def test_default_catalog_registers_cli_and_webhook() -> None:
    catalog = default_channel_catalog()
    assert catalog.ids() == ["cli", "webhook"]
    channel = catalog.create("cli")
    assert channel.name == "cli"
    hook = catalog.create("webhook")
    assert hook.name == "webhook"


def test_unknown_channel_raises() -> None:
    catalog = default_channel_catalog()
    try:
        catalog.create("telegram")
    except ChannelNotFound as exc:
        assert "telegram" in str(exc)
        return
    raise AssertionError("expected ChannelNotFound")


def test_create_uses_cli_channel(platform: Universal) -> None:
    agent = platform.factory.create("general", name="wired", channel="cli")
    assert agent.channel is not None
    assert agent.channel.name == "cli"
    assert agent.info().channel == "cli"


def test_create_rejects_unknown_channel(platform: Universal) -> None:
    try:
        platform.factory.create("general", channel="telegram")
    except ChannelNotFound:
        assert platform.factory.list() == []
        return
    raise AssertionError("expected ChannelNotFound")
