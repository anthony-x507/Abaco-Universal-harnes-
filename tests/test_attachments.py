"""Image and audio uploads become real model input, not a path note."""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.server import create_app


def test_image_upload_is_described_not_just_a_path(platform: Universal, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    agent = platform.factory.create("general", name="eyes")
    platform.factory.start(agent.id)
    png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    ).decode("ascii")
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        f"/v1/agents/{agent.id}/ask",
        json={
            "prompt": "what is this",
            "attachments": [
                {"name": "shot.png", "mime": "image/png", "kind": "image", "data": png}
            ],
        },
    )
    assert response.status_code == 200
    history = response.json()["history"]
    user = next(turn for turn in history if turn["role"] == "user")
    assert "Attached image shot.png" in user["content"]
    assert "Binary content is not sent" not in user["content"]
    assert "image/png" in user["content"] or "shot.png" in user["content"]


def test_create_keeps_chosen_emoji(platform: Universal) -> None:
    client = TestClient(create_app(platform, demo=True))
    created = client.post(
        "/v1/agents",
        json={"template": "coder", "name": "bot", "emoji": "🦊"},
    )
    assert created.status_code == 200
    assert created.json()["emoji"] == "🦊"
    rows = client.get("/v1/templates").json()["templates"]
    faces = {row["id"]: row["emoji"] for row in rows}
    assert faces["general"] == "💬"
    assert faces["researcher"] == "🔎"
    assert faces["coder"] == "💻"
