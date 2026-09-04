"""Shared fixtures. FakeProvider never talks to a network."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from universal.config import Settings
from universal.core.platform import Universal
from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.providers.base import Provider


class FakeProvider(Provider):
    """Deterministic provider for tests. Optional scripted replies / tool calls."""

    def __init__(
        self,
        reply: str | Callable[[list[Message]], str] = "ok",
        *,
        model: str = "fake-model",
        tool_script: list[list[ToolCall]] | None = None,
    ) -> None:
        self._reply = reply
        self._model = model
        self.tool_script = list(tool_script or [])
        self.calls: list[list[Message]] = []

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        self.calls.append(list(messages))
        if self.tool_script:
            planned = self.tool_script.pop(0)
            if planned:
                return CompletionResponse(
                    text="",
                    tool_calls=planned,
                    model=self._model,
                    finish_reason="tool_calls",
                )
        if callable(self._reply):
            text = self._reply(messages)
        else:
            text = self._reply
        return CompletionResponse(text=text, model=self._model, finish_reason="stop")


@pytest.fixture(autouse=True)
def _isolate_memory_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNIVERSAL_MEMORY_DIR", str(tmp_path / "universal-memory"))
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "user-data"))
    from universal.nervous import provider_breaker

    provider_breaker().reset()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        llm_base_url="https://example.test/v1",
        llm_api_key="test-key",
        llm_model="fake-model",
    )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider(reply=lambda messages: f"echo:{messages[-1].content}")


@pytest.fixture
def platform(settings: Settings, provider: FakeProvider) -> Universal:
    return Universal(settings, provider=provider)
