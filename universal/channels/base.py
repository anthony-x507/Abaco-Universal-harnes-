"""BaseCommunication — the channel contract Telegram/Slack will implement later."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InboundMessage:
    """A message arriving from a user or another system."""

    text: str
    sender_id: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OutboundMessage:
    """A message the agent wants to send back out."""

    text: str
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[InboundMessage], str | OutboundMessage | None]


class BaseCommunication(ABC):
    """Transport that an agent uses to talk to the outside world.

    v1 ships :class:`universal.channels.cli.CLIChannel`. Future plugins
    (Telegram, Slack, HTTP webhooks) implement this same interface and are
    assembled onto an agent by the factory.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable channel id (``cli``, ``telegram``, ``slack``, …)."""

    @abstractmethod
    def start(self) -> None:
        """Open the transport. Idempotent."""

    @abstractmethod
    def stop(self) -> None:
        """Close the transport. Idempotent."""

    @abstractmethod
    def send(self, message: OutboundMessage) -> None:
        """Deliver an outbound message."""

    @abstractmethod
    def bind(self, handler: MessageHandler) -> None:
        """Register the callable that turns inbound text into a reply."""

    def receive(self) -> InboundMessage | None:
        """Optional pull API. Return None on EOF / no message."""
        return None

    def handle_text(self, text: str) -> str:
        """Push one inbound string through the bound handler.

        CLI implements this. Other channels override it the same way so
        ``Agent.accept`` stays channel-shaped after ``factory.start``.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement handle_text yet"
        )
