"""Composition root: constructs registry and lifecycle once, then injects them."""

from __future__ import annotations

from universal.channels.catalog import ChannelCatalog
from universal.config import Settings
from universal.core.factory import AgentFactory
from universal.core.lifecycle import AgentLifecycle
from universal.core.registry import AgentRegistry
from universal.plugins.catalog import PluginCatalog
from universal.providers.base import Provider
from universal.templates.catalog import TemplateCatalog


class Universal:
    """Process-wide Universal platform instance.

    This is the only type that constructs ``AgentRegistry`` and
    ``AgentLifecycle``. Both are injected into the factory, which forwards
    the same objects to ``AgentGenerator`` and ``AgentManager``.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        provider: Provider | None = None,
        templates: TemplateCatalog | None = None,
        plugins: PluginCatalog | None = None,
        channels: ChannelCatalog | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.registry = AgentRegistry()
        self.lifecycle = AgentLifecycle(self.registry)
        self.factory = AgentFactory(
            self.registry,
            self.lifecycle,
            self.settings,
            provider=provider,
            templates=templates,
            plugins=plugins,
            channels=channels,
        )

    def replace_settings(self, settings: Settings) -> None:
        """Update in-memory settings on this root. Does not write a file."""
        self.settings = settings
        self.factory.settings = settings
        self.factory.generator.replace_settings(settings)

    def provider(self) -> Provider:
        """The single provider instance shared by agents this root creates."""
        return self.factory.generator.provider()

    @classmethod
    def from_env(cls, *, provider: Provider | None = None) -> Universal:
        return cls(Settings.from_env(), provider=provider)
