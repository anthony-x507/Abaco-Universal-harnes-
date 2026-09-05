"""Provider protocol and HTTP dialect adapters.

``Provider`` is the agent-facing contract (not a plugin).
``ProviderAdapter`` only normalizes auth, URL, payload, and parse.
One live HTTP client still owns the socket.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from universal.core.types import CompletionResponse, Message, ToolSpec
from universal.exceptions import ProviderError


class ProviderAdapter(ABC):
    """HTTP dialect for one family of LLM hosts."""

    name: str = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()

    def allows_empty_key(self) -> bool:
        return False

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """Auth and content-type headers."""

    @abstractmethod
    def request_url(self, *, stream: bool = False) -> str:
        """Absolute POST URL for this dialect."""

    @abstractmethod
    def build_payload(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Host-specific JSON body."""

    @abstractmethod
    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        """Normalize a full response to ``CompletionResponse``."""

    def parse_stream_line(self, line: str) -> str | None:
        """Return a text delta, or None if the line is not text."""
        return None


class Provider(ABC):
    """Something that can complete a chat prompt."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Default model id sent with completions."""

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        """Return the next assistant message (and optional tool calls)."""

    def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        """Yield assistant text deltas. Default: one chunk from ``complete``.

        Tool-call rounds must use ``complete``. This helper raises if the
        fallback completion asks for tools.
        """
        response = self.complete(messages, tools=tools, model=model)
        if response.wants_tools:
            raise ProviderError("stream() cannot emit tool calls; use complete()")
        if response.text:
            yield response.text
