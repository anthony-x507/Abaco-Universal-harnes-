"""Public factory facade: create / start / stop / list / delete / deploy.

Manager and Generator share the registry and lifecycle injected here.
The factory never constructs a second pair.
"""

from __future__ import annotations

from pathlib import Path

from universal.config import Settings
from universal.core.agent import Agent
from universal.core.generator import AgentGenerator
from universal.core.lifecycle import AgentLifecycle
from universal.core.manager import AgentManager
from universal.core.registry import AgentRegistry
from universal.core.types import AgentInfo
from universal.deploy.github import GitHubDeployTarget
from universal.exceptions import DeployError
from universal.channels.catalog import ChannelCatalog
from universal.plugins.catalog import PluginCatalog
from universal.providers.base import Provider
from universal.templates.catalog import TemplateCatalog


class AgentFactory:
    """Single entry for the agent factory operations listed in the product brief."""

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
            raise TypeError(
                "AgentFactory requires an injected AgentRegistry and AgentLifecycle. "
                "Construct them once on Universal and pass them in."
            )
        if lifecycle.registry is not registry:
            raise ValueError("lifecycle.registry must be the same object as registry")
        self.registry = registry
        self.lifecycle = lifecycle
        self.settings = settings
        self.generator = AgentGenerator(
            registry,
            lifecycle,
            settings,
            provider=provider,
            templates=templates,
            plugins=plugins,
            channels=channels,
        )
        self.manager = AgentManager(registry, lifecycle)

    def create(
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
        emoji: str | None = None,
        system_prompt: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
    ) -> Agent:
        return self.generator.generate(
            template_id,
            name,
            provider=provider,
            channel=channel,
            outbound_url=outbound_url,
            plugins=plugins,
            memory=memory,
            agent_id=agent_id,
            emoji=emoji,
            system_prompt=system_prompt,
            llm_model=llm_model,
            llm_provider=llm_provider,
        )

    def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        emoji: str | None = None,
        system_prompt: str | None = None,
        channel: str | None = None,
        outbound_url: str | None = None,
        llm_model: str | None = None,
        provider_name: str | None = None,
        llm_api_key: str | None = None,
    ) -> Agent:
        from universal.core.faces import pick_face

        agent = self.registry.get(agent_id)
        if name is not None:
            cleaned = name.strip()
            if cleaned:
                agent.name = cleaned
        if emoji is not None:
            agent.emoji = emoji.strip() or pick_face()
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if channel is not None or outbound_url is not None:
            channel_id = channel or (agent.channel.name if agent.channel is not None else "cli")
            current_out = str(getattr(agent.channel, "outbound_url", "") or "")
            url = current_out if outbound_url is None else outbound_url
            extra: dict[str, object] = {}
            if url:
                extra["outbound_url"] = url
            transport = self.generator.channels.create(channel_id, **extra)
            if hasattr(transport, "agent_id"):
                transport.agent_id = agent.id
            agent.channel = transport
            agent.bind_channel()
        if llm_api_key is not None and llm_api_key.strip():
            from universal.llm_store import save_agent_api_key

            save_agent_api_key(agent.id, llm_api_key)
        if llm_model is not None or provider_name is not None or llm_api_key is not None:
            self.bind_model(
                agent,
                llm_model=llm_model,
                preset_name=provider_name,
                api_key=llm_api_key,
            )
        self.registry.save()
        return agent

    def bind_model(
        self,
        agent: Agent,
        *,
        llm_model: str | None = None,
        preset_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Set this agent's model and live client. Other agents keep the shared provider."""
        from universal.exceptions import ConfigError
        from universal.llm_store import load_agent_api_key
        from universal.providers.catalog import get_provider, is_local_base_url
        from universal.providers.openai_compat import OpenAICompatProvider

        model = (llm_model or "").strip()
        base_url = ""
        if preset_name:
            preset = get_provider(preset_name)
            if preset is None:
                raise ConfigError(f"Unknown model preset {preset_name!r}")
            model = model or str(preset.default_model or "")
            base_url = str(preset.base_url or "").strip()
            agent.llm_provider = preset_name
        if model:
            agent.llm_model = model
        if self.generator._provider_injected:
            return
        secret = (api_key or "").strip() or load_agent_api_key(agent.id)
        shared = self.generator.provider()
        process_key = self.settings.llm_api_key or str(getattr(shared, "_api_key", "") or "")
        key = secret or process_key
        target_url = (
            base_url.rstrip("/")
            if base_url
            else str(getattr(agent.provider, "base_url", "") or getattr(shared, "base_url", "") or "").rstrip("/")
        )
        shared_url = str(getattr(shared, "base_url", "") or "").rstrip("/")
        use_shared = (not secret) and (not target_url or target_url == shared_url)
        if use_shared:
            agent.provider = shared
            return
        if not key and is_local_base_url(target_url or shared_url):
            key = "local"
        if not key:
            return
        url = target_url or shared_url
        if not url:
            return
        agent.provider = OpenAICompatProvider(
            base_url=url,
            api_key=key,
            model=model or str(getattr(shared, "model", "") or "gpt-4o-mini"),
            timeout=self.settings.llm_timeout,
            organization=self.settings.llm_organization,
        )

    def rebind_live_clients(self, old_shared: Provider | None) -> None:
        """Point existing agents at the rebuilt process client, or their own key."""
        if self.generator._provider_injected:
            return
        new_shared = self.generator.provider()
        from universal.llm_store import load_agent_api_key

        for agent in self.registry.all():
            secret = load_agent_api_key(agent.id)
            if secret or agent.llm_provider:
                self.bind_model(
                    agent,
                    llm_model=agent.llm_model or None,
                    preset_name=agent.llm_provider or None,
                )
                continue
            if old_shared is not None and agent.provider is old_shared:
                agent.provider = new_shared
                continue
            self.bind_model(agent, llm_model=agent.llm_model or None)

    def start(self, agent_id: str) -> Agent:
        return self.manager.start(agent_id)

    def stop(self, agent_id: str) -> Agent:
        return self.manager.stop(agent_id)

    def list(self) -> list[AgentInfo]:
        return self.manager.list()

    def delete(self, agent_id: str) -> Agent:
        return self.manager.delete(agent_id)

    def deploy(
        self,
        agent_id: str,
        dest: Path | None = None,
        *,
        target: str = "zip",
    ) -> Path:
        if target == "zip":
            return self.manager.deploy(agent_id, dest)
        if target == "github":
            # Do not write a ZIP as a side effect of a stub that cannot deploy.
            result = GitHubDeployTarget().deploy(dest or Path("."))
            raise DeployError(result.message)
        raise DeployError(f"Unknown deploy target {target!r}. v1 supports 'zip' (GitHub is a stub).")
