"""Persist LLM settings and per-agent keys under user data.

Never write these files into the registry sidecar or a ZIP. Mode 0600.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from universal.config import Settings
from universal.paths import user_data_dir

SETTINGS_NAME = "llm.json"
SECRETS_NAME = "agent_secrets.json"


def settings_file() -> Path:
    return user_data_dir() / SETTINGS_NAME


def agent_secrets_file() -> Path:
    return user_data_dir() / SECRETS_NAME


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_secret_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_llm_settings() -> dict[str, Any]:
    """Return persisted LLM fields. Missing file → empty dict."""
    return _read_json(settings_file())


def load_persisted_channel() -> str:
    raw = str(load_llm_settings().get("default_channel") or "").strip()
    return raw or "cli"


def save_llm_settings(settings: Settings, *, default_channel: str | None = None) -> None:
    current = load_llm_settings()
    channel = default_channel if default_channel is not None else str(current.get("default_channel") or "cli")
    _write_secret_json(
        settings_file(),
        {
            "llm_base_url": settings.llm_base_url,
            "llm_api_key": settings.llm_api_key,
            "llm_model": settings.llm_model,
            "llm_timeout": settings.llm_timeout,
            "llm_organization": settings.llm_organization,
            "default_channel": channel or "cli",
        },
    )


def _secrets_map() -> dict[str, dict[str, str]]:
    raw = _read_json(agent_secrets_file()).get("agents")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for agent_id, row in raw.items():
        if not isinstance(row, dict):
            continue
        key = str(row.get("llm_api_key") or "").strip()
        if key:
            out[str(agent_id)] = {"llm_api_key": key}
    return out


def load_agent_api_key(agent_id: str) -> str:
    return _secrets_map().get(agent_id, {}).get("llm_api_key", "")


def save_agent_api_key(agent_id: str, api_key: str) -> None:
    cleaned = api_key.strip()
    rows = _secrets_map()
    if cleaned:
        rows[agent_id] = {"llm_api_key": cleaned}
    else:
        rows.pop(agent_id, None)
    _write_secret_json(agent_secrets_file(), {"agents": rows})


def discard_agent_api_key(agent_id: str) -> None:
    rows = _secrets_map()
    if agent_id not in rows:
        return
    rows.pop(agent_id, None)
    _write_secret_json(agent_secrets_file(), {"agents": rows})
