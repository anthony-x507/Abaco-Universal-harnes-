"""Single in-process catalog of agents. Construct once and inject."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from universal.exceptions import AgentNotFound

if TYPE_CHECKING:
    from universal.core.agent import Agent

ENV_REGISTRY_FILE = "UNIVERSAL_REGISTRY_FILE"


def resolve_registry_file(explicit: str | Path | None = None) -> Path | None:
    """Library / CLI: persist only when a path is passed or the env is set."""
    if explicit is not None:
        text = str(explicit).strip()
        return Path(text) if text else None
    raw = os.environ.get(ENV_REGISTRY_FILE)
    if raw is None or not raw.strip():
        return None
    return Path(raw.strip())


def default_serve_registry_file() -> Path | None:
    """Serve/desktop default: user-data ``registry.json`` unless the env overrides it.

    An empty ``UNIVERSAL_REGISTRY_FILE`` disables the sidecar (in-memory only).
    A leftover ``.universal/registry.json`` in the process cwd is copied once
    so a git update of the checkout does not drop identities.
    """
    raw = os.environ.get(ENV_REGISTRY_FILE)
    if raw is not None:
        return Path(raw.strip()) if raw.strip() else None
    from universal.paths import get_registry_file

    target = get_registry_file()
    if not target.is_file():
        legacy = Path.cwd() / ".universal" / "registry.json"
        if legacy.is_file():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                return legacy
    return target


class AgentRegistry:
    """Owns agent identity. One instance per process / ``Universal`` root.

    Manager and Generator must receive this same object. They must not
    construct their own registry.

    Optional ``persist_path`` is a JSON sidecar of identities, not a second
    registry. History, secrets, and running processes are never written.
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._agents: dict[str, Agent] = {}
        self.persist_path = Path(persist_path) if persist_path else None
        self._persist_enabled = self.persist_path is not None

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def add(self, agent: Agent) -> Agent:
        if agent.id in self._agents:
            raise ValueError(f"Agent {agent.id!r} is already registered")
        self._agents[agent.id] = agent
        self.save()
        return agent

    def get(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise AgentNotFound(f"Agent {agent_id!r} is not registered")
        return agent

    def remove(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            raise AgentNotFound(f"Agent {agent_id!r} is not registered")
        agent = self._agents.pop(agent_id)
        self.save()
        return agent

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

    @contextmanager
    def suspend_persist(self) -> Iterator[None]:
        previous = self._persist_enabled
        self._persist_enabled = False
        try:
            yield
        finally:
            self._persist_enabled = previous

    def load_records(self) -> list[dict[str, object]]:
        if self.persist_path is None or not self.persist_path.is_file():
            return []
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("agents")
        else:
            return []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def save(self) -> None:
        if not self._persist_enabled or self.persist_path is None:
            return
        records = []
        for agent in self.all():
            record = agent.identity_record()
            record["state"] = "stopped"
            records.append(record)
        path = self.persist_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"version": 1, "agents": records}, indent=2) + "\n"
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
