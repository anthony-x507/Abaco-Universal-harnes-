"""Built-in plugins assembled onto agents by templates and the factory."""

from universal.plugins.system_prompt import SystemPromptPlugin
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool
from universal.plugins.transcript import TranscriptPlugin

__all__ = [
    "SystemPromptPlugin",
    "ToolBeltPlugin",
    "TranscriptPlugin",
    "utc_now_tool",
]
