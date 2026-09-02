"""In-process factory session. One Universal instance; no second store."""

from __future__ import annotations

import shlex
from pathlib import Path

from universal.channels.cli import CLIChannel
from universal.core.platform import Universal
from universal.exceptions import UniversalError
from universal.templates.catalog import list_templates


class FactorySession:
    """Runs create / start / stop / list / delete / ask / deploy against one root.

    This is how factory operations stay on the injected registry. A disk or
    sqlite catalog would be a second registry and is intentionally not added.
    """

    def __init__(self, platform: Universal) -> None:
        self.platform = platform

    def execute(self, line: str) -> str:
        text = line.strip()
        if not text or text.startswith("#"):
            return ""
        try:
            parts = shlex.split(text)
        except ValueError as exc:
            return f"error: {exc}"
        command, *rest = parts
        handler = {
            "help": self._help,
            "templates": self._templates,
            "create": self._create,
            "list": self._list,
            "start": self._start,
            "stop": self._stop,
            "delete": self._delete,
            "ask": self._ask,
            "deploy": self._deploy,
            "quit": self._quit,
            "exit": self._quit,
        }.get(command)
        if handler is None:
            return f"error: unknown command {command!r}. Type help."
        try:
            return handler(rest)
        except UniversalError as exc:
            return f"error: {exc}"

    def _help(self, _args: list[str]) -> str:
        return (
            "commands: templates | create <template> [--name NAME] | list | "
            "start <id> | stop <id> | delete <id> | ask <id> <prompt> | "
            "deploy <id> [--out PATH] | help | quit"
        )

    def _templates(self, _args: list[str]) -> str:
        return "\n".join(f"{t.id}\t{t.name}\t{t.description}" for t in list_templates())

    def _create(self, args: list[str]) -> str:
        if not args:
            return "error: create <template> [--name NAME]"
        template = args[0]
        name = _option(args[1:], "--name")
        agent = self.platform.factory.create(template, name)
        return agent.id

    def _list(self, _args: list[str]) -> str:
        infos = self.platform.factory.list()
        if not infos:
            return "(empty)"
        return "\n".join(
            f"{info.id}\t{info.name}\t{info.template_id}\t{info.state.value}" for info in infos
        )

    def _start(self, args: list[str]) -> str:
        if not args:
            return "error: start <id>"
        agent = self.platform.factory.start(args[0])
        return agent.id

    def _stop(self, args: list[str]) -> str:
        if not args:
            return "error: stop <id>"
        agent = self.platform.factory.stop(args[0])
        return agent.id

    def _delete(self, args: list[str]) -> str:
        if not args:
            return "error: delete <id>"
        agent = self.platform.factory.delete(args[0])
        return agent.id

    def _ask(self, args: list[str]) -> str:
        if len(args) < 2:
            return "error: ask <id> <prompt>"
        agent_id, prompt = args[0], " ".join(args[1:])
        agent = self.platform.registry.get(agent_id)
        self.platform.factory.start(agent.id)
        channel = agent.channel
        if isinstance(channel, CLIChannel):
            with channel.capture():
                return agent.accept(prompt)
        return agent.accept(prompt)

    def _deploy(self, args: list[str]) -> str:
        if not args:
            return "error: deploy <id> [--out PATH]"
        dest = _option(args[1:], "--out")
        path = self.platform.factory.deploy(args[0], Path(dest) if dest else None)
        return str(path)

    def _quit(self, _args: list[str]) -> str:
        return "quit"


def _option(args: list[str], flag: str) -> str | None:
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return None
