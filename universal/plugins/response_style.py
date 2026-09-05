"""Global response-style preference: concise, detailed, or default.

Native on every agent. Preference is stored under ``user_data_dir()`` and
defaults to concise. ``before_complete`` injects a style instruction;
``after_complete`` enforces the concise line budget without dropping
tool calls or other ``CompletionResponse`` metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from universal.core.plugin import Plugin
from universal.core.types import CompletionResponse, Message, ToolCall, ToolSpec
from universal.paths import user_data_dir
from universal.plugins._support import parse_tool_args

if TYPE_CHECKING:
    from universal.core.agent import Agent

ResponseStyle = Literal["concise", "detailed", "default"]

VALID_STYLES: frozenset[str] = frozenset({"concise", "detailed", "default"})
DEFAULT_STYLE: ResponseStyle = "concise"
CONCISE_MAX_NONEMPTY_LINES = 3
PREFERENCE_FILENAME = "response_style.json"
DETAIL_REQUEST_MARKERS = (
    "detail",
    "explain",
    "step by step",
    "show your work",
    "full answer",
    "in depth",
    "detall",
    "explica",
    "paso a paso",
    "respuesta completa",
    "profundidad",
)

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "concise": (
        "Response style: concise. Keep answers short — at most three non-empty lines. "
        "No preamble, no capability lists, no filler."
    ),
    "detailed": (
        "Response style: detailed. Give thorough, well-structured answers with enough "
        "context and steps to be complete."
    ),
    "default": (
        "Response style: default. Use a balanced length — clear and helpful without "
        "unnecessary verbosity."
    ),
}


def preference_path() -> Path:
    return user_data_dir() / PREFERENCE_FILENAME


def load_response_style() -> ResponseStyle:
    path = preference_path()
    if not path.is_file():
        return DEFAULT_STYLE
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_STYLE
    if not isinstance(loaded, dict):
        return DEFAULT_STYLE
    style = str(loaded.get("style") or "").strip().lower()
    if style in VALID_STYLES:
        return style  # type: ignore[return-value]
    return DEFAULT_STYLE


def save_response_style(style: str) -> ResponseStyle:
    normalized = str(style or "").strip().lower()
    if normalized not in VALID_STYLES:
        raise ValueError(f"style must be one of {sorted(VALID_STYLES)}")
    path = preference_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"style": normalized}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return normalized  # type: ignore[return-value]


def style_instruction(style: ResponseStyle | None = None) -> str:
    current = style if style is not None else load_response_style()
    return _STYLE_INSTRUCTIONS[current]


def enforce_concise_text(text: str, *, max_nonempty: int = CONCISE_MAX_NONEMPTY_LINES) -> str:
    """Keep at most ``max_nonempty`` non-empty lines; preserve blank-line layout up to that budget."""
    if not text:
        return text
    kept: list[str] = []
    nonempty = 0
    for line in text.splitlines():
        if line.strip():
            if nonempty >= max_nonempty:
                break
            nonempty += 1
            kept.append(line)
        elif nonempty > 0 and nonempty < max_nonempty:
            kept.append(line)
    return "\n".join(kept)


def requests_detail(messages: list[Message]) -> bool:
    """Honor an explicit request for detail even while concise is the saved default."""
    for message in reversed(messages):
        if message.role != "user":
            continue
        prompt = message.content.casefold()
        return any(marker in prompt for marker in DETAIL_REQUEST_MARKERS)
    return False


class ResponseStylePlugin(Plugin):
    def __init__(self) -> None:
        self._name = "response_style"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="set_response_style",
                description=(
                    "Set the global reply style for this Universal install: "
                    "concise (default, max three non-empty lines), detailed, or default."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "enum": ["concise", "detailed", "default"],
                            "description": "concise | detailed | default",
                        }
                    },
                    "required": ["style"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "set_response_style":
            return None
        args = parse_tool_args(call)
        style = str(args.get("style") or "").strip().lower()
        try:
            saved = save_response_style(style)
        except ValueError as exc:
            return f"Error: {exc}"
        return json.dumps({"style": saved, "path": str(preference_path())}, indent=2)

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        instruction = style_instruction()
        if not instruction:
            return messages
        style_msg = Message(role="system", content=instruction)
        if not messages:
            return [style_msg]
        # Keep an existing leading system prompt first; append style as a second system turn.
        if messages[0].role == "system":
            return [messages[0], style_msg, *messages[1:]]
        return [style_msg, *messages]

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        if load_response_style() != "concise" or requests_detail(messages):
            return response
        trimmed = enforce_concise_text(response.text)
        if trimmed == response.text:
            return response
        return CompletionResponse(
            text=trimmed,
            tool_calls=list(response.tool_calls),
            model=response.model,
            finish_reason=response.finish_reason,
            raw=response.raw,
        )
