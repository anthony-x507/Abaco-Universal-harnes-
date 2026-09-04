"""Hybrid runtime: Python is the gate; Node only runs user-writable plugins."""

from __future__ import annotations

import shutil
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.permission_gate import ask_permission
from universal.runtime_manager import (
    RuntimeManager,
    _safe_plugin_path,
    default_manager,
    reset_manager,
    seed_runtime_dir,
)
from universal.server import create_app
from universal.exceptions import ConfigError


def _client(platform: Universal, tmp_path: Path, monkeypatch) -> TestClient:
    runtime = RuntimeManager(runtime_dir=tmp_path / "agent_runtime", port=43129)
    reset_manager(runtime)
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    return TestClient(create_app(platform, demo=True))


def test_seed_ships_inside_the_package() -> None:
    seed = seed_runtime_dir()
    assert (seed / "runtime.js").is_file()
    assert (seed / "package.json").is_file()
    assert (seed / "plugins" / "terminal.js").is_file()
    assert (seed / "plugins" / "evolution.js").is_file()


def test_install_copies_seed_into_user_data(tmp_path: Path) -> None:
    dest = tmp_path / "agent_runtime"
    manager = RuntimeManager(runtime_dir=dest, port=43129)
    manager.ensure_installed()
    assert (dest / "runtime.js").is_file()
    assert (dest / "plugins" / "terminal.js").is_file()
    assert (dest / "plugins" / "evolution.js").is_file()
    (dest / "plugins" / "terminal.js").write_text("// user evolved\n", encoding="utf-8")
    manager.ensure_installed()
    assert (dest / "plugins" / "terminal.js").read_text(encoding="utf-8") == "// user evolved\n"


def test_evolve_requires_permission_and_stays_in_plugins(tmp_path: Path, monkeypatch) -> None:
    dest = tmp_path / "agent_runtime"
    manager = RuntimeManager(runtime_dir=dest, port=43129)
    manager.ensure_installed()
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    denied = manager.apply_evolution(
        target_file="plugins/sample.js",
        new_code="module.exports = { name: 'sample' }\n",
        reason="test",
    )
    assert denied["granted"] is False
    assert not (dest / "plugins" / "sample.js").exists()

    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    ok = manager.apply_evolution(
        target_file="plugins/sample.js",
        new_code="module.exports = { name: 'sample', version: '2.0.0' }\n",
        reason="test",
    )
    assert ok["granted"] is True
    assert "sample" in (dest / "plugins" / "sample.js").read_text(encoding="utf-8")


def test_evolve_rejects_path_escape(tmp_path: Path) -> None:
    dest = tmp_path / "agent_runtime"
    dest.mkdir()
    try:
        _safe_plugin_path(dest, "../secrets.js")
        raise AssertionError("escaped")
    except ConfigError:
        pass
    try:
        _safe_plugin_path(dest, "runtime.js")
        raise AssertionError("core file")
    except ConfigError:
        pass


def test_permission_env_modes(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    assert ask_permission(action="x").granted is True
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    monkeypatch.delenv("UNIVERSAL_PERMISSION_GRANT", raising=False)
    assert ask_permission(action="x").granted is False


def test_factory_llm_and_runtime_routes(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    client = _client(platform, tmp_path, monkeypatch)
    health = client.get("/health").json()
    assert "runtime" in health
    assert health["runtime"]["ok"] is False

    complete = client.post(
        "/v1/llm/complete",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )
    assert complete.status_code == 200
    assert complete.json()["content"].startswith("echo:")

    evolve = client.post(
        "/v1/runtime/evolve",
        json={
            "target_file": "plugins/hello.js",
            "new_code": "module.exports = { name: 'hello', version: '1.0.0' }\n",
            "reason": "unit test",
        },
    )
    assert evolve.status_code == 200
    assert evolve.json()["granted"] is True
    plugins = client.get("/v1/runtime/plugins").json()["plugins"]
    names = {row["name"] for row in plugins}
    assert "hello" in names or "terminal_access" in names or "terminal" in names

    blocked = client.post(
        "/v1/runtime/evolve",
        json={"target_file": "../etc/passwd", "new_code": "nope", "reason": "no"},
    )
    assert blocked.status_code == 403

    reset_manager()


def test_ask_still_uses_the_python_agent(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    client = _client(platform, tmp_path, monkeypatch)
    created = client.post("/v1/agents", json={"template": "general", "name": "hybrid"})
    agent_id = created.json()["id"]
    asked = client.post(f"/v1/agents/{agent_id}/ask", json={"prompt": "hello"})
    assert asked.status_code == 200
    assert asked.json()["answer"].startswith("echo:")
    reset_manager()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for the live runtime")
def test_node_think_goes_through_python_llm(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    import uvicorn

    from universal.server import create_app

    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    factory_port = _free_port()
    runtime_port = _free_port()
    manager = RuntimeManager(runtime_dir=tmp_path / "agent_runtime", port=runtime_port)
    reset_manager(manager)
    app = create_app(platform, demo=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=factory_port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.05)
    try:
        manager.start(core_url=f"http://127.0.0.1:{factory_port}")
        assert manager.healthy()
        listed = httpx.get(f"{manager.url}/list_plugins", timeout=2).json()["plugins"]
        names = {row["name"] for row in listed}
        assert "terminal_access" in names
        assert "propose_evolution" in names
        thought = httpx.post(
            f"{manager.url}/think",
            json={"prompt": "runtime ping", "history": [], "agent_id": "t"},
            timeout=20,
        )
        assert thought.status_code == 200
        assert "runtime ping" in thought.json()["response"]
    finally:
        manager.stop()
        server.should_exit = True
        reset_manager()
