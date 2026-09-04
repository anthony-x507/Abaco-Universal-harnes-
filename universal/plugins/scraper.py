"""Fetch public http(s) pages and extract visible text."""

from __future__ import annotations

from bs4 import BeautifulSoup

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import assert_public_http_url, fetch_text, parse_tool_args

USER_AGENT = "UniversalHarness/0.1 (+https://github.com; research)"


class ScraperPlugin(Plugin):
    """Scrape a public URL. Blocks localhost and private addresses."""

    def __init__(self) -> None:
        self._name = "scraper"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="scrape_url",
                description="Fetch a public web page and return visible text.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "http(s) URL to scrape"},
                        "selector": {
                            "type": "string",
                            "description": "Optional CSS selector (default: body)",
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum characters to return",
                        },
                    },
                    "required": ["url"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "scrape_url":
            return None
        args = parse_tool_args(call)
        url = str(args.get("url") or "").strip()
        selector = str(args.get("selector") or "body")
        try:
            max_length = int(args.get("max_length") if args.get("max_length") is not None else 5000)
        except (TypeError, ValueError):
            max_length = 5000
        max_length = max(200, min(max_length, 50_000))
        return self._scrape(url, selector, max_length)

    def _scrape(self, url: str, selector: str, max_length: int) -> str:
        if not url:
            return "Error: url is required"
        try:
            assert_public_http_url(url)
            html = fetch_text(url, timeout=15.0, headers={"User-Agent": USER_AGENT})
        except Exception as exc:
            return f"Error scraping: {exc}"
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        target = soup.select_one(selector) if selector else soup
        if target is None:
            return "No content found."
        text = target.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        if not cleaned:
            return "No content found."
        if len(cleaned) > max_length:
            return cleaned[:max_length] + "\n... [truncated]"
        return cleaned
