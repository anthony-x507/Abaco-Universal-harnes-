"""Starts, stops, lists, and deletes agents. Does not own registry or lifecycle."""

from __future__ import annotations

from pathlib import Path

from universal.core.agent import Agent
from universal.core.lifecycle import AgentLifecycle
from universal.core.registry import AgentRegistry
from universal.core.types import AgentInfo
from universal.deploy.packager import ZipPackager
from universal.exceptions import LifecycleError


class AgentManager:
    """Operational control plane for registered agents.

    Receives the shared ``AgentRegistry`` and ``AgentLifecycle``. Never
    constructs its own copies.
    """

    def __init__(self, registry: AgentRegistry, lifecycle: AgentLifecycle) -> None:
        if registry is None or lifecycle is None:
            raise TypeError("AgentManager requires injected registry and lifecycle")
        if lifecycle.registry is not registry:
            raise ValueError("lifecycle.registry must be the same object as registry")
        self.registry = registry
        self.lifecycle = lifecycle

    def start(self, agent_id: str) -> Agent:
        agent = self.registry.get(agent_id)
        state = self.lifecycle.state_of(agent_id)
        if state.value == "running":
            return agent
        self.lifecycle.start(agent_id)
        return agent

    def stop(self, agent_id: str) -> Agent:
        agent = self.registry.get(agent_id)
        self.lifecycle.stop(agent_id)
        return agent

    def list(self) -> list[AgentInfo]:
        infos: list[AgentInfo] = []
        for agent in self.registry.all():
            try:
                state = self.lifecycle.state_of(agent.id)
            except LifecycleError:
                state = agent.info().state
            infos.append(agent.info(state))
        return infos

    def delete(self, agent_id: str) -> Agent:
        state = None
        try:
            state = self.lifecycle.state_of(agent_id)
        except LifecycleError:
            state = None
        if state is not None and state.value == "running":
            self.lifecycle.stop(agent_id)
        agent = self.registry.remove(agent_id)
        self.lifecycle.forget(agent_id)
        agent.discard_persisted_history()
        from universal.llm_store import discard_agent_api_key
        from universal.situation import discard_situation

        discard_agent_api_key(agent.id)
        discard_situation(agent.id)
        return agent

    def deploy(self, agent_id: str, dest: Path | None = None) -> Path:
        agent = self.registry.get(agent_id)
        state = self.lifecycle.state_of(agent_id)
        return ZipPackager().pack(agent, dest, state=state)
