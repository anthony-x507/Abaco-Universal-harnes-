"""Install pip / npm / brew packages after the signed permission gate."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import Any

from universal.permission_gate import ask_permission
from universal.rules import is_enforced

MANAGERS = ("pip", "npm", "brew")
ACTIONS = ("install", "uninstall", "list")
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@+/=\-]*$")
TIMEOUT = 120.0


def _argv(manager: str, action: str, package: str) -> list[str]:
    if manager == "pip":
        cmd = [sys.executable, "-m", "pip", action]
        if package:
            cmd.append(package)
        return cmd
    if manager == "npm":
        cmd = ["npm", action]
        if package:
            cmd.append(package)
        return cmd
    cmd = ["brew", action]
    if package:
        cmd.append(package)
    return cmd


def run_package_manager(*, action: str, package: str, manager: str, agent: str = "package_manager") -> dict[str, Any]:
    action = action.strip().lower()
    manager = manager.strip().lower()
    package = package.strip()
    if action not in ACTIONS:
        return {"ok": False, "error": f"action must be one of {', '.join(ACTIONS)}"}
    if manager not in MANAGERS:
        return {"ok": False, "error": f"manager must be one of {', '.join(MANAGERS)}"}
    if action != "list" and not package:
        return {"ok": False, "error": "package is required"}
    if package and not PACKAGE_RE.match(package):
        return {"ok": False, "error": "package name is not allowed"}
    if not is_enforced("allow_self_install") or not is_enforced("install_packages_allowed"):
        return {"ok": False, "error": "allow_self_install is off. The agent may not install packages."}
    if action != "list":
        decision = ask_permission(
            action=f"The agent wants to {action} “{package}” with {manager}",
            details=" ".join(_argv(manager, action, package)),
            agent=agent,
            rule_id="allow_self_install",
        )
        if not decision.granted:
            return {"ok": False, "error": f"Installation blocked ({decision.reason})."}
    binary = "pip" if manager == "pip" else manager
    if manager != "pip" and shutil.which(binary) is None:
        return {"ok": False, "error": f"{manager} is not installed on this machine."}
    try:
        result = subprocess.run(
            _argv(manager, action, package),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{manager} {action} timed out after {int(TIMEOUT)}s"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode != 0:
        return {"ok": False, "error": output or f"{manager} exited {result.returncode}"}
    return {"ok": True, "manager": manager, "action": action, "package": package, "output": output or "[no output]"}
