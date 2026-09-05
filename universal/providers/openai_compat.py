"""Live HTTP provider. One client; dialect comes from ``ProviderAdapter``."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from universal.core.types import CompletionResponse, Message, ToolSpec
from universal.exceptions import ProviderError
from universal.providers.base import Provider, ProviderAdapter
from universal.providers.factory import detect_adapter_type, get_provider_adapter
from universal.providers.openai import OpenAIAdapter

EMPTY_KEY_MESSAGE = (
    "No API key for this agent. Save one in Chat, Settings, or the agent's Settings tab."
)


class OpenAICompatProvider(Provider):
    """POST through the selected adapter. Default dialect is OpenAI-compatible."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 60.0,
        organization: str = "",
        client: httpx.Client | None = None,
        adapter: ProviderAdapter | None = None,
        adapter_type: str | None = None,
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
        kind = adapter_type or detect_adapter_type(self._base_url, model)
        self._adapter = adapter or get_provider_adapter(kind, self._base_url, api_key, model)
        self._adapter.api_key = api_key
        self._adapter.model = model
        self.adapter_type = kind

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model(self) -> str:
        return self._model

    def apply_api_key(self, api_key: str) -> None:
        """Stamp a saved key onto this live client. Does not rebuild HTTP."""
        cleaned = (api_key or "").strip()
        if cleaned:
            self._api_key = cleaned
            self._adapter.api_key = cleaned

    @property
    def completions_url(self) -> str:
        return self._adapter.request_url()

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> CompletionResponse:
        self._require_key()
        if model:
            self._adapter.model = model
        payload = self._adapter.build_payload(
            messages, tools=tools, model=model or self._model, stream=False
        )
        return self._adapter.parse_response(self._post_json(payload, stream=False))

    def complete_vision(
        self,
        *,
        prompt: str,
        image_b64: str,
        mime: str = "image/jpeg",
        model: str | None = None,
    ) -> str:
        """One multimodal completion on the same HTTP client. Not a second provider."""
        self._require_key()
        if not isinstance(self._adapter, OpenAIAdapter):
            raise ProviderError("Vision is only available on OpenAI-compatible hosts")
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                        },
                    ],
                }
            ],
        }
        return self._adapter.parse_response(self._post_json(payload, stream=False)).text or ""

    def _require_key(self) -> None:
        if self._api_key or self._adapter.allows_empty_key():
            return
        raise ProviderError(EMPTY_KEY_MESSAGE)

    def _headers(self) -> dict[str, str]:
        headers = dict(self._adapter.get_headers())
        if self._organization and "OpenAI-Organization" not in headers:
            headers["OpenAI-Organization"] = self._organization
        return headers

    def _post_json(self, payload: dict[str, Any], *, stream: bool) -> dict[str, Any]:
        url = self._adapter.request_url(stream=stream)
        try:
            response = self._client.post(url, json=payload, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderError("LLM request timed out", status_code=408) from exc
        except httpx.ConnectError as exc:
            raise ProviderError("Cannot reach LLM service", status_code=503) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider HTTP error: {exc}", status_code=502) from exc
        if response.status_code >= 400:
            raise self._http_status_error(response.status_code, response.text[:400])
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("Provider returned non-JSON") from exc
        if not isinstance(data, dict):
            raise ProviderError("Provider returned non-object JSON")
        return data

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
        self._require_key()
        if model:
            self._adapter.model = model
        payload = self._adapter.build_payload(
            messages, tools=None, model=model or self._model, stream=True
        )
        url = self._adapter.request_url(stream=True)
        try:
            with self._client.stream("POST", url, json=payload, headers=self._headers()) as response:
                if response.status_code >= 400:
                    snippet = response.read().decode("utf-8", errors="replace")[:400]
                    raise self._http_status_error(response.status_code, snippet)
                for line in response.iter_lines():
                    if not line:
                        continue
                    piece = self._adapter.parse_stream_line(line)
                    if piece:
                        yield piece
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError("LLM request timed out", status_code=408) from exc
        except httpx.ConnectError as exc:
            raise ProviderError("Cannot reach LLM service", status_code=503) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider HTTP error: {exc}", status_code=502) from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OpenAICompatProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _http_status_error(status_code: int, snippet: str) -> ProviderError:
        if status_code == 401:
            return ProviderError("Invalid API key", status_code=401)
        if status_code == 429:
            return ProviderError("Rate limit exceeded", status_code=429)
        if status_code == 408:
            return ProviderError("LLM request timed out", status_code=408)
        return ProviderError(f"LLM error: HTTP {status_code}: {snippet}", status_code=status_code)
