"""Hito 5: product docs stay English, lock-safe, and the examples run."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.server import create_app

ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = (
    ROOT / "README.md",
    ROOT / "DEMO.md",
    ROOT / "demo.sh",
    ROOT / "web" / "README.md",
)


def test_product_docs_have_no_aegis() -> None:
    for path in DOC_FILES:
        text = path.read_text(encoding="utf-8")
        assert "aegis" not in text.lower(), f"{path.name} must not mention Aegis"


def test_readme_covers_hito5_surfaces() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in (
        "universal ask",
        "universal chat",
        "universal shell",
        "universal serve",
        "webhook",
        "memory.json",
        "Agent.run",
        "registry.json",
        "usage.json",
        "utc_now",
        "run_command",
        "search_web",
        "universal[media]",
        "DEMO.md",
        "demo.sh",
    ):
        assert needle in text, f"README missing {needle!r}"


def test_demo_guide_has_seven_steps() -> None:
    text = (ROOT / "DEMO.md").read_text(encoding="utf-8")
    for heading in (
        "Step 1",
        "Step 2",
        "Step 3",
        "Step 4",
        "Step 5",
        "Step 6",
        "Step 7",
    ):
        assert heading in text
    assert "/v1/agents/" in text
    assert "webhook" in text
    assert "registry.json" in text


def test_documented_http_examples_work(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["product"] == "Universal platform"

    researcher = client.post(
        "/v1/agents",
        json={"template": "researcher", "name": "demo-researcher", "channel": "cli"},
    )
    assert researcher.status_code == 200
    body = researcher.json()
    from tests.native_expect import RESEARCHER_LABELS

    assert body["plugin_labels"] == RESEARCHER_LABELS
    assert "usage" in body
    agent_id = body["id"]

    ran = client.post(
        f"/v1/agents/{agent_id}/run",
        json={"prompt": "What time is it in UTC? Investigate and summarize."},
    )
    assert ran.status_code == 200
    assert ran.json()["answer"]
    assert ran.json()["usage"]["calls"] >= 1

    hook = client.post(
        "/v1/agents",
        json={"template": "researcher", "name": "demo-hook", "channel": "webhook"},
    )
    hook_id = hook.json()["id"]
    inbound = client.post(
        f"/v1/agents/{hook_id}/webhook",
        json={"text": "hello from another process"},
    )
    assert inbound.status_code == 200
    assert inbound.json()["answer"]

    zip_response = client.post(f"/v1/agents/{agent_id}/deploy")
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"].startswith("application/zip")
    disposition = zip_response.headers.get("content-disposition", "")
    assert re.search(r"filename=.+\.zip", disposition)


def test_demo_script_is_executable_and_sane() -> None:
    script = ROOT / "demo.sh"
    text = script.read_text(encoding="utf-8")
    assert script.stat().st_mode & 0o111
    assert "serve --demo" in text
    assert "demo-researcher" in text
    assert "demo-hook" in text
    assert "Demo ready" in text
