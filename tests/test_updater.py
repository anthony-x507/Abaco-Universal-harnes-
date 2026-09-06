"""GitHub update check and user-data persistence. No live GitHub, no hdiutil."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.exceptions import ConfigError
from universal.paths import get_memory_dir, get_plugins_dir, user_data_dir
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.plugins.installer import ensure_plugins_installed
from universal.release import BAKED_REPO, current_version, load_release
from universal.server import create_app
from universal.updater import (
    APP_BUNDLE_NAME,
    INSTALL_WARNING,
    LEGACY_BUNDLE_NAME,
    PREVIOUS_BUNDLE_NAME,
    UpdateStatus,
    Updater,
    clear_macos_webview_caches,
    install_warning,
    is_newer,
    parse_version,
    pick_dmg_asset,
    running_from_applications,
)
from tests.native_expect import RESEARCHER_PLUGIN_NAMES


ROOT = Path(__file__).resolve().parents[1]
CREATE_DMG = ROOT / "scripts" / "create_dmg.sh"
LEGACY_MISSING_APP = "Mounted image has no Universal.app"


def _fake_app(path: Path, marker: str = "canonical") -> Path:
    contents = path / "Contents" / "MacOS"
    contents.mkdir(parents=True)
    (contents / "marker").write_text(marker, encoding="utf-8")
    return path


def _legacy_1_2_15_find_app(volumes_root: Path) -> Path:
    """Exact lookup from packaged 1.2.15 / 1.2.16 ``updater._install_dmg``."""
    src = volumes_root / "Universal" / "Universal.app"
    if not src.is_dir():
        raise ConfigError(LEGACY_MISSING_APP)
    return src


def _stage_dmg(app: Path, stage: Path) -> None:
    env = {**os.environ, "UNIVERSAL_APP_BUNDLE": str(app)}
    subprocess.run(
        ["bash", str(CREATE_DMG), "--stage", str(stage)],
        check=True,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_version_compare() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert is_newer("1.0.1", "1.0.0")
    assert not is_newer("1.0.0", "1.0.10")
    assert is_newer("0.2.0", "0.1.0")


def test_repo_is_baked_and_ignores_env(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_UPDATE_REPO", "evil/other")
    data = load_release()
    assert data["repo"] == BAKED_REPO
    assert current_version() == "1.2.18"
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
                "name": "Abaco-Coding-Harness.dmg",
                "browser_download_url": "https://github.com/acme/universal/releases/download/v9.9.9/Abaco-Coding-Harness.dmg",
            }
        ],
    }
    client.get.return_value = response
    updater = Updater(repo="acme/universal", client=client)
    status = updater.check_for_updates()
    assert status.available is True
    assert status.latest == "9.9.9"
    assert status.url.endswith("Abaco-Coding-Harness.dmg")


def test_pick_dmg_prefers_canonical_name() -> None:
    url = pick_dmg_asset(
        [
            {
                "name": "notes.txt",
                "browser_download_url": "https://github.com/acme/universal/notes.txt",
            },
            {
                "name": "Universal.dmg",
                "browser_download_url": "https://github.com/acme/universal/Universal.dmg",
            },
            {
                "name": "Abaco-Coding-Harness.dmg",
                "browser_download_url": "https://github.com/acme/universal/Abaco-Coding-Harness.dmg",
            },
            {
                "name": "Abaco-Harness.dmg",
                "browser_download_url": "https://github.com/acme/universal/Abaco-Harness.dmg",
            },
        ]
    )
    assert url == "https://github.com/acme/universal/Abaco-Coding-Harness.dmg"


def test_pick_dmg_accepts_any_dmg_for_old_release_layout() -> None:
    url = pick_dmg_asset(
        [
            {
                "name": "Abaco-Harness.dmg",
                "browser_download_url": "https://github.com/acme/universal/Abaco-Harness.dmg",
            }
        ]
    )
    assert url and url.endswith("Abaco-Harness.dmg")


def test_apply_schedules_relaunch_without_killing_tests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_UPDATE_ALLOW_INSTALL", "1")
    scheduled: list[object] = []

    class FakeTimer:
        def __init__(self, delay: float, fn: object) -> None:
            scheduled.append((delay, fn))

        def start(self) -> None:
            return None

    monkeypatch.setattr("universal.updater.threading.Timer", FakeTimer)
    monkeypatch.setattr(
        Updater,
        "check",
        lambda self: UpdateStatus(
            current="1.0.6",
            latest="9.9.9",
            available=True,
            url="https://github.com/acme/universal/releases/download/v9.9.9/Abaco-Coding-Harness.dmg",
            release_notes="",
            repo="acme/universal",
        ),
    )
    monkeypatch.setattr(Updater, "_download", lambda self, url, dest: dest.write_bytes(b"dmg"))
    monkeypatch.setattr(Updater, "_install_dmg", lambda self, dmg, dest: None)
    monkeypatch.setattr(Updater, "_clear_caches_after_install", lambda self: None)
    dest = tmp_path / APP_BUNDLE_NAME
    dest.mkdir()
    updater = Updater(repo="acme/universal")
    message = updater.apply(dest_app=dest)
    assert "relaunching" in message.lower()
    assert scheduled
    delay, _fn = scheduled[0]
    assert delay >= 1


def test_apply_refuses_outside_packaged_mac() -> None:
    updater = Updater(repo="acme/universal")
    try:
        updater.apply()
    except Exception as exc:
        assert "Install is only allowed" in str(exc)
        return
    raise AssertionError("expected ConfigError")


def test_clear_macos_webview_caches(tmp_path: Path) -> None:
    stale = tmp_path / "Library" / "WebKit" / "Universal"
    stale.mkdir(parents=True)
    (stale / "old.html").write_text("Write in the middle column", encoding="utf-8")
    extra = tmp_path / "Library" / "Caches" / "com.universal.app"
    extra.mkdir(parents=True)
    removed = clear_macos_webview_caches(tmp_path)
    assert not stale.exists()
    assert not extra.exists()
    assert any(path.endswith("Universal") for path in removed)


def test_install_warning_when_frozen_outside_applications(monkeypatch) -> None:
    monkeypatch.setattr("universal.updater.sys.frozen", True, raising=False)
    monkeypatch.setattr(
        "universal.updater.sys.executable",
        "/Users/me/Downloads/Abaco Coding Harness.app/Contents/MacOS/Abaco Coding Harness",
    )
    assert install_warning() == INSTALL_WARNING


def test_running_from_legacy_applications_paths(monkeypatch) -> None:
    monkeypatch.setattr("universal.updater.sys.frozen", True, raising=False)
    monkeypatch.setattr(
        "universal.updater.sys.executable",
        "/Applications/Universal.app/Contents/MacOS/Universal",
    )
    assert running_from_applications() is True
    monkeypatch.setattr(
        "universal.updater.sys.executable",
        "/Applications/Abaco Harness.app/Contents/MacOS/Abaco Harness",
    )
    assert running_from_applications() is True
    monkeypatch.setattr(
        "universal.updater.sys.executable",
        "/Applications/Abaco Coding Harness.app/Contents/MacOS/Abaco Coding Harness",
    )
    assert running_from_applications() is True


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
            current="1.2.18",
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
    assert body["current"] == "1.2.18"
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
    assert "Universal.app" in data["release_notes"]
    assert "Abaco Coding Harness" in data["release_notes"]


def test_v1_2_17_dmg_layout_breaks_old_updater(tmp_path: Path) -> None:
    """v1.2.17 shipped only Abaco Harness.app on volume 'Abaco Harness'."""
    volumes = tmp_path / "Volumes"
    _fake_app(volumes / "Abaco Harness" / PREVIOUS_BUNDLE_NAME)
    with pytest.raises(ConfigError, match=LEGACY_MISSING_APP):
        _legacy_1_2_15_find_app(volumes)
    mount, src = Updater._mounted_app(volumes)
    assert mount == volumes / "Abaco Harness"
    assert src == volumes / "Abaco Harness" / PREVIOUS_BUNDLE_NAME


def test_bridge_dmg_layout_serves_old_and_new_updaters(tmp_path: Path) -> None:
    app = _fake_app(tmp_path / APP_BUNDLE_NAME, marker="bridge")
    stage = tmp_path / "stage"
    _stage_dmg(app, stage)

    assert (stage / APP_BUNDLE_NAME / "Contents" / "MacOS" / "marker").read_text(
        encoding="utf-8"
    ) == "bridge"
    assert (stage / LEGACY_BUNDLE_NAME / "Contents" / "MacOS" / "marker").read_text(
        encoding="utf-8"
    ) == "bridge"
    assert not (stage / PREVIOUS_BUNDLE_NAME).exists()

    volumes = tmp_path / "Volumes"
    mount = volumes / "Universal"
    shutil.copytree(stage, mount)

    legacy = _legacy_1_2_15_find_app(volumes)
    assert legacy == mount / LEGACY_BUNDLE_NAME
    assert legacy.is_dir()

    found_mount, found_src = Updater._mounted_app(volumes)
    assert found_mount == mount
    assert found_src == mount / APP_BUNDLE_NAME


def test_new_updater_accepts_legacy_bundle_only(tmp_path: Path) -> None:
    volumes = tmp_path / "Volumes"
    _fake_app(volumes / "Universal" / LEGACY_BUNDLE_NAME)
    mount, src = Updater._mounted_app(volumes)
    assert mount == volumes / "Universal"
    assert src == volumes / "Universal" / LEGACY_BUNDLE_NAME
    assert _legacy_1_2_15_find_app(volumes) == src


def test_new_updater_missing_both_bundles_is_empty(tmp_path: Path) -> None:
    volumes = tmp_path / "Volumes"
    (volumes / "Universal").mkdir(parents=True)
    assert Updater._mounted_app(volumes) == (None, None)
    with pytest.raises(ConfigError, match=LEGACY_MISSING_APP):
        _legacy_1_2_15_find_app(volumes)
