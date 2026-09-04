"""GitHub update check and user-data persistence. No live GitHub, no hdiutil."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.paths import get_memory_dir, get_plugins_dir, user_data_dir
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.plugins.installer import ensure_plugins_installed
from universal.release import BAKED_REPO, current_version, load_release
from universal.server import create_app
from universal.updater import INSTALL_WARNING, UpdateStatus, Updater, install_warning, is_newer, parse_version
from tests.native_expect import RESEARCHER_PLUGIN_NAMES


def test_version_compare() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert is_newer("1.0.1", "1.0.0")
    assert not is_newer("1.0.0", "1.0.10")
    assert is_newer("0.2.0", "0.1.0")


def test_repo_is_baked_and_ignores_env(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_UPDATE_REPO", "evil/other")
    data = load_release()
    assert data["repo"] == BAKED_REPO
    assert current_version() == "1.0.1"
    updater = Updater()
    assert updater.repo == BAKED_REPO


def test_check_parses_github_payload() -> None:
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "tag_name": "v9.9.9",
        "body": "notes",
        "assets": [
            {
                "name": "Universal.dmg",
                "browser_download_url": "https://github.com/acme/universal/releases/download/v9.9.9/Universal.dmg",
            }
        ],
    }
    client.get.return_value = response
    updater = Updater(repo="acme/universal", client=client)
    status = updater.check_for_updates()
    assert status.available is True
    assert status.latest == "9.9.9"
    assert status.url.endswith(".dmg")


def test_apply_refuses_outside_packaged_mac() -> None:
    updater = Updater(repo="acme/universal")
    try:
        updater.apply()
    except Exception as exc:
        assert "Install is only allowed" in str(exc)
        return
    raise AssertionError("expected ConfigError")


def test_install_warning_when_frozen_outside_applications(monkeypatch) -> None:
    monkeypatch.setattr("universal.updater.sys.frozen", True, raising=False)
    monkeypatch.setattr("universal.updater.sys.executable", "/Users/me/Downloads/Universal.app/Contents/MacOS/Universal")
    assert install_warning() == INSTALL_WARNING


def test_installer_writes_manifest_not_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    names = ensure_plugins_installed()
    assert names == list(NATIVE_PLUGIN_NAMES)
    plugins_dir = get_plugins_dir()
    assert (plugins_dir / "manifest.json").is_file()
    assert not (plugins_dir / "terminal.py").exists()
    body = json.loads((plugins_dir / "manifest.json").read_text(encoding="utf-8"))
    assert body["plugins"] == list(NATIVE_PLUGIN_NAMES)
    assert body["version"] == current_version()


def test_memory_and_registry_use_user_data(tmp_path: Path, monkeypatch, settings, provider) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "persist"))
    monkeypatch.delenv("UNIVERSAL_MEMORY_DIR", raising=False)
    monkeypatch.delenv("UNIVERSAL_REGISTRY_FILE", raising=False)
    ensure_plugins_installed()
    persist = user_data_dir() / "registry.json"
    root = Universal(settings, provider=provider, persist_path=persist)
    agent = root.factory.create("researcher", name="keep-plugins")
    root.factory.start(agent.id)
    agent.complete("my name is Ada")
    assert agent.plugins.names() == list(RESEARCHER_PLUGIN_NAMES)
    assert persist.is_file()
    assert get_memory_dir() == tmp_path / "persist" / "memory"
    assert agent.memory_path().parent == get_memory_dir()


def test_http_update_check(platform: Universal, monkeypatch) -> None:
    def fake_check(self) -> UpdateStatus:  # noqa: ARG001
        return UpdateStatus(
            current="1.0.1",
            latest=None,
            available=False,
            url=None,
            release_notes="",
            repo=BAKED_REPO,
            reason="Already up to date.",
        )

    monkeypatch.setattr(Updater, "check", fake_check)
    client = TestClient(create_app(platform, demo=True))
    health = client.get("/health")
    assert health.json()["version"] == current_version()
    body = client.get("/v1/update").json()
    assert body["current"] == "1.0.1"
    assert body["repo"] == BAKED_REPO
    assert body["available"] is False
    assert "in_applications" in body
    apply = client.post("/v1/update")
    assert apply.status_code == 400


def test_version_json_exists() -> None:
    path = Path(__file__).resolve().parents[1] / "version.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == current_version()
    assert data["repo"] == BAKED_REPO
