"""Native DeepSeek monitor. Calls the factory module, not a Node HTTP loop."""

from __future__ import annotations

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.strategist import format_report, scan_deepseek


class StrategistPlugin(Plugin):
    @property
    def name(self) -> str:
        return "strategist"

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="deepseek_monitor",
                description="Scan official DeepSeek Harness GitHub repos and compare them with Universal. Not a Twitter feed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "refresh": {
                            "type": "boolean",
                            "description": "If true, hit GitHub again. If false, return the last saved report.",
                        }
                    },
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "deepseek_monitor":
            return None
        from universal.plugins._support import parse_tool_args

        args = parse_tool_args(call)
        refresh = bool(args.get("refresh")) if "refresh" in args else True
        return format_report(scan_deepseek(refresh=refresh))
