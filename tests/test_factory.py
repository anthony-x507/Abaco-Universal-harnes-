"""Factory create / start / stop / list / delete."""

from __future__ import annotations

from universal.core.platform import Universal
from universal.core.types import AgentState
from universal.exceptions import AgentNotFound


def test_create_start_stop_list_delete(platform: Universal) -> None:
    agent = platform.factory.create("general", name="alpha")
    assert platform.lifecycle.state_of(agent.id) is AgentState.CREATED
    assert len(platform.factory.list()) == 1

    platform.factory.start(agent.id)
    assert platform.lifecycle.state_of(agent.id) is AgentState.RUNNING
    assert agent.channel is not None and agent.channel.running

    platform.factory.start(agent.id)  # idempotent
    assert platform.lifecycle.state_of(agent.id) is AgentState.RUNNING

    platform.factory.stop(agent.id)
    assert platform.lifecycle.state_of(agent.id) is AgentState.STOPPED
    assert agent.channel is not None and not agent.channel.running

    removed = platform.factory.delete(agent.id)
    assert removed.id == agent.id
    assert platform.factory.list() == []
    try:
        platform.registry.get(agent.id)
    except AgentNotFound:
        return
    raise AssertionError("deleted agent must leave the registry")


def test_delete_stops_running_agent(platform: Universal) -> None:
    agent = platform.factory.create("general", name="beta")
    platform.factory.start(agent.id)
    platform.factory.delete(agent.id)
    assert agent.id not in platform.registry


def test_list_is_empty_on_fresh_platform(platform: Universal) -> None:
    assert platform.factory.list() == []
