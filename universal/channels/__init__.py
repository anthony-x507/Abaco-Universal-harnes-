"""Communication channels. v1 ships a CLI channel; Telegram/Slack plug in later."""

from universal.channels.base import BaseCommunication, InboundMessage, OutboundMessage
from universal.channels.cli import CLIChannel

__all__ = ["BaseCommunication", "CLIChannel", "InboundMessage", "OutboundMessage"]
