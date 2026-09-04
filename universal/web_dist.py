"""Locate the built SPA (``web/dist``) for serve and the desktop wrapper."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """Repo root in source; PyInstaller extract dir when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resolve_web_dist() -> Path | None:
    """Return the directory that contains ``index.html``, or None."""
    candidates: list[Path] = []
    env = os.environ.get("UNIVERSAL_WEB_DIST", "").strip()
    if env:
        candidates.append(Path(env))
    root = resource_root()
    candidates.append(root / "web" / "dist")
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "index.html").is_file():
            return resolved
    return None
