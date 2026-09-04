"""Per-agent mission state. Not the lifecycle ``AgentState``.

Keyed by agent id under user data so it survives replacing Universal.app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from universal.paths import user_data_dir

MAX_ATTEMPTS = 3


class MissionPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    BLOCKED = "blocked"
    DEVIATING = "deviating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    SEALED = "sealed"


def situation_dir() -> Path:
    path = user_data_dir() / "situation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def situation_path(agent_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in agent_id)[:80] or "agent"
    return situation_dir() / f"{safe}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Situation:
    agent_id: str
    agent_name: str = ""
    phase: MissionPhase = MissionPhase.IDLE
    objective: str = ""
    current_step: str = ""
    steps: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    obstacles: list[dict[str, str]] = field(default_factory=list)
    deviations: list[dict[str, str]] = field(default_factory=list)
    alternatives: list[dict[str, str]] = field(default_factory=list)
    attempts: int = 0
    team: str = ""
    last_checkpoint: str = ""
    proof_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        remaining = [step for step in self.steps if step not in self.completed]
        return {
            "agent_id": self.agent_id,
            "agent": self.agent_name or self.agent_id,
            "phase": self.phase.value,
            "objective": self.objective,
            "current_step": self.current_step,
            "steps_remaining": remaining,
            "steps_completed": list(self.completed),
            "steps_blocked": list(self.blocked),
            "obstacles": list(self.obstacles),
            "deviations": list(self.deviations),
            "alternatives": list(self.alternatives),
            "attempts": self.attempts,
            "max_attempts": MAX_ATTEMPTS,
            "team": self.team or None,
            "last_checkpoint": self.last_checkpoint or None,
            "proof_id": self.proof_id or None,
        }

    def save(self) -> None:
        path = situation_path(self.agent_id)
        payload = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "phase": self.phase.value,
            "objective": self.objective,
            "current_step": self.current_step,
            "steps": self.steps,
            "completed": self.completed,
            "blocked": self.blocked,
            "obstacles": self.obstacles,
            "deviations": self.deviations,
            "alternatives": self.alternatives,
            "attempts": self.attempts,
            "team": self.team,
            "last_checkpoint": self.last_checkpoint,
            "proof_id": self.proof_id,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, agent_id: str, *, agent_name: str = "") -> Situation:
        path = situation_path(agent_id)
        if not path.is_file():
            return cls(agent_id=agent_id, agent_name=agent_name)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls(agent_id=agent_id, agent_name=agent_name)
        if not isinstance(raw, dict):
            return cls(agent_id=agent_id, agent_name=agent_name)
        try:
            phase = MissionPhase(str(raw.get("phase") or "idle"))
        except ValueError:
            phase = MissionPhase.IDLE
        return cls(
            agent_id=agent_id,
            agent_name=str(raw.get("agent_name") or agent_name),
            phase=phase,
            objective=str(raw.get("objective") or ""),
            current_step=str(raw.get("current_step") or ""),
            steps=[str(item) for item in (raw.get("steps") or [])],
            completed=[str(item) for item in (raw.get("completed") or [])],
            blocked=[str(item) for item in (raw.get("blocked") or [])],
            obstacles=[item for item in (raw.get("obstacles") or []) if isinstance(item, dict)],
            deviations=[item for item in (raw.get("deviations") or []) if isinstance(item, dict)],
            alternatives=[item for item in (raw.get("alternatives") or []) if isinstance(item, dict)],
            attempts=int(raw.get("attempts") or 0),
            team=str(raw.get("team") or ""),
            last_checkpoint=str(raw.get("last_checkpoint") or ""),
            proof_id=str(raw.get("proof_id") or ""),
        )

    def set_objective(self, objective: str) -> None:
        self.objective = objective.strip()
        self.phase = MissionPhase.PLANNING
        self.attempts = 0
        self.save()

    def set_steps(self, steps: list[str], *, team: str = "") -> None:
        self.steps = [step.strip() for step in steps if str(step).strip()]
        self.completed = []
        self.blocked = []
        self.current_step = self.steps[0] if self.steps else ""
        if team:
            self.team = team
        self.phase = MissionPhase.EXECUTING if self.steps else MissionPhase.PLANNING
        self.save()

    def complete_step(self, step: str) -> None:
        name = step.strip()
        if name and name not in self.completed:
            self.completed.append(name)
        if name in self.blocked:
            self.blocked = [item for item in self.blocked if item != name]
        remaining = [item for item in self.steps if item not in self.completed]
        self.current_step = remaining[0] if remaining else ""
        if remaining:
            self.phase = MissionPhase.EXECUTING
        else:
            from universal.proof import is_sealed
            from universal.rules import is_enforced

            if is_enforced("sentinel_proof_required") and not is_sealed(self.agent_id):
                self.phase = MissionPhase.VERIFYING
            else:
                self.phase = MissionPhase.COMPLETED
        self.save()

    def report_obstacle(self, step: str, obstacle: str) -> None:
        self.obstacles.append({"step": step, "obstacle": obstacle, "at": _now()})
        if step and step not in self.blocked:
            self.blocked.append(step)
        self.attempts += 1
        self.phase = MissionPhase.FAILED if self.attempts >= MAX_ATTEMPTS else MissionPhase.BLOCKED
        self.save()

    def report_deviation(self, reason: str, from_step: str, to_step: str) -> None:
        self.deviations.append({"from": from_step, "to": to_step, "reason": reason, "at": _now()})
        if to_step:
            self.current_step = to_step
        self.phase = MissionPhase.DEVIATING
        self.save()

    def add_alternative(self, step: str, path: str) -> None:
        self.alternatives.append({"step": step, "path": path, "at": _now()})
        self.save()

    def checkpoint(self) -> None:
        self.last_checkpoint = _now()
        self.save()

    def reset(self) -> None:
        self.phase = MissionPhase.IDLE
        self.objective = ""
        self.current_step = ""
        self.steps = []
        self.completed = []
        self.blocked = []
        self.obstacles = []
        self.deviations = []
        self.alternatives = []
        self.attempts = 0
        self.team = ""
        self.last_checkpoint = ""
        self.proof_id = ""
        self.save()


def discard_situation(agent_id: str) -> None:
    try:
        situation_path(agent_id).unlink(missing_ok=True)
    except OSError:
        return
