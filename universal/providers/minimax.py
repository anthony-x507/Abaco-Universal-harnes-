"""MiniMax OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class MinimaxAdapter(OpenAIAdapter):
    name = "minimax"
