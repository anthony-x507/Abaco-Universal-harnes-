"""Governance, wallet, and Tor gate. No YAML templates. No real charges."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.rules import RULE_IDS, ensure_rules_file, is_enforced, load_rules
from universal.server import create_app
from universal.wallet_store import list_cards, save_card, simulate_purchase, wallet_path


def test_no_yaml_mother_or_factory_templates() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "universal" / "templates" / "mother.yaml").exists()
    assert not (root / "universal" / "factory" / "templates").exists()


def test_default_rules_include_finance_and_tor() -> None:
    ids = {rule.id for rule in load_rules()}
    assert "no_purchase_without_permission" in ids
    assert "no_dark_web_without_permission" in ids
    assert "navigator_auto_notify" in ids
    assert "navigator_allow_deviations" in ids
    assert "navigator_no_false_promises" in ids
    assert "memory_share_between_agents" in ids
    assert "strategist_deepseek_tracking" in ids
    assert "sentinel_proof_required" in ids
    assert set(RULE_IDS) <= ids
    assert is_enforced("no_purchase_without_permission")
    assert is_enforced("no_dark_web_without_permission")
    assert is_enforced("navigator_auto_notify")
    assert is_enforced("memory_share_between_agents") is False
    assert is_enforced("sentinel_proof_required") is False


def test_rules_file_can_disable_a_rule(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "rules": [{"id": "no_purchase_without_permission", "enforced": False}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    assert is_enforced("no_purchase_without_permission") is False
    assert is_enforced("no_dark_web_without_permission") is True


def test_rule_enforcer_is_native(platform: Universal) -> None:
    assert "rule_enforcer" in NATIVE_PLUGIN_NAMES
    agent = platform.factory.create("general", name="governed")
    assert "rule_enforcer" in agent.plugins.names()
    plugin = agent.plugins.get("rule_enforcer")
    assert plugin is not None
    listed_raw = plugin.invoke_tool(ToolCall(id="t1", name="list_rules", arguments="{}"))
    assert listed_raw is not None
    listed = json.loads(listed_raw)
    assert {row["id"] for row in listed} >= {"no_purchase_without_permission", "no_dark_web_without_permission"}
    checked_raw = plugin.invoke_tool(
        ToolCall(id="t2", name="check_rule", arguments='{"rule_id":"no_purchase_without_permission"}')
    )
    assert checked_raw is not None
    assert json.loads(checked_raw)["enforced"] is True


def test_wallet_save_list_delete_and_purchase_gate(platform: Universal, monkeypatch) -> None:
    client = TestClient(create_app(platform, demo=True))
    rules = client.get("/v1/rules").json()
    assert {row["id"] for row in rules["rules"]} >= {
        "no_purchase_without_permission",
        "no_dark_web_without_permission",
    }

    saved = client.post(
        "/v1/wallet/cards",
        json={
            "card_name": "Travel",
            "card_number": "4111111111111111",
            "expiry": "12/29",
            "cvv": "123",
        },
    ).json()
    assert saved["ok"] is True
    assert saved["last4"] == "1111"
    raw = wallet_path().read_text(encoding="utf-8")
    assert "4111111111111111" not in raw
    assert "123" not in raw

    names = client.get("/v1/wallet/cards").json()["cards"]
    assert names == ["Travel"]

    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    blocked = client.post(
        "/v1/wallet/purchase",
        json={"card_name": "Travel", "amount": 12.5, "merchant": "Cafe"},
    ).json()
    assert blocked["ok"] is False
    assert blocked.get("blocked") is True

    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    bought = client.post(
        "/v1/wallet/purchase",
        json={"card_name": "Travel", "amount": 12.5, "merchant": "Cafe"},
    ).json()
    assert bought["ok"] is True
    assert bought["simulated"] is True
    assert bought["last4"] == "1111"

    deleted = client.post("/v1/wallet/cards/delete", json={"card_name": "Travel"}).json()
    assert deleted["ok"] is True
    assert list_cards()["cards"] == []


def test_tor_requires_permission(platform: Universal, monkeypatch) -> None:
    client = TestClient(create_app(platform, demo=True))
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    blocked = client.post(
        "/v1/browse/tor",
        json={"action": "navegar", "url": "http://exampleonion.onion/"},
    ).json()
    assert blocked["ok"] is False
    assert blocked.get("blocked") is True

    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    allowed = client.post(
        "/v1/browse/tor",
        json={"action": "navegar", "url": "http://exampleonion.onion/"},
    ).json()
    assert allowed["ok"] is False
    assert "torsocks" in allowed.get("error", "") or allowed.get("error")


def test_runtime_seed_ships_wallet_and_tor() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "agent_runtime" / "plugins" / "wallet.js").is_file()
    assert (root / "agent_runtime" / "plugins" / "tor_browser.js").is_file()
    assert (root / "universal" / "agent_runtime_seed" / "plugins" / "wallet.js").is_file()
    assert (root / "universal" / "agent_runtime_seed" / "plugins" / "tor_browser.js").is_file()


def test_save_card_helper_roundtrip(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "allow")
    saved = save_card(card_name="Home", card_number="5555555555554444", expiry="01/30", cvv="999")
    assert saved["ok"] is True
    assert simulate_purchase(card_name="Home", amount=1, merchant="Shop")["ok"] is True
    ensure_rules_file()


def test_purchase_skips_dialog_when_rule_is_off(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps({"version": "1.0", "rules": [{"id": "no_purchase_without_permission", "enforced": False}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    monkeypatch.setenv("UNIVERSAL_PERMISSION_MODE", "deny")
    saved = save_card(card_name="Work", card_number="4111111111111111", expiry="12/29", cvv="123")
    assert saved["ok"] is True
    bought = simulate_purchase(card_name="Work", amount=3, merchant="Books")
    assert bought["ok"] is True
    assert bought["simulated"] is True


def test_ensure_rules_file_adds_new_catalog_ids(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "abaco_rules.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "rules": [{"id": "no_system_delete", "description": "old", "enforced": False}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSAL_RULES_FILE", str(path))
    ensure_rules_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = {row["id"] for row in data["rules"]}
    assert ids >= set(RULE_IDS)
    by_id = {row["id"]: row for row in data["rules"]}
    assert by_id["no_system_delete"]["enforced"] is False
    assert by_id["no_purchase_without_permission"]["enforced"] is True


def test_node_wallet_and_tor_are_thin_clients() -> None:
    root = Path(__file__).resolve().parents[1]
    wallet = (root / "agent_runtime" / "plugins" / "wallet.js").read_text(encoding="utf-8")
    tor = (root / "agent_runtime" / "plugins" / "tor_browser.js").read_text(encoding="utf-8")
    assert "createCipheriv" not in wallet
    assert "default_password" not in wallet
    assert "torsocks" not in tor
    assert "corePost('/v1/wallet/purchase'" in wallet
    assert "corePost('/v1/browse/tor'" in tor
