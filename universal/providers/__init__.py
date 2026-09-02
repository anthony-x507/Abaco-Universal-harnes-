"""Language-model providers. v1 ships one real OpenAI-compatible HTTP client."""

from universal.providers.base import Provider
from universal.providers.openai_compat import OpenAICompatProvider

__all__ = ["OpenAICompatProvider", "Provider"]
