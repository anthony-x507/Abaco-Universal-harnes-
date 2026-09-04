"""DuckDuckGo Instant Answer search. No API key."""

from __future__ import annotations

import json

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import fetch_text, parse_tool_args

DDG_URL = "https://api.duckduckgo.com/"


class WebSearchPlugin(Plugin):
    """Search the public web via DuckDuckGo’s Instant Answer API."""

    def __init__(self) -> None:
        self._name = "web_search"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="search_web",
                description="Search the web (DuckDuckGo Instant Answer, no API key).",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum related topics to return",
                        },
                    },
                    "required": ["query"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "search_web":
            return None
        args = parse_tool_args(call)
        query = str(args.get("query") or "").strip()
        try:
            max_results = int(args.get("max_results") if args.get("max_results") is not None else 5)
        except (TypeError, ValueError):
            max_results = 5
        max_results = max(1, min(max_results, 20))
        return self._search(query, max_results)

    def _search(self, query: str, max_results: int) -> str:
        if not query:
            return "Error: query is required"
        try:
            raw = fetch_text(
                DDG_URL,
                timeout=10.0,
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = json.loads(raw)
        except Exception as exc:
            return f"Error searching: {exc}"
        if not isinstance(data, dict):
            return "No results found."
        lines: list[str] = []
        abstract = data.get("AbstractText")
        if abstract:
            lines.append(f"[Abstract] {abstract}")
        added = 0
        for topic in data.get("RelatedTopics") or []:
            if added >= max_results:
                break
            if not isinstance(topic, dict):
                continue
            text = topic.get("Text") or topic.get("Name")
            if not text:
                continue
            lines.append(f"- {text}")
            added += 1
        return "\n".join(lines) if lines else "No results found."
