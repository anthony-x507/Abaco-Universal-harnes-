"""Plugin protocol and a host that can hot-swap plugins on a live agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.exceptions import PluginError

if TYPE_CHECKING:
    from universal.core.agent import Agent


class Plugin(ABC):
    """A plugin is assembled onto an agent alongside a model and a channel.

    Hooks run around ``Agent.complete``. Tools advertised here are offered to
    the provider and invoked in the agent loop. Install and uninstall are
    supported while the agent is running (hot-swap).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable unique name used as the install key."""

    def on_attach(self, agent: Agent) -> None:
        """Called after the plugin is installed on ``agent``."""

    def on_detach(self, agent: Agent) -> None:
        """Called just before the plugin is removed from ``agent``."""

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        """Mutate or replace the outgoing message list. Return the list to send."""
        return messages

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        """Inspect or replace the final model response."""
        return response

    def tools(self) -> list[ToolSpec]:
        """Tool schemas this plugin contributes to the provider call."""
        return []

    def invoke_tool(self, call: ToolCall) -> str | None:
        """Handle a tool call. Return a string result, or None if not yours."""
        return None


class PluginHost:
    """Ordered plugin collection with install/uninstall (hot-swap) support."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._order: list[str] = []

    def __contains__(self, name: str) -> bool:
        return name in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def names(self) -> list[str]:
        return list(self._order)

    def all(self) -> list[Plugin]:
        return [self._plugins[name] for name in self._order]

    def install(self, plugin: Plugin, agent: Agent, *, replace: bool = True) -> None:
        """Attach ``plugin``. If the name exists and ``replace`` is true, swap it."""
        name = plugin.name
        if not name:
            raise PluginError("Plugin.name must be a non-empty string")
        if name in self._plugins:
            if not replace:
                raise PluginError(f"Plugin {name!r} is already installed")
            self.uninstall(name, agent)
        self._plugins[name] = plugin
        self._order.append(name)
        plugin.on_attach(agent)

    def uninstall(self, name: str, agent: Agent) -> Plugin:
        if name not in self._plugins:
            raise PluginError(f"Plugin {name!r} is not installed")
        plugin = self._plugins.pop(name)
        self._order.remove(name)
        plugin.on_detach(agent)
        return plugin

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        current = messages
        for plugin in self.all():
            current = plugin.before_complete(agent, current)
        return current

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        current = response
        for plugin in self.all():
            current = plugin.after_complete(agent, messages, current)
        return current

    def collect_tools(self) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        seen: set[str] = set()
        for plugin in self.all():
            for spec in plugin.tools():
                if spec.name in seen:
                    raise PluginError(f"Duplicate tool name {spec.name!r}")
                seen.add(spec.name)
                specs.append(spec)
        return specs

    def invoke_tool(self, call: ToolCall) -> str:
        for plugin in self.all():
            result = plugin.invoke_tool(call)
            if result is not None:
                return result
        return f"error: no plugin handles tool {call.name!r}"

    def snapshot(self) -> list[dict[str, Any]]:
        return [{"name": plugin.name, "class": type(plugin).__name__} for plugin in self.all()]
