"""Sentinel Proof: HMAC evidence, stages not templates, no quantum claim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.proof import (
    challenge,
    draft_contract,
    load_proof,
    record_oracle,
    seal,
    verify_bundle,
)
from universal.server import create_app
from universal.situation import MissionPhase, Situation
from universal.templates.catalog import get_template
from tests.conftest import FakeProvider


def _call(name: str, **kwargs: object) -> ToolCall:
    return ToolCall(id="t1", name=name, arguments=json.dumps(kwargs))


def _enable_proof_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps({"version": "1.0", "rules": [{"id": "sentinel_proof_required", "enforced": True}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))


def test_no_node_proof_or_quantum_claims() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "agent_runtime" / "plugins" / "navigator.js").exists()
    assert not (root / "agent_runtime" / "plugins" / "orchestrator.js").exists()
    assert not (root / "agent_runtime" / "plugins" / "improvement_evaluator.js").exists()
    assert not (root / "universal" / "state.py").exists()
    text = (root / "universal" / "proof.py").read_text(encoding="utf-8")
    assert "quantum: False" in text or '"quantum": False' in text
    assert "hmac" in text.lower()
    assert "sentinel-proof-v1" in text
    ui = (root / "web" / "src" / "components" / "ProofPanel.tsx").read_text(encoding="utf-8")
    assert "Not quantum" in ui
    assert "HMAC" in ui


def test_draft_oracle_challenge_seal_and_verify(platform: Universal) -> None:
    agent = platform.factory.create("general", name="proof-ok")
    bundle = draft_contract(
        agent.id,
        objective="Ship the sealed demo",
        requirements=["tests pass", "no secrets in zip"],
        agent_name=agent.name,
    )
    assert bundle["status"] == "draft"
    assert bundle["quantum"] is False
    assert bundle["engine"] == "sentinel-proof-v1"
    assert Situation.load(agent.id).proof_id == bundle["id"]
    reqs = [row["id"] for row in bundle["requirements"]]
    for req_id in reqs:
        record_oracle(bundle["id"], requirement_id=req_id, passed=True, evidence=f"checked {req_id}")
    challenge(bundle["id"], requirement_id=reqs[0], mutation="drop the test file", still_holds=True)
    sealed = seal(bundle["id"])
    assert sealed["status"] == "sealed"
    assert sealed["signature"]
    assert verify_bundle(sealed) is True
    assert Situation.load(agent.id).phase is MissionPhase.SEALED
    with pytest.raises(ValueError, match="sealed"):
        record_oracle(bundle["id"], requirement_id=reqs[0], passed=True, evidence="again")
    with pytest.raises(ValueError, match="sealed"):
        challenge(bundle["id"], requirement_id=reqs[0], mutation="again", still_holds=True)


def test_failed_challenge_cannot_seal(platform: Universal) -> None:
    agent = platform.factory.create("general", name="proof-fail")
    bundle = draft_contract(agent.id, objective="Hold the line", requirements=["output is deterministic"])
    req_id = bundle["requirements"][0]["id"]
    record_oracle(bundle["id"], requirement_id=req_id, passed=True, evidence="same hash twice")
    challenge(bundle["id"], requirement_id=req_id, mutation="shuffle input", still_holds=False)
    with pytest.raises(ValueError, match="challenge"):
        seal(bundle["id"])
    stored = load_proof(bundle["id"])
    assert stored is not None
    assert stored["status"] == "rejected"
    assert stored.get("signature") in (None, "")


def test_missing_oracle_cannot_seal(platform: Universal) -> None:
    agent = platform.factory.create("general", name="proof-gap")
    bundle = draft_contract(agent.id, objective="Need both checks", requirements=["a", "b"])
    first = bundle["requirements"][0]["id"]
    record_oracle(bundle["id"], requirement_id=first, passed=True, evidence="only a")
    challenge(bundle["id"], requirement_id=first, mutation="omit b", still_holds=True)
    with pytest.raises(ValueError, match="oracle"):
        seal(bundle["id"])


def test_rule_holds_last_step_in_verifying_until_seal(
    platform: Universal, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_proof_rule(tmp_path, monkeypatch)
    agent = platform.factory.create("general", name="proof-nav")
    nav = agent.plugins.get("navigator")
    proof = agent.plugins.get("proof")
    assert nav is not None and proof is not None
    nav.invoke_tool(_call("set_objective", objective="Seal before done"))
    nav.invoke_tool(_call("plan_steps", steps=["write", "check"]))
    nav.invoke_tool(_call("complete_step", step="write"))
    out = nav.invoke_tool(_call("complete_step", step="check"))
    assert out is not None and "Seal a Sentinel Proof" in out
    assert Situation.load(agent.id).phase is MissionPhase.VERIFYING
    drafted = proof.invoke_tool(
        _call("draft_contract", objective="Seal before done", requirements=["check passed"])
    )
    assert drafted is not None and "draft" in drafted
    payload = json.loads(drafted)
    req_id = payload["requirements"][0]["id"]
    proof.invoke_tool(_call("record_oracle", requirement_id=req_id, passed=True, evidence="green"))
    proof.invoke_tool(
        _call("challenge_requirement", requirement_id=req_id, mutation="empty output", still_holds=True)
    )
    sealed = proof.invoke_tool(_call("seal_proof"))
    assert sealed is not None
    body = json.loads(sealed)
    assert body["status"] == "sealed"
    assert body["verified"] is True
    assert Situation.load(agent.id).phase is MissionPhase.SEALED


def test_last_step_completes_when_proof_rule_is_off(platform: Universal) -> None:
    agent = platform.factory.create("general", name="proof-off")
    nav = agent.plugins.get("navigator")
    assert nav is not None
    nav.invoke_tool(_call("set_objective", objective="Just finish"))
    nav.invoke_tool(_call("plan_steps", steps=["one"]))
    out = nav.invoke_tool(_call("complete_step", step="one"))
    assert out is not None and "Objective reached" in out
    assert Situation.load(agent.id).phase is MissionPhase.COMPLETED


def test_http_proof_path(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post("/v1/agents", json={"template": "general", "name": "http-proof"}).json()
    empty = client.get(f"/v1/agents/{created['id']}/proof")
    assert empty.status_code == 200
    assert empty.json()["proof"] is None
    drafted = client.post(
        f"/v1/agents/{created['id']}/proof",
        json={"objective": "HTTP seal", "requirements": ["route works"]},
    )
    assert drafted.status_code == 200
    proof_id = drafted.json()["id"]
    req_id = drafted.json()["requirements"][0]["id"]
    assert drafted.json()["quantum"] is False
    oracle = client.post(
        f"/v1/proofs/{proof_id}/oracle",
        json={"requirement_id": req_id, "passed": True, "evidence": "200 from TestClient"},
    )
    assert oracle.status_code == 200
    challenged = client.post(
        f"/v1/proofs/{proof_id}/challenge",
        json={"requirement_id": req_id, "mutation": "wrong agent id", "still_holds": True},
    )
    assert challenged.status_code == 200
    sealed = client.post(f"/v1/proofs/{proof_id}/seal")
    assert sealed.status_code == 200
    body = sealed.json()
    assert body["status"] == "sealed"
    assert body["verified"] is True
    assert body["signature"]
    listed = client.get(f"/v1/agents/{created['id']}/proof").json()["proof"]
    assert listed["id"] == proof_id
    assert listed["verified"] is True
    blocked = client.post(
        f"/v1/proofs/{proof_id}/oracle",
        json={"requirement_id": req_id, "passed": True, "evidence": "late"},
    )
    assert blocked.status_code == 400


def test_t03_still_one_system_message_with_proof_tools(platform: Universal, provider: FakeProvider) -> None:
    template = get_template("general")
    assert "seal_proof" in template.system_prompt
    assert "HMAC" in template.system_prompt
    assert "quantum" in template.system_prompt.lower()
    agent = platform.factory.create("general", name="t03-proof")
    assert agent.system_prompt == template.system_prompt
    platform.factory.start(agent.id)
    agent.accept("ping")
    first = provider.calls[0][0]
    assert first.role == "system"
    assert first.content == template.system_prompt
    assert sum(1 for message in provider.calls[0] if message.role == "system") == 1
