"""Factory routes for the Node runtime. Not a Chat Completions clone."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from universal.core.types import Message, ToolCall, ToolSpec
from universal.exceptions import ConfigError
from universal.permission_gate import ask_permission
from universal.runtime_manager import default_manager


class LlmCompleteBody(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    model: str | None = None


class PermissionBody(BaseModel):
    action: str = "The runtime wants to do something"
    details: str = ""
    agent: str = "Runtime"
    rule_id: str | None = None


class WalletSaveBody(BaseModel):
    card_name: str
    card_number: str
    expiry: str
    cvv: str


class WalletDeleteBody(BaseModel):
    card_name: str


class WalletBuyBody(BaseModel):
    card_name: str
    amount: float
    merchant: str


class TorBody(BaseModel):
    action: str = "navegar"
    url: str = ""
    query: str = ""
    timeout: int = 30


class PackageBody(BaseModel):
    action: str
    package: str = ""
    manager: str


class EvolveBody(BaseModel):
    target_file: str
    new_code: str
    reason: str = "Proposed by the evolvable runtime"
    agent: str = "evolution"


class ThinkBody(BaseModel):
    prompt: str
    agent_id: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


def _messages_from_body(raw: list[dict[str, Any]]) -> list[Message]:
    messages: list[Message] = []
    for item in raw:
        role = str(item.get("role") or "user")
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        content = item.get("content")
        if not isinstance(content, str):
            content = "" if content is None else json.dumps(content)
        calls_raw = item.get("tool_calls") or []
        tool_calls: list[ToolCall] | None = None
        if isinstance(calls_raw, list) and calls_raw:
            tool_calls = []
            for call in calls_raw:
                if not isinstance(call, dict):
                    continue
                fn = call.get("function") if isinstance(call.get("function"), dict) else call
                arguments = fn.get("arguments") if isinstance(fn, dict) else "{}"
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                tool_calls.append(
                    ToolCall(
                        id=str(call.get("id") or "tool"),
                        name=str((fn or {}).get("name") or call.get("name") or "tool"),
                        arguments=arguments,
                    )
                )
        messages.append(
            Message(
                role=role,  # type: ignore[arg-type]
                content=content,
                tool_call_id=str(item["tool_call_id"]) if item.get("tool_call_id") else None,
                tool_calls=tool_calls,
            )
        )
    return messages


def _tools_from_body(raw: list[dict[str, Any]]) -> list[ToolSpec]:
    specs: list[ToolSpec] = []
    for item in raw:
        name = str(item.get("name") or "")
        if not name:
            continue
        parameters = item.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {"type": "object", "properties": {}}
        specs.append(
            ToolSpec(
                name=name,
                description=str(item.get("description") or ""),
                parameters=parameters,
            )
        )
    return specs


def register_runtime_routes(app: FastAPI, state: Any) -> None:
    @app.get("/v1/runtime")
    def runtime_status() -> dict[str, Any]:
        return default_manager().status()

    @app.get("/v1/runtime/plugins")
    def runtime_plugins() -> dict[str, Any]:
        return {"plugins": default_manager().list_plugins()}

    @app.post("/v1/llm/complete")
    def llm_complete(body: LlmCompleteBody) -> dict[str, Any]:
        """Internal bridge: Node asks the signed core to talk to the one provider."""
        if not state.demo:
            state.platform.settings.require_live()
        messages = _messages_from_body(body.messages)
        tools = _tools_from_body(body.tools) or None
        response = state.platform.provider().complete(messages, tools=tools, model=body.model)
        return {
            "content": response.text,
            "tool_calls": [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ],
            "model": response.model,
            "finish_reason": response.finish_reason,
        }

    @app.get("/v1/rules")
    def get_rules() -> dict[str, Any]:
        from universal.rules import rules_payload

        return rules_payload()

    @app.post("/v1/permission/ask")
    def permission_ask(body: PermissionBody) -> dict[str, Any]:
        return ask_permission(
            action=body.action,
            details=body.details,
            agent=body.agent,
            rule_id=body.rule_id,
        ).to_dict()

    @app.get("/v1/wallet/cards")
    def wallet_list() -> dict[str, Any]:
        from universal.wallet_store import list_cards

        return list_cards()

    @app.post("/v1/wallet/list")
    def wallet_list_post() -> dict[str, Any]:
        from universal.wallet_store import list_cards

        return list_cards()

    @app.post("/v1/wallet/cards")
    def wallet_save(body: WalletSaveBody) -> dict[str, Any]:
        from universal.wallet_store import save_card

        return save_card(
            card_name=body.card_name,
            card_number=body.card_number,
            expiry=body.expiry,
            cvv=body.cvv,
        )

    @app.post("/v1/wallet/cards/delete")
    def wallet_delete(body: WalletDeleteBody) -> dict[str, Any]:
        from universal.wallet_store import delete_card

        return delete_card(body.card_name)

    @app.post("/v1/wallet/purchase")
    def wallet_purchase(body: WalletBuyBody) -> dict[str, Any]:
        from universal.wallet_store import simulate_purchase

        return simulate_purchase(card_name=body.card_name, amount=body.amount, merchant=body.merchant)

    @app.post("/v1/browse/tor")
    def browse_tor(body: TorBody) -> dict[str, Any]:
        from universal.tor_access import fetch_via_tor, save_via_tor
        from urllib.parse import quote

        action = body.action.strip().lower()
        if action == "buscar":
            query = body.query.strip()
            if not query:
                raise HTTPException(status_code=400, detail="query is required")
            url = f"https://duckduckgo.com/html/?q={quote(query)}"
            return fetch_via_tor(url=url, timeout=body.timeout, action="search")
        if action == "descargar":
            if not body.url.strip():
                raise HTTPException(status_code=400, detail="url is required")
            return save_via_tor(url=body.url, timeout=body.timeout)
        if not body.url.strip():
            raise HTTPException(status_code=400, detail="url is required")
        return fetch_via_tor(url=body.url, timeout=body.timeout, action="fetch")

    @app.post("/v1/packages/run")
    def packages_run(body: PackageBody) -> dict[str, Any]:
        from universal.packages import run_package_manager

        return run_package_manager(action=body.action, package=body.package, manager=body.manager)

    @app.post("/v1/runtime/evolve")
    def runtime_evolve(body: EvolveBody) -> dict[str, Any]:
        try:
            result = default_manager().apply_evolution(
                target_file=body.target_file,
                new_code=body.new_code,
                reason=body.reason,
                agent=body.agent,
            )
        except ConfigError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return result

    @app.post("/v1/runtime/think")
    def runtime_think(body: ThinkBody) -> dict[str, Any]:
        prompt = body.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        history = body.history
        agent_id = body.agent_id or ""
        if agent_id:
            agent = state.platform.registry.get(agent_id)
            if not history:
                history = [{"role": message.role, "content": message.content} for message in agent.history]
            answer = default_manager().think(prompt=prompt, history=history, agent_id=agent.id)
            agent.record_turn(prompt, answer)
            payload = {
                "answer": answer,
                "agent_id": agent.id,
                "history": [{"role": m.role, "content": m.content} for m in agent.history],
            }
            return payload
        answer = default_manager().think(prompt=prompt, history=history, agent_id="anon")
        return {"answer": answer}
