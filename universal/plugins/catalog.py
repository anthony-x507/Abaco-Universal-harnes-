"""Plugin id → factory. Templates name plugins; the generator does not switch on strings."""

from __future__ import annotations

from collections.abc import Callable

from universal.core.plugin import Plugin
from universal.exceptions import PluginError
from universal.plugins.improvement import ImprovementPlugin
from universal.plugins.navigator import NavigatorPlugin
from universal.plugins.package_manager import PackageManagerPlugin
from universal.plugins.proof import ProofPlugin
from universal.plugins.rules import RuleEnforcerPlugin
from universal.plugins.strategist import StrategistPlugin
from universal.plugins.team import TeamPlugin
from universal.plugins.scraper import ScraperPlugin
from universal.plugins.stt import STTPlugin
from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.terminal import TerminalPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.plugins.transcript import TranscriptPlugin
from universal.plugins.tts import TTSPlugin
from universal.plugins.vision import VisionPlugin
from universal.plugins.web_search import WebSearchPlugin

PluginFactory = Callable[..., Plugin]

NATIVE_PLUGIN_NAMES: tuple[str, ...] = (
    "terminal",
    "tts",
    "stt",
    "vision",
    "web_search",
    "scraper",
    "rule_enforcer",
    "navigator",
    "team",
    "strategist",
    "proof",
    "improvement",
    "package_manager",
)


def merge_native_plugin_ids(requested: tuple[str, ...]) -> tuple[str, ...]:
    """Native plugins are always installed. Extra ids follow, without duplicates."""
    seen: list[str] = []
    for plugin_id in (*NATIVE_PLUGIN_NAMES, *requested):
        if plugin_id and plugin_id not in seen:
            seen.append(plugin_id)
    return tuple(seen)


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


def _terminal_plugin(**_kwargs: object) -> TerminalPlugin:
    return TerminalPlugin()


def _tts_plugin(**_kwargs: object) -> TTSPlugin:
    return TTSPlugin()


def _stt_plugin(**_kwargs: object) -> STTPlugin:
    return STTPlugin()


def _vision_plugin(**_kwargs: object) -> VisionPlugin:
    return VisionPlugin()


def _web_search_plugin(**_kwargs: object) -> WebSearchPlugin:
    return WebSearchPlugin()


def _scraper_plugin(**_kwargs: object) -> ScraperPlugin:
    return ScraperPlugin()


def _rules_plugin(**_kwargs: object) -> RuleEnforcerPlugin:
    return RuleEnforcerPlugin()


def _navigator_plugin(**_kwargs: object) -> NavigatorPlugin:
    return NavigatorPlugin()


def _team_plugin(**_kwargs: object) -> TeamPlugin:
    return TeamPlugin()


def _strategist_plugin(**_kwargs: object) -> StrategistPlugin:
    return StrategistPlugin()


def _proof_plugin(**_kwargs: object) -> ProofPlugin:
    return ProofPlugin()


def _improvement_plugin(**_kwargs: object) -> ImprovementPlugin:
    return ImprovementPlugin()


def _package_manager_plugin(**_kwargs: object) -> PackageManagerPlugin:
    return PackageManagerPlugin()


def default_plugin_catalog() -> PluginCatalog:
    catalog = PluginCatalog()
    catalog.register("system_prompt", _system_prompt_plugin)
    catalog.register("transcript", _transcript_plugin)
    catalog.register("tools", _tools_plugin)
    catalog.register("terminal", _terminal_plugin)
    catalog.register("tts", _tts_plugin)
    catalog.register("stt", _stt_plugin)
    catalog.register("vision", _vision_plugin)
    catalog.register("web_search", _web_search_plugin)
    catalog.register("scraper", _scraper_plugin)
    catalog.register("rule_enforcer", _rules_plugin)
    catalog.register("navigator", _navigator_plugin)
    catalog.register("team", _team_plugin)
    catalog.register("strategist", _strategist_plugin)
    catalog.register("proof", _proof_plugin)
    catalog.register("improvement", _improvement_plugin)
    catalog.register("package_manager", _package_manager_plugin)
    return catalog


catalog = default_plugin_catalog()
