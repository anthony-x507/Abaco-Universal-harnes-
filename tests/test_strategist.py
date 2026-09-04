"""DeepSeek Harness monitor. No Node plugin. No fourth template. No live GitHub."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.server import create_app
from universal.strategist import (
    RULE_ID,
    analyze_changes,
    compare_with_universal,
    format_report,
    scan_deepseek,
)


def _fetch(url: str):
    if url.endswith("/repos/deepseek-ai/deepseek-harness"):
        return 200, {
            "name": "deepseek-harness",
            "full_name": "deepseek-ai/deepseek-harness",
            "description": "Everything is a plugin.",
            "stargazers_count": 111894,
            "forks_count": 10,
            "updated_at": "2026-09-01T00:00:00Z",
            "html_url": "https://github.com/deepseek-ai/deepseek-harness",
            "language": "TypeScript",
        }
    if url.endswith("/repos/deepseek-ai/DeepSeek-Coder"):
        return 200, {
            "name": "DeepSeek-Coder",
            "full_name": "deepseek-ai/DeepSeek-Coder",
            "description": "Code model",
            "stargazers_count": 100,
            "forks_count": 1,
            "updated_at": "2026-01-01T00:00:00Z",
            "html_url": "https://github.com/deepseek-ai/DeepSeek-Coder",
            "language": "Python",
        }
    if url.endswith("/repos/deepseek-ai/DeepSeek-Chat"):
        return 404, {"message": "Not Found"}
    if "/releases" in url:
        return 200, [
            {
                "tag_name": "v0.1.0",
                "name": "Developer preview",
                "body": "Everything is a plugin. Breaking change: APIs will evolve.",
                "published_at": "2026-08-13T00:00:00Z",
                "html_url": "https://github.com/deepseek-ai/deepseek-harness/releases/tag/v0.1.0",
            }
        ]
    if url.endswith("README.md"):
        return 200, "# DeepSeek Harness\nEverything is a plugin.\nSandbox and schedule plugins."
    if url.endswith("package.json"):
        return 200, '{"name":"@deepseek-ai/dsh"}'
    if "duckduckgo" in url:
        return 200, {"Abstract": "Open-source agent harness.", "RelatedTopics": [{"Text": "dsh"}]}
    return 404, {}


def test_no_node_strategist_plugin() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "agent_runtime" / "plugins" / "strategist_integration.js").exists()
    assert not (root / "universal" / "templates" / "mother.yaml").exists()


def test_scan_records_missing_chat_and_compares(platform: Universal) -> None:  # noqa: ARG001
    report = scan_deepseek(refresh=True, fetch=_fetch)
    assert report["ok"] is True
    assert report["harness"]["stars"] == 111894
    assert report["coder"]["full_name"] == "deepseek-ai/DeepSeek-Coder"
    assert report["chat"] is None
    assert report["repos"]["chat"]["missing"] is True
    assert report["new_releases"][0]["tag"] == "v0.1.0"
    assert any(row["feature"] == "plugin_surface" for row in report["comparisons"])
    assert report["popularity"]["twitter"] == "not_available"
    text = format_report(report)
    assert "deepseek-ai/deepseek-harness" in text
    assert "X/Twitter" in text


def test_rule_off_blocks_scan(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps({"version": "1.0", "rules": [{"id": RULE_ID, "enforced": False}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    report = scan_deepseek(refresh=True, fetch=_fetch)
    assert report["blocked"] is True
    assert report["ok"] is False


def test_http_get_empty_then_scan(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    empty = client.get("/v1/strategist/deepseek")
    assert empty.status_code == 200
    assert empty.json()["scanned"] is False
    from universal import strategist as module

    monkeypatch_fetch = _fetch
    original = module._default_fetch
    module._default_fetch = monkeypatch_fetch  # type: ignore[assignment]
    try:
        scanned = client.post("/v1/strategist/deepseek/scan")
    finally:
        module._default_fetch = original  # type: ignore[assignment]
    assert scanned.status_code == 200
    assert scanned.json()["harness"]["full_name"] == "deepseek-ai/deepseek-harness"
    cached = client.get("/v1/strategist/deepseek")
    assert cached.json()["new_releases"][0]["tag"] == "v0.1.0"


def test_plugin_tool(platform: Universal, monkeypatch) -> None:
    from universal import strategist as module

    monkeypatch.setattr(module, "_default_fetch", _fetch)
    agent = platform.factory.create("general", name="watch")
    plugin = agent.plugins.get("strategist")
    assert plugin is not None
    out = plugin.invoke_tool(ToolCall(id="t1", name="deepseek_monitor", arguments='{"refresh":true}'))
    assert out is not None
    assert "deepseek-ai/deepseek-harness" in out


def test_analyze_and_compare_helpers() -> None:
    changes = analyze_changes("Everything is a plugin. Sandbox included.", "{}")
    assert changes
    rows = compare_with_universal(
        {"description": "Everything is a plugin.", "stars": 2000},
        changes,
    )
    features = {row["feature"] for row in rows}
    assert "plugin_surface" in features
    assert "visibility" in features
