"""Provider protocol — one implementation ships in v1 (OpenAI-compatible HTTP)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from universal.core.types import CompletionResponse, Message, ToolSpec


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
