"""Local shell access for the owner’s own harness."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args

_DENIED: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-[a-z-]*r[a-z-]*f[a-z-]*\s+/", re.I),
    re.compile(r"\brm\s+-[a-z-]*f[a-z-]*r[a-z-]*\s+/", re.I),
    re.compile(r"\bmkfs(?:\.\w+)?\b", re.I),
    re.compile(r"\bdd\b.*\bof=", re.I),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:", re.I),
    re.compile(r"\b(?:shutdown|reboot|halt|poweroff)\b", re.I),
)

DEFAULT_TIMEOUT = 15.0


class TerminalPlugin(Plugin):
    """Run a local command and return stdout/stderr."""

    def __init__(self) -> None:
        self._name = "terminal"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="run_command",
                description="Execute a local shell command and return its output.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"},
                    },
                    "required": ["command"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "run_command":
            return None
        args = parse_tool_args(call)
        command = str(args.get("command") or "").strip()
        if not command:
            return "Error: command is required"
        return self._run(command)

    def _run(self, command: str) -> str:
        reason = self._denied_reason(command)
        if reason:
            return f"Error: {reason}"
        cwd = os.environ.get("UNIVERSAL_TERMINAL_DIR") or os.getcwd()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
                cwd=str(Path(cwd)),
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {int(DEFAULT_TIMEOUT)}s"
        except OSError as exc:
            return f"Error: {exc}"
        parts: list[str] = []
        if result.stdout:
            parts.append(result.stdout.rstrip())
        if result.stderr:
            parts.append("[stderr]\n" + result.stderr.rstrip())
        if result.returncode != 0:
            parts.append(f"[exit {result.returncode}]")
        return "\n".join(parts) if parts else "[no output]"

    @staticmethod
    def _denied_reason(command: str) -> str | None:
        compact = " ".join(command.split())
        for pattern in _DENIED:
            if pattern.search(compact):
                return "refusing a destructive or system-control command"
        return None
