"""HTTP factory control plane. One Universal root per process. Not an OpenAI clone."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from universal.channels.catalog import list_channels
from universal.channels.cli import CLIChannel
from universal.config import Settings
from universal.core.platform import Universal
from universal.exceptions import (
    AgentNotFound,
    ChannelNotFound,
    ConfigError,
    LifecycleError,
    ProviderError,
    TemplateNotFound,
    UniversalError,
)
from universal.templates.catalog import list_templates


COMING_CHANNELS = ("webhook",)


class CreateAgentBody(BaseModel):
    template: str = Field(default="general")
    name: str | None = None
    channel: str | None = None


class AskBody(BaseModel):
    prompt: str
    stream: bool = False


class SettingsBody(BaseModel):
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    default_channel: str | None = None


@dataclass
class ServerState:
    platform: Universal
    default_channel: str = "cli"
    demo: bool = False
    deploy_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="universal-deploy-")))


def _agent_payload(platform: Universal, agent_id: str) -> dict[str, Any]:
    agent = platform.registry.get(agent_id)
    state = platform.lifecycle.state_of(agent_id)
    payload = agent.info(state).to_dict()
    payload["history"] = [
        {"role": message.role, "content": message.content} for message in agent.history
    ]
    return payload


def _settings_payload(state: ServerState) -> dict[str, Any]:
    public = state.platform.settings.public_dict()
    return {
        **public,
        "demo": state.demo,
        "default_channel": state.default_channel,
        "channels": list_channels(),
        "channels_coming": list(COMING_CHANNELS),
    }


def create_app(platform: Universal, *, demo: bool = False) -> FastAPI:
    """Build the FastAPI app around an already-constructed Universal root."""
    state = ServerState(platform=platform, demo=demo)
    app = FastAPI(title="Universal platform", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.universal = state

    @app.exception_handler(AgentNotFound)
    @app.exception_handler(TemplateNotFound)
    @app.exception_handler(ChannelNotFound)
    async def _not_found(_request: Request, exc: UniversalError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=404)

    @app.exception_handler(ConfigError)
    @app.exception_handler(LifecycleError)
    async def _bad_request(_request: Request, exc: UniversalError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.exception_handler(ProviderError)
    async def _provider(_request: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=502)

    @app.exception_handler(UniversalError)
    async def _universal(_request: Request, exc: UniversalError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "product": "Universal platform",
            "demo": state.demo,
            "agents": len(state.platform.factory.list()),
        }

    @app.get("/v1/templates")
    def templates() -> dict[str, Any]:
        return {
            "templates": [
                {"id": t.id, "name": t.name, "description": t.description} for t in list_templates()
            ]
        }

    @app.get("/v1/channels")
    def channels() -> dict[str, Any]:
        return {"channels": list_channels(), "coming": list(COMING_CHANNELS)}

    @app.get("/v1/settings")
    def get_settings() -> dict[str, Any]:
        return _settings_payload(state)

    @app.put("/v1/settings")
    def put_settings(body: SettingsBody) -> dict[str, Any]:
        if body.default_channel:
            known = list_channels()
            if body.default_channel not in known:
                raise ChannelNotFound(
                    f"Unknown channel {body.default_channel!r}. Known: {', '.join(known)}"
                )
            state.default_channel = body.default_channel
        if any(
            value is not None
            for value in (body.llm_base_url, body.llm_api_key, body.llm_model)
        ):
            updated = state.platform.settings.with_updates(
                llm_base_url=body.llm_base_url,
                llm_api_key=body.llm_api_key,
                llm_model=body.llm_model,
            )
            state.platform.replace_settings(updated)
        return _settings_payload(state)

    @app.get("/v1/agents")
    def list_agents() -> dict[str, Any]:
        return {
            "agents": [
                _agent_payload(state.platform, info.id) for info in state.platform.factory.list()
            ]
        }

    @app.post("/v1/agents")
    def create_agent(body: CreateAgentBody) -> dict[str, Any]:
        channel = body.channel or state.default_channel
        agent = state.platform.factory.create(body.template, body.name, channel=channel)
        return _agent_payload(state.platform, agent.id)

    @app.get("/v1/agents/{agent_id}")
    def get_agent(agent_id: str) -> dict[str, Any]:
        return _agent_payload(state.platform, agent_id)

    @app.post("/v1/agents/{agent_id}/start")
    def start_agent(agent_id: str) -> dict[str, Any]:
        state.platform.factory.start(agent_id)
        return _agent_payload(state.platform, agent_id)

    @app.post("/v1/agents/{agent_id}/stop")
    def stop_agent(agent_id: str) -> dict[str, Any]:
        state.platform.factory.stop(agent_id)
        return _agent_payload(state.platform, agent_id)

    @app.delete("/v1/agents/{agent_id}")
    def delete_agent(agent_id: str) -> dict[str, Any]:
        payload = _agent_payload(state.platform, agent_id)
        state.platform.factory.delete(agent_id)
        return {"deleted": payload}

    def _prepare_ask(agent_id: str, prompt: str) -> Any:
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        if not state.demo:
            state.platform.settings.require_live()
        agent = state.platform.registry.get(agent_id)
        state.platform.factory.start(agent.id)
        return agent

    @app.post("/v1/agents/{agent_id}/ask")
    def ask_agent(agent_id: str, body: AskBody) -> Any:
        prompt = body.prompt.strip()
        agent = _prepare_ask(agent_id, prompt)
        channel = agent.channel
        if body.stream:
            def events() -> Iterator[str]:
                pieces: list[str] = []
                try:
                    stream = agent.accept_stream(prompt)
                    if isinstance(channel, CLIChannel):
                        with channel.capture():
                            for piece in stream:
                                pieces.append(piece)
                                yield f"data: {json.dumps({'text': piece})}\n\n"
                    else:
                        for piece in stream:
                            pieces.append(piece)
                            yield f"data: {json.dumps({'text': piece})}\n\n"
                    payload = _agent_payload(state.platform, agent.id)
                    payload["answer"] = "".join(pieces)
                    payload["done"] = True
                    yield f"data: {json.dumps(payload)}\n\n"
                except UniversalError as exc:
                    yield f"data: {json.dumps({'error': str(exc)})}\n\n"

            return StreamingResponse(events(), media_type="text/event-stream")

        if isinstance(channel, CLIChannel):
            with channel.capture():
                answer = agent.accept(prompt)
        else:
            answer = agent.accept(prompt)
        payload = _agent_payload(state.platform, agent.id)
        payload["answer"] = answer
        return payload

    @app.post("/v1/agents/{agent_id}/deploy")
    def deploy_agent(agent_id: str) -> FileResponse:
        path = state.platform.factory.deploy(agent_id, state.deploy_dir)
        return FileResponse(path, filename=path.name, media_type="application/zip")

    return app


def run_server(*, host: str = "127.0.0.1", port: int = 43124, demo: bool = False) -> int:
    import uvicorn

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigError("v1 serve binds localhost only. Do not pass a public host.")

    settings = Settings.from_env()
    if demo:
        from universal.providers.demo import EchoProvider

        platform = Universal(settings, provider=EchoProvider())
    else:
        platform = Universal(settings)
    app = create_app(platform, demo=demo)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
