"""Single in-process catalog of agents. Construct once and inject."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from universal.exceptions import AgentNotFound

if TYPE_CHECKING:
    from universal.core.agent import Agent


class AgentRegistry:
    """Owns agent identity. One instance per process / ``Universal`` root.

    Manager and Generator must receive this same object. They must not
    construct their own registry.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def add(self, agent: Agent) -> Agent:
        if agent.id in self._agents:
            raise ValueError(f"Agent {agent.id!r} is already registered")
        self._agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise AgentNotFound(f"Agent {agent_id!r} is not registered")
        return agent

    def remove(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            raise AgentNotFound(f"Agent {agent_id!r} is not registered")
        return self._agents.pop(agent_id)

    def ids(self) -> list[str]:
        return list(self._agents.keys())

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def find_by_name(self, name: str) -> Agent | None:
        for agent in self._agents.values():
            if agent.name == name:
                return agent
        return None

    def __iter__(self) -> Iterator[Agent]:
        return iter(self._agents.values())
