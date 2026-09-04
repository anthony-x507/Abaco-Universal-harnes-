"""Visible improvement + in-process wiring. No Redis. No mother."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.improvement import decide, list_proposals, propose
from universal.nervous import CircuitBreaker, CircuitOpen, health_snapshot, list_events, provider_breaker
from universal.server import create_app
from tests.conftest import FakeProvider


def _call(name: str, **kwargs: object) -> ToolCall:
    return ToolCall(id="t1", name=name, arguments=json.dumps(kwargs))


def test_no_redis_or_mother_or_node_evaluator() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "shared" / "event-bus.js").exists()
    assert not (root / "universal" / "core.py").exists()
    assert not (root / "universal" / "templates" / "mother.yaml").exists()
    assert not (root / "agent_runtime" / "plugins" / "improvement_evaluator.js").exists()
    assert (root / "docs" / "wiring.md").is_file()
    assert "Redis" in (root / "docs" / "wiring.md").read_text(encoding="utf-8")


def test_propose_accept_and_events(platform: Universal) -> None:
    agent = platform.factory.create("general", name="improve-me")
    plugin = agent.plugins.get("improvement")
    assert plugin is not None
    out = plugin.invoke_tool(
        _call("propose_improvement", task="Ship the demo", proposed_plan="Seal proof first")
    )
    assert out is not None and "pending" in out
    row = json.loads(out)
    assert list_proposals(agent.id)[0]["id"] == row["id"]
    accepted = decide(row["id"], accepted=True)
    assert accepted["status"] == "accepted"
    kinds = [item["kind"] for item in list_events()]
    assert "improvement.proposed" in kinds
    assert "improvement.decided" in kinds
    assert "notice" in kinds


def test_rule_off_blocks_propose(platform: Universal, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps({"version": "1.0", "rules": [{"id": "improvement_allow_suggestions", "enforced": False}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    with pytest.raises(PermissionError):
        propose("agent", task="x", proposed_plan="y")


def test_circuit_opens_after_three_failures() -> None:
    provider_breaker().reset()
    breaker = CircuitBreaker("test", max_failures=3, reset_after=60)

    def boom() -> None:
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            breaker.execute(boom)
    assert breaker.state == "open"
    with pytest.raises(CircuitOpen):
        breaker.execute(lambda: 1)
    provider_breaker().reset()


def test_health_reports_in_process_bus(platform: Universal) -> None:
    snap = health_snapshot()
    assert snap["bus"] == "in-process"
    assert snap["redis"] is False
    assert snap["nats"] is False
    client = TestClient(create_app(platform, demo=True))
    health = client.get("/health").json()
    assert health["nervous"]["redis"] is False
    created = client.post("/v1/agents", json={"template": "general", "name": "wire"}).json()
    proposed = client.post(
        f"/v1/agents/{created['id']}/improvements",
        json={"task": "Close the puzzle", "proposed_plan": "Keep the Python bus"},
    )
    assert proposed.status_code == 200
    assert proposed.json()["status"] == "pending"
    accepted = client.post(f"/v1/improvements/{proposed.json()['id']}/accept")
    assert accepted.status_code == 200
    events = client.get("/v1/events").json()
    assert events["nervous"]["bus"] == "in-process"
    assert any(row["kind"].startswith("improvement") for row in events["events"])


def test_t03_still_one_system_message(platform: Universal, provider: FakeProvider) -> None:
    from universal.templates.catalog import get_template

    template = get_template("general")
    assert "propose_improvement" in template.system_prompt
    agent = platform.factory.create("general", name="t03-improve")
    assert agent.system_prompt == template.system_prompt
    platform.factory.start(agent.id)
    agent.accept("ping")
    first = provider.calls[0][0]
    assert first.role == "system"
    assert first.content == template.system_prompt
    assert sum(1 for message in provider.calls[0] if message.role == "system") == 1
