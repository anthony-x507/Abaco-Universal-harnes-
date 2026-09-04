"""Catalog of OpenAI-compatible presets. One client class, many labels."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.cli import main
from universal.core.platform import Universal
from universal.providers.catalog import (
    PROVIDERS,
    get_provider,
    list_providers,
    list_providers_without_custom,
)
from universal.server import create_app


def test_providers_count() -> None:
    assert len(PROVIDERS) >= 40


def test_get_provider() -> None:
    row = get_provider("OpenAI (GPT-4o-mini)")
    assert row is not None
    assert row.base_url == "https://api.openai.com/v1"
    assert row.default_model == "gpt-4o-mini"


def test_list_providers() -> None:
    names = list_providers()
    assert "DeepSeek Chat" in names
    assert "Ollama (Llama 3.2)" in names
    assert "Custom (URL)" in names
    assert "Custom (URL)" not in list_providers_without_custom()


def test_provider_no_api_key() -> None:
    row = get_provider("Ollama (Llama 3.2)")
    assert row is not None
    assert row.requires_api_key is False


def test_custom_provider() -> None:
    row = get_provider("Custom (URL)")
    assert row is not None
    assert row.base_url == ""
    assert row.default_model == "custom-model"


def test_http_models_lists_presets(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    response = client.get("/v1/models")
    assert response.status_code == 200
    rows = response.json()["models"]
    assert len(rows) >= 40
    assert rows[0]["name"] == "OpenAI (GPT-4o-mini)"
    assert client.post("/v1/chat/completions", json={}).status_code == 404


def test_create_applies_preset_to_new_settings(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "general", "name": "groq-face", "provider": "Groq (Llama 3 70B)"},
    )
    assert created.status_code == 200
    assert platform.settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert platform.settings.llm_model == "llama3-70b-8192"
    assert created.json()["model"]  # demo echo still injected


def test_unknown_preset_is_400(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    response = client.post("/v1/agents", json={"template": "general", "provider": "not-a-host"})
    assert response.status_code == 400


def test_cli_models(capsys: object) -> None:
    assert main(["models"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "DeepSeek Chat" in out
    assert "Ollama (Llama 3.2)" in out
    assert main(["models", "--json"]) == 0
    dumped = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '"default_model": "gpt-4o-mini"' in dumped
