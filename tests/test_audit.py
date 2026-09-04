"""Harness audit: HMAC seal, lock-safe oracles, no fake npm CLI."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from universal.audit import CHECKS, compute_verdict, doctor, run_audit, verify_audit
from universal.cli import main
from universal.core.platform import Universal
from universal.proof import verify_bundle
from universal.server import create_app


def test_scripts_do_not_call_npm_cli() -> None:
    root = Path(__file__).resolve().parents[1]
    run = (root / "audit" / "scripts" / "run-audit.sh").read_text(encoding="utf-8")
    verify = (root / "audit" / "scripts" / "verify-proof.sh").read_text(encoding="utf-8")
    assert "python3 -m universal audit" in run
    assert "npm install" not in run
    assert "sentinel-proof init" not in run
    assert "sentinel-proof init" not in verify
    assert not (root / "universal" / "state.py").exists()
    assert not (root / "agent_runtime" / "plugins" / "navigator.js").exists()


def test_verdict_rules() -> None:
    required_ok = [{"priority": "required", "risk": "high", "passed": True}]
    assert compute_verdict(required_ok, True) == "VERIFIED"
    assert compute_verdict(required_ok, False) == "FAILED"
    assert compute_verdict([{"priority": "required", "risk": "critical", "passed": False}], True) == "FAILED"
    assert compute_verdict([{"priority": "required", "risk": "medium", "passed": False}], True) == "PARTIAL"


def test_run_audit_seals_verified(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "output"
    summary = run_audit(root=root, output=out)
    assert summary["verdict"] == "VERIFIED"
    assert summary["verified"] is True
    assert summary["quantum"] is False
    assert summary["kind"] == "audit"
    sealed = json.loads((out / "proof.sealed.json").read_text(encoding="utf-8"))
    assert verify_bundle(sealed) is True
    assert sealed["verdict"] == "VERIFIED"
    assert (out / "report.md").is_file()
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "VERIFIED" in report
    assert "not quantum" in report.lower() or "HMAC" in report
    assert "mother.yaml" in report or "OUT OF SCOPE" in report
    checked = verify_audit(out / "proof.sealed.json")
    assert checked["verified"] is True
    required = [check for check in CHECKS if check.priority == "required"]
    assert len(required) >= 20
    desired = [row for row in summary["results"] if row["priority"] == "desired"]
    assert desired
    assert all(not row["passed"] for row in desired)


def test_cli_doctor_and_verify(tmp_path: Path, capsys: object) -> None:
    assert main(["audit", "--doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert payload["ok"] is True
    assert payload["sentinel_proof_npm"] is False
    out = tmp_path / "cli-out"
    assert main(["audit", "--output", str(out)]) == 0
    printed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert printed["verdict"] == "VERIFIED"
    assert main(["audit", "--verify", str(out / "proof.sealed.json")]) == 0


def test_http_audit_run(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("universal.audit.repo_root", lambda: Path(__file__).resolve().parents[1])
    client = TestClient(create_app(platform, demo=True))
    empty = client.get("/v1/audit")
    assert empty.status_code == 200
    ran = client.post("/v1/audit/run")
    assert ran.status_code == 200
    body = ran.json()
    assert body["verdict"] == "VERIFIED"
    assert body["verified"] is True
    assert body["quantum"] is False
    listed = client.get("/v1/audit").json()["audit"]
    assert listed["id"] == body["id"]


def test_doctor_does_not_require_docker() -> None:
    payload = doctor()
    assert "docker" in payload
    assert payload["ok"] is True
