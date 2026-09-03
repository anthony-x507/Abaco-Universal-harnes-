"""Channel id → factory. Templates and create() name channels; the generator does not switch on strings."""

from __future__ import annotations

from collections.abc import Callable

from universal.channels.base import BaseCommunication
from universal.channels.cli import CLIChannel
from universal.channels.webhook import WebhookChannel
from universal.exceptions import ChannelNotFound

ChannelFactory = Callable[..., BaseCommunication]


class ChannelCatalog:
    """In-memory channel factories. Injected into the generator (same pattern as plugins)."""

    def __init__(self) -> None:
        self._factories: dict[str, ChannelFactory] = {}

    def ids(self) -> list[str]:
        return list(self._factories.keys())

    def register(self, channel_id: str, factory: ChannelFactory) -> None:
        if not channel_id:
            raise ChannelNotFound("Channel id must be a non-empty string")
        self._factories[channel_id] = factory

    def create(self, channel_id: str, **kwargs: object) -> BaseCommunication:
        try:
            factory = self._factories[channel_id]
        except KeyError as exc:
            known = ", ".join(self.ids()) or "(none)"
            raise ChannelNotFound(f"Unknown channel {channel_id!r}. Known: {known}") from exc
        return factory(**kwargs)


def _cli_channel(**_kwargs: object) -> CLIChannel:
    return CLIChannel()


def _webhook_channel(**kwargs: object) -> WebhookChannel:
    url = str(kwargs.get("outbound_url") or "")
    return WebhookChannel(outbound_url=url)


def default_channel_catalog() -> ChannelCatalog:
    catalog = ChannelCatalog()
    catalog.register("cli", _cli_channel)
    catalog.register("webhook", _webhook_channel)
    return catalog


catalog = default_channel_catalog()


def list_channels() -> list[str]:
    return catalog.ids()
