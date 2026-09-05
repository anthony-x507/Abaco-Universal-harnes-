"""ByteDance Doubao / Volcengine Ark dialect."""

from universal.providers.openai import OpenAIAdapter


class DoubaoAdapter(OpenAIAdapter):
    name = "doubao"
