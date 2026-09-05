"""Mistral OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class MistralAdapter(OpenAIAdapter):
    name = "mistral"
