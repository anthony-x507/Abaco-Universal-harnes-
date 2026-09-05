"""Language-model providers. One live HTTP client; dialects via adapters."""

from universal.providers.base import Provider, ProviderAdapter
from universal.providers.factory import get_provider_adapter
from universal.providers.openai_compat import OpenAICompatProvider

__all__ = ["OpenAICompatProvider", "Provider", "ProviderAdapter", "get_provider_adapter"]
