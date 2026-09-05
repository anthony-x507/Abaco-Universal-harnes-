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
    assert len(companies) == 50
    assert len(set(companies)) == 50
    assert len(list_companies("cn")) == 10
    assert len(list_companies("us")) == 40
    assert len(PROVIDERS) == 51
    assert PROVIDERS[-1].name == "Custom (URL)"
    names = [row.name for row in PROVIDERS]
    assert len(names) == len(set(names))
    assert all(row.region in {"cn", "us", ""} for row in PROVIDERS)


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
    assert "Zhipu (GLM-5.2)" in names
    assert "MiniMax (M3)" in names
    zhipu = get_provider("Zhipu (GLM-5.2)")
    mini = get_provider("MiniMax (M3)")
    assert zhipu is not None and zhipu.default_model == "glm-5.2"
    assert mini is not None and mini.default_model == "MiniMax-M3"
    assert "Custom (URL)" in names
    assert "Custom (URL)" not in list_providers_without_custom()
    assert "Ollama (Local)" in names
    assert "Groq (Llama 3 70B)" not in names
    assert sum(1 for name in names if name.startswith("OpenAI ")) == 1
    assert sum(1 for name in names if name.startswith("Anthropic ")) == 1
    assert sum(1 for name in names if name.startswith("DeepSeek ")) == 1
    assert get_provider("Ollama (Local)") is not None
    assert get_provider("Ollama (Local)").region == "us"
    assert get_provider("DeepSeek (V4 Pro)").region == "cn"


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
    assert len(rows) == 51
    china = client.get("/v1/models", params={"region": "cn"}).json()["models"]
    assert len([row for row in china if row["company"] != "Custom"]) == 10
    assert all(row["region"] in {"cn", ""} for row in china)
    assert any(row["name"] == "OpenAI (GPT-5.6 Sol)" and row["company"] == "OpenAI" for row in rows)
    assert rows[0]["name"] == "DeepSeek (V4 Pro)"
    assert rows[0]["region"] == "cn"
    assert client.post("/v1/chat/completions", json={}).status_code == 404


def test_create_keeps_process_settings(platform: Universal) -> None:
    before_url = platform.settings.llm_base_url
    before_model = platform.settings.llm_model
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "general", "name": "groq-face", "provider": "Groq (Compound)"},
    )
    assert created.status_code == 200
    assert created.json()["model"] == "groq/compound"
    assert platform.settings.llm_base_url == before_url
    assert platform.settings.llm_model == before_model


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
