"""User-data locations that survive replacing Universal.app.

Native plugin *code* stays in the Python package (not copied here).
This directory holds memory, the registry sidecar, chat history, and a plugin manifest.
Secrets are never written. Chat history is stored under ``history/`` by agent id.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_USER_DATA = "UNIVERSAL_USER_DATA"
APP_NAME = "Universal"


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """macOS Application Support, else XDG / %APPDATA%, overridable for tests."""
    override = os.environ.get(ENV_USER_DATA, "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    home = Path.home()
    if sys.platform == "darwin":
        path = home / "Library" / "Application Support" / APP_NAME
    elif os.name == "nt":
        base = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        path = Path(base) / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
        path = Path(base) / "universal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_plugins_dir() -> Path:
    """Metadata only (manifest). Executable plugins are not loaded from here."""
    path = user_data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runtime_dir() -> Path:
    """User-writable Node runtime. The signed app never writes here after first copy."""
    path = user_data_dir() / "agent_runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_memory_dir() -> Path:
    env = os.environ.get("UNIVERSAL_MEMORY_DIR", "").strip()
    if env:
        path = Path(env)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if is_packaged() or os.environ.get(ENV_USER_DATA, "").strip():
        path = user_data_dir() / "memory"
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = Path(os.environ.get("TMPDIR", "/tmp")) / "universal-memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_registry_file() -> Path:
    """Default sidecar when serve/desktop persist and the env is unset."""
    return user_data_dir() / "registry.json"


def get_history_dir() -> Path:
    """Per-agent chat transcripts. Survives replacing Universal.app."""
    env = os.environ.get("UNIVERSAL_HISTORY_DIR", "").strip()
    if env:
        path = Path(env)
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = user_data_dir() / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_user_data_dirs() -> dict[str, str]:
    plugins = get_plugins_dir()
    memory = get_memory_dir()
    runtime = get_runtime_dir()
    history = get_history_dir()
    data = user_data_dir()
    return {
        "user_data": str(data),
        "plugins": str(plugins),
        "memory": str(memory),
        "runtime": str(runtime),
        "history": str(history),
        "registry": str(get_registry_file()),
    }
