"""Describe a local image via the bound provider, or a demo caption."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args

if TYPE_CHECKING:
    from universal.core.agent import Agent


class VisionPlugin(Plugin):
    """Uses the agent’s provider when it exposes complete_vision; otherwise demo text."""

    def __init__(self) -> None:
        self._name = "vision"
        self._agent: Agent | None = None

    @property
    def name(self) -> str:
        return self._name

    def on_attach(self, agent: Agent) -> None:
        self._agent = agent

    def on_detach(self, agent: Agent) -> None:
        if self._agent is agent:
            self._agent = None

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="describe_image",
                description="Describe a local image using the bound vision-capable provider.",
                parameters={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to an image file"},
                        "prompt": {
                            "type": "string",
                            "description": "Optional prompt for the vision model",
                        },
                    },
                    "required": ["image_path"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "describe_image":
            return None
        args = parse_tool_args(call)
        image_path = str(args.get("image_path") or "").strip()
        prompt = str(args.get("prompt") or "Describe this image in detail")
        return self._describe(image_path, prompt)

    def _describe(self, image_path: str, prompt: str) -> str:
        if not image_path:
            return "Error: image_path is required"
        path = Path(image_path)
        if not path.is_file():
            return f"Error: file not found: {image_path}"
        try:
            data = path.read_bytes()
        except OSError as exc:
            return f"Error reading image: {exc}"
        mime, _ = mimetypes.guess_type(path.name)
        mime = mime or "image/jpeg"
        encoded = base64.b64encode(data).decode("ascii")
        provider = getattr(self._agent, "provider", None)
        vision = getattr(provider, "complete_vision", None)
        if callable(vision):
            try:
                return str(vision(prompt=prompt, image_b64=encoded, mime=mime))
            except Exception as exc:
                return f"Error analyzing image: {exc}"
        size = path.stat().st_size
        return (
            f"(demo) image: {path.name} ({size} bytes, {mime}). "
            f"Prompt: {prompt}"
        )
