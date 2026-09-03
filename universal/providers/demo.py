"""Development echo provider. Not a catalog entry. Only used with `universal serve --demo`."""

from __future__ import annotations

from universal.core.types import CompletionResponse, Message, ToolSpec
from universal.providers.base import Provider


class EchoProvider(Provider):
    """Repeats the last user turn. Lets the SPA exercise factory wiring without a live key."""

    @property
    def model(self) -> str:
        return "demo-echo"

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return CompletionResponse(
            text=f"(demo) {last}",
            model=self.model,
            finish_reason="stop",
        )
