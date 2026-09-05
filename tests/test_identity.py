"""Identity is native on every agent, injected into every template, and served.

No mother.yaml, no universal/factory. The canonical identity is Python
(universal/identity.py); the YAML is only a human mirror.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from universal.audit import repo_root
from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.identity import (
    IDENTITY_NAME,
    IDENTITY_VERSION,
    capabilities_text,
    identity_payload,
    identity_prompt_block,
)
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.plugins.identity import IdentityPlugin
from universal.server import create_app
from universal.templates.catalog import get_template


def _call(name: str) -> ToolCall:
    return ToolCall(id="t1", name=name, arguments="{}")


def test_identity_is_a_native_plugin() -> None:
    assert "identity" in NATIVE_PLUGIN_NAMES
    assert "response_style" in NATIVE_PLUGIN_NAMES
    assert NATIVE_PLUGIN_NAMES[-1] == "response_style"


def test_every_created_agent_has_identity(platform: Universal) -> None:
    for template_id in ("general", "researcher", "coder"):
        agent = platform.factory.create(template_id, name=f"id-{template_id}")
        assert "identity" in agent.plugins
        tools = {spec.name for spec in agent.plugins.collect_tools()}
        assert {"show_identity", "list_capabilities"} <= tools


def test_all_three_prompts_contain_the_identity_block(platform: Universal) -> None:
    block = identity_prompt_block()
    assert IDENTITY_NAME in block
    assert "Your capabilities:" not in block
    assert capabilities_text() not in block
    for template_id in ("general", "researcher", "coder"):
        prompt = get_template(template_id).system_prompt
        assert block in prompt
        assert IDENTITY_NAME in prompt
        assert "`show_identity`" in prompt
        assert "list_capabilities" in prompt
        assert "at most 3 lines" in prompt
        assert "Do not list your rules, identity, or capabilities" in prompt


def test_identity_tools_return_the_name() -> None:
    plugin = IdentityPlugin()
    shown = plugin.invoke_tool(_call("show_identity"))
    assert shown is not None
    payload = json.loads(shown)["payload"]
    assert payload["name"] == IDENTITY_NAME
    assert payload["identity_version"] == IDENTITY_VERSION
    assert payload["quantum"] is False

    listed = plugin.invoke_tool(_call("list_capabilities"))
    assert listed is not None
    assert IDENTITY_NAME in listed
    assert capabilities_text() in listed


def test_identity_payload_lists_real_capabilities() -> None:
    payload = identity_payload()
    ids = {cap["id"] for cap in payload["capabilities"]}
    expected = {
        "terminal",
        "tts",
        "stt",
        "vision",
        "web_search",
        "scraper",
        "package_manager",
        "team",
        "navigator",
        "improvement",
        "strategist",
        "rule_enforcer",
        "proof",
        "self_modify",
        "identity",
        "wallet",
        "tor_browser",
    }
    assert expected <= ids


def test_runtime_identity_route_get_and_post(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    for method in (client.get, client.post):
        response = method("/v1/identity")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == IDENTITY_NAME
        assert body["quantum"] is False


def test_no_mother_yaml_or_factory_dir() -> None:
    root = repo_root()
    assert not (root / "mother.yaml").exists()
    assert not (root / "universal" / "templates" / "mother.yaml").exists()
    assert not (root / "universal" / "factory").exists()
