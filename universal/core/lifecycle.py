"""Single lifecycle controller. Construct once and inject with the registry."""

from __future__ import annotations

from universal.core.registry import AgentRegistry
from universal.core.types import AgentState
from universal.exceptions import LifecycleError

_ALLOWED: dict[AgentState, frozenset[AgentState]] = {
    AgentState.CREATED: frozenset({AgentState.STARTING, AgentState.ERROR}),
    AgentState.STARTING: frozenset({AgentState.RUNNING, AgentState.ERROR}),
    AgentState.RUNNING: frozenset({AgentState.STOPPING, AgentState.ERROR}),
    AgentState.STOPPING: frozenset({AgentState.STOPPED, AgentState.ERROR}),
    AgentState.STOPPED: frozenset({AgentState.STARTING, AgentState.ERROR}),
    AgentState.ERROR: frozenset({AgentState.STARTING, AgentState.STOPPED}),
}


class AgentLifecycle:
    """Tracks and transitions agent states. One instance per ``Universal`` root.

    Manager and Generator must receive this same object. They must not
    construct their own lifecycle.
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self._states: dict[str, AgentState] = {}
        self._errors: dict[str, str] = {}

    def mark_created(self, agent_id: str) -> AgentState:
        self._states[agent_id] = AgentState.CREATED
        self._errors.pop(agent_id, None)
        return AgentState.CREATED

    def state_of(self, agent_id: str) -> AgentState:
        if agent_id not in self._states:
            # Registry is source of truth for existence; default created.
            if agent_id in self.registry:
                self._states[agent_id] = AgentState.CREATED
            else:
                raise LifecycleError(f"No lifecycle state for unknown agent {agent_id!r}")
        return self._states[agent_id]

    def error_of(self, agent_id: str) -> str | None:
        return self._errors.get(agent_id)

    def start(self, agent_id: str) -> AgentState:
        agent = self.registry.get(agent_id)
        current = self.state_of(agent_id)
        if current is AgentState.RUNNING:
            return AgentState.RUNNING
        self._transition(agent_id, AgentState.STARTING)
        try:
            if agent.channel is not None:
                agent.channel.start()
            self._transition(agent_id, AgentState.RUNNING)
        except Exception as exc:  # noqa: BLE001 — surface any channel failure
            self.mark_error(agent_id, str(exc))
            raise
        return AgentState.RUNNING

    def stop(self, agent_id: str) -> AgentState:
        agent = self.registry.get(agent_id)
        current = self.state_of(agent_id)
        if current is AgentState.STOPPED:
            return AgentState.STOPPED
        if current is AgentState.CREATED:
            self._states[agent_id] = AgentState.STOPPED
            return AgentState.STOPPED
        self._transition(agent_id, AgentState.STOPPING)
        try:
            if agent.channel is not None:
                agent.channel.stop()
            self._transition(agent_id, AgentState.STOPPED)
        except Exception as exc:  # noqa: BLE001
            self.mark_error(agent_id, str(exc))
            raise
        return AgentState.STOPPED

    def mark_error(self, agent_id: str, message: str) -> AgentState:
        self._errors[agent_id] = message
        self._states[agent_id] = AgentState.ERROR
        return AgentState.ERROR

    def forget(self, agent_id: str) -> None:
        self._states.pop(agent_id, None)
        self._errors.pop(agent_id, None)

    def _transition(self, agent_id: str, target: AgentState) -> None:
        current = self.state_of(agent_id)
        allowed = _ALLOWED.get(current, frozenset())
        if target not in allowed:
            raise LifecycleError(f"Cannot move agent {agent_id!r} from {current.value} to {target.value}")
        self._states[agent_id] = target
        if target is not AgentState.ERROR:
            self._errors.pop(agent_id, None)
