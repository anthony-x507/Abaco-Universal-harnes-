"""Native Anthropic Messages API dialect."""

from __future__ import annotations

import json
from typing import Any

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.exceptions import ProviderError
from universal.providers.base import ProviderAdapter


class AnthropicAdapter(ProviderAdapter):
    """``x-api-key`` + POST ``/v1/messages``."""

    name = "anthropic"

    def get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def request_url(self, *, stream: bool = False) -> str:
        if self.base_url.endswith("/messages"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}/v1/messages"

    def build_payload(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        system_parts: list[str] = []
        body: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            if message.role == "tool":
                body.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id or "tool",
                                "content": message.content,
                            }
                        ],
                    }
                )
                continue
            if message.role == "assistant" and message.tool_calls:
                blocks: list[dict[str, Any]] = []
                if message.content:
                    blocks.append({"type": "text", "text": message.content})
                for call in message.tool_calls:
                    try:
                        inp = json.loads(call.arguments or "{}")
                    except ValueError:
                        inp = {"raw": call.arguments}
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": call.name,
                            "input": inp,
                        }
                    )
                body.append({"role": "assistant", "content": blocks})
                continue
            role = "assistant" if message.role == "assistant" else "user"
            body.append({"role": role, "content": message.content})
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": body,
            "max_tokens": 4096,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if stream:
            payload["stream"] = True
        if tools:
            payload["tools"] = [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "input_schema": spec.parameters or {"type": "object", "properties": {}},
                }
                for spec in tools
            ]
        return payload

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        blocks = data.get("content") or []
        if not isinstance(blocks, list):
            raise ProviderError("Anthropic response has no content")
        texts: list[str] = []
        tool_calls: list[ToolCall] = []
        for index, block in enumerate(blocks):
            if not isinstance(block, dict):
                continue
            kind = str(block.get("type") or "")
            if kind == "text":
                texts.append(str(block.get("text") or ""))
            elif kind == "tool_use":
                name = str(block.get("name") or "")
                if not name:
                    continue
                raw_in = block.get("input") or {}
                arguments = raw_in if isinstance(raw_in, str) else json.dumps(raw_in)
                tool_calls.append(
                    ToolCall(
                        id=str(block.get("id") or f"call_{index}"),
                        name=name,
                        arguments=arguments or "{}",
                    )
                )
        finish = str(data.get("stop_reason") or "stop")
        if finish == "tool_use":
            finish = "tool_calls"
        return CompletionResponse(
            text="".join(texts),
            tool_calls=tool_calls,
            model=str(data.get("model") or self.model or ""),
            finish_reason=finish,
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
        if data.get("type") != "content_block_delta":
            return None
        delta = data.get("delta") or {}
        text = delta.get("text")
        return str(text) if text else None
