"""package_manager is native, permission-gated, and never a fourth template."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.packages import run_package_manager
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.server import create_app
from universal.templates.catalog import get_template


def test_no_mother_yaml() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "universal" / "templates" / "mother.yaml").exists()
    assert not (root / "mother.yaml").exists()


def test_package_manager_is_native(platform: Universal) -> None:
    assert "package_manager" in NATIVE_PLUGIN_NAMES
    agent = platform.factory.create("general", name="pkgs")
    assert "package_manager" in agent.plugins.names()
    plugin = agent.plugins.get("package_manager")
    assert plugin is not None
    specs = plugin.tools()
    assert any(spec.name == "package_manager" for spec in specs)


def test_templates_are_proactive() -> None:
    for template_id in ("general", "researcher", "coder"):
        prompt = get_template(template_id).system_prompt
        assert "I can try to install" in prompt
        assert "package_manager" in prompt
        assert 'Do not say "I can\'t"' in prompt


def test_install_blocked_when_rule_off(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(tmp_path / "rules.json"))
    (tmp_path / "rules.json").write_text(
        '{"version":"1.0","rules":[{"id":"allow_self_install","enforced":false}]}',
        encoding="utf-8",
    )
    result = run_package_manager(action="install", package="requests", manager="pip")
    assert result["ok"] is False
    assert "allow_self_install" in result["error"]


def test_install_denied_without_dialog(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    result = run_package_manager(action="install", package="requests", manager="pip")
    assert result["ok"] is False
    assert "blocked" in result["error"].lower() or "denied" in result["error"].lower()


def test_rejects_shell_metacharacters(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    result = run_package_manager(action="install", package="foo; rm -rf /", manager="pip")
    assert result["ok"] is False
    assert "not allowed" in result["error"]


def test_http_packages_route(platform: Universal, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        "/v1/packages/run",
        json={"action": "install", "package": "requests", "manager": "pip"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
