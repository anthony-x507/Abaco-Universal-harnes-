"""Zhipu GLM / Z.ai OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class ZhipuAdapter(OpenAIAdapter):
    name = "zhipu"
