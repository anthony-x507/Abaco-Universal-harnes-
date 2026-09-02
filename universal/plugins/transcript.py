"""In-memory transcript of complete() hooks — useful for tests and debugging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from universal.core.plugin import Plugin
from universal.core.types import CompletionResponse, Message

if TYPE_CHECKING:
    from universal.core.agent import Agent

Kind = Literal["before", "after"]


@dataclass
class TranscriptEvent:
    kind: Kind
    payload: Any = None


@dataclass
class TranscriptPlugin(Plugin):
    """Records before/after complete hooks. Hot-swappable."""

    events: list[TranscriptEvent] = field(default_factory=list)
    _name: str = "transcript"

    @property
    def name(self) -> str:
        return self._name

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        self.events.append(TranscriptEvent("before", list(messages)))
        return messages

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        self.events.append(TranscriptEvent("after", response))
        return response

    def clear(self) -> None:
        self.events.clear()
