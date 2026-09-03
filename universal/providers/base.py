"""Provider protocol — one implementation ships in v1 (OpenAI-compatible HTTP)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from universal.core.types import CompletionResponse, Message, ToolSpec
from universal.exceptions import ProviderError


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
