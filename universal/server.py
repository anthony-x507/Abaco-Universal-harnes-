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
from universal.channels.webhook import WebhookChannel
from universal.config import Settings
from universal.core.platform import Universal
from universal.core.registry import default_serve_registry_file
from universal.exceptions import (
    AgentNotFound,
    ChannelNotFound,
    ConfigError,
    LifecycleError,
    ProviderError,
    TemplateNotFound,
    UniversalError,
)
from universal.providers.catalog import PROVIDERS, get_provider
from universal.release import current_version
from universal.rules import rules_payload
from universal.runtime_api import register_runtime_routes
from universal.runtime_manager import default_manager
from universal.templates.catalog import list_templates
from universal.web_dist import resolve_web_dist


COMING_CHANNELS: tuple[str, ...] = ()


def _whisper_ready() -> bool:
    from universal.plugins.stt import whisper_available

    return whisper_available()


class CreateAgentBody(BaseModel):
    template: str = Field(default="general")
    name: str | None = None
    channel: str | None = None
    outbound_url: str | None = None
    provider: str | None = None
    emoji: str | None = None
    llm_model: str | None = None


class UpdateAgentBody(BaseModel):
    name: str | None = None
    emoji: str | None = None
    channel: str | None = None
    outbound_url: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    llm_model: str | None = None


class AttachmentBody(BaseModel):
    name: str
    mime: str = "application/octet-stream"
    data: str = ""
    kind: str = "file"
    transcript: str | None = None


class TranscribeBody(BaseModel):
    name: str = "clip.wav"
    mime: str = "audio/wav"
    data: str
    model: str = "tiny"


class WebhookBody(BaseModel):
    text: str
    sender_id: str | None = None


class AskBody(BaseModel):
    prompt: str = ""
    stream: bool = False
    attachments: list[AttachmentBody] = Field(default_factory=list)


class RunBody(BaseModel):
    prompt: str = ""
    stream: bool = False
    max_iterations: int = 5
    attachments: list[AttachmentBody] = Field(default_factory=list)


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
    asking: set[str] = field(default_factory=set)
    deploy_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="universal-deploy-")))


