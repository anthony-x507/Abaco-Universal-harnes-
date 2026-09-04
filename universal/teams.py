"""Teams of existing agents. No fourth template. No mother YAML."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from universal.paths import user_data_dir

DelegateFn = Callable[[str, str], str]
_DELEGATE: DelegateFn | None = None


def set_delegate_hook(fn: DelegateFn | None) -> None:
    global _DELEGATE
    _DELEGATE = fn


def teams_dir() -> Path:
    path = user_data_dir() / "teams"
    path.mkdir(parents=True, exist_ok=True)
    return path


def team_path(name: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)[:80] or "team"
    return teams_dir() / f"{safe}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_team(name: str) -> dict[str, Any] | None:
    path = team_path(name)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save_team(name: str, data: dict[str, Any]) -> dict[str, Any]:
    data["name"] = name
    path = team_path(name)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def create_team(name: str, members: list[dict[str, str]]) -> dict[str, Any]:
    payload = {
        "name": name,
        "members": members,
        "created_at": _now(),
        "last_checkpoint": "",
        "notes": [],
        "current_step": "",
    }
    return save_team(name, payload)


def add_note(name: str, *, agent_id: str, text: str) -> dict[str, Any]:
    team = load_team(name)
    if team is None:
        raise KeyError(name)
    notes = list(team.get("notes") or [])
    notes.append({"agent_id": agent_id, "text": text, "at": _now()})
    team["notes"] = notes[-40:]
    return save_team(name, team)


def checkpoint_team(name: str) -> dict[str, Any]:
    team = load_team(name)
    if team is None:
        raise KeyError(name)
    team["last_checkpoint"] = _now()
    return save_team(name, team)


def team_snapshot(name: str) -> dict[str, Any] | None:
    """Team file plus each member's saved mission. Resume is load, not recreate."""
    team = load_team(name)
    if team is None:
        return None
    from universal.situation import Situation

    members: list[dict[str, Any]] = []
    for row in team.get("members") or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        member_id = str(item.get("id") or "")
        if member_id:
            item["situation"] = Situation.load(member_id, agent_name=str(item.get("name") or "")).to_dict()
        members.append(item)
    payload = dict(team)
    payload["members"] = members
    return payload


def delegate(agent_id: str, prompt: str) -> str:
    if _DELEGATE is None:
        return "error: team delegate is only available while the factory is running"
    return _DELEGATE(agent_id, prompt)
