"""Prove one AgentRegistry and one AgentLifecycle are constructed and injected."""

from __future__ import annotations

from universal.config import Settings
from universal.core.factory import AgentFactory
from universal.core.generator import AgentGenerator
from universal.core.lifecycle import AgentLifecycle
from universal.core.manager import AgentManager
from universal.core.platform import Universal
from universal.core.registry import AgentRegistry
from tests.conftest import FakeProvider


def test_universal_constructs_registry_and_lifecycle_once() -> None:
    platform = Universal(
        Settings(llm_base_url="https://example.test/v1", llm_api_key="k", llm_model="m"),
        provider=FakeProvider(),
    )
    assert platform.factory.registry is platform.registry
    assert platform.factory.lifecycle is platform.lifecycle
    assert platform.lifecycle.registry is platform.registry


def test_generator_and_manager_share_injected_instances() -> None:
    registry = AgentRegistry()
    lifecycle = AgentLifecycle(registry)
    settings = Settings(llm_base_url="https://example.test/v1", llm_api_key="k", llm_model="m")
    generator = AgentGenerator(registry, lifecycle, settings, provider=FakeProvider())
    manager = AgentManager(registry, lifecycle)

    assert generator.registry is manager.registry is registry
    assert generator.lifecycle is manager.lifecycle is lifecycle

    agent = generator.generate("general", name="shared")
    listed = manager.list()
    assert len(listed) == 1
    assert listed[0].id == agent.id
    assert manager.start(agent.id) is agent
    assert manager.stop(agent.id) is agent


def test_factory_forwards_the_same_objects() -> None:
    registry = AgentRegistry()
    lifecycle = AgentLifecycle(registry)
    settings = Settings(llm_base_url="https://example.test/v1", llm_api_key="k", llm_model="m")
    factory = AgentFactory(registry, lifecycle, settings, provider=FakeProvider())

    assert factory.generator.registry is factory.manager.registry is registry
    assert factory.generator.lifecycle is factory.manager.lifecycle is lifecycle


def test_factory_rejects_mismatched_lifecycle_registry() -> None:
    registry = AgentRegistry()
    other = AgentRegistry()
    lifecycle = AgentLifecycle(other)
    settings = Settings(llm_base_url="https://example.test/v1", llm_api_key="k", llm_model="m")
    try:
        AgentFactory(registry, lifecycle, settings, provider=FakeProvider())
    except ValueError as exc:
        assert "same object" in str(exc)
    else:
        raise AssertionError("expected ValueError for mismatched registry")
