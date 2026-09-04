"""Native Sentinel Proof tools. Roles are stages, not extra templates."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args
from universal.proof import (
    challenge,
    draft_contract,
    latest_for_agent,
    load_proof,
    record_oracle,
    seal,
    summarize,
)


class ProofPlugin(Plugin):
    def __init__(self) -> None:
        self._agent_id = ""
        self._agent_name = ""

    @property
    def name(self) -> str:
        return "proof"

    def on_attach(self, agent: object) -> None:
        self._agent_id = str(getattr(agent, "id", "") or "")
        self._agent_name = str(getattr(agent, "name", "") or "")

    def on_detach(self, agent: object) -> None:  # noqa: ARG002
        self._agent_id = ""
        self._agent_name = ""

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="draft_contract",
                description="Write atomic requirements for the current objective. This is the contract agent role.",
                parameters={
                    "type": "object",
                    "properties": {
                        "objective": {"type": "string"},
                        "requirements": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["objective", "requirements"],
                },
            ),
            ToolSpec(
                name="record_oracle",
                description="Record an independent check for one requirement. passed must be true only if you actually checked.",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirement_id": {"type": "string"},
                        "passed": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["requirement_id", "passed", "evidence"],
                },
            ),
            ToolSpec(
                name="challenge_requirement",
                description="Adversary role: mutate the claim. still_holds is false if the mutation breaks it.",
                parameters={
                    "type": "object",
                    "properties": {
                        "requirement_id": {"type": "string"},
                        "mutation": {"type": "string"},
                        "still_holds": {"type": "boolean"},
                    },
                    "required": ["requirement_id", "mutation", "still_holds"],
                },
            ),
            ToolSpec(
                name="seal_proof",
                description="Deterministic reducer. Seals only if every oracle passed and every challenge still holds. HMAC, not quantum.",
                parameters={"type": "object", "properties": {}},
            ),
            ToolSpec(
                name="proof_status",
                description="Show the latest proof bundle for this agent.",
                parameters={"type": "object", "properties": {}},
            ),
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name not in {
            "draft_contract",
            "record_oracle",
            "challenge_requirement",
            "seal_proof",
            "proof_status",
        }:
            return None
        if not self._agent_id:
            return "error: proof is not attached to an agent"
        args = parse_tool_args(call)
        if call.name == "draft_contract":
            objective = str(args.get("objective") or "").strip()
            raw = args.get("requirements") or []
            reqs = [str(item).strip() for item in raw if str(item).strip()] if isinstance(raw, list) else []
            try:
                bundle = draft_contract(
                    self._agent_id,
                    objective=objective,
                    requirements=reqs,
                    agent_name=self._agent_name,
                )
            except ValueError as exc:
                return f"error: {exc}"
            return json.dumps(summarize(bundle), indent=2)
        bundle = latest_for_agent(self._agent_id)
        if bundle is None:
            return "error: no proof draft for this agent"
        proof_id = str(bundle["id"])
        try:
            if call.name == "record_oracle":
                bundle = record_oracle(
                    proof_id,
                    requirement_id=str(args.get("requirement_id") or ""),
                    passed=bool(args.get("passed")),
                    evidence=str(args.get("evidence") or ""),
                )
            elif call.name == "challenge_requirement":
                bundle = challenge(
                    proof_id,
                    requirement_id=str(args.get("requirement_id") or ""),
                    mutation=str(args.get("mutation") or ""),
                    still_holds=bool(args.get("still_holds")),
                )
            elif call.name == "seal_proof":
                bundle = seal(proof_id)
            else:
                loaded = load_proof(proof_id)
                bundle = loaded or bundle
        except (KeyError, ValueError) as exc:
            return f"error: {exc}"
        return json.dumps(summarize(bundle), indent=2)
