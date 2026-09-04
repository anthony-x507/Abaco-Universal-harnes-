"""Quality-gate tests from docs/testing_guide.md (notes/59.md).

No live LLM. Each test gets a fresh Universal via the platform fixture
unless it builds its own root on purpose (T09 shared-client rebind).
"""

from __future__ import annotations

import threading
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from universal.config import Settings
from universal.core.platform import Universal
from universal.core.types import AgentState, CompletionResponse, Message, ToolSpec
from universal.exceptions import ConfigError, ProviderError
from universal.server import create_app, run_server
from universal.templates.catalog import get_template
from tests.conftest import FakeProvider


def _client(platform: Universal, *, demo: bool = True) -> TestClient:
    return TestClient(create_app(platform, demo=demo))


def test_t01_general_and_coder_install_native_plugins(platform: Universal) -> None:
    from universal.plugins.catalog import NATIVE_PLUGIN_NAMES

    general = platform.factory.create("general", name="t01-g")
    coder = platform.factory.create("coder", name="t01-c")
    assert general.plugins.names() == list(NATIVE_PLUGIN_NAMES)
    assert coder.plugins.names() == list(NATIVE_PLUGIN_NAMES)
    assert "system_prompt" not in general.plugins
    assert "transcript" not in general.plugins
    assert "tools" not in general.plugins
    assert "tools" not in coder.plugins


def test_t02_researcher_installs_natives_plus_tools_utc_now(platform: Universal) -> None:
    from tests.native_expect import RESEARCHER_PLUGIN_NAMES

    agent = platform.factory.create("researcher", name="t02")
    assert agent.plugins.names() == list(RESEARCHER_PLUGIN_NAMES)
    tools = agent.plugins.get("tools")
    assert tools is not None
    names = [spec.name for spec in tools.tools()]
    assert names == ["utc_now"]


def test_t03_system_prompt_is_template_field_not_a_plugin(
    platform: Universal, provider: FakeProvider
) -> None:
    template = get_template("general")
    agent = platform.factory.create("general", name="t03")
    assert agent.system_prompt == template.system_prompt
    assert "system_prompt" not in agent.plugins
    platform.factory.start(agent.id)
    agent.accept("ping")
    first = provider.calls[0][0]
    assert first.role == "system"
    assert first.content == template.system_prompt
    assert sum(1 for message in provider.calls[0] if message.role == "system") == 1


def test_t04_histories_do_not_mix(platform: Universal) -> None:
    one = platform.factory.create("general", name="alpha")
    two = platform.factory.create("general", name="beta")
    platform.factory.start(one.id)
    platform.factory.start(two.id)
    one.accept("alpha-only")
    two.accept("beta-only")
    one_text = " ".join(turn.content for turn in one.history)
    two_text = " ".join(turn.content for turn in two.history)
    assert "alpha-only" in one_text
    assert "beta-only" not in one_text
    assert "beta-only" in two_text
    assert "alpha-only" not in two_text


def test_t05_reset_history_is_per_agent(platform: Universal) -> None:
    one = platform.factory.create("general", name="keep")
    two = platform.factory.create("general", name="clear")
    platform.factory.start(one.id)
    platform.factory.start(two.id)
    one.accept("stay")
    two.accept("gone")
    two.reset_history()
    assert two.history == []
    assert any(turn.content == "stay" for turn in one.history)


def test_t06_second_in_flight_ask_is_409(platform: Universal) -> None:
    entered = threading.Event()
    release = threading.Event()

    class GatedProvider(FakeProvider):
        def complete(
            self,
            messages: list[Message],
            *,
            tools: list[ToolSpec] | None = None,
            model: str | None = None,
        ) -> CompletionResponse:
            entered.set()
            assert release.wait(timeout=2), "first ask never released"
            return super().complete(messages, tools=tools, model=model)

    gated = GatedProvider(reply="slow-ok")
    root = Universal(platform.settings, provider=gated)
    client = _client(root)
    agent_id = client.post("/v1/agents", json={"template": "general", "name": "t06"}).json()["id"]
    first_status: dict[str, int] = {}

    def first_ask() -> None:
        first_status["code"] = client.post(
            f"/v1/agents/{agent_id}/ask", json={"prompt": "one"}
        ).status_code

    worker = threading.Thread(target=first_ask)
    worker.start()
    assert entered.wait(timeout=2), "first ask did not reach the provider"
    second = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "two"})
    assert second.status_code == 409
    assert "already answering" in str(second.json()).lower()
    release.set()
    worker.join(timeout=2)
    assert first_status.get("code") == 200


def test_t07_delete_during_ask_clears_registry_and_lock(platform: Universal) -> None:
    client_app = create_app(platform, demo=True)
    client = TestClient(client_app)
    agent_id = client.post("/v1/agents", json={"template": "general", "name": "t07"}).json()["id"]
    client_app.state.universal.asking.add(agent_id)
    deleted = client.delete(f"/v1/agents/{agent_id}")
    assert deleted.status_code == 200
    assert agent_id not in platform.registry
    assert agent_id not in client_app.state.universal.asking


