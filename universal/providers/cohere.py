"""Cohere Compatibility API dialect (OpenAI-shaped)."""

from universal.providers.openai import OpenAIAdapter


class CohereAdapter(OpenAIAdapter):
    name = "cohere"
