"""Release metadata. ``_version.py`` is the source of truth."""

from __future__ import annotations

import json
from pathlib import Path

from universal._version import __version__
from universal.web_dist import resource_root

DEFAULT_NOTES = (
    "Native plugins, desktop wrapper, and GitHub update check. "
    "Whisper remains an optional extra."
)


def version_file() -> Path:
    return resource_root() / "version.json"


def load_release() -> dict[str, str]:
    path = version_file()
    data: dict[str, str] = {
        "version": __version__,
        "release_notes": DEFAULT_NOTES,
        "repo": "",
    }
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = {}
        if isinstance(loaded, dict):
            if loaded.get("version"):
                data["version"] = str(loaded["version"])
            if loaded.get("release_notes"):
                data["release_notes"] = str(loaded["release_notes"])
            if loaded.get("repo"):
                data["repo"] = str(loaded["repo"])
    env_repo = __import__("os").environ.get("UNIVERSAL_UPDATE_REPO", "").strip()
    if env_repo:
        data["repo"] = env_repo
    return data


def current_version() -> str:
    return load_release()["version"]
