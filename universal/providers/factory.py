"""Select the HTTP dialect adapter. Does not construct a second registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from universal.exceptions import ProviderError
from universal.providers.alibaba import AlibabaAdapter
from universal.providers.anthropic import AnthropicAdapter
from universal.providers.baidu import BaiduAdapter
from universal.providers.base import ProviderAdapter
from universal.providers.cohere import CohereAdapter
from universal.providers.doubao import DoubaoAdapter
from universal.providers.google import GoogleAdapter
from universal.providers.local import LMStudioAdapter, OllamaAdapter, VLLMAdapter
from universal.providers.minimax import MinimaxAdapter
from universal.providers.mistral import MistralAdapter
from universal.providers.moonshot import MoonshotAdapter
from universal.providers.openai import OpenAIAdapter
from universal.providers.sensenova import SenseNovaAdapter
from universal.providers.tencent import TencentAdapter
from universal.providers.yi import YiAdapter
from universal.providers.zhipu import ZhipuAdapter

if TYPE_CHECKING:
    from universal.providers.openai_compat import OpenAICompatProvider

PROVIDER_MAP: dict[str, type[ProviderAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleAdapter,
    "mistral": MistralAdapter,
    "cohere": CohereAdapter,
    "perplexity": OpenAIAdapter,
    "groq": OpenAIAdapter,
    "together": OpenAIAdapter,
    "fireworks": OpenAIAdapter,
    "replicate": OpenAIAdapter,
    "anyscale": OpenAIAdapter,
    "lepton": OpenAIAdapter,
    "openrouter": OpenAIAdapter,
    "huggingface": OpenAIAdapter,
    "nousresearch": OpenAIAdapter,
    "microsoft": OpenAIAdapter,
    "nvidia": OpenAIAdapter,
    "cerebras": OpenAIAdapter,
    "sambanova": OpenAIAdapter,
    "ai21": OpenAIAdapter,
    "writer": OpenAIAdapter,
    "adept": OpenAIAdapter,
    "databricks": OpenAIAdapter,
    "snowflake": OpenAIAdapter,
    "xai": OpenAIAdapter,
    "inflection": OpenAIAdapter,
    "ruliad": OpenAIAdapter,
    "lighton": OpenAIAdapter,
    "alephalpha": OpenAIAdapter,
    "stability": OpenAIAdapter,
    "deepseek": OpenAIAdapter,
    "zhipu": ZhipuAdapter,
    "minimax": MinimaxAdapter,
    "moonshot": MoonshotAdapter,
    "baidu": BaiduAdapter,
    "alibaba": AlibabaAdapter,
    "tencent": TencentAdapter,
    "doubao": DoubaoAdapter,
    "sensenova": SenseNovaAdapter,
    "yi": YiAdapter,
    "ollama": OllamaAdapter,
    "lmstudio": LMStudioAdapter,
    "vllm": VLLMAdapter,
    "local": OllamaAdapter,
    "custom": OpenAIAdapter,
}

_COMPANY_ADAPTER: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "mistral": "mistral",
    "cohere": "cohere",
    "deepseek": "deepseek",
    "zhipu": "zhipu",
    "minimax": "minimax",
    "moonshot": "moonshot",
    "baidu": "baidu",
    "alibaba": "alibaba",
    "tencent": "tencent",
    "bytedance": "doubao",
    "01.ai": "yi",
    "sensetime": "sensenova",
    "ollama": "ollama",
    "lm studio": "lmstudio",
    "vllm": "vllm",
}


def detect_adapter_type(
    base_url: str = "",
    model: str = "",
    provider_type: str | None = None,
    company: str = "",
) -> str:
    """Pick a dialect from an explicit type, catalog company, or URL."""
    explicit = (provider_type or "").strip().lower()
    url = (base_url or "").lower()
    if explicit in PROVIDER_MAP:
        if explicit == "google" and "/openai" in url:
            return "openai"
        if explicit == "anthropic" and "openrouter" in url:
            return "openai"
        return explicit
    company_key = (company or "").strip().lower()
    if company_key in _COMPANY_ADAPTER:
        mapped = _COMPANY_ADAPTER[company_key]
        if mapped == "google" and "/openai" in url:
            return "openai"
        if mapped == "anthropic" and "openrouter" in url:
            return "openai"
        if mapped in PROVIDER_MAP:
            return mapped
    if "api.anthropic.com" in url:
        return "anthropic"
    if "generativelanguage.googleapis.com" in url and "/openai" not in url:
        return "google"
    if "bigmodel.cn" in url or "api.z.ai" in url:
        return "zhipu"
    if "minimax" in url:
        return "minimax"
    if "moonshot" in url:
        return "moonshot"
    if "baidubce" in url or "qianfan" in url:
        return "baidu"
    if "dashscope" in url or "aliyuncs.com" in url:
        return "alibaba"
    if "hunyuan" in url:
        return "tencent"
    if "volces.com" in url or "volcengine" in url:
        return "doubao"
    if "lingyiwanwu" in url:
        return "yi"
    if "11434" in url:
        return "ollama"
    if ":1234" in url:
        return "lmstudio"
    if model:
        pass
    return "openai"


def get_provider_adapter(
    provider_type: str,
    base_url: str,
    api_key: str | None = None,
    model: str | None = None,
) -> ProviderAdapter:
    """Return the dialect adapter for this host."""
    key = detect_adapter_type(base_url, model or "", provider_type)
    adapter_cls = PROVIDER_MAP.get(key)
    if adapter_cls is None:
        raise ProviderError(f"Unsupported provider type: {provider_type}")
    return adapter_cls(base_url, api_key, model)


def build_live_provider(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 60.0,
    organization: str = "",
    client: object | None = None,
    adapter_type: str | None = None,
    preset_name: str | None = None,
) -> OpenAICompatProvider:
    """One HTTP client, dialect selected by preset/URL."""
    from universal.providers.catalog import get_provider
    from universal.providers.openai_compat import OpenAICompatProvider

    url = base_url
    chosen_model = model
    kind = adapter_type
    company = ""
    if preset_name:
        row = get_provider(preset_name)
        if row is not None:
            url = url or row.base_url
            chosen_model = chosen_model or row.default_model
            kind = kind or row.adapter
            company = row.company
    kind = detect_adapter_type(url, chosen_model, kind, company)
    return OpenAICompatProvider(
        base_url=url,
        api_key=api_key,
        model=chosen_model,
        timeout=timeout,
        organization=organization,
        client=client,  # type: ignore[arg-type]
        adapter_type=kind,
    )
