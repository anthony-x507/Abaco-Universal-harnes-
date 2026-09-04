"""Sentinel Proof: sealed evidence for a mission. Not quantum. Not a second registry.

Stages live in one bundle: contract → independent oracles → adversary challenges
→ deterministic reducer. Only a passing bundle gets an HMAC seal.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from universal.notifications import add_notice
from universal.paths import user_data_dir

RULE_ID = "sentinel_proof_required"


def proofs_dir() -> Path:
    path = user_data_dir() / "proofs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def proof_key_path() -> Path:
    return user_data_dir() / "proof.key"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_key() -> bytes:
    path = proof_key_path()
    if path.is_file():
        return path.read_bytes()
    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def _canonical(payload: dict[str, Any]) -> bytes:
    body = {key: payload[key] for key in payload if key not in {"signature", "payload_hash"}}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    raw = _canonical(payload)
    digest = hashlib.sha256(raw).hexdigest()
    signature = hmac.new(_load_key(), raw, hashlib.sha256).hexdigest()
    payload["payload_hash"] = digest
    payload["signature"] = signature
    return payload


def verify_bundle(payload: dict[str, Any]) -> bool:
    signature = str(payload.get("signature") or "")
    if not signature:
        return False
    expected = hmac.new(_load_key(), _canonical(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def proof_path(proof_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in proof_id)[:80] or "proof"
    return proofs_dir() / f"{safe}.json"


def load_proof(proof_id: str) -> dict[str, Any] | None:
    path = proof_path(proof_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save_proof(payload: dict[str, Any]) -> dict[str, Any]:
    path = proof_path(str(payload["id"]))
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def latest_for_agent(agent_id: str) -> dict[str, Any] | None:
    newest: dict[str, Any] | None = None
    for path in proofs_dir().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict) or raw.get("agent_id") != agent_id:
            continue
        if newest is None or str(raw.get("updated_at") or "") > str(newest.get("updated_at") or ""):
            newest = raw
    return newest


def is_sealed(agent_id: str) -> bool:
    bundle = latest_for_agent(agent_id)
    return bool(bundle and bundle.get("status") == "sealed" and verify_bundle(bundle))


def _req_id(index: int, text: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in text.lower())[:24].strip("-")
    return f"r{index + 1}-{slug or 'req'}"


def draft_contract(
    agent_id: str,
    *,
    objective: str,
    requirements: list[str],
    agent_name: str = "",
    kind: str = "mission",
    requirement_ids: list[str] | None = None,
) -> dict[str, Any]:
    texts = [item.strip() for item in requirements if str(item).strip()]
    if not objective.strip() or not texts:
        raise ValueError("objective and at least one requirement are required")
    proof_id = uuid.uuid4().hex[:12]
    rows = []
    for index, text in enumerate(texts):
        req_id = (requirement_ids[index] if requirement_ids and index < len(requirement_ids) else _req_id(index, text))
        rows.append({"id": req_id, "text": text})
    payload = {
        "id": proof_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "objective": objective.strip(),
        "kind": kind,
        "verdict": None,
        "status": "draft",
        "requirements": rows,
        "oracles": [],
        "challenges": [],
        "created_at": _now(),
        "updated_at": _now(),
        "sealed_at": None,
        "payload_hash": None,
        "signature": None,
        "quantum": False,
        "engine": "sentinel-proof-v1",
    }
    if kind != "audit":
        from universal.situation import MissionPhase, Situation

        sit = Situation.load(agent_id, agent_name=agent_name)
        sit.proof_id = proof_id
        if sit.phase.value in {"completed", "executing", "planning", "evaluating"}:
            sit.phase = MissionPhase.VERIFYING
        sit.save()
    return save_proof(payload)


def record_oracle(
    proof_id: str,
    *,
    requirement_id: str,
    passed: bool,
    evidence: str,
    oracle: str = "independent",
) -> dict[str, Any]:
    bundle = load_proof(proof_id)
    if bundle is None:
        raise KeyError(proof_id)
    if bundle.get("status") == "sealed":
        raise ValueError("sealed bundles cannot change")
    ids = {row["id"] for row in bundle.get("requirements") or [] if isinstance(row, dict)}
    if requirement_id not in ids:
        raise ValueError(f"unknown requirement {requirement_id}")
    bundle.setdefault("oracles", []).append(
        {
            "requirement_id": requirement_id,
            "passed": bool(passed),
            "evidence": evidence.strip(),
            "oracle": oracle,
            "at": _now(),
        }
    )
    bundle["status"] = "verifying"
    bundle["updated_at"] = _now()
    return save_proof(bundle)


def challenge(
    proof_id: str,
    *,
    requirement_id: str,
    mutation: str,
    still_holds: bool,
) -> dict[str, Any]:
    bundle = load_proof(proof_id)
    if bundle is None:
        raise KeyError(proof_id)
    if bundle.get("status") == "sealed":
        raise ValueError("sealed bundles cannot change")
    ids = {row["id"] for row in bundle.get("requirements") or [] if isinstance(row, dict)}
    if requirement_id not in ids:
        raise ValueError(f"unknown requirement {requirement_id}")
    bundle.setdefault("challenges", []).append(
        {
            "requirement_id": requirement_id,
            "mutation": mutation.strip(),
            "still_holds": bool(still_holds),
            "at": _now(),
        }
    )
    bundle["status"] = "challenged" if still_holds else "rejected"
    bundle["updated_at"] = _now()
    return save_proof(bundle)


def _oracle_ok(bundle: dict[str, Any]) -> tuple[bool, str]:
    reqs = [row["id"] for row in bundle.get("requirements") or [] if isinstance(row, dict) and row.get("id")]
    oracles = [row for row in bundle.get("oracles") or [] if isinstance(row, dict)]
    if not reqs:
        return False, "no requirements"
    for req_id in reqs:
        hits = [row for row in oracles if row.get("requirement_id") == req_id]
        if not hits:
            return False, f"requirement {req_id} has no oracle"
        if not all(bool(row.get("passed")) for row in hits):
            return False, f"requirement {req_id} failed an oracle"
    return True, "oracles passed"


def _challenge_ok(bundle: dict[str, Any]) -> tuple[bool, str]:
    challenges = [row for row in bundle.get("challenges") or [] if isinstance(row, dict)]
    if not challenges:
        return False, "adversary has not challenged the contract"
    if any(not bool(row.get("still_holds")) for row in challenges):
        return False, "a challenge broke a requirement"
    return True, "challenges held"


def seal(proof_id: str) -> dict[str, Any]:
    bundle = load_proof(proof_id)
    if bundle is None:
        raise KeyError(proof_id)
    if bundle.get("status") == "sealed" and verify_bundle(bundle):
        return bundle
    ok, reason = _oracle_ok(bundle)
    if not ok:
        bundle["status"] = "rejected"
        bundle["updated_at"] = _now()
        save_proof(bundle)
        raise ValueError(reason)
    ok, reason = _challenge_ok(bundle)
    if not ok:
        bundle["status"] = "rejected"
        bundle["updated_at"] = _now()
        save_proof(bundle)
        raise ValueError(reason)
    bundle["status"] = "sealed"
    bundle["sealed_at"] = _now()
    bundle["updated_at"] = bundle["sealed_at"]
    bundle["quantum"] = False
    sign_bundle(bundle)
    save_proof(bundle)
    from universal.situation import MissionPhase, Situation

    sit = Situation.load(str(bundle.get("agent_id") or ""), agent_name=str(bundle.get("agent_name") or ""))
    sit.proof_id = str(bundle["id"])
    sit.phase = MissionPhase.SEALED
    sit.save()
    add_notice(
        agent_id=str(bundle.get("agent_id") or "proof"),
        kind="proof",
        message=f"Proof {bundle['id']} sealed for “{bundle.get('objective')}”. HMAC {str(bundle.get('signature') or '')[:12]}…",
    )
    return bundle


def summarize(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": bundle.get("id"),
        "agent_id": bundle.get("agent_id"),
        "objective": bundle.get("objective"),
        "kind": bundle.get("kind") or "mission",
        "verdict": bundle.get("verdict"),
        "status": bundle.get("status"),
        "requirements": bundle.get("requirements") or [],
        "oracles": bundle.get("oracles") or [],
        "challenges": bundle.get("challenges") or [],
        "sealed_at": bundle.get("sealed_at"),
        "signature": bundle.get("signature"),
        "payload_hash": bundle.get("payload_hash"),
        "verified": bundle.get("status") == "sealed" and verify_bundle(bundle),
        "quantum": False,
        "engine": bundle.get("engine"),
        "updated_at": bundle.get("updated_at"),
    }


def latest_audit() -> dict[str, Any] | None:
    newest: dict[str, Any] | None = None
    for path in proofs_dir().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict) or raw.get("kind") != "audit":
            continue
        if newest is None or str(raw.get("updated_at") or "") > str(newest.get("updated_at") or ""):
            newest = raw
    return newest


def seal_audit(proof_id: str, *, verdict: str) -> dict[str, Any]:
    """Seal an audit bundle. HMAC attests the recorded oracles; verdict may be PARTIAL/FAILED."""
    allowed = {"VERIFIED", "PARTIAL", "BLOCKED", "FAILED"}
    if verdict not in allowed:
        raise ValueError(f"verdict must be one of {sorted(allowed)}")
    bundle = load_proof(proof_id)
    if bundle is None:
        raise KeyError(proof_id)
    reqs = [row["id"] for row in bundle.get("requirements") or [] if isinstance(row, dict) and row.get("id")]
    oracles = [row for row in bundle.get("oracles") or [] if isinstance(row, dict)]
    if not reqs:
        raise ValueError("no requirements")
    for req_id in reqs:
        if not any(row.get("requirement_id") == req_id for row in oracles):
            raise ValueError(f"requirement {req_id} has no oracle")
    if not any(isinstance(row, dict) for row in bundle.get("challenges") or []):
        raise ValueError("adversary has not challenged the contract")
    bundle["verdict"] = verdict
    bundle["kind"] = "audit"
    bundle["status"] = "sealed"
    bundle["sealed_at"] = _now()
    bundle["updated_at"] = bundle["sealed_at"]
    bundle["quantum"] = False
    sign_bundle(bundle)
    save_proof(bundle)
    add_notice(
        agent_id=str(bundle.get("agent_id") or "audit"),
        kind="audit",
        message=f"Audit {bundle['id']} sealed as {verdict}. HMAC {str(bundle.get('signature') or '')[:12]}…",
    )
    return bundle
