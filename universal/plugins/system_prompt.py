"""Ensures the template system prompt is the first message of every completion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from universal.core.plugin import Plugin
from universal.core.types import Message

if TYPE_CHECKING:
    from universal.core.agent import Agent


class SystemPromptPlugin(Plugin):
    """Prepends (or replaces) the leading system message."""

    def __init__(self, prompt: str, *, name: str = "system_prompt") -> None:
        self._name = name
        self.prompt = prompt

    @property
    def name(self) -> str:
        return self._name

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        if not self.prompt:
            return messages
        body = [m for m in messages if m.role != "system"]
        return [Message(role="system", content=self.prompt), *body]
