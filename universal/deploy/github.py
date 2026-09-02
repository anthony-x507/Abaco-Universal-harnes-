"""GitHub deploy — stub interface for v1. ZIP packager is the working target."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeployResult:
    ok: bool
    message: str
    url: str = ""


class GitHubDeployTarget:
    """Reserved interface. Not implemented in v1 — use :class:`ZipPackager`."""

    def deploy(self, archive: Path) -> DeployResult:
        return DeployResult(
            ok=False,
            message=(
                "GitHub deploy is deferred. Use the ZIP packager (target='zip'). "
                f"No archive was written for {archive}."
            ),
        )
