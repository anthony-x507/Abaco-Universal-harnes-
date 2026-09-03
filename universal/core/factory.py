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
        )

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
