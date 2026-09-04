"""User-visible mission notices. Stored under user data, not in chat history."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from universal.paths import user_data_dir


def notifications_path() -> Path:
    return user_data_dir() / "notifications.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict[str, Any]]:
    path = notifications_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []


def _save(rows: list[dict[str, Any]]) -> None:
    path = notifications_path()
    path.write_text(json.dumps(rows[-80:], indent=2), encoding="utf-8")


def add_notice(*, agent_id: str, kind: str, message: str) -> dict[str, Any]:
    row = {
        "id": uuid.uuid4().hex[:12],
        "agent_id": agent_id,
        "kind": kind,
        "message": message,
        "at": _now(),
        "acked": False,
    }
    rows = _load()
    rows.append(row)
    _save(rows)
    from universal.nervous import emit

    emit("notice", agent_id=agent_id, notice_id=row["id"], kind=kind, message=message)
    return row


def list_notices(*, unread_only: bool = False) -> list[dict[str, Any]]:
    rows = _load()
    if unread_only:
        return [row for row in rows if not row.get("acked")]
    return rows


def ack_notice(notice_id: str) -> dict[str, Any] | None:
    rows = _load()
    found: dict[str, Any] | None = None
    for row in rows:
        if str(row.get("id")) == notice_id:
            row["acked"] = True
            found = row
    if found:
        _save(rows)
    return found
