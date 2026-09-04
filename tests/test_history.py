"""Chat history is stored under user data, not in the registry sidecar."""

from __future__ import annotations

import json
from pathlib import Path

from universal.config import Settings
from universal.core.platform import Universal
from universal.paths import get_history_dir
from tests.conftest import FakeProvider


def test_history_reloads_after_a_new_root(tmp_path: Path, settings: Settings, provider: FakeProvider) -> None:
    persist = tmp_path / "registry.json"
    first = Universal(settings, provider=provider, persist_path=persist)
    agent = first.factory.create("general", name="keep-chat")
    first.factory.start(agent.id)
    agent.complete("remember this thread")
    path = agent.history_path()
    assert path.is_file()
    assert path.parent == get_history_dir()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored[0]["content"] == "remember this thread"
    assert "history" not in json.loads(persist.read_text())["agents"][0]

    second = Universal(settings, provider=FakeProvider(reply="fresh"), persist_path=persist)
    restored = second.registry.get(agent.id)
    assert [turn.content for turn in restored.history] == [
        "remember this thread",
        "echo:remember this thread",
    ]


def test_reset_and_delete_remove_the_history_file(platform: Universal) -> None:
    agent = platform.factory.create("general", name="wipe-chat")
    platform.factory.start(agent.id)
    agent.complete("gone soon")
    path = agent.history_path()
    assert path.is_file()
    agent.reset_history()
    assert agent.history == []
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == []
    agent_id = agent.id
    platform.factory.delete(agent_id)
    assert not path.exists()
