"""Coordinate existing agents. Does not create a mother template."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.notifications import add_notice
from universal.permission_gate import ask_permission
from universal.plugins._support import parse_tool_args
from universal.rules import is_enforced
from universal.situation import Situation
from universal.teams import add_note, checkpoint_team, create_team, delegate, load_team


class TeamPlugin(Plugin):
    def __init__(self) -> None:
        self._agent_id = ""
        self._agent_name = ""

    @property
    def name(self) -> str:
        return "team"

    def on_attach(self, agent: object) -> None:
        self._agent_id = str(getattr(agent, "id", "") or "")
        self._agent_name = str(getattr(agent, "name", "") or "")

    def on_detach(self, agent: object) -> None:  # noqa: ARG002
        self._agent_id = ""
        self._agent_name = ""

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="create_team",
                description="Group existing agent ids into a named team. Does not create new agents.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "member_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "member_ids"],
                },
            ),
            ToolSpec(
                name="delegate_task",
                description="Ask another existing team member to handle a task through its own accept path.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "task": {"type": "string"},
                        "team": {"type": "string"},
                    },
                    "required": ["agent_id", "task"],
                },
            ),
            ToolSpec(
                name="team_status",
                description="Show saved team members, notes count, and checkpoint.",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            ToolSpec(
                name="team_checkpoint",
                description="Save a resume point for a team.",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            ToolSpec(
                name="share_note",
                description="Attach a short note to a team. Asks first when memory sharing is enforced.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["name", "text"],
                },
            ),
            ToolSpec(
                name="read_team_notes",
                description="Read notes already shared on a team.",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name not in {
            "create_team",
            "delegate_task",
            "team_status",
            "team_checkpoint",
            "share_note",
            "read_team_notes",
        }:
            return None
        args = parse_tool_args(call)
        if call.name == "create_team":
            name = str(args.get("name") or "").strip()
            raw = args.get("member_ids") or []
            ids = [str(item).strip() for item in raw if str(item).strip()] if isinstance(raw, list) else []
            if not name or not ids:
                return "error: name and member_ids are required"
            members = [{"id": item} for item in ids]
            if self._agent_id and self._agent_id not in ids:
                members.append({"id": self._agent_id})
            team = create_team(name, members)
            sit = Situation.load(self._agent_id, agent_name=self._agent_name)
            sit.team = name
            sit.save()
            return f"Team {name} has {len(team['members'])} members."
        if call.name == "delegate_task":
            target = str(args.get("agent_id") or "").strip()
            task = str(args.get("task") or "").strip()
            if not target or not task:
                return "error: agent_id and task are required"
            if target == self._agent_id:
                return "error: delegate to another agent, not yourself"
            answer = delegate(target, task)
            team_name = str(args.get("team") or "").strip()
            add_notice(
                agent_id=self._agent_id,
                kind="delegate",
                message=f"{self._agent_name or self._agent_id} asked {target} to: {task}",
            )
            if team_name:
                sit = Situation.load(target)
                sit.team = team_name
                sit.save()
            return answer
        if call.name == "team_status":
            name = str(args.get("name") or "").strip()
            team = load_team(name)
            if team is None:
                return f"error: team {name!r} not found"
            return json.dumps(team, indent=2)
        if call.name == "team_checkpoint":
            name = str(args.get("name") or "").strip()
            try:
                team = checkpoint_team(name)
            except KeyError:
                return f"error: team {name!r} not found"
            return f"Team checkpoint at {team.get('last_checkpoint')}"
        if call.name == "share_note":
            name = str(args.get("name") or "").strip()
            text = str(args.get("text") or "").strip()
            if not name or not text:
                return "error: name and text are required"
            if is_enforced("memory_share_between_agents"):
                decision = ask_permission(
                    action=f"Share a note with team {name}",
                    details=text,
                    agent=self._agent_name or "team",
                    rule_id="memory_share_between_agents",
                )
                if not decision.granted:
                    return f"error: sharing denied ({decision.reason})"
            try:
                add_note(name, agent_id=self._agent_id, text=text)
            except KeyError:
                return f"error: team {name!r} not found"
            return "Note shared with the team."
        name = str(args.get("name") or "").strip()
        team = load_team(name)
        if team is None:
            return f"error: team {name!r} not found"
        return json.dumps(team.get("notes") or [], indent=2)
