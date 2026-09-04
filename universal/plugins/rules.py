"""Signed-core rule list. The factory, not Node, is the supervisor."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args
from universal.rules import is_enforced, load_rules


class RuleEnforcerPlugin(Plugin):
    def __init__(self) -> None:
        self._name = "rule_enforcer"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="list_rules",
                description="List governance rules and whether each one is enforced.",
                parameters={"type": "object", "properties": {}},
            ),
            ToolSpec(
                name="check_rule",
                description="Check whether a named governance rule is currently enforced.",
                parameters={
                    "type": "object",
                    "properties": {
                        "rule_id": {
                            "type": "string",
                            "description": "Rule id such as no_purchase_without_permission",
                        }
                    },
                    "required": ["rule_id"],
                },
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name == "list_rules":
            return json.dumps([rule.to_dict() for rule in load_rules()], indent=2)
        if call.name != "check_rule":
            return None
        args = parse_tool_args(call)
        rule_id = str(args.get("rule_id") or "").strip()
        if not rule_id:
            return "Error: rule_id is required"
        return json.dumps({"rule_id": rule_id, "enforced": is_enforced(rule_id)})
