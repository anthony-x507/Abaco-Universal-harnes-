"""self_modify is native, permission-gated, and cannot touch the core."""

from __future__ import annotations

from pathlib import Path

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.self_modify import apply_self_modify


def test_self_modify_is_native(platform: Universal) -> None:
    assert "self_modify" in NATIVE_PLUGIN_NAMES
    agent = platform.factory.create("general", name="self")
    assert "self_modify" in agent.plugins.names()


def test_self_modify_blocks_core(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    result = apply_self_modify(
        file_path="universal/core/factory.py",
        new_content="nope",
        reason="test",
    )
    assert result["ok"] is False
    assert "core" in result["error"].lower()


def test_self_modify_writes_when_allowed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "plugin_note.txt"

    class Allowed:
        granted = True
        reason = "allow"

    monkeypatch.setattr("universal.self_modify.ask_permission", lambda **_k: Allowed())
    result = apply_self_modify(
        file_path=str(dest),
        new_content="ok",
        reason="note",
    )
    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "ok"


def test_self_modify_tool_blocks_core() -> None:
    from universal.plugins.self_modify import SelfModifyPlugin

    plugin = SelfModifyPlugin()
    out = plugin.invoke_tool(
        ToolCall(
            id="t",
            name="self_modify",
            arguments='{"file_path":"universal/core/registry.py","new_content":"x","reason":"no"}',
        )
    )
    assert out is not None and out.startswith("Error:")
