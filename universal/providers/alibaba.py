"""Alibaba DashScope compatible-mode dialect."""

from universal.providers.openai import OpenAIAdapter


class AlibabaAdapter(OpenAIAdapter):
    name = "alibaba"
