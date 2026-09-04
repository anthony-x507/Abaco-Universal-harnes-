"""Shared expectations for factory-default native plugins."""

from __future__ import annotations

from universal.plugins.catalog import NATIVE_PLUGIN_NAMES

NATIVE_TOOL_NAMES = (
    "run_command",
    "speak",
    "transcribe",
    "describe_image",
    "search_web",
    "scrape_url",
)

NATIVE_LABELS = [
    "Terminal: run_command",
    "Tts: speak",
    "Stt: transcribe",
    "Vision: describe_image",
    "Web Search: search_web",
    "Scraper: scrape_url",
]

RESEARCHER_PLUGIN_NAMES = (*NATIVE_PLUGIN_NAMES, "tools")
RESEARCHER_LABELS = [*NATIVE_LABELS, "Tools: utc_now"]
