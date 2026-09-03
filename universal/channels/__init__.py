"""Communication channels. v1 ships CLI and webhook, chosen at create."""

from universal.channels.base import BaseCommunication, InboundMessage, OutboundMessage
from universal.channels.catalog import ChannelCatalog, default_channel_catalog, list_channels
from universal.channels.cli import CLIChannel
from universal.channels.webhook import WebhookChannel

__all__ = [
    "BaseCommunication",
    "ChannelCatalog",
    "CLIChannel",
    "InboundMessage",
    "OutboundMessage",
    "WebhookChannel",
    "default_channel_catalog",
    "list_channels",
]
