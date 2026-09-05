"""Let the agent change non-core files after an explicit allow."""

from __future__ import annotations

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args
from universal.self_modify import apply_self_modify


class SelfModifyPlugin(Plugin):
    def __init__(self) -> None:
        self._name = "self_modify"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="self_modify",
                description=(
                    "Change the agent's own plugin or helper file after the user allows it. "
                    "Never AgentRegistry, AgentLifecycle, or AgentFactory."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to change"},
                        "new_content": {"type": "string", "description": "New file contents"},
                        "reason": {"type": "string", "description": "Why this change is needed"},
                    },
                    "required": ["file_path", "new_content", "reason"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "self_modify":
            return None
        args = parse_tool_args(call)
        result = apply_self_modify(
            file_path=str(args.get("file_path") or ""),
            new_content=str(args.get("new_content") or ""),
            reason=str(args.get("reason") or ""),
        )
        if result.get("ok"):
            return f"Updated {result.get('file')}"
        return f"Error: {result.get('error')}"
