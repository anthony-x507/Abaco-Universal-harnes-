"""Native visible-improvement tools. Stages stay on the same agent."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.improvement import decide, list_proposals, propose
from universal.plugins._support import parse_tool_args


class ImprovementPlugin(Plugin):
    def __init__(self) -> None:
        self._agent_id = ""
        self._agent_name = ""

    @property
    def name(self) -> str:
        return "improvement"

    def on_attach(self, agent: object) -> None:
        self._agent_id = str(getattr(agent, "id", "") or "")
        self._agent_name = str(getattr(agent, "name", "") or "")

    def on_detach(self, agent: object) -> None:  # noqa: ARG002
        self._agent_id = ""
        self._agent_name = ""

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="propose_improvement",
                description="Propose a better plan for a task. The user must accept before you switch plans.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "proposed_plan": {"type": "string"},
                        "original_plan": {"type": "string"},
                    },
                    "required": ["task", "proposed_plan"],
                },
            ),
            ToolSpec(
                name="accept_improvement",
                description="Record that the user accepted a pending improvement (use the proposal id).",
                parameters={
                    "type": "object",
                    "properties": {"proposal_id": {"type": "string"}},
                    "required": ["proposal_id"],
                },
            ),
            ToolSpec(
                name="reject_improvement",
                description="Record that the user rejected a pending improvement.",
                parameters={
                    "type": "object",
                    "properties": {"proposal_id": {"type": "string"}},
                    "required": ["proposal_id"],
                },
            ),
            ToolSpec(
                name="list_improvements",
                description="List improvement proposals for this agent.",
                parameters={"type": "object", "properties": {}},
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name not in {
            "propose_improvement",
            "accept_improvement",
            "reject_improvement",
            "list_improvements",
        }:
            return None
        if not self._agent_id:
            return "error: improvement is not attached to an agent"
        args = parse_tool_args(call)
        try:
            if call.name == "propose_improvement":
                row = propose(
                    self._agent_id,
                    task=str(args.get("task") or ""),
                    proposed_plan=str(args.get("proposed_plan") or ""),
                    original_plan=str(args.get("original_plan") or ""),
                    agent_name=self._agent_name,
                )
                return json.dumps(row, indent=2)
            if call.name == "list_improvements":
                return json.dumps(list_proposals(self._agent_id), indent=2)
            proposal_id = str(args.get("proposal_id") or "")
            row = decide(proposal_id, accepted=call.name == "accept_improvement")
            return json.dumps(row, indent=2)
        except PermissionError as exc:
            return f"error: {exc}"
        except KeyError:
            return "error: proposal not found"
        except ValueError as exc:
            return f"error: {exc}"
