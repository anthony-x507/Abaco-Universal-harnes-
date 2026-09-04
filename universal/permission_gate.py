"""Native permission gate. The signed core is the only place that can grant."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

ENV_MODE = "UNIVERSAL_PERMISSION_MODE"
ENV_GRANT = "UNIVERSAL_PERMISSION_GRANT"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    granted: bool
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"granted": self.granted, "reason": self.reason}


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _truncate(text: str, limit: int = 700) -> str:
    raw = " ".join(text.split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1] + "…"


def ask_permission(
    *,
    action: str,
    details: str = "",
    agent: str = "Runtime",
    rule_id: str | None = None,
) -> PermissionDecision:
    """Ask the user. Tests can force allow/deny with UNIVERSAL_PERMISSION_MODE."""
    if rule_id:
        from universal.rules import is_enforced

        if not is_enforced(rule_id):
            return PermissionDecision(True, f"rule {rule_id} is not enforced")
    mode = os.environ.get(ENV_MODE, "").strip().lower()
    if mode == "allow" or os.environ.get(ENV_GRANT, "").strip() == "1":
        return PermissionDecision(True, "allowed by environment")
    if mode == "deny":
        return PermissionDecision(False, "denied by environment")

    if sys.platform == "darwin":
        return _ask_macos(action=action, details=details, agent=agent)

    return PermissionDecision(False, "no native dialog on this OS; set UNIVERSAL_PERMISSION_MODE=allow")


def _ask_macos(*, action: str, details: str, agent: str) -> PermissionDecision:
    title = _escape_applescript("Universal platform — permission")
    heading = _escape_applescript(_truncate(f"{agent} needs permission", 80))
    body = _escape_applescript(_truncate(f"{action}\n\n{details}".strip(), 900))
    script = (
        f'display dialog "{heading}" & return & return & "{body}" '
        f'buttons {{"Deny", "Allow"}} default button "Deny" '
        f'with title "{title}" with icon caution'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PermissionDecision(False, f"dialog failed: {exc}")
    if result.returncode != 0:
        return PermissionDecision(False, "user dismissed the dialog")
    return PermissionDecision("Allow" in (result.stdout or ""), "macos dialog")
