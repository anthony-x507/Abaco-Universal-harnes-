"""Mission state, notices, and teams of existing agents. No mother YAML."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.notifications import list_notices
from universal.server import create_app
from universal.situation import MissionPhase, Situation, situation_path
from universal.templates.catalog import get_template
from tests.conftest import FakeProvider


def _call(name: str, **kwargs: object) -> ToolCall:
    return ToolCall(id="t1", name=name, arguments=json.dumps(kwargs))


def test_no_mother_yaml_or_fourth_template() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "universal" / "templates" / "mother.yaml").exists()
    assert not (root / "mother.yaml").exists()
    assert not (root / "universal" / "factory").exists()
    from universal.templates.catalog import catalog

    assert catalog.ids() == ["general", "researcher", "coder"]


def test_objective_persists_across_reload(platform: Universal) -> None:
    agent = platform.factory.create("general", name="nav-persist")
    plugin = agent.plugins.get("navigator")
    assert plugin is not None
    assert plugin.invoke_tool(_call("set_objective", objective="Ship the demo")) == "Objective set: Ship the demo"
    assert situation_path(agent.id).is_file()
    reloaded = Situation.load(agent.id)
    assert reloaded.objective == "Ship the demo"
    assert reloaded.phase is MissionPhase.PLANNING
    again = Situation.load(agent.id, agent_name="nav-persist")
    assert again.objective == "Ship the demo"
    assert again.to_dict()["agent"] == "nav-persist"


def test_obstacle_notifies_and_fails_at_three_attempts(platform: Universal) -> None:
    agent = platform.factory.create("general", name="nav-block")
    plugin = agent.plugins.get("navigator")
    assert plugin is not None
    plugin.invoke_tool(_call("set_objective", objective="Finish the report"))
    plugin.invoke_tool(_call("plan_steps", steps=["research", "write"]))
    for index in range(2):
        out = plugin.invoke_tool(_call("report_obstacle", step="research", obstacle=f"paywall {index}"))
        assert out is not None and "Blocked" in out
        assert Situation.load(agent.id).phase is MissionPhase.BLOCKED
    out = plugin.invoke_tool(_call("report_obstacle", step="research", obstacle="paywall 2"))
    assert out is not None and "failed" in out.lower()
    status = Situation.load(agent.id)
    assert status.phase is MissionPhase.FAILED
    assert status.attempts == 3
    notices = list_notices()
    assert len(notices) >= 3
    assert all(row["kind"] == "blocked" for row in notices)
    assert any("Finish the report" in str(row["message"]) for row in notices)


def test_deviation_denied_when_permission_is_deny(platform: Universal, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    agent = platform.factory.create("general", name="nav-dev")
    plugin = agent.plugins.get("navigator")
    assert plugin is not None
    plugin.invoke_tool(_call("set_objective", objective="Stay on plan"))
    plugin.invoke_tool(_call("plan_steps", steps=["a", "b"]))
    out = plugin.invoke_tool(_call("report_deviation", reason="shortcut", from_step="a", to_step="b"))
    assert out is not None and out.startswith("error: deviation denied")
    status = Situation.load(agent.id)
    assert status.phase is MissionPhase.EXECUTING
    assert status.deviations == []
    assert list_notices() == []


def test_create_team_and_delegate_uses_accept(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    lead = client.post("/v1/agents", json={"template": "general", "name": "lead"}).json()
    helper = client.post("/v1/agents", json={"template": "coder", "name": "helper"}).json()
    team = client.post("/v1/teams", json={"name": "lab", "member_ids": [lead["id"], helper["id"]]})
    assert team.status_code == 200
    assert len(team.json()["members"]) == 2
    delegated = client.post(
        "/v1/teams/lab/delegate",
        json={"agent_id": helper["id"], "task": "summarize the notes"},
    )
    assert delegated.status_code == 200
    assert delegated.json()["answer"].startswith("echo:")
    assert "summarize the notes" in delegated.json()["answer"]
    assert platform.lifecycle.state_of(helper["id"]).value == "running"
    got = client.get("/v1/teams/lab")
    assert got.status_code == 200
    assert got.json()["name"] == "lab"
    situation = client.get(f"/v1/agents/{lead['id']}/situation")
    assert situation.status_code == 200
    assert situation.json()["phase"] == "idle"
    checkpoint = client.post("/v1/teams/lab/checkpoint")
    assert checkpoint.status_code == 200
    assert checkpoint.json()["last_checkpoint"]
    helper_agent = platform.registry.get(helper["id"])
    navigator = helper_agent.plugins.get("navigator")
    assert navigator is not None
    navigator.invoke_tool(
        ToolCall(id="t2", name="set_objective", arguments=json.dumps({"objective": "summarize the notes"}))
    )
    plugin = platform.registry.get(lead["id"]).plugins.get("team")
    assert plugin is not None
    resumed = plugin.invoke_tool(ToolCall(id="t3", name="resume_team", arguments=json.dumps({"name": "lab"})))
    assert resumed is not None
    payload = json.loads(resumed)
    assert payload["last_checkpoint"]
    helper_row = next(row for row in payload["members"] if row["id"] == helper["id"])
    assert helper_row["situation"]["objective"] == "summarize the notes"
    listed = client.get("/v1/teams/lab").json()
    assert listed["members"][0]["situation"]["phase"]


def test_team_plugin_share_note_asks_when_enforced(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps({"version": "1.0", "rules": [{"id": "memory_share_between_agents", "enforced": True}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    lead = platform.factory.create("general", name="note-lead")
    helper = platform.factory.create("coder", name="note-helper")
    plugin = lead.plugins.get("team")
    assert plugin is not None
    created = plugin.invoke_tool(
        ToolCall(
            id="t1",
            name="create_team",
            arguments=json.dumps({"name": "notes", "member_ids": [lead.id, helper.id]}),
        )
    )
    assert created is not None and "Team notes" in created
    denied = plugin.invoke_tool(
        ToolCall(id="t2", name="share_note", arguments=json.dumps({"name": "notes", "text": "secret fact"}))
    )
    assert denied is not None and denied.startswith("error: sharing denied")


def test_t03_still_one_system_message(platform: Universal, provider: FakeProvider) -> None:
    template = get_template("general")
    agent = platform.factory.create("general", name="t03-mission")
    assert "Never promise a result you cannot produce" in template.system_prompt
    assert agent.system_prompt == template.system_prompt
    platform.factory.start(agent.id)
    agent.accept("ping")
    first = provider.calls[0][0]
    assert first.role == "system"
    assert first.content.startswith(template.system_prompt)
    assert "Response style:" in first.content
    assert sum(1 for message in provider.calls[0] if message.role == "system") == 1


def test_delete_discards_situation(platform: Universal) -> None:
    agent = platform.factory.create("general", name="gone")
    plugin = agent.plugins.get("navigator")
    assert plugin is not None
    plugin.invoke_tool(_call("set_objective", objective="temp"))
    assert situation_path(agent.id).is_file()
    agent_id = agent.id
    platform.factory.delete(agent_id)
    assert not situation_path(agent_id).is_file()


def test_http_situation_reset_and_notices(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post("/v1/agents", json={"template": "general", "name": "http-nav"}).json()
    agent = platform.registry.get(created["id"])
    plugin = agent.plugins.get("navigator")
    assert plugin is not None
    plugin.invoke_tool(_call("set_objective", objective="Keep going"))
    plugin.invoke_tool(_call("plan_steps", steps=["one"]))
    plugin.invoke_tool(_call("report_obstacle", step="one", obstacle="missing file"))
    body = client.get(f"/v1/agents/{created['id']}/situation").json()
    assert body["phase"] == "blocked"
    assert body["objective"] == "Keep going"
    notices = client.get("/v1/notifications").json()["notifications"]
    assert notices
    acked = client.post(f"/v1/notifications/{notices[0]['id']}/ack")
    assert acked.status_code == 200
    assert client.get("/v1/notifications").json()["notifications"] == []
    reset = client.post(f"/v1/agents/{created['id']}/situation/reset")
    assert reset.status_code == 200
    assert reset.json()["phase"] == "idle"
    assert reset.json()["objective"] == ""
