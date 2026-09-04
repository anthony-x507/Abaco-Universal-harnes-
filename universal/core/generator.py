"""Creates agents from templates. Does not own registry or lifecycle."""

from __future__ import annotations

from universal.channels.catalog import ChannelCatalog
from universal.channels.catalog import catalog as default_channels
from universal.config import Settings
from universal.core.agent import Agent
from universal.core.lifecycle import AgentLifecycle
from universal.core.registry import AgentRegistry
from universal.plugins.catalog import PluginCatalog, merge_native_plugin_ids
from universal.plugins.catalog import catalog as default_plugins
from universal.providers.base import Provider
from universal.providers.openai_compat import OpenAICompatProvider
from universal.templates.catalog import TemplateCatalog, catalog as default_catalog


class AgentGenerator:
    """Assembles an agent from a template + provider + channel + plugins.

    Receives the shared ``AgentRegistry`` and ``AgentLifecycle``. Never
    constructs its own copies.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        lifecycle: AgentLifecycle,
        settings: Settings,
        *,
        provider: Provider | None = None,
        templates: TemplateCatalog | None = None,
        plugins: PluginCatalog | None = None,
        channels: ChannelCatalog | None = None,
    ) -> None:
        if registry is None or lifecycle is None:
            raise TypeError("AgentGenerator requires injected registry and lifecycle")
        if lifecycle.registry is not registry:
            raise ValueError("lifecycle.registry must be the same object as registry")
        self.registry = registry
        self.lifecycle = lifecycle
        self.settings = settings
        self._provider = provider
        self._provider_injected = provider is not None
        self.templates = templates or default_catalog
        self.plugins = plugins or default_plugins
        self.channels = channels or default_channels

    def provider(self) -> Provider:
        """One shared provider per generator. Do not construct a client per agent."""
        if self._provider is None:
            from universal.providers.catalog import is_local_base_url

            api_key = self.settings.llm_api_key
            if not api_key and is_local_base_url(self.settings.llm_base_url):
                api_key = "local"
            self._provider = OpenAICompatProvider(
                base_url=self.settings.llm_base_url,
                api_key=api_key,
                model=self.settings.llm_model,
                timeout=self.settings.llm_timeout,
                organization=self.settings.llm_organization,
            )
        return self._provider

    def replace_settings(self, settings: Settings) -> None:
        """Point this generator at new settings. Rebuilds the cached live client."""
        self.settings = settings
        if not self._provider_injected:
            self._provider = None

    def generate(
        self,
        template_id: str,
        name: str | None = None,
        *,
        provider: Provider | None = None,
        channel: str = "cli",
        outbound_url: str | None = None,
        plugins: tuple[str, ...] | list[str] | None = None,
        memory: bool | None = None,
        agent_id: str | None = None,
    ) -> Agent:
        template = self.templates.get(template_id)
        agent_name = name or f"{template.id}-{template.name.lower()}"
        extra: dict[str, object] = {}
        if outbound_url:
            extra["outbound_url"] = outbound_url
        transport = self.channels.create(channel, **extra)
        requested = template.default_plugins if plugins is None else tuple(plugins)
        plugin_ids = merge_native_plugin_ids(requested)
        memory_flag = template.memory if memory is None else bool(memory)
        agent = Agent(
            name=agent_name,
            provider=provider or self.provider(),
            template_id=template.id,
            system_prompt=template.system_prompt,
            channel=transport,
            memory=memory_flag,
            agent_id=agent_id,
        )
        if hasattr(transport, "agent_id"):
            transport.agent_id = agent.id
        self._install_default_plugins(agent, plugin_ids, template.system_prompt)
        agent.bind_channel()
        self.registry.add(agent)
        self.lifecycle.mark_created(agent.id)
        return agent

    def _install_default_plugins(
        self, agent: Agent, plugin_ids: tuple[str, ...], system_prompt: str
    ) -> None:
        for plugin_id in plugin_ids:
            agent.attach_plugin(self.plugins.create(plugin_id, system_prompt=system_prompt))
