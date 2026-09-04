"""API keys and chat history survive restart. Secrets never enter the registry or ZIP."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from universal.config import Settings
from universal.core.platform import Universal
from universal.core.registry import default_serve_registry_file
from universal.core.types import Message
from universal.llm_store import load_agent_api_key, settings_file
from universal.paths import get_registry_file, user_data_dir
from universal.server import create_app


def _live_settings(**extra: str) -> Settings:
    values = {
        "llm_base_url": "https://api.x.ai/v1",
        "llm_api_key": "",
        "llm_model": "grok-3",
    }
    values.update(extra)
    return Settings(**values)


def test_stale_empty_client_picks_up_the_saved_key() -> None:
    """Photo bug: UI said the key was saved, but ninja still had an empty client."""
    root = Universal(_live_settings(llm_api_key="xai-stale"))
    agent = root.factory.create("general", name="ninja")
    agent.llm_provider = "xAI (Grok 4.6)"
    agent.llm_model = "grok-4.6"
    agent.provider._api_key = ""
    client = TestClient(create_app(root, demo=False))
    body = client.get(f"/v1/agents/{agent.id}").json()
    assert body["has_api_key"] is True
    assert agent.provider._api_key == "xai-stale"
    assert agent.provider.base_url.rstrip("/") == "https://api.x.ai/v1"


def test_put_key_rebinds_the_existing_shared_client() -> None:
    root = Universal(_live_settings())
    agent = root.factory.create("general", name="ninja")
    assert getattr(agent.provider, "_api_key", None) == ""
    client = TestClient(create_app(root, demo=False))
    saved = client.put(
        "/v1/settings",
        json={
            "llm_api_key": "xai-live",
            "llm_base_url": "https://api.x.ai/v1",
            "llm_model": "grok-3",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["llm_api_key"] == "***"
    assert agent.provider is root.provider()
    assert agent.provider._api_key == "xai-live"
    other = root.factory.create("general", name="buddy")
    assert other.provider is agent.provider


def test_settings_and_history_survive_a_new_root(monkeypatch) -> None:
    monkeypatch.delenv("UNIVERSAL_LLM_API_KEY", raising=False)
    monkeypatch.delenv("UNIVERSAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("UNIVERSAL_LLM_MODEL", raising=False)
    persist = get_registry_file()
    first = Universal(_live_settings(), persist_path=persist)
    agent = first.factory.create("general", name="ninja")
    first.factory.start(agent.id)
    agent._remember_turn(Message(role="user", content="hola ninja"), "listo")
    client = TestClient(create_app(first, demo=False))
    assert client.put("/v1/settings", json={"llm_api_key": "xai-keep"}).status_code == 200
    stored = json.loads(settings_file().read_text(encoding="utf-8"))
    assert stored["llm_api_key"] == "xai-keep"
    sidecar = persist.read_text(encoding="utf-8")
    assert "xai-keep" not in sidecar
    assert "hola ninja" not in sidecar

    second = Universal(Settings.from_env(), persist_path=persist)
    assert second.settings.llm_api_key == "xai-keep"
    restored = second.registry.get(agent.id)
    assert [turn.content for turn in restored.history] == ["hola ninja", "listo"]
    assert restored.provider._api_key == "xai-keep"


def test_agent_key_stays_out_of_registry_and_zip(tmp_path: Path) -> None:
    persist = get_registry_file()
    root = Universal(_live_settings(llm_api_key="shared-key"), persist_path=persist)
    agent = root.factory.create("general", name="ninja")
    client = TestClient(create_app(root, demo=False))
    patched = client.patch(f"/v1/agents/{agent.id}", json={"llm_api_key": "only-ninja", "provider": "xAI (Grok 4.6)"})
    assert patched.status_code == 200
    assert patched.json()["has_api_key"] is True
    assert load_agent_api_key(agent.id) == "only-ninja"
    assert "only-ninja" not in persist.read_text(encoding="utf-8")
    dest = root.factory.deploy(agent.id, tmp_path / "ninja.zip")
    with zipfile.ZipFile(dest) as archive:
        for name in archive.namelist():
            body = archive.read(name).decode("utf-8", errors="ignore")
            assert "only-ninja" not in body
            assert "shared-key" not in body


def test_per_agent_key_does_not_steal_the_shared_client() -> None:
    root = Universal(_live_settings(llm_api_key="shared-key"))
    first = root.factory.create("general", name="one")
    second = root.factory.create("general", name="two")
    assert first.provider is second.provider
    root.factory.update(first.id, llm_api_key="only-one")
    assert first.provider is not second.provider
    assert first.provider._api_key == "only-one"
    assert second.provider._api_key == "shared-key"


def test_serve_registry_defaults_to_user_data() -> None:
    assert default_serve_registry_file() == get_registry_file()
    assert get_registry_file().parent == user_data_dir()


def test_legacy_cwd_registry_migrates_once(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UNIVERSAL_REGISTRY_FILE", raising=False)
    target = get_registry_file()
    if target.is_file():
        target.unlink()
    legacy = tmp_path / ".universal" / "registry.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"version": 1, "agents": []}\n', encoding="utf-8")
    migrated = default_serve_registry_file()
    assert migrated == target
    assert target.is_file()
    assert '"version": 1' in target.read_text(encoding="utf-8")
