"""OpenAI Chat Completions dialect (DeepSeek, Groq, OpenRouter, and shims)."""

from __future__ import annotations

import json
from typing import Any

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.exceptions import ProviderError
from universal.providers.base import ProviderAdapter


class OpenAIAdapter(ProviderAdapter):
    """Bearer token + POST ``{base}/chat/completions``."""

    name = "openai"

    def get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def request_url(self, *, stream: bool = False) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def build_payload(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [message.to_openai() for message in messages],
        }
        if stream:
            payload["stream"] = True
        if tools:
            payload["tools"] = [spec.to_openai() for spec in tools]
            payload["tool_choice"] = "auto"
        return payload

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("Provider response has no choices")
        message = choices[0].get("message") or {}
        raw_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for index, call in enumerate(raw_calls):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(fn.get("name") or call.get("name") or "")
            if not name:
                continue
            arguments = fn.get("arguments", call.get("arguments", "{}"))
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments)
            tool_calls.append(
                ToolCall(
                    id=str(call.get("id") or f"call_{index}"),
                    name=name,
                    arguments=arguments or "{}",
                )
            )
        text = message.get("content") or ""
        return CompletionResponse(
            text=text,
            tool_calls=tool_calls,
            model=str(data.get("model") or self.model or ""),
            finish_reason=str(choices[0].get("finish_reason") or "stop"),
            raw=data,
        )

    def parse_stream_line(self, line: str) -> str | None:
        payload = line.strip()
        if payload.startswith("data:"):
            payload = payload[5:].strip()
        if not payload or payload == "[DONE]":
            return None
        try:
            data = json.loads(payload)
        except ValueError:
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta") or {}
        piece = delta.get("content")
        return str(piece) if piece else None
