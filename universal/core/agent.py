"""Minimal agent that completes a prompt via the provider, with a tool loop."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from universal.channels.base import InboundMessage
from universal.core.plugin import Plugin, PluginHost
from universal.core.types import AgentInfo, AgentState, CompletionResponse, Message, utcnow
from universal.exceptions import ProviderError

if TYPE_CHECKING:
    from universal.channels.base import BaseCommunication
    from universal.providers.base import Provider


def new_agent_id() -> str:
    return uuid.uuid4().hex[:12]


class Agent:
    """An assembled agent: model + channel + plugins, identified in the registry.

    ``complete(prompt)`` is the working path for v1: it runs plugin hooks, calls
    the provider, and loops on tool calls until the model returns text.
    """

    def __init__(
        self,
        *,
        name: str,
        provider: Provider,
        template_id: str,
        system_prompt: str = "",
        channel: BaseCommunication | None = None,
        agent_id: str | None = None,
        max_tool_iters: int = 8,
    ) -> None:
        self.id = agent_id or new_agent_id()
        self.name = name
        self.template_id = template_id
        self.system_prompt = system_prompt
        self.provider = provider
        self.channel = channel
        self.plugins = PluginHost()
        self.max_tool_iters = max_tool_iters
        self.created_at = utcnow()
        self._history: list[Message] = []

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    def attach_plugin(self, plugin: Plugin, *, replace: bool = True) -> None:
        """Hot-swap: install (or replace) a plugin on this agent."""
        self.plugins.install(plugin, self, replace=replace)

    def detach_plugin(self, name: str) -> Plugin:
        """Hot-swap: remove a plugin from this agent."""
        return self.plugins.uninstall(name, self)

    def reset_history(self) -> None:
        self._history.clear()

    def complete(self, prompt: str, *, remember: bool = True) -> str:
        """Send ``prompt`` through plugins and the provider; return assistant text."""
        user = Message(role="user", content=prompt)
        turn: list[Message] = []
        if self.system_prompt:
            turn.append(Message(role="system", content=self.system_prompt))
        turn.extend(self._history)
        turn.append(user)
        turn = self.plugins.before_complete(self, turn)

        tools = self.plugins.collect_tools()
        response: CompletionResponse | None = None
        working = list(turn)

        for _ in range(self.max_tool_iters):
            response = self.provider.complete(working, tools=tools or None)
            if response.wants_tools:
                working.append(
                    Message(
                        role="assistant",
                        content=response.text or "",
                        tool_calls=response.tool_calls,
                    )
                )
                for call in response.tool_calls:
                    result = self.plugins.invoke_tool(call)
                    working.append(
                        Message(
                            role="tool",
                            content=result,
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
                continue
            break
        else:
            raise ProviderError(
                f"Agent {self.id!r} exceeded max_tool_iters={self.max_tool_iters}"
            )

        assert response is not None
        response = self.plugins.after_complete(self, working, response)
        if remember:
            self._history.append(user)
            self._history.append(Message(role="assistant", content=response.text))
        return response.text

    def info(self, state: AgentState = AgentState.CREATED) -> AgentInfo:
        channel_name = self.channel.name if self.channel is not None else ""
        model = getattr(self.provider, "model", "") or ""
        return AgentInfo(
            id=self.id,
            name=self.name,
            template_id=self.template_id,
            state=state,
            channel=channel_name,
            plugins=self.plugins.names(),
            created_at=self.created_at,
            model=str(model),
        )

    def bind_channel(self) -> None:
        """Point the channel handler at this agent's ``complete``."""
        if self.channel is None:
            return

        def _handle(inbound: InboundMessage) -> str:
            return self.complete(inbound.text)

        self.channel.bind(_handle)
