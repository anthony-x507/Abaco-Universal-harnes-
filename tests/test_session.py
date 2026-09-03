"""In-process factory session uses the injected registry — no second store."""

from __future__ import annotations

from pathlib import Path

from universal.core.platform import Universal
from universal.session import FactorySession
from tests.conftest import FakeProvider


def test_session_create_start_ask_stop_delete(platform: Universal, tmp_path: Path) -> None:
    session = FactorySession(platform)
    agent_id = session.execute("create general --name sess")
    assert agent_id
    assert agent_id in session.execute("list")

    assert session.execute(f"start {agent_id}") == agent_id
    answer = session.execute(f"ask {agent_id} hello there")
    assert answer.startswith("echo:")

    zip_path = tmp_path / "sess.zip"
    written = session.execute(f"deploy {agent_id} --out {zip_path}")
    assert Path(written).is_file()

    assert session.execute(f"stop {agent_id}") == agent_id
    assert session.execute(f"delete {agent_id}") == agent_id
    assert session.execute("list") == "(empty)"


def test_session_create_webhook(platform: Universal) -> None:
    session = FactorySession(platform)
    agent_id = session.execute(
        "create general --name hook --channel webhook --outbound-url http://example.test/cb"
    )
    agent = platform.registry.get(agent_id)
    assert agent.channel is not None
    assert agent.channel.name == "webhook"
    assert getattr(agent.channel, "outbound_url") == "http://example.test/cb"


def test_session_unknown_command(platform: Universal) -> None:
    session = FactorySession(platform)
    assert session.execute("explode").startswith("error:")


def test_session_shares_platform_registry(settings: object, provider: FakeProvider) -> None:
    platform = Universal(settings, provider=provider)  # type: ignore[arg-type]
    session = FactorySession(platform)
    agent_id = session.execute("create coder --name wired")
    assert platform.registry.get(agent_id).name == "wired"
    assert platform.factory.generator.registry is platform.registry
    assert platform.factory.manager.registry is platform.registry
