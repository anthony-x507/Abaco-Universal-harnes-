"""Permission-gated writes. The signed core stays off-limits."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from universal.permission_gate import ask_permission
from universal.rules import is_enforced

CORE_MARKERS = (
    "universal/core/",
    "universal/core.py",
    "universal/agent.py",
    "/registry.py",
    "/lifecycle.py",
    "/factory.py",
    "/platform.py",
    "agentregistry",
    "agentlifecycle",
    "agentfactory",
)


def _blocked_core(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    return any(marker in lowered for marker in CORE_MARKERS)


def apply_self_modify(
    *,
    file_path: str,
    new_content: str,
    reason: str,
    agent: str = "self_modify",
) -> dict[str, Any]:
    """Write a non-core file after the user allows it."""
    dest = (file_path or "").strip()
    if not dest:
        return {"ok": False, "error": "file_path is required"}
    if _blocked_core(dest):
        return {"ok": False, "error": "Cannot modify the Universal core (registry, lifecycle, factory)."}
    if not is_enforced("self_modify_allowed"):
        return {"ok": False, "error": "self_modify_allowed is off."}
    decision = ask_permission(
        action="The agent wants to change its own code",
        details=f"File: {dest}\nReason: {reason}",
        agent=agent,
        rule_id="ask_before_self_modify",
    )
    if not decision.granted:
        return {"ok": False, "error": f"Change blocked ({decision.reason})."}
    path = Path(dest)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content, encoding="utf-8")
    return {"ok": True, "file": str(path), "reason": reason}
