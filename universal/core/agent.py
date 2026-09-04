"""Minimal agent that completes a prompt via the provider, with a tool loop."""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from universal.channels.base import InboundMessage
from universal.core.plugin import Plugin, PluginHost
from universal.core.types import AgentInfo, AgentState, CompletionResponse, Message, utcnow
from universal.core.usage import UsageStats, record_provider_call

_NAME_FACT = re.compile(r"\bmy name is\s+(.+?)(?:[.!?]|$)", re.IGNORECASE)
DEFAULT_HISTORY_TURNS = 10
TOOL_REPEAT_LIMIT = 3
TOOL_LIMIT_MESSAGE = (
    "The agent could not finish this task within the tool-call limit. "
    "Try a simpler question, or turn Auto off."
)
TOOL_REPEAT_NUDGE = (
    "You already called this tool repeatedly. Give a final answer now from "
    "the tool results you have. Do not call tools again."
)

if TYPE_CHECKING:
    from universal.channels.base import BaseCommunication
    from universal.providers.base import Provider


def new_agent_id() -> str:
    return uuid.uuid4().hex[:12]


class Agent:
    """An assembled agent: model + channel + plugins, identified in the registry.

    ``complete(prompt)`` is the working path for v1: it runs plugin hooks, calls
    the provider, and loops on tool calls until the model returns text.
    """

    def __init__(
        self,
        *,
        name: str,
        provider: Provider,
        template_id: str,
        system_prompt: str = "",
        channel: BaseCommunication | None = None,
        agent_id: str | None = None,
        max_tool_iters: int = 8,
        memory: bool = False,
        memory_dir: Path | None = None,
        max_history_turns: int = DEFAULT_HISTORY_TURNS,
        emoji: str = "",
        llm_model: str = "",
    ) -> None:
        self.id = agent_id or new_agent_id()
        self.name = name
        self.template_id = template_id
        self.emoji = emoji
        self.system_prompt = system_prompt
        self.llm_model = (llm_model or "").strip()
        self.provider = provider
        self.channel = channel
        self.plugins = PluginHost()
        self.max_tool_iters = max_tool_iters
        self.max_history_turns = max_history_turns
        self.memory_enabled = memory
        self.memory_dir = memory_dir
        self.memory_data: dict[str, Any] = {"facts": [], "last_conversation": ""}
        self.created_at = utcnow()
        self._history: list[Message] = []
        self.usage = UsageStats()
        if memory:
            self._load_memory()

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    def attach_plugin(self, plugin: Plugin, *, replace: bool = True) -> None:
        """Hot-swap: install (or replace) a plugin on this agent."""
        self.plugins.install(plugin, self, replace=replace)

    def detach_plugin(self, name: str) -> Plugin:
        """Hot-swap: remove a plugin from this agent."""
        return self.plugins.uninstall(name, self)

    def record_turn(self, prompt: str, answer: str) -> None:
        """Persist one inbound turn that the Node runtime already answered."""
        self._history.append(Message(role="user", content=prompt))
        self._history.append(Message(role="assistant", content=answer))

    def reset_history(self) -> None:
        self._history.clear()
        transcript = self.plugins.get("transcript")
        clear = getattr(transcript, "clear", None)
        if callable(clear):
            clear()

    def memory_path(self) -> Path:
        from universal.paths import get_memory_dir

        root = self.memory_dir or get_memory_dir()
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in self.name)[:80] or "agent"
        return root / f"{safe}.json"

    def _load_memory(self) -> None:
        path = self.memory_path()
        if not path.is_file():
            return
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(loaded, dict):
            self.memory_data = {
                "facts": list(loaded.get("facts") or []),
                "last_conversation": str(loaded.get("last_conversation") or ""),
            }

    def _save_memory(self) -> None:
        path = self.memory_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.memory_data, indent=2), encoding="utf-8")

    def _update_memory(self, user_text: str, answer: str) -> None:
        match = _NAME_FACT.search(user_text)
        if match:
            person = match.group(1).strip()
            facts = [
                fact
                for fact in list(self.memory_data.get("facts") or [])
                if not str(fact).startswith("The user's name is ")
            ]
            facts.append(f"The user's name is {person}.")
            self.memory_data["facts"] = facts[-20:]
        self.memory_data["last_conversation"] = f"User: {user_text}\nAgent: {answer}"
        self._save_memory()

    def _history_for_provider(self) -> list[Message]:
        limit = max(0, self.max_history_turns) * 2
        if limit == 0:
            return []
        return self._history[-limit:]

    def plugin_labels(self) -> list[str]:
        """Readable plugin names for the UI (not internal catalog ids)."""
        labels: list[str] = []
        for plugin in self.plugins.all():
            tools = plugin.tools()
            names = [spec.name for spec in tools if spec.name]
            title = plugin.name.replace("_", " ").title()
            if plugin.name == "tools" and names:
                labels.append("Tools: " + ", ".join(names))
            elif names:
                labels.append(f"{title}: {', '.join(names)}")
            else:
                labels.append(title)
        return labels

    def identity_record(self) -> dict[str, Any]:
        """Identity fields for the registry sidecar. No history, no secrets."""
        channel = self.channel
        outbound = getattr(channel, "outbound_url", "") or ""
        return {
            "id": self.id,
            "name": self.name,
            "template_id": self.template_id,
            "channel": channel.name if channel is not None else "cli",
            "outbound_url": outbound,
            "memory": self.memory_enabled,
            "plugins": self.plugins.names(),
            "emoji": self.emoji,
            "system_prompt": self.system_prompt,
            "llm_model": self.llm_model,
        }

    @contextmanager
    def tool_iter_limit(self, max_iterations: int | None) -> Iterator[None]:
        if max_iterations is None:
            yield
            return
        previous = self.max_tool_iters
        self.max_tool_iters = max(1, int(max_iterations))
        try:
            yield
        finally:
            self.max_tool_iters = previous

    def _prompt_messages(self, prompt: str) -> tuple[Message, list[Message]]:
        user = Message(role="user", content=prompt)
        turn: list[Message] = []
        if self.system_prompt:
            turn.append(Message(role="system", content=self.system_prompt))
        facts = [str(fact) for fact in (self.memory_data.get("facts") or [])] if self.memory_enabled else []
        if facts:
            turn.append(Message(role="system", content="Persistent memory:\n" + "\n".join(facts)))
        turn.extend(self._history_for_provider())
        turn.append(user)
        return user, turn

    def complete(self, prompt: str, *, remember: bool = True) -> str:
        """Send ``prompt`` through plugins and the provider; return assistant text."""
        user, turn = self._prompt_messages(prompt)
        turn = self.plugins.before_complete(self, turn)

        tools = self.plugins.collect_tools()
        working = list(turn)
        response = self._run_tool_loop(working, tools)

        response = self.plugins.after_complete(self, working, response)
        if remember:
            self._history.append(user)
            self._history.append(Message(role="assistant", content=response.text))
        if self.memory_enabled:
            self._update_memory(prompt, response.text)
        return response.text

    def complete_stream_events(self, prompt: str, *, remember: bool = True) -> Iterator[dict[str, object]]:
        """Same path as ``complete_stream``, plus status events for the factory SSE."""
        user, turn = self._prompt_messages(prompt)
        turn = self.plugins.before_complete(self, turn)

        tools = self.plugins.collect_tools()
        working = list(turn)
        assembled = ""

        if tools:
            response = yield from self._run_tool_loop_events(working, tools)
            response = self.plugins.after_complete(self, working, response)
            assembled = response.text
            if assembled:
                yield {"type": "token", "text": assembled}
        else:
            pieces: list[str] = []
            started = time.perf_counter()
            for piece in self.provider.stream(working, tools=None, model=self.llm_model or None):
                pieces.append(piece)
                yield {"type": "token", "text": piece}
            assembled = "".join(pieces)
            response = CompletionResponse(text=assembled, model=getattr(self.provider, "model", "") or "")
            record_provider_call(
                self,
                response,
                messages=working,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            response = self.plugins.after_complete(self, working, response)
            assembled = response.text

        if remember:
            self._history.append(user)
            self._history.append(Message(role="assistant", content=assembled))
        if self.memory_enabled:
            self._update_memory(prompt, assembled)

    def complete_stream(self, prompt: str, *, remember: bool = True) -> Iterator[str]:
        """Same plugin/tool path as ``complete``, yielding final-text deltas."""
        for event in self.complete_stream_events(prompt, remember=remember):
            if event.get("type") == "token" and event.get("text"):
                yield str(event["text"])

    def _provider_complete(
        self, working: list[Message], tools: list[Any] | None
    ) -> CompletionResponse:
        started = time.perf_counter()
        response = self.provider.complete(
            working, tools=tools or None, model=self.llm_model or None
        )
        record_provider_call(
            self,
            response,
            messages=working,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        return response

    def _apply_tool_calls(self, working: list[Message], response: CompletionResponse) -> None:
        working.append(
            Message(
                role="assistant",
                content=response.text or "",
                tool_calls=response.tool_calls,
            )
        )
        for i, call in enumerate(response.tool_calls):
            if not call.id:
                call.id = f"call_{i}"
            try:
                result = self.plugins.invoke_tool(call)
            except Exception as exc:
                result = f"error: tool {call.name!r} failed: {exc}"
            working.append(
                Message(
                    role="tool",
                    content=result,
                    name=call.name,
                    tool_call_id=call.id,
                )
            )

    def _close_tool_loop(self, working: list[Message]) -> CompletionResponse:
        working.append(Message(role="user", content=TOOL_REPEAT_NUDGE))
        response = self._provider_complete(working, None)
        text = (response.text or "").strip()
        if not text or response.wants_tools:
            return CompletionResponse(
                text=TOOL_LIMIT_MESSAGE,
                model=response.model,
                finish_reason="stop",
            )
        return response

    def _run_tool_loop(self, working: list[Message], tools: list[Any]) -> CompletionResponse:
        streak = 0
        last_names: tuple[str, ...] | None = None
        response: CompletionResponse | None = None
        for _ in range(self.max_tool_iters):
            response = self._provider_complete(working, tools)
            if not response.wants_tools:
                return response
            names = tuple(call.name for call in response.tool_calls)
            streak = streak + 1 if names == last_names else 1
            last_names = names
            self._apply_tool_calls(working, response)
            if streak >= TOOL_REPEAT_LIMIT:
                return self._close_tool_loop(working)
        return self._close_tool_loop(working)

    def _run_tool_loop_events(
        self, working: list[Message], tools: list[Any]
    ) -> Iterator[dict[str, object]]:
        streak = 0
        last_names: tuple[str, ...] | None = None
        for _ in range(self.max_tool_iters):
            response = self._provider_complete(working, tools)
            if not response.wants_tools:
                return response
            names = tuple(call.name for call in response.tool_calls)
            streak = streak + 1 if names == last_names else 1
            last_names = names
            self._apply_tool_calls(working, response)
            for call in response.tool_calls:
                yield self._status_event_for_tool(call)
            if streak >= TOOL_REPEAT_LIMIT:
                return self._close_tool_loop(working)
        return self._close_tool_loop(working)

    @staticmethod
    def _status_event_for_tool(call: object) -> dict[str, object]:
        name = str(getattr(call, "name", "") or "")
        if name in {"call_agent", "delegate"}:
            target = name
            raw = str(getattr(call, "arguments", "") or "")
            try:
                args = json.loads(raw) if raw else {}
            except ValueError:
                args = {}
            if isinstance(args, dict):
                target = str(args.get("name") or args.get("target") or name)
            return {"type": "delegating", "target": target}
        return {"type": "tool_execution", "tool": name}

    def info(self, state: AgentState = AgentState.CREATED) -> AgentInfo:
        channel_name = self.channel.name if self.channel is not None else ""
        model = self.llm_model or getattr(self.provider, "model", "") or ""
        return AgentInfo(
            id=self.id,
            name=self.name,
            template_id=self.template_id,
            state=state,
            channel=channel_name,
            plugins=self.plugins.names(),
            created_at=self.created_at,
            model=str(model),
            emoji=self.emoji,
        )

    def bind_channel(self) -> None:
        """Point the channel handler at this agent's ``complete``."""
        if self.channel is None:
            return

        def _handle(inbound: InboundMessage) -> str:
            return self.complete(inbound.text)

        self.channel.bind(_handle)
        bind_stream = getattr(self.channel, "bind_stream", None)
        if callable(bind_stream):
            bind_stream(lambda inbound: self.complete_stream_events(inbound.text))

    def run(self, prompt: str, *, max_iterations: int = 5) -> str:
        """Autonomous layer above ``accept``: same inbound, tighter tool budget.

        ``complete`` already loops tools. This only caps ``max_tool_iters`` for
        one inbound turn and still goes through the bound channel.
        """
        with self.tool_iter_limit(max_iterations):
            return self.accept(prompt)

    def run_stream_events(
        self, prompt: str, *, max_iterations: int = 5
    ) -> Iterator[dict[str, object]]:
        with self.tool_iter_limit(max_iterations):
            yield from self.accept_stream_events(prompt)

    def accept(self, text: str) -> str:
        """Inbound path after ``factory.start``: go through the bound channel.

        ``complete`` stays the model path (what the channel handler calls).
        Using ``complete`` from a started agent would skip the channel
        contract. If no channel is assembled, this falls back to ``complete``.
        """
        if self.channel is None:
            return self.complete(text)
        return self.channel.handle_text(text)

    def accept_stream(self, text: str) -> Iterator[str]:
        """Inbound streaming path after ``factory.start``. Still channel-shaped."""
        for event in self.accept_stream_events(text):
            if event.get("type") == "token" and event.get("text"):
                yield str(event["text"])

    def accept_stream_events(self, text: str) -> Iterator[dict[str, object]]:
        """Inbound stream with status events. Still goes through the bound channel."""
        if self.channel is None:
            yield from self.complete_stream_events(text)
            return
        handle_stream = getattr(self.channel, "handle_text_stream", None)
        if not callable(handle_stream):
            yield {"type": "token", "text": self.channel.handle_text(text)}
            return
        for piece in handle_stream(text):
            if isinstance(piece, dict):
                yield piece
            elif piece:
                yield {"type": "token", "text": str(piece)}
