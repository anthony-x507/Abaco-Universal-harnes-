"""Situational tools. The agent records where it is; it does not invent a second lifecycle."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.notifications import add_notice
from universal.plugins._support import parse_tool_args
from universal.rules import is_enforced
from universal.situation import Situation


class NavigatorPlugin(Plugin):
    def __init__(self) -> None:
        self._agent_id = ""
        self._agent_name = ""

    @property
    def name(self) -> str:
        return "navigator"

    def on_attach(self, agent: object) -> None:
        self._agent_id = str(getattr(agent, "id", "") or "")
        self._agent_name = str(getattr(agent, "name", "") or "")

    def on_detach(self, agent: object) -> None:  # noqa: ARG002
        self._agent_id = ""
        self._agent_name = ""

    def _status(self) -> Situation:
        return Situation.load(self._agent_id, agent_name=self._agent_name)

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="set_objective",
                description="Set the mission objective. Use this before multi-step work. Never claim you finished it here.",
                parameters={
                    "type": "object",
                    "properties": {"objective": {"type": "string"}},
                    "required": ["objective"],
                },
            ),
            ToolSpec(
                name="plan_steps",
                description="Replace the mission plan with an ordered list of steps toward the objective.",
                parameters={
                    "type": "object",
                    "properties": {
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "team": {"type": "string"},
                    },
                    "required": ["steps"],
                },
            ),
            ToolSpec(
                name="complete_step",
                description="Mark one planned step done. Only call this after the work actually succeeded.",
                parameters={
                    "type": "object",
                    "properties": {"step": {"type": "string"}},
                    "required": ["step"],
                },
            ),
            ToolSpec(
                name="report_obstacle",
                description="Record a blocker and notify the user. Be specific. Do not invent a workaround you cannot run.",
                parameters={
                    "type": "object",
                    "properties": {
                        "step": {"type": "string"},
                        "obstacle": {"type": "string"},
                    },
                    "required": ["step", "obstacle"],
                },
            ),
            ToolSpec(
                name="report_deviation",
                description="Record a change of plan. If the deviations rule is on, this asks the user first.",
                parameters={
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                        "from_step": {"type": "string"},
                        "to_step": {"type": "string"},
                    },
                    "required": ["reason", "from_step", "to_step"],
                },
            ),
            ToolSpec(
                name="suggest_path",
                description="Propose an alternative path for a blocked step. Does not execute it.",
                parameters={
                    "type": "object",
                    "properties": {
                        "step": {"type": "string"},
                        "path": {"type": "string"},
                    },
                    "required": ["step", "path"],
                },
            ),
            ToolSpec(
                name="checkpoint",
                description="Save a mission checkpoint timestamp so work can resume later.",
                parameters={"type": "object", "properties": {}},
            ),
            ToolSpec(
                name="mission_status",
                description="Return the saved mission: objective, current step, blockers, attempts.",
                parameters={"type": "object", "properties": {}},
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name not in {
            "set_objective",
            "plan_steps",
            "complete_step",
            "report_obstacle",
            "report_deviation",
            "suggest_path",
            "checkpoint",
            "mission_status",
        }:
            return None
        if not self._agent_id:
            return "error: navigator is not attached to an agent"
        args = parse_tool_args(call)
        status = self._status()
        if call.name == "set_objective":
            objective = str(args.get("objective") or "").strip()
            if not objective:
                return "error: objective is required"
            status.set_objective(objective)
            return f"Objective set: {objective}"
        if call.name == "plan_steps":
            raw = args.get("steps") or []
            steps = [str(item).strip() for item in raw if str(item).strip()] if isinstance(raw, list) else []
            if not steps:
                return "error: steps must be a non-empty list"
            status.set_steps(steps, team=str(args.get("team") or ""))
            return "Plan: " + " → ".join(steps)
        if call.name == "complete_step":
            step = str(args.get("step") or "").strip()
            if not step:
                return "error: step is required"
            status.complete_step(step)
            if status.phase.value == "completed":
                return f"Step done: {step}. Objective reached: {status.objective}"
            return f"Step done: {step}. Next: {status.current_step}"
        if call.name == "report_obstacle":
            step = str(args.get("step") or "").strip()
            obstacle = str(args.get("obstacle") or "").strip()
            if not step or not obstacle:
                return "error: step and obstacle are required"
            status.report_obstacle(step, obstacle)
            message = (
                f"{self._agent_name or self._agent_id} is blocked on “{step}”: {obstacle}. "
                f"Objective remains: {status.objective or '(none)'}. Attempts: {status.attempts}/{status.to_dict()['max_attempts']}."
            )
            if is_enforced("navigator_auto_notify"):
                add_notice(agent_id=self._agent_id, kind="blocked", message=message)
            if status.phase.value == "failed":
                return f"Blocked and failed after {status.attempts} attempts. Tell the user honestly. {message}"
            return f"Blocked. {message} Suggest a path or ask the user."
        if call.name == "report_deviation":
            reason = str(args.get("reason") or "").strip()
            from_step = str(args.get("from_step") or "").strip()
            to_step = str(args.get("to_step") or "").strip()
            if not reason or not from_step or not to_step:
                return "error: reason, from_step, and to_step are required"
            if is_enforced("navigator_allow_deviations"):
                from universal.permission_gate import ask_permission

                decision = ask_permission(
                    action=f"Change the plan from {from_step!r} to {to_step!r}",
                    details=reason,
                    agent=self._agent_name or "navigator",
                    rule_id="navigator_allow_deviations",
                )
                if not decision.granted:
                    return f"error: deviation denied ({decision.reason})"
            status.report_deviation(reason, from_step, to_step)
            add_notice(
                agent_id=self._agent_id,
                kind="deviation",
                message=f"{self._agent_name or self._agent_id} changed course: {from_step} → {to_step}. {reason}",
            )
            return f"Deviation recorded. Now on: {to_step}. Objective remains: {status.objective or '(none)'}."
        if call.name == "suggest_path":
            step = str(args.get("step") or "").strip()
            path = str(args.get("path") or "").strip()
            if not step or not path:
                return "error: step and path are required"
            status.add_alternative(step, path)
            add_notice(
                agent_id=self._agent_id,
                kind="alternative",
                message=f"Alternative for “{step}”: {path}",
            )
            return f"Alternative stored for {step}. Waiting for the user before taking it."
        if call.name == "checkpoint":
            status.checkpoint()
            return f"Checkpoint saved at {status.last_checkpoint}."
        return json.dumps(status.to_dict(), indent=2)
