"""Tencent Hunyuan OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class TencentAdapter(OpenAIAdapter):
    name = "tencent"
