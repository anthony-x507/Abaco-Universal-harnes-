"""Baidu Qianfan OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class BaiduAdapter(OpenAIAdapter):
    name = "baidu"
