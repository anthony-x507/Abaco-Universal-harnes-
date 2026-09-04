"""Ensure user-data dirs exist. Native plugins stay in the package catalog.

Copying ``*.py`` into Application Support would be a second plugin loader
(the factory does not import user-writable code). Persistence across
updates is the registry sidecar + memory files + this manifest.
"""

from __future__ import annotations

import json

from universal.exceptions import PluginError
from universal.paths import ensure_user_data_dirs, get_plugins_dir
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES, catalog
from universal.release import current_version


def ensure_plugins_installed() -> list[str]:
    ensure_user_data_dirs()
    missing = [name for name in NATIVE_PLUGIN_NAMES if name not in catalog.ids()]
    if missing:
        raise PluginError(f"Native plugins missing from catalog: {', '.join(missing)}")
    manifest = get_plugins_dir() / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": current_version(),
                "plugins": list(NATIVE_PLUGIN_NAMES),
                "note": "Code is loaded from the Universal package, not from this folder.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return list(NATIVE_PLUGIN_NAMES)
