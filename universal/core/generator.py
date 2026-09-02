"""Creates agents from templates. Does not own registry or lifecycle."""

from __future__ import annotations

from universal.channels.cli import CLIChannel
from universal.config import Settings
from universal.core.agent import Agent
from universal.core.lifecycle import AgentLifecycle
from universal.core.registry import AgentRegistry
from universal.plugins.catalog import PluginCatalog
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
    ) -> None:
        if registry is None or lifecycle is None:
            raise TypeError("AgentGenerator requires injected registry and lifecycle")
        if lifecycle.registry is not registry:
            raise ValueError("lifecycle.registry must be the same object as registry")
        self.registry = registry
        self.lifecycle = lifecycle
        self.settings = settings
        self._provider = provider
        self.templates = templates or default_catalog
        self.plugins = plugins or default_plugins

    def provider(self) -> Provider:
        """One shared provider per generator. Do not construct a client per agent."""
        if self._provider is None:
            self._provider = OpenAICompatProvider(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                model=self.settings.llm_model,
                timeout=self.settings.llm_timeout,
                organization=self.settings.llm_organization,
            )
        return self._provider

    def generate(
        self,
        template_id: str,
        name: str | None = None,
        *,
        provider: Provider | None = None,
    ) -> Agent:
        template = self.templates.get(template_id)
        agent_name = name or f"{template.id}-{template.name.lower()}"
        channel = CLIChannel()
        agent = Agent(
            name=agent_name,
            provider=provider or self.provider(),
            template_id=template.id,
            system_prompt=template.system_prompt,
            channel=channel,
        )
        self._install_default_plugins(agent, template.default_plugins, template.system_prompt)
        agent.bind_channel()
        self.registry.add(agent)
        self.lifecycle.mark_created(agent.id)
        return agent

    def _install_default_plugins(
        self, agent: Agent, plugin_ids: tuple[str, ...], system_prompt: str
    ) -> None:
        for plugin_id in plugin_ids:
            agent.attach_plugin(self.plugins.create(plugin_id, system_prompt=system_prompt))
