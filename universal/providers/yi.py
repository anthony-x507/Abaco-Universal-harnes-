"""01.AI Yi OpenAI-compatible dialect."""

from universal.providers.openai import OpenAIAdapter


class YiAdapter(OpenAIAdapter):
    name = "yi"
