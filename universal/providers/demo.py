"""Development echo provider. Not a catalog entry. Only used with `universal serve --demo`."""

from __future__ import annotations

from collections.abc import Iterator

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
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
        already_used_tool = any(message.role == "tool" for message in messages)
        wants_clock = any(word in last.lower() for word in ("time", "utc", "clock"))
        if (
            tools
            and not already_used_tool
            and wants_clock
            and any(spec.name == "utc_now" for spec in tools)
        ):
            return CompletionResponse(
                text="",
                tool_calls=[ToolCall(id="demo_utc", name="utc_now", arguments="{}")],
                model=model or self.model,
                finish_reason="tool_calls",
            )
        return CompletionResponse(
            text=f"(demo) {last}",
            model=model or self.model,
            finish_reason="stop",
        )

    def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        text = self.complete(messages, tools=tools, model=model).text
        step = 4
        for index in range(0, len(text), step):
            yield text[index : index + step]
