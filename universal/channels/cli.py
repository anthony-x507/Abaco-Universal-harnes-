"""Working v1 channel: stdin/stdout, with a programmatic inject path for tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TextIO

from universal.channels.base import (
    BaseCommunication,
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)


class CLIChannel(BaseCommunication):
    """Local CLI transport.

    ``serve_once`` / ``serve_forever`` pull lines, call the bound handler
    (normally ``agent.complete``), and print the reply. Tests inject lines
    via ``deliver`` without touching a real TTY.
    """

    def __init__(
        self,
        *,
        reader: Callable[[], str] | None = None,
        writer: Callable[[str], None] | None = None,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._stdin = stdin
        self._stdout = stdout
        self._handler: MessageHandler | None = None
        self._stream_handler: Callable[[InboundMessage], Iterator[object]] | None = None
        self._running = False
        self._inbox: list[str] = []

    @property
    def name(self) -> str:
        return "cli"

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def bind(self, handler: MessageHandler) -> None:
        self._handler = handler

    def bind_stream(self, handler: Callable[[InboundMessage], Iterator[object]]) -> None:
        self._stream_handler = handler

    def send(self, message: OutboundMessage) -> None:
        text = message.text if message.text.endswith("\n") else message.text + "\n"
        if self._writer is not None:
            self._writer(text.rstrip("\n"))
            return
        stream = self._stdout
        if stream is None:
            print(message.text)
            return
        stream.write(text)
        stream.flush()

    def deliver(self, text: str) -> None:
        """Queue a line as if the user typed it (tests and programmatic clients)."""
        self._inbox.append(text)

    def receive(self) -> InboundMessage | None:
        if self._inbox:
            return InboundMessage(text=self._inbox.pop(0), sender_id="local")
        try:
            if self._reader is not None:
                line = self._reader()
            elif self._stdin is not None:
                line = self._stdin.readline()
                if line == "":
                    return None
            else:
                line = input()
        except EOFError:
            return None
        return InboundMessage(text=line.rstrip("\n"), sender_id="local")

    def handle(self, inbound: InboundMessage) -> str:
        if self._handler is None:
            raise RuntimeError("CLIChannel.bind() was not called")
        result = self._handler(inbound)
        if result is None:
            return ""
        if isinstance(result, OutboundMessage):
            self.send(result)
            return result.text
        outbound = OutboundMessage(text=result)
        self.send(outbound)
        return result

    def handle_text(self, text: str) -> str:
        return self.handle(InboundMessage(text=text, sender_id="local"))

    def handle_text_stream(self, text: str) -> Iterator[object]:
        """Push one inbound string through the stream handler, then send the full reply."""
        inbound = InboundMessage(text=text, sender_id="local")
        if self._stream_handler is None:
            yield self.handle(inbound)
            return
        parts: list[str] = []
        for piece in self._stream_handler(inbound):
            if isinstance(piece, dict):
                yield piece
                token = piece.get("text") if piece.get("type") == "token" else None
                if token:
                    parts.append(str(token))
                continue
            parts.append(str(piece))
            yield piece
        full = "".join(parts)
        if full:
            self.send(OutboundMessage(text=full))

    @contextmanager
    def capture(self) -> Iterator[list[str]]:
        """Temporarily send outbound text into a list (JSON ask, tests)."""
        chunks: list[str] = []
        prev_writer = self._writer
        prev_stdout = self._stdout
        self._writer = chunks.append
        self._stdout = None
        try:
            yield chunks
        finally:
            self._writer = prev_writer
            self._stdout = prev_stdout

    def serve_once(self) -> str:
        inbound = self.receive()
        if inbound is None:
            self.stop()
            return ""
        stripped = inbound.text.strip()
        if stripped in {":q", "/quit", "/exit"}:
            self.stop()
            return ""
        if not stripped:
            return ""
        return self.handle(inbound)

    def serve_forever(self, *, prompt: str = "you> ") -> None:
        """Read / handle / print until quit or EOF. Used by ``universal chat``."""
        if not self._running:
            self.start()
        while self._running:
            if prompt:
                print(prompt, end="", flush=True)
            self.serve_once()
