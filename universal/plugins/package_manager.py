"""Install pip / npm / brew packages with an explicit user allow."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.packages import run_package_manager
from universal.plugins._support import parse_tool_args


class PackageManagerPlugin(Plugin):
    def __init__(self) -> None:
        self._name = "package_manager"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="package_manager",
                description=(
                    "Install, uninstall, or list a package with pip, npm, or brew. "
                    "The user must allow install/uninstall. Prefer this over inventing a missing tool."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["install", "uninstall", "list"],
                            "description": "Action",
                        },
                        "package": {"type": "string", "description": "Package name"},
                        "manager": {
                            "type": "string",
                            "enum": ["pip", "npm", "brew"],
                            "description": "Package manager",
                        },
                    },
                    "required": ["action", "manager"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "package_manager":
            return None
        args = parse_tool_args(call)
        result = run_package_manager(
            action=str(args.get("action") or ""),
            package=str(args.get("package") or ""),
            manager=str(args.get("manager") or ""),
        )
        if result.get("ok"):
            return f"Package {result.get('package') or ''} {result.get('action')}:\n{result.get('output')}"
        return f"Error: {result.get('error')}"
