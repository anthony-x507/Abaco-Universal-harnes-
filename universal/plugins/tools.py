"""Tool-calling plugin: advertise tools to the provider and invoke them."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec


ToolFn = Callable[[dict[str, Any]], str]


@dataclass
class BoundTool:
    spec: ToolSpec
    fn: ToolFn


def utc_now_tool() -> BoundTool:
    """Real built-in tool: current UTC timestamp. No network, no secrets."""

    def _run(_args: dict[str, Any]) -> str:
        return datetime.now(timezone.utc).isoformat()

    return BoundTool(
        spec=ToolSpec(
            name="utc_now",
            description="Return the current time in UTC as an ISO-8601 timestamp.",
            parameters={"type": "object", "properties": {}},
        ),
        fn=_run,
    )


@dataclass
class ToolBeltPlugin(Plugin):
    """Holds named tools. Install or hot-swap onto a running agent."""

    tools_list: list[BoundTool] = field(default_factory=list)
    _name: str = "tools"

    @property
    def name(self) -> str:
        return self._name

    def add(self, tool: BoundTool) -> None:
        self.tools_list.append(tool)

    def tools(self) -> list[ToolSpec]:
        return [tool.spec for tool in self.tools_list]

    def invoke_tool(self, call: ToolCall) -> str | None:
        for tool in self.tools_list:
            if tool.spec.name == call.name:
                try:
                    args = json.loads(call.arguments or "{}")
                    if not isinstance(args, dict):
                        args = {}
                except json.JSONDecodeError:
                    args = {}
                return tool.fn(args)
        return None
