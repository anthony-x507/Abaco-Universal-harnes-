"""Shared value types for the Universal platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


class AgentState(str, Enum):
    """Lifecycle states for a registered agent."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(slots=True)
class ToolCall:
    """A function/tool invocation requested by the model."""

    id: str
    name: str
    arguments: str


@dataclass(slots=True)
class ToolSpec:
    """JSON-schema tool description sent to an OpenAI-compatible provider."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(slots=True)
class Message:
    """One turn in a conversation (OpenAI-compatible shape)."""

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

    def to_openai(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            payload["name"] = self.name
        if self.tool_call_id:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ]
        return payload


@dataclass(slots=True)
class CompletionResponse:
    """Normalized provider result."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    finish_reason: str = "stop"
    raw: dict[str, Any] | None = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@dataclass(slots=True)
class AgentInfo:
    """Public snapshot of a registered agent. Safe to print or serialize."""

    id: str
    name: str
    template_id: str
    state: AgentState
    channel: str
    plugins: list[str]
    created_at: datetime
    model: str = ""
    emoji: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template_id": self.template_id,
            "state": self.state.value,
            "channel": self.channel,
            "plugins": list(self.plugins),
            "created_at": self.created_at.isoformat(),
            "model": self.model,
            "emoji": self.emoji,
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
