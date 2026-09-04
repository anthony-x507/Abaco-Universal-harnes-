"""Catalog of OpenAI-compatible presets. One client class, one company each."""

from __future__ import annotations

from fastapi.testclient import TestClient

from universal.cli import main
from universal.core.platform import Universal
from universal.providers.catalog import (
    PROVIDERS,
    get_provider,
    list_companies,
    list_providers,
    list_providers_without_custom,
)
from universal.server import create_app


def test_one_latest_model_per_company() -> None:
    companies = list_companies()
    assert len(companies) == 40
    assert len(set(companies)) == 40
    assert len(PROVIDERS) == 41
    assert PROVIDERS[-1].name == "Custom (URL)"
    names = [row.name for row in PROVIDERS]
    assert len(names) == len(set(names))


def test_get_provider() -> None:
    row = get_provider("OpenAI (GPT-5.6 Sol)")
    assert row is not None
    assert row.company == "OpenAI"
    assert row.base_url == "https://api.openai.com/v1"
    assert row.default_model == "gpt-5.6-sol"


def test_list_providers() -> None:
    names = list_providers()
    assert "DeepSeek (V4 Pro)" in names
    assert "Anthropic (Claude Fable 5.1)" in names
    assert "Custom (URL)" in names
    assert "Custom (URL)" not in list_providers_without_custom()
    assert "Ollama (Llama 3.2)" not in names
    assert "Groq (Llama 3 70B)" not in names
    assert sum(1 for name in names if name.startswith("OpenAI ")) == 1
    assert sum(1 for name in names if name.startswith("Anthropic ")) == 1
    assert sum(1 for name in names if "Llama 3" in name) == 0


def test_openrouter_is_transport_not_ten_rows() -> None:
    via_openrouter = [
        row for row in PROVIDERS if row.base_url == "https://openrouter.ai/api/v1" and row.company != "OpenRouter"
    ]
    assert via_openrouter
    assert get_provider("OpenRouter (Auto)") is not None
    assert len([row for row in PROVIDERS if row.company == "OpenRouter"]) == 1


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
    assert len(rows) == 41
    assert rows[0]["name"] == "OpenAI (GPT-5.6 Sol)"
    assert rows[0]["company"] == "OpenAI"
    assert client.post("/v1/chat/completions", json={}).status_code == 404


def test_create_applies_preset_to_new_settings(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "general", "name": "groq-face", "provider": "Groq (Compound)"},
    )
    assert created.status_code == 200
    assert platform.settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert platform.settings.llm_model == "groq/compound"
    assert created.json()["model"]  # demo echo still injected


def test_unknown_preset_is_400(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    response = client.post("/v1/agents", json={"template": "general", "provider": "not-a-host"})
    assert response.status_code == 400


def test_cli_models(capsys: object) -> None:
    assert main(["models"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "DeepSeek (V4 Pro)" in out
    assert "xAI (Grok 4.6)" in out
    assert main(["models", "--json"]) == 0
    dumped = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '"default_model": "gpt-5.6-sol"' in dumped
    assert '"company": "OpenAI"' in dumped