def _agent_payload(platform: Universal, agent_id: str) -> dict[str, Any]:
    agent = platform.registry.get(agent_id)
    state = platform.lifecycle.state_of(agent_id)
    payload = agent.info(state).to_dict()
    payload["history"] = [
        {"role": message.role, "content": message.content} for message in agent.history
    ]
    payload["plugin_labels"] = agent.plugin_labels()
    payload["usage"] = agent.usage.to_dict()
    payload["system_prompt"] = agent.system_prompt
    if not payload.get("emoji"):
        from universal.core.faces import face_for

        payload["emoji"] = face_for(agent.id, agent.emoji)
    channel = agent.channel
    if isinstance(channel, WebhookChannel):
        payload["outbound_url"] = channel.outbound_url
        if channel.last_outbound_error:
            payload["outbound_error"] = channel.last_outbound_error
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
    app = FastAPI(title="Universal platform", version="1.0.5")
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
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)

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
            "web": bool(getattr(app.state, "web_dist", None)),
            "version": current_version(),
            "whisper": _whisper_ready(),
            "runtime": default_manager().status(),
            "rules": [str(rule["id"]) for rule in rules_payload()["rules"] if isinstance(rule, dict)],
        }

    @app.get("/v1/update")
    def update_status() -> dict[str, Any]:
        from universal.updater import Updater

        updater = Updater()
        try:
            return updater.check().to_dict()
        finally:
            updater.close()

    @app.post("/v1/update")
    def update_apply() -> dict[str, Any]:
        from universal.updater import Updater

        updater = Updater()
        try:
            message = updater.apply()
        except ConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            updater.close()
        return {"ok": True, "message": message}

    @app.get("/v1/models")
    def list_models() -> dict[str, Any]:
        return {"models": [row.to_dict() for row in PROVIDERS]}

    @app.get("/v1/templates")
    def templates() -> dict[str, Any]:
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "emoji": t.emoji,
                }
                for t in list_templates()
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

    def _apply_provider_preset(name: str) -> None:
        preset = get_provider(name)
        if preset is None:
            raise ConfigError(f"Unknown model preset {name!r}")
        updates: dict[str, str] = {}
        if preset.base_url:
            updates["llm_base_url"] = preset.base_url
        if preset.default_model:
            updates["llm_model"] = preset.default_model
        if updates:
            state.platform.replace_settings(state.platform.settings.with_updates(**updates))

    @app.post("/v1/transcribe")
    def transcribe_audio(body: TranscribeBody) -> dict[str, Any]:
        from universal.attachments import save_upload
        from universal.core.types import ToolCall
        from universal.plugins.stt import STTPlugin

        path = save_upload("transcribe", body.name or "clip.wav", body.data)
        plugin = STTPlugin()
        text = plugin.invoke_tool(
            ToolCall(
                id="ui",
                name="transcribe",
                arguments=json.dumps({"audio_path": str(path), "model": body.model or "tiny"}),
            )
        )
        heard = str(text or "").strip()
        if not heard or heard.startswith("Error") or "not installed" in heard.lower():
            raise HTTPException(status_code=503, detail=heard or "Whisper could not transcribe that clip.")
        return {"text": heard, "path": str(path)}

    @app.post("/v1/agents")
    def create_agent(body: CreateAgentBody) -> dict[str, Any]:
        if body.provider:
            _apply_provider_preset(body.provider)
        channel = body.channel or state.default_channel
        llm_model = body.llm_model
        if body.provider:
            preset = get_provider(body.provider)
            if preset and not llm_model:
                llm_model = preset.default_model
        agent = state.platform.factory.create(
            body.template,
            body.name,
            channel=channel,
            outbound_url=body.outbound_url,
            emoji=body.emoji,
            llm_model=llm_model,
        )
        return _agent_payload(state.platform, agent.id)

    @app.get("/v1/agents/{agent_id}")
    def get_agent(agent_id: str) -> dict[str, Any]:
        return _agent_payload(state.platform, agent_id)

    @app.patch("/v1/agents/{agent_id}")
    def update_agent(agent_id: str, body: UpdateAgentBody) -> dict[str, Any]:
        state.platform.factory.update(
            agent_id,
            name=body.name,
            emoji=body.emoji,
            system_prompt=body.system_prompt,
            channel=body.channel,
            outbound_url=body.outbound_url,
            llm_model=body.llm_model,
            provider_name=body.provider,
        )
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
        state.asking.discard(agent_id)
        state.platform.factory.delete(agent_id)
        return {"deleted": payload}

    def _prepare_ask(agent_id: str, prompt: str, attachments: list[AttachmentBody] | None = None) -> tuple[Any, str]:
        if not state.demo:
            state.platform.settings.require_live()
        agent = state.platform.registry.get(agent_id)
        from universal.attachments import apply_attachments

        text = apply_attachments(agent, prompt, [item.model_dump() for item in attachments or []])
        if not text.strip():
            raise HTTPException(status_code=400, detail="prompt or an attachment is required")
        if agent.id in state.asking:
            raise HTTPException(status_code=409, detail="Agent is already answering")
        state.asking.add(agent.id)
        state.platform.factory.start(agent.id)
        return agent, text

    def _finish_ask(agent_id: str) -> None:
        state.asking.discard(agent_id)

    def _stream_events(agent: Any, prompt: str, *, stream_fn: Any) -> StreamingResponse:
        channel = agent.channel

        def events() -> Iterator[str]:
            pieces: list[str] = []
            try:
                def emit() -> Iterator[str]:
                    for event in stream_fn(prompt):
                        kind = str(event.get("type") or "")
                        if kind == "token" and event.get("text"):
                            pieces.append(str(event["text"]))
                            yield f"data: {json.dumps({'type': 'token', 'text': event['text']})}\n\n"
                        elif kind in {"tool_execution", "delegating"}:
                            yield f"data: {json.dumps(event)}\n\n"

                if isinstance(channel, CLIChannel):
                    with channel.capture():
                        yield from emit()
                else:
                    yield from emit()
                payload = _agent_payload(state.platform, agent.id)
                payload["answer"] = "".join(pieces)
                payload["done"] = True
                payload["type"] = "done"
                yield f"data: {json.dumps(payload)}\n\n"
            except UniversalError as exc:
                status = getattr(exc, "status_code", 502)
                yield f"data: {json.dumps({'error': str(exc), 'status': status})}\n\n"
            finally:
                _finish_ask(agent.id)

        return StreamingResponse(events(), media_type="text/event-stream")

    def _complete_turn(agent: Any, prompt: str, *, answer_fn: Any) -> dict[str, Any]:
        channel = agent.channel
        try:
            if isinstance(channel, CLIChannel):
                with channel.capture():
                    answer = answer_fn(prompt)
            else:
                answer = answer_fn(prompt)
            payload = _agent_payload(state.platform, agent.id)
            payload["answer"] = answer
            return payload
        finally:
            _finish_ask(agent.id)

    @app.post("/v1/agents/{agent_id}/ask")
    def ask_agent(agent_id: str, body: AskBody) -> Any:
        agent, prompt = _prepare_ask(agent_id, body.prompt.strip(), body.attachments)
        if body.stream:
            return _stream_events(agent, prompt, stream_fn=agent.accept_stream_events)
        return _complete_turn(agent, prompt, answer_fn=agent.accept)

    @app.post("/v1/agents/{agent_id}/run")
    def run_agent(agent_id: str, body: RunBody) -> Any:
        agent, prompt = _prepare_ask(agent_id, body.prompt.strip(), body.attachments)
        max_iterations = max(1, int(body.max_iterations))
        runtime = default_manager()
        if runtime.healthy() and not body.stream:
            history = [{"role": message.role, "content": message.content} for message in agent.history]
            try:
                answer = runtime.think(prompt=prompt, history=history, agent_id=agent.id)
            except Exception:
                answer = None
            else:
                agent.record_turn(prompt, answer)
                payload = _agent_payload(state.platform, agent.id)
                payload["answer"] = answer
                payload["runtime"] = True
                _finish_ask(agent.id)
                return payload
        if body.stream:
            return _stream_events(
                agent,
                prompt,
                stream_fn=lambda text: agent.run_stream_events(text, max_iterations=max_iterations),
            )
        return _complete_turn(
            agent,
            prompt,
            answer_fn=lambda text: agent.run(text, max_iterations=max_iterations),
        )

    @app.post("/v1/agents/{agent_id}/reset")
    def reset_agent(agent_id: str) -> dict[str, Any]:
        agent = state.platform.registry.get(agent_id)
        agent.reset_history()
        payload = _agent_payload(state.platform, agent.id)
        payload["status"] = "reset"
        return payload

    @app.post("/v1/agents/{agent_id}/webhook")
    def webhook_inbound(agent_id: str, body: WebhookBody) -> dict[str, Any]:
        text = body.text.strip()
        agent = state.platform.registry.get(agent_id)
        channel = agent.channel
        if not isinstance(channel, WebhookChannel):
            raise HTTPException(status_code=400, detail="Agent is not on the webhook channel")
        prepared, prompt = _prepare_ask(agent_id, text)
        try:
            answer = prepared.accept(prompt)
            payload = _agent_payload(state.platform, prepared.id)
            payload["answer"] = answer
            return payload
        finally:
            _finish_ask(prepared.id)

    @app.post("/v1/agents/{agent_id}/deploy")
    def deploy_agent(agent_id: str) -> FileResponse:
        path = state.platform.factory.deploy(agent_id, state.deploy_dir)
        return FileResponse(path, filename=path.name, media_type="application/zip")

    register_runtime_routes(app, state)

    dist = resolve_web_dist()
    app.state.web_dist = dist
    if dist is not None:
        _mount_spa(app, dist)

    return app


