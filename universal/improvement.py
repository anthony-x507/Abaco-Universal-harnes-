"""Visible improvement proposals. Not a Node plugin. Not a second planner."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from universal.nervous import emit
from universal.notifications import add_notice
from universal.paths import user_data_dir
from universal.rules import is_enforced

RULE_ID = "improvement_allow_suggestions"


def proposals_dir() -> Path:
    path = user_data_dir() / "proposals"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(proposal_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in proposal_id)[:80]
    return proposals_dir() / f"{safe}.json"


def load_proposal(proposal_id: str) -> dict[str, Any] | None:
    path = _path(proposal_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save_proposal(row: dict[str, Any]) -> dict[str, Any]:
    path = _path(str(row["id"]))
    path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def list_proposals(agent_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in proposals_dir().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        if agent_id and raw.get("agent_id") != agent_id:
            continue
        rows.append(raw)
    rows.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return rows


def propose(
    agent_id: str,
    *,
    task: str,
    proposed_plan: str,
    original_plan: str = "",
    agent_name: str = "",
) -> dict[str, Any]:
    if not task.strip() or not proposed_plan.strip():
        raise ValueError("task and proposed_plan are required")
    if not is_enforced(RULE_ID):
        raise PermissionError(f"{RULE_ID} is off")
    row = {
        "id": uuid.uuid4().hex[:12],
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task": task.strip(),
        "original_plan": original_plan.strip(),
        "proposed_plan": proposed_plan.strip(),
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    save_proposal(row)
    add_notice(
        agent_id=agent_id,
        kind="improvement",
        message=f"Proposed improvement for “{task.strip()}”. Accept or reject in Mission.",
    )
    emit("improvement.proposed", agent_id=agent_id, proposal_id=row["id"], task=task.strip())
    return row


def decide(proposal_id: str, *, accepted: bool) -> dict[str, Any]:
    row = load_proposal(proposal_id)
    if row is None:
        raise KeyError(proposal_id)
    if row.get("status") != "pending":
        raise ValueError("proposal is no longer pending")
    row["status"] = "accepted" if accepted else "rejected"
    row["updated_at"] = _now()
    save_proposal(row)
    emit(
        "improvement.decided",
        agent_id=row.get("agent_id"),
        proposal_id=row["id"],
        accepted=accepted,
    )
    add_notice(
        agent_id=str(row.get("agent_id") or ""),
        kind="improvement",
        message=("Improvement accepted." if accepted else "Improvement rejected."),
    )
    return row