def test_t08_stream_provider_error_emits_sse_error(platform: Universal) -> None:
    class BoomStream(FakeProvider):
        def complete(
            self,
            messages: list[Message],
            *,
            tools: list[ToolSpec] | None = None,
            model: str | None = None,
        ) -> CompletionResponse:
            # Factory agents always advertise native tools, so SSE uses complete().
            raise ProviderError("stream-broke")

        def stream(
            self,
            messages: list[Message],
            *,
            tools: list[ToolSpec] | None = None,
            model: str | None = None,
        ):
            yield "partial"
            raise ProviderError("stream-broke")

    root = Universal(platform.settings, provider=BoomStream(reply="unused"))
    client = _client(root)
    agent_id = client.post("/v1/agents", json={"template": "general", "name": "t08"}).json()["id"]
    with client.stream(
        "POST",
        f"/v1/agents/{agent_id}/ask",
        json={"prompt": "keep-me", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "stream-broke" in body
    assert "error" in body


def test_t09_settings_change_rebinds_shared_clients() -> None:
    settings = Settings(
        llm_base_url="https://old.example.test/v1",
        llm_api_key="test-key",
        llm_model="fake-model",
    )
    root = Universal(settings)
    first = root.factory.create("general", name="old-url")
    assert first.provider.base_url == "https://old.example.test/v1"
    client = TestClient(create_app(root, demo=True))
    updated = client.put("/v1/settings", json={"llm_base_url": "https://new.example.test/v1"})
    assert updated.status_code == 200
    second = root.factory.create("general", name="new-url")
    assert first.provider.base_url == "https://new.example.test/v1"
    assert second.provider.base_url == "https://new.example.test/v1"
    assert first.provider is second.provider


def test_t11_ask_without_prior_start_auto_starts(platform: Universal) -> None:
    client = _client(platform)
    created = client.post("/v1/agents", json={"template": "general", "name": "t11"})
    agent_id = created.json()["id"]
    assert created.json()["state"] == "created"
    asked = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "hello"})
    assert asked.status_code == 200
    assert asked.json()["answer"].startswith("echo:")
    assert asked.json()["state"] == "running"
    assert platform.lifecycle.state_of(agent_id) is AgentState.RUNNING


def test_t12_delete_while_lifecycle_error(platform: Universal) -> None:
    client = _client(platform)
    agent_id = client.post("/v1/agents", json={"template": "general", "name": "t12"}).json()["id"]
    platform.lifecycle.mark_error(agent_id, "forced")
    assert platform.lifecycle.state_of(agent_id) is AgentState.ERROR
    deleted = client.delete(f"/v1/agents/{agent_id}")
    assert deleted.status_code == 200
    assert agent_id not in platform.registry


def test_t13_channels_lists_cli_and_webhook(platform: Universal) -> None:
    listed = _client(platform).get("/v1/channels").json()
    assert isinstance(listed["channels"], list)
    assert "cli" in listed["channels"]
    assert "webhook" in listed["channels"]


def test_w01_webhook_inbound_returns_answer(platform: Universal) -> None:
    client = _client(platform)
    agent_id = client.post(
        "/v1/agents",
        json={"template": "general", "name": "w01", "channel": "webhook"},
    ).json()["id"]
    inbound = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "hello-w01"})
    assert inbound.status_code == 200
    assert inbound.json()["answer"].startswith("echo:")
    assert "hello-w01" in inbound.json()["answer"]
    assert inbound.json().get("outbound_url") == ""
    assert "outbound_error" not in inbound.json()


def test_w02_outbound_posts_result(platform: Universal, monkeypatch: object) -> None:
    posts: list[tuple[str, dict[str, object]]] = []

    def fake_post(url: str, json: dict[str, object] | None = None, timeout: float | None = None):
        posts.append((url, json or {}))

        class _Response:
            def raise_for_status(self) -> None:
                return None

        return _Response()

    monkeypatch.setattr("universal.channels.webhook.httpx.post", fake_post)  # type: ignore[attr-defined]
    client = _client(platform)
    agent_id = client.post(
        "/v1/agents",
        json={
            "template": "general",
            "name": "w02",
            "channel": "webhook",
            "outbound_url": "http://example.test/cb",
        },
    ).json()["id"]
    inbound = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "ping"})
    assert inbound.status_code == 200
    assert inbound.json()["answer"].startswith("echo:")
    assert posts == [("http://example.test/cb", {"agent_id": agent_id, "text": inbound.json()["answer"]})]


def test_w03_outbound_failure_sets_outbound_error(platform: Universal, monkeypatch: object) -> None:
    def boom_post(url: str, json: dict[str, object] | None = None, timeout: float | None = None):
        raise httpx.ConnectError("outbound down", request=httpx.Request("POST", url))

    monkeypatch.setattr("universal.channels.webhook.httpx.post", boom_post)  # type: ignore[attr-defined]
    client = _client(platform)
    agent_id = client.post(
        "/v1/agents",
        json={
            "template": "general",
            "name": "w03",
            "channel": "webhook",
            "outbound_url": "http://example.test/cb",
        },
    ).json()["id"]
    inbound = client.post(f"/v1/agents/{agent_id}/webhook", json={"text": "still-works"})
    assert inbound.status_code == 200
    body = inbound.json()
    assert body["answer"].startswith("echo:")
    assert "still-works" in body["answer"]
    assert body.get("outbound_error")
    assert agent_id in platform.registry


def test_w04_channels_include_webhook(platform: Universal) -> None:
    listed = _client(platform).get("/v1/channels").json()["channels"]
    assert listed == ["cli", "webhook"]


def test_lock_no_aegis_in_product_source() -> None:
    roots = [Path("universal"), Path("web/src")]
    hits: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx", ".css", ".json"}:
                continue
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "aegis" in text.lower():
                hits.append(str(path))
    assert hits == []


def test_lock_no_chat_completions_route(platform: Universal) -> None:
    client = _client(platform)
    assert client.post("/v1/chat/completions", json={}).status_code == 404
    assert client.get("/v1/chat/completions").status_code == 404


def test_lock_serve_rejects_public_bind(monkeypatch: object) -> None:
    called: list[object] = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: called.append(kwargs))  # type: ignore[attr-defined]
    try:
        run_server(host="0.0.0.0", port=43124, demo=True)
    except ConfigError as exc:
        assert "localhost" in str(exc).lower()
        assert called == []
        return
    raise AssertionError("expected ConfigError for public bind")
