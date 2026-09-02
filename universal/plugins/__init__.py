"""Built-in plugins assembled onto agents by templates and the factory."""

from universal.plugins.catalog import PluginCatalog, catalog, default_plugin_catalog
from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.plugins.transcript import TranscriptPlugin

__all__ = [
    "PluginCatalog",
    "SystemPromptPlugin",
    "ToolBeltPlugin",
    "TranscriptPlugin",
    "catalog",
    "default_plugin_catalog",
    "utc_now_tool",
]
