"""CLI surface: templates listing and one-shot ask via an injected platform."""

from __future__ import annotations

from universal.cli import main


def test_cli_templates(capsys: object) -> None:
    assert main(["templates"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "general" in out
    assert "researcher" in out
    assert "coder" in out


def test_cli_templates_json(capsys: object) -> None:
    assert main(["templates", "--json"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '"id": "general"' in out


def test_cli_ask_without_key_fails(monkeypatch: object, capsys: object) -> None:
    monkeypatch.delenv("UNIVERSAL_LLM_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("UNIVERSAL_LLM_BASE_URL", raising=False)  # type: ignore[attr-defined]
    assert main(["ask", "hello"]) == 2
    err = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "UNIVERSAL_LLM_API_KEY" in err
