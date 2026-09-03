"""Webhook channel: factory inbound HTTP plus optional outbound POST."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from universal.channels.base import (
    BaseCommunication,
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)

Poster = Callable[[str, dict[str, Any]], None]


class WebhookChannel(BaseCommunication):
    """Channel chosen at ``create(..., channel="webhook")``.

    Inbound is ``handle_text`` (what ``Agent.accept`` calls after start).
    The factory route ``POST /v1/agents/{id}/webhook`` is that inbound, not a
    bypass. Outbound ``send`` POSTs JSON to ``outbound_url`` when set.
    """

    def __init__(
        self,
        *,
        outbound_url: str = "",
        poster: Poster | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.outbound_url = outbound_url.strip()
        self.agent_id = ""
        self._poster = poster
        self._timeout = timeout
        self._handler: MessageHandler | None = None
        self._running = False

    @property
    def name(self) -> str:
        return "webhook"

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def bind(self, handler: MessageHandler) -> None:
        self._handler = handler

    def send(self, message: OutboundMessage) -> None:
        if not self.outbound_url:
            return
        payload = {"agent_id": self.agent_id, "text": message.text}
        if self._poster is not None:
            self._poster(self.outbound_url, payload)
            return
        try:
            httpx.post(self.outbound_url, json=payload, timeout=self._timeout)
        except httpx.HTTPError:
            return

    def handle(self, inbound: InboundMessage) -> str:
        if self._handler is None:
            raise RuntimeError("WebhookChannel.bind() was not called")
        result = self._handler(inbound)
        if result is None:
            return ""
        if isinstance(result, OutboundMessage):
            self.send(result)
            return result.text
        self.send(OutboundMessage(text=result))
        return result

    def handle_text(self, text: str) -> str:
        return self.handle(InboundMessage(text=text, sender_id="webhook"))
