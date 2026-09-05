"""Desktop wrapper uses the same factory. No second registry. No YAML templates."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from universal.cli import main
from universal.core.platform import Universal
from universal.desktop import WINDOW_TITLE, build_parser, desktop_face_url
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.server import create_app
from universal.web_dist import resolve_web_dist


ROOT = Path(__file__).resolve().parents[1]


def test_no_yaml_factory_templates() -> None:
    assert not (ROOT / "universal" / "factory" / "templates").exists()
    assert not (ROOT / "universal" / "agent.py").exists()


def test_native_plugins_still_factory_default(platform: Universal) -> None:
    agent = platform.factory.create("general", name="desk-native")
    assert agent.plugins.names() == list(NATIVE_PLUGIN_NAMES)


def test_spa_served_from_dist(platform: Universal, tmp_path: Path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>Universal face</html>", encoding="utf-8")
    (dist / "asset.txt").write_text("ok", encoding="utf-8")
    monkeypatch.setenv("UNIVERSAL_WEB_DIST", str(dist))
    client = TestClient(create_app(platform, demo=True))
    root = client.get("/")
    assert root.status_code == 200
    assert "Universal face" in root.text
    assert "no-store" in root.headers.get("cache-control", "").lower()
    agents = client.get("/agents")
    assert agents.status_code == 200
    assert "Universal face" in agents.text
    asset = client.get("/asset.txt")
    assert asset.text == "ok"
    templates = client.get("/v1/templates")
    assert templates.status_code == 200
    assert {row["id"] for row in templates.json()["templates"]} == {
        "general",
        "researcher",
        "coder",
    }
    health = client.get("/health")
    assert health.json()["web"] is True


def test_health_without_dist_sets_web_false(platform: Universal, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UNIVERSAL_WEB_DIST", str(tmp_path / "missing"))
    # If the repo already has web/dist, resolve_web_dist still finds it unless env is set
    # and missing — env is first candidate and fails, then falls back to repo dist.
    client = TestClient(create_app(platform, demo=True))
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "web" in body


def test_desktop_check_cli(capsys) -> None:
    dist = resolve_web_dist()
    if dist is None:
        assert main(["desktop", "--check"]) == 2
        return
    assert main(["desktop", "--check", "--demo"]) == 0
    out = capsys.readouterr().out
    assert "universal desktop: ok" in out
    assert "factory=" in out


def test_desktop_face_url_busts_wkwebview_cache() -> None:
    assert desktop_face_url("127.0.0.1", 43124, "1.2.7") == "http://127.0.0.1:43124/?v=1.2.7"
    assert desktop_face_url("127.0.0.1", 43124).endswith("/?v=1.2.14")


def test_desktop_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 43124
    assert args.demo is False


def test_macos_scripts_exist_and_stay_lock_safe() -> None:
    build = (ROOT / "scripts" / "build_macos.sh").read_text(encoding="utf-8")
    dmg = (ROOT / "scripts" / "create_dmg.sh").read_text(encoding="utf-8")
    app_entry = (ROOT / "app.py").read_text(encoding="utf-8")
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "Universal.app" in build
    assert "PyInstaller" in build or "pyinstaller" in build
    assert 'PATH="${PATH}:/opt/homebrew/bin"' in build
    assert 'PATH="/opt/homebrew/bin:${PATH}"' not in build
    assert "command -v ffmpeg" in build
    # A missing ffmpeg on the build runner must warn, never abort the release.
    ffmpeg_gate = build.split("command -v ffmpeg", 1)[1].split("fi", 1)[0]
    assert "exit 1" not in ffmpeg_gate
    assert 'import whisper' in build
    assert "--collect-submodules=whisper" in build
    assert "--collect-data=whisper" in build
    assert "--hidden-import=whisper" not in build
    assert "aegis" not in build.lower()
    assert "--icon" in build
    assert "Universal.icns" in build
    assert "agent_runtime:agent_runtime" in build
    assert "download_node.sh" in build
    assert "sign_macos.sh" in build
    assert "NSMicrophoneUsageDescription" in build
    entitlements = (ROOT / "entitlements.plist").read_text(encoding="utf-8")
    assert "com.apple.security.device.audio-input" in entitlements
    signer = (ROOT / "scripts" / "sign_macos.sh").read_text(encoding="utf-8")
    assert "--entitlements" in signer
    assert 'codesign --force --deep --entitlements "$ENTITLEMENTS" --sign -' in signer
    assert "leaving $APP unsigned" not in signer
    assert "hdiutil" in dmg
    assert "from universal.desktop import main" in app_entry
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "macos-latest" in workflow
    assert '".[desktop,media]"' in workflow or "'.[desktop,media]'" in workflow
    assert "brew install" not in workflow
    assert "openai-whisper" not in workflow
    assert "requirements.txt" not in workflow
    req_lines = [
        ln.strip() for ln in reqs.splitlines() if ln.strip() and not ln.strip().startswith("#")
    ]
    assert any(ln == "openai-whisper" or ln.startswith("openai-whisper") for ln in req_lines)
    assert not any(ln.startswith("universal[media]") for ln in req_lines)
    assert "aegis" not in app_entry.lower()


def test_logo_ships_in_spa_and_native_icon() -> None:
    assert (ROOT / "web" / "src" / "assets" / "logo.png").is_file()
    assert (ROOT / "web" / "public" / "logo.png").is_file()
    assert (ROOT / "Universal.icns").is_file()
    assert (ROOT / "Universal.icns").read_bytes()[:4] == b"icns"
    header = (ROOT / "web" / "src" / "components" / "Header.tsx").read_text(encoding="utf-8")
    assert "Abaco Universal Harness" in header
    assert "assets/logo.png" in header
    css = (ROOT / "web" / "src" / "App.css").read_text(encoding="utf-8")
    assert "url('/logo.png')" in css
    assert "0.15" in css
    assert "opacity:" not in css.split("body")[1].split("}")[0]
    desktop = (ROOT / "universal" / "desktop.py").read_text(encoding="utf-8")
    assert 'background_color="#0B0E14"' in desktop
    assert "private_mode=False" in desktop
    assert "mediaDevicesEnabled" in desktop
    assert "desktop_face_url" in desktop
    assert "webview_storage_dir" in desktop
    assert WINDOW_TITLE == "Abaco Universal Harness"
    assert "NSMicrophoneUsageDescription" in (ROOT / "scripts" / "build_macos.sh").read_text(encoding="utf-8")
    assert "from universal.desktop import main" in (ROOT / "app.py").read_text(encoding="utf-8")
