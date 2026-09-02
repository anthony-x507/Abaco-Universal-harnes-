"""Command-line entry for the Universal platform."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from universal._version import __version__
from universal.channels.cli import CLIChannel
from universal.config import Settings
from universal.core.platform import Universal
from universal.exceptions import UniversalError
from universal.session import FactorySession
from universal.templates.catalog import list_templates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universal",
        description="Universal platform — plugin-based agent factory and harness.",
    )
    parser.add_argument("--version", action="version", version=f"universal {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Create a one-shot agent and print its answer.")
    ask.add_argument("prompt", help="User prompt to complete.")
    ask.add_argument("--template", "-t", default="general", help="Template id (default: general).")
    ask.add_argument("--name", help="Optional agent name.")
    ask.add_argument("--json", action="store_true", help="Print a JSON object instead of plain text.")

    chat = sub.add_parser("chat", help="Interactive loop on the CLI channel. Type /quit to exit.")
    chat.add_argument("--template", "-t", default="general")
    chat.add_argument("--name", help="Optional agent name.")

    templates = sub.add_parser("templates", help="List the three built-in templates.")
    templates.add_argument("--json", action="store_true")

    create = sub.add_parser(
        "create",
        help="Create an agent in this process and print its id (gone when the process exits).",
    )
    create.add_argument("template", help="Template id: general, researcher, or coder.")
    create.add_argument("--name", help="Optional agent name.")

    sub.add_parser(
        "list",
        help="List agents in this process only. Use `universal shell` to keep a registry alive.",
    )

    deploy = sub.add_parser("deploy", help="Create an agent and write a ZIP package.")
    deploy.add_argument("template", nargs="?", default="general")
    deploy.add_argument("--name", help="Optional agent name.")
    deploy.add_argument("--out", "-o", type=Path, help="Destination zip path or directory.")

    sub.add_parser(
        "shell",
        help="In-process factory session: create/start/stop/list/delete/ask/deploy.",
    )

    return parser


def _platform() -> Universal:
    return Universal.from_env()


def _cmd_templates(args: argparse.Namespace) -> int:
    rows = list_templates()
    if args.json:
        print(json.dumps([{"id": t.id, "name": t.name, "description": t.description} for t in rows], indent=2))
        return 0
    for template in rows:
        print(f"{template.id:12} {template.name:12} {template.description}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    settings.require_live()
    platform = Universal(settings)
    agent = platform.factory.create(args.template, args.name)
    platform.factory.start(agent.id)
    try:
        channel = agent.channel
        if args.json and isinstance(channel, CLIChannel):
            with channel.capture():
                answer = agent.accept(args.prompt)
            print(json.dumps({"agent_id": agent.id, "template": agent.template_id, "answer": answer}, indent=2))
        else:
            # Channel send() is the user-visible answer (no second print).
            agent.accept(args.prompt)
    finally:
        platform.factory.stop(agent.id)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    settings.require_live()
    platform = Universal(settings)
    agent = platform.factory.create(args.template, args.name)
    platform.factory.start(agent.id)
    print(f"Universal chat  template={agent.template_id}  id={agent.id}  (/quit to exit)")
    assert agent.channel is not None
    try:
        agent.channel.serve_forever(prompt="you> ")
    finally:
        platform.factory.stop(agent.id)
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    platform = _platform()
    agent = platform.factory.create(args.template, args.name)
    print(agent.id)
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    platform = _platform()
    infos = platform.factory.list()
    if not infos:
        print("No agents in this process. Use `universal shell` to keep the registry alive.")
        return 0
    for info in infos:
        print(f"{info.id}  {info.name}  {info.template_id}  {info.state.value}")
    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    platform = _platform()
    agent = platform.factory.create(args.template, args.name)
    path = platform.factory.deploy(agent.id, args.out)
    print(path)
    return 0


def _cmd_shell(_args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    platform = Universal(settings)
    session = FactorySession(platform)
    print("Universal factory shell. Type help. quit to exit.")
    while True:
        try:
            line = input("universal> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        result = session.execute(line)
        if result == "quit":
            return 0
        if result:
            print(result)


_HANDLERS = {
    "ask": _cmd_ask,
    "chat": _cmd_chat,
    "templates": _cmd_templates,
    "create": _cmd_create,
    "list": _cmd_list,
    "deploy": _cmd_deploy,
    "shell": _cmd_shell,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = _HANDLERS[args.command]
    try:
        return handler(args)
    except UniversalError as exc:
        print(f"universal: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("universal: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
