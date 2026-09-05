"""Moonshot / Kimi OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class MoonshotAdapter(OpenAIAdapter):
    name = "moonshot"
