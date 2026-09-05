"""Native Google Gemini generateContent dialect."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.exceptions import ProviderError
from universal.providers.base import ProviderAdapter


class GoogleAdapter(ProviderAdapter):
    """API key as query param + ``:generateContent``."""

    name = "google"

    def get_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def request_url(self, *, stream: bool = False) -> str:
        method = "streamGenerateContent" if stream else "generateContent"
        model = self.model or "gemini-pro"
        if "/models/" in self.base_url:
            root = self.base_url
        else:
            root = f"{self.base_url.rstrip('/')}/models/{model}"
        url = f"{root}:{method}"
        if self.api_key:
            url = f"{url}?{urlencode({'key': self.api_key})}"
        return url

    def build_payload(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        if model:
            self.model = model
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            if message.role == "tool":
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": message.name or "tool",
                                    "response": {"result": message.content},
                                }
                            }
                        ],
                    }
                )
                continue
            role = "model" if message.role == "assistant" else "user"
            parts: list[dict[str, Any]] = []
            if message.content:
                parts.append({"text": message.content})
            if message.role == "assistant" and message.tool_calls:
                for call in message.tool_calls:
                    try:
                        args = json.loads(call.arguments or "{}")
                    except ValueError:
                        args = {"raw": call.arguments}
                    parts.append({"functionCall": {"name": call.name, "args": args}})
            contents.append({"role": role, "parts": parts or [{"text": ""}]})
        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        if tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": spec.name,
                            "description": spec.description,
                            "parameters": spec.parameters or {"type": "object", "properties": {}},
                        }
                        for spec in tools
                    ]
                }
            ]
        return payload

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        candidates = data.get("candidates") or []
        if not candidates:
            raise ProviderError("Gemini response has no candidates")
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        texts: list[str] = []
        tool_calls: list[ToolCall] = []
        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                continue
            if part.get("text"):
                texts.append(str(part["text"]))
            call = part.get("functionCall") or {}
            name = str(call.get("name") or "")
            if name:
                args = call.get("args") or {}
                arguments = args if isinstance(args, str) else json.dumps(args)
                tool_calls.append(
                    ToolCall(id=f"call_{index}", name=name, arguments=arguments or "{}")
                )
        finish = str(candidates[0].get("finishReason") or "STOP").lower()
        if finish == "stop":
            finish = "stop"
        return CompletionResponse(
            text="".join(texts),
            tool_calls=tool_calls,
            model=self.model,
            finish_reason="tool_calls" if tool_calls else finish,
            raw=data,
        )

    def parse_stream_line(self, line: str) -> str | None:
        payload = line.strip()
        if payload.startswith("data:"):
            payload = payload[5:].strip()
        if not payload:
            return None
        try:
            data = json.loads(payload)
        except ValueError:
            return None
        try:
            return self.parse_response(data).text or None
        except ProviderError:
            return None
