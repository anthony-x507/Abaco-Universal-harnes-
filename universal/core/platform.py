"""Composition root: constructs registry and lifecycle once, then injects them."""

from __future__ import annotations

from pathlib import Path

from universal.channels.catalog import ChannelCatalog
from universal.config import Settings
from universal.core.factory import AgentFactory
from universal.core.lifecycle import AgentLifecycle
from universal.core.registry import AgentRegistry
from universal.core.usage import StatsCollector
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
        persist_path: str | Path | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.stats = StatsCollector()
        self.registry = AgentRegistry(persist_path=persist_path)
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
        self._restore_identities()

    def replace_settings(self, settings: Settings) -> None:
        """Update in-memory settings on this root. Does not write a file."""
        self.settings = settings
        self.factory.settings = settings
        self.factory.generator.replace_settings(settings)

    def provider(self) -> Provider:
        """The single provider instance shared by agents this root creates."""
        return self.factory.generator.provider()

    def _restore_identities(self) -> None:
        """Rebuild agents from the sidecar. Never auto-start. Chat history is a separate file."""
        records = self.registry.load_records()
        if not records:
            return
        with self.registry.suspend_persist():
            for record in records:
                agent_id = str(record.get("id") or "")
                template_id = str(record.get("template_id") or "")
                if not agent_id or not template_id:
                    continue
                try:
                    raw_plugins = record.get("plugins")
                    plugins = tuple(str(item) for item in raw_plugins) if isinstance(raw_plugins, list) else None
                    memory = record.get("memory")
                    stored_prompt = record.get("system_prompt")
                    stored_model = record.get("llm_model")
                    agent = self.factory.create(
                        template_id,
                        str(record.get("name") or "") or None,
                        channel=str(record.get("channel") or "cli"),
                        outbound_url=str(record.get("outbound_url") or "") or None,
                        plugins=plugins,
                        memory=bool(memory) if memory is not None else None,
                        agent_id=agent_id,
                        emoji=str(record.get("emoji") or "") or None,
                        system_prompt=str(stored_prompt) if isinstance(stored_prompt, str) else None,
                        llm_model=str(stored_model) if isinstance(stored_model, str) else None,
                    )
                    if str(record.get("state") or "") == "error":
                        self.lifecycle.mark_error(agent.id, "restored in error state")
                    else:
                        self.lifecycle.stop(agent.id)
                except Exception:
                    continue
        self.registry.save()

    @classmethod
    def from_env(cls, *, provider: Provider | None = None) -> Universal:
        return cls(Settings.from_env(), provider=provider)
