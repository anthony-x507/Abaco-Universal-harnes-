"""One real OpenAI-compatible HTTP provider. Configured only by env / Settings."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.exceptions import ProviderError
from universal.providers.base import Provider


class OpenAICompatProvider(Provider):
    """POST ``{base_url}/chat/completions`` with a Bearer token.

    Works with OpenAI, Azure-compatible gateways, OpenRouter, Ollama's OpenAI
    shim, and any other server that speaks the Chat Completions API. Hugging
    Face and MLX are deferred as real plugins — they are not stubbed here.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 60.0,
        organization: str = "",
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise ProviderError("Provider base_url is required")
        if not model:
            raise ProviderError("Provider model is required")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._organization = organization
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model(self) -> str:
        return self._model

    @property
    def completions_url(self) -> str:
        if self._base_url.endswith("/chat/completions"):
            return self._base_url
        return f"{self._base_url}/chat/completions"

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        if not self._api_key:
            raise ProviderError(
                "UNIVERSAL_LLM_API_KEY is empty. Set it before calling a live model."
            )
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [message.to_openai() for message in messages],
        }
        if tools:
            payload["tools"] = [spec.to_openai() for spec in tools]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        try:
            response = self._client.post(self.completions_url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderError(f"Provider timed out after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider HTTP error: {exc}") from exc

        if response.status_code >= 400:
            snippet = response.text[:400]
            raise ProviderError(f"Provider returned HTTP {response.status_code}: {snippet}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("Provider returned non-JSON") from exc

        return self._parse(data)

    def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        if tools:
            yield from super().stream(messages, tools=tools, model=model)
            return
        if not self._api_key:
            raise ProviderError(
                "UNIVERSAL_LLM_API_KEY is empty. Set it before calling a live model."
            )
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [message.to_openai() for message in messages],
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._organization:
            headers["OpenAI-Organization"] = self._organization
        try:
            with self._client.stream(
                "POST", self.completions_url, json=payload, headers=headers
            ) as response:
                if response.status_code >= 400:
                    snippet = response.read().decode("utf-8", errors="replace")[:400]
                    raise ProviderError(f"Provider returned HTTP {response.status_code}: {snippet}")
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                    except ValueError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        yield str(piece)
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError(f"Provider timed out after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider HTTP error: {exc}") from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OpenAICompatProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _parse(data: dict[str, Any]) -> CompletionResponse:
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("Provider response has no choices")
        message = choices[0].get("message") or {}
        raw_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=str(call.get("id") or ""),
                name=str((call.get("function") or {}).get("name") or ""),
                arguments=str((call.get("function") or {}).get("arguments") or "{}"),
            )
            for call in raw_calls
        ]
        text = message.get("content") or ""
        return CompletionResponse(
            text=text,
            tool_calls=tool_calls,
            model=str(data.get("model") or ""),
            finish_reason=str(choices[0].get("finish_reason") or "stop"),
            raw=data,
        )
