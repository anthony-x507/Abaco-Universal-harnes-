"""SenseTime SenseNova — OpenAI-shaped (often via OpenRouter)."""

from universal.providers.openai import OpenAIAdapter


class SenseNovaAdapter(OpenAIAdapter):
    name = "sensenova"
