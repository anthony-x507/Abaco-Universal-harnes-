"""Built-in plugins assembled onto agents by templates and the factory."""

from universal.plugins.catalog import (
    NATIVE_PLUGIN_NAMES,
    PluginCatalog,
    catalog,
    default_plugin_catalog,
    merge_native_plugin_ids,
)
from universal.plugins.scraper import ScraperPlugin
from universal.plugins.stt import STTPlugin
from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.terminal import TerminalPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.plugins.transcript import TranscriptPlugin
from universal.plugins.tts import TTSPlugin
from universal.plugins.vision import VisionPlugin
from universal.plugins.web_search import WebSearchPlugin

__all__ = [
    "NATIVE_PLUGIN_NAMES",
    "PluginCatalog",
    "ScraperPlugin",
    "STTPlugin",
    "SystemPromptPlugin",
    "TerminalPlugin",
    "ToolBeltPlugin",
    "TranscriptPlugin",
    "TTSPlugin",
    "VisionPlugin",
    "WebSearchPlugin",
    "catalog",
    "default_plugin_catalog",
    "merge_native_plugin_ids",
    "utc_now_tool",
]