def _mount_spa(app: FastAPI, dist: Path) -> None:
    """Serve the Vite build from the same origin as ``/v1`` (desktop / packaged).

    Must not register a catch-all route under ``/v1`` — that would turn
    ``POST /v1/chat/completions`` into 405 instead of 404.
    """
    root = dist.resolve()

    def _safe_file(url_path: str) -> Path | None:
        relative = url_path.lstrip("/")
        if not relative or relative == "health" or relative.startswith("v1/") or relative == "v1":
            return None
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "GET":
            existing = _safe_file(request.url.path)
            if existing is not None:
                return FileResponse(existing)
        response = await call_next(request)
        if (
            request.method == "GET"
            and response.status_code == 404
            and not request.url.path.startswith("/v1")
            and request.url.path != "/health"
        ):
            index = root / "index.html"
            if index.is_file():
                return FileResponse(index)
        return response

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(root / "index.html")


def build_serve_app(
    *,
    demo: bool = False,
    persist: bool = True,
    persist_path: Path | str | None = None,
) -> FastAPI:
    """One Universal root + factory app. Shared by ``serve`` and the desktop window."""
    settings = Settings.from_env()
    if persist_path is None and persist:
        persist_path = default_serve_registry_file()
    elif not persist:
        persist_path = None
    if demo:
        from universal.providers.demo import EchoProvider

        platform = Universal(settings, provider=EchoProvider(), persist_path=persist_path)
    else:
        platform = Universal(settings, persist_path=persist_path)
    return create_app(platform, demo=demo)


def run_server(*, host: str = "127.0.0.1", port: int = 43124, demo: bool = False) -> int:
    import uvicorn

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigError("v1 serve binds localhost only. Do not pass a public host.")

    app = build_serve_app(demo=demo)
    from universal.rules import ensure_rules_file

    ensure_rules_file()
    runtime = default_manager()
    runtime.start(core_url=f"http://{host}:{port}")
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        runtime.stop()
    return 0
