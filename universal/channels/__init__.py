"""Communication channels. v1 ships a CLI channel; webhook is next, chosen at create."""

from universal.channels.base import BaseCommunication, InboundMessage, OutboundMessage
from universal.channels.catalog import ChannelCatalog, default_channel_catalog, list_channels
from universal.channels.cli import CLIChannel

__all__ = [
    "BaseCommunication",
    "ChannelCatalog",
    "CLIChannel",
    "InboundMessage",
    "OutboundMessage",
    "default_channel_catalog",
    "list_channels",
]
