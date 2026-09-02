"""Plugin id → factory. Templates name plugins; the generator does not switch on strings."""

from __future__ import annotations

from collections.abc import Callable

from universal.core.plugin import Plugin
from universal.exceptions import PluginError
from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.plugins.transcript import TranscriptPlugin

PluginFactory = Callable[..., Plugin]


class PluginCatalog:
    """In-memory plugin factories. Injected into the generator (same pattern as templates)."""

    def __init__(self) -> None:
        self._factories: dict[str, PluginFactory] = {}

    def ids(self) -> list[str]:
        return list(self._factories.keys())

    def register(self, plugin_id: str, factory: PluginFactory) -> None:
        if not plugin_id:
            raise PluginError("Plugin id must be a non-empty string")
        self._factories[plugin_id] = factory

    def create(self, plugin_id: str, **kwargs: object) -> Plugin:
        try:
            factory = self._factories[plugin_id]
        except KeyError as exc:
            known = ", ".join(self.ids()) or "(none)"
            raise PluginError(f"Unknown plugin {plugin_id!r}. Known: {known}") from exc
        return factory(**kwargs)


def _tools_plugin(**_kwargs: object) -> ToolBeltPlugin:
    belt = ToolBeltPlugin()
    belt.add(utc_now_tool())
    return belt


def _system_prompt_plugin(*, system_prompt: str = "", **_kwargs: object) -> SystemPromptPlugin:
    return SystemPromptPlugin(str(system_prompt))


def _transcript_plugin(**_kwargs: object) -> TranscriptPlugin:
    return TranscriptPlugin()


def default_plugin_catalog() -> PluginCatalog:
    catalog = PluginCatalog()
    catalog.register("system_prompt", _system_prompt_plugin)
    catalog.register("transcript", _transcript_plugin)
    catalog.register("tools", _tools_plugin)
    return catalog


catalog = default_plugin_catalog()
