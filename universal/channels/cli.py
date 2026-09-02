"""Working v1 channel: stdin/stdout, with a programmatic inject path for tests."""

from __future__ import annotations

from collections.abc import Callable
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

    def serve_once(self) -> str:
        inbound = self.receive()
        if inbound is None:
            return ""
        if inbound.text.strip() in {":q", "/quit", "/exit"}:
            self.stop()
            return ""
        return self.handle(inbound)

    def serve_forever(self, *, prompt: str = "you> ") -> None:
        self.start()
        while self._running:
            if prompt and self._stdin is None and self._reader is None:
                print(prompt, end="", flush=True)
            reply = self.serve_once()
            if not self._running:
                break
            if reply == "" and not self._inbox:
                # EOF with no reply ends the loop.
                if self._reader is None and self._stdin is not None:
                    break
                if self._reader is None and self._stdin is None and not self._inbox:
                    # input() EOF already returned None
                    pass
