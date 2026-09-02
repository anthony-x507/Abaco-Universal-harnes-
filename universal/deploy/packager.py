"""ZIP packager — enough to export an agent in v1. No secrets in the archive."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from universal._version import __version__
from universal.core.agent import Agent
from universal.core.types import AgentState
from universal.exceptions import DeployError


class ZipPackager:
    """Writes a portable ZIP: manifest, system prompt, public config."""

    def pack(
        self,
        agent: Agent,
        dest: Path | None = None,
        *,
        state: AgentState | None = None,
    ) -> Path:
        dest = Path(dest) if dest is not None else Path(f"{agent.name}-{agent.id}.zip")
        dest = dest.expanduser()
        if dest.is_dir():
            dest = dest / f"{agent.name}-{agent.id}.zip"
        dest.parent.mkdir(parents=True, exist_ok=True)

        info = agent.info(state or AgentState.CREATED)
        manifest = {
            "universal_version": __version__,
            "product": "Universal platform",
            "agent": info.to_dict(),
            "system_prompt": agent.system_prompt,
            "plugins": agent.plugins.snapshot(),
        }
        # Provider settings are not on the agent; record only the model id.
        config = {
            "model": info.model,
            "template_id": agent.template_id,
            "note": "API keys are never written into a Universal package.",
        }

        try:
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
                archive.writestr("config.json", json.dumps(config, indent=2) + "\n")
                archive.writestr("system_prompt.txt", agent.system_prompt + "\n")
                archive.writestr(
                    "README.txt",
                    (
                        f"Universal platform agent package\n"
                        f"name={agent.name}\n"
                        f"id={agent.id}\n"
                        f"template={agent.template_id}\n"
                        f"Unpack and recreate with: universal create {agent.template_id} "
                        f"--name {agent.name}\n"
                    ),
                )
        except OSError as exc:
            raise DeployError(f"Failed to write package {dest}: {exc}") from exc
        return dest
