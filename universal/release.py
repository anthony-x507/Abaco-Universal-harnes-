"""Release metadata. ``version.json`` is baked into the app; no env override for the repo."""

from __future__ import annotations

import json
from pathlib import Path

from universal._version import __version__
from universal.web_dist import resource_root

BAKED_REPO = "anthony-x507/Abaco-Universal-harnes-"
DEFAULT_NOTES = "Native Mac app. Download Universal.dmg only."


def version_file() -> Path:
    return resource_root() / "version.json"


def load_release() -> dict[str, str]:
    path = version_file()
    data: dict[str, str] = {
        "version": __version__,
        "release_notes": DEFAULT_NOTES,
        "repo": BAKED_REPO,
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
    return data


def current_version() -> str:
    return load_release()["version"]
