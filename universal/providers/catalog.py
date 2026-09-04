"""Named OpenAI-compatible presets. Not a second provider stack.

Each row is a label + base URL + default model for the existing
``OpenAICompatProvider``. Nothing here constructs an HTTP client.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelProvider:
    name: str
    base_url: str
    default_model: str
    docs: str = ""
    requires_api_key: bool = True

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "docs": self.docs,
            "requires_api_key": self.requires_api_key,
        }


PROVIDERS: tuple[ModelProvider, ...] = (
    ModelProvider("OpenAI (GPT-4o-mini)", "https://api.openai.com/v1", "gpt-4o-mini", "https://platform.openai.com/"),
    ModelProvider("OpenAI (GPT-4o)", "https://api.openai.com/v1", "gpt-4o", "https://platform.openai.com/"),
    ModelProvider("OpenAI (o1-mini)", "https://api.openai.com/v1", "o1-mini", "https://platform.openai.com/"),
    ModelProvider("OpenAI (GPT-4.1-mini)", "https://api.openai.com/v1", "gpt-4.1-mini", "https://platform.openai.com/"),
    ModelProvider("DeepSeek Chat", "https://api.deepseek.com/v1", "deepseek-chat", "https://platform.deepseek.com/"),
    ModelProvider("DeepSeek Coder", "https://api.deepseek.com/v1", "deepseek-coder", "https://platform.deepseek.com/"),
    ModelProvider("DeepSeek R1", "https://api.deepseek.com/v1", "deepseek-reasoner", "https://platform.deepseek.com/"),
    ModelProvider("Groq (Llama 3 70B)", "https://api.groq.com/openai/v1", "llama3-70b-8192", "https://console.groq.com/"),
    ModelProvider("Groq (Llama 3.1 70B)", "https://api.groq.com/openai/v1", "llama-3.1-70b-versatile", "https://console.groq.com/"),
    ModelProvider("Groq (Mixtral 8x7B)", "https://api.groq.com/openai/v1", "mixtral-8x7b-32768", "https://console.groq.com/"),
    ModelProvider("OpenRouter (GPT-4o)", "https://openrouter.ai/api/v1", "openai/gpt-4o", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Claude 3.5)", "https://openrouter.ai/api/v1", "anthropic/claude-3.5-sonnet", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Gemini Pro)", "https://openrouter.ai/api/v1", "google/gemini-pro-1.5", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Llama 3 70B)", "https://openrouter.ai/api/v1", "meta-llama/llama-3-70b-instruct", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (DeepSeek)", "https://openrouter.ai/api/v1", "deepseek/deepseek-chat", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Mistral 7B)", "https://openrouter.ai/api/v1", "mistralai/mistral-7b-instruct", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Gemma 2 9B)", "https://openrouter.ai/api/v1", "google/gemma-2-9b-it", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Phi-3 Mini)", "https://openrouter.ai/api/v1", "microsoft/phi-3-mini-128k-instruct", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Qwen 2 7B)", "https://openrouter.ai/api/v1", "qwen/qwen-2-7b-instruct", "https://openrouter.ai/"),
    ModelProvider("OpenRouter (Claude 3 Opus)", "https://openrouter.ai/api/v1", "anthropic/claude-3-opus", "https://openrouter.ai/"),
    ModelProvider(
        "Ollama (Llama 3.2)",
        "http://localhost:11434/v1",
        "llama3.2",
        "https://ollama.com/",
        requires_api_key=False,
    ),
    ModelProvider(
        "Ollama (Mistral)",
        "http://localhost:11434/v1",
        "mistral",
        "https://ollama.com/",
        requires_api_key=False,
    ),
    ModelProvider(
        "Ollama (Gemma 2)",
        "http://localhost:11434/v1",
        "gemma2",
        "https://ollama.com/",
        requires_api_key=False,
    ),
    ModelProvider(
        "Ollama (Phi-3)",
        "http://localhost:11434/v1",
        "phi3",
        "https://ollama.com/",
        requires_api_key=False,
    ),
    ModelProvider("Mistral (Large)", "https://api.mistral.ai/v1", "mistral-large-latest", "https://console.mistral.ai/"),
    ModelProvider("Mistral (Small)", "https://api.mistral.ai/v1", "mistral-small-latest", "https://console.mistral.ai/"),
    ModelProvider("Mistral (Codestral)", "https://api.mistral.ai/v1", "codestral-latest", "https://console.mistral.ai/"),
    ModelProvider("Cohere (Command R)", "https://api.cohere.ai/v1", "command-r", "https://dashboard.cohere.com/"),
    ModelProvider("Cohere (Command R+)", "https://api.cohere.ai/v1", "command-r-plus", "https://dashboard.cohere.com/"),
    ModelProvider(
        "Together (Llama 3 70B)",
        "https://api.together.xyz/v1",
        "meta-llama/Llama-3-70b-chat-hf",
        "https://together.ai/",
    ),
    ModelProvider(
        "Together (Llama 3.1 70B)",
        "https://api.together.xyz/v1",
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "https://together.ai/",
    ),
    ModelProvider(
        "Together (Mixtral 8x7B)",
        "https://api.together.xyz/v1",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "https://together.ai/",
    ),
    ModelProvider(
        "Fireworks (Llama 3 70B)",
        "https://api.fireworks.ai/inference/v1",
        "accounts/fireworks/models/llama-v3-70b-instruct",
        "https://fireworks.ai/",
    ),
    ModelProvider(
        "Fireworks (Mixtral)",
        "https://api.fireworks.ai/inference/v1",
        "accounts/fireworks/models/mixtral-8x7b-instruct",
        "https://fireworks.ai/",
    ),
    ModelProvider("Perplexity (Sonar Small)", "https://api.perplexity.ai", "sonar-small-chat", "https://docs.perplexity.ai/"),
    ModelProvider("Perplexity (Sonar Medium)", "https://api.perplexity.ai", "sonar-medium-chat", "https://docs.perplexity.ai/"),
    ModelProvider(
        "Anyscale (Llama 2 70B)",
        "https://api.endpoints.anyscale.com/v1",
        "meta-llama/Llama-2-70b-chat-hf",
        "https://anyscale.com/",
    ),
    ModelProvider("Lepton (Llama 3 70B)", "https://api.lepton.ai/v1", "llama3-70b", "https://lepton.ai/"),
    ModelProvider("LM Studio", "http://localhost:1234/v1", "local-model", "https://lmstudio.ai/", requires_api_key=False),
    ModelProvider(
        "vLLM",
        "http://localhost:8000/v1",
        "meta-llama/Llama-3-8B-Instruct",
        "https://vllm.ai/",
        requires_api_key=False,
    ),
    ModelProvider(
        "Text Generation WebUI",
        "http://localhost:5000/v1",
        "local-model",
        "https://github.com/oobabooga/text-generation-webui",
        requires_api_key=False,
    ),
    ModelProvider(
        "Custom (URL)",
        "",
        "custom-model",
        "For custom OpenAI-compatible endpoints",
        requires_api_key=True,
    ),
)


def get_provider(name: str) -> ModelProvider | None:
    return next((row for row in PROVIDERS if row.name == name), None)


def list_providers() -> list[str]:
    return [row.name for row in PROVIDERS]


def list_providers_without_custom() -> list[str]:
    return [row.name for row in PROVIDERS if row.name != "Custom (URL)"]


def match_provider(base_url: str, model: str) -> ModelProvider:
    """Best catalog row for current settings. Custom if nothing matches."""
    base = (base_url or "").rstrip("/")
    for row in PROVIDERS:
        if row.name == "Custom (URL)":
            continue
        if row.base_url.rstrip("/") == base and row.default_model == model:
            return row
    custom = get_provider("Custom (URL)")
    assert custom is not None
    return custom


def is_local_base_url(base_url: str) -> bool:
    host = (base_url or "").lower()
    return any(token in host for token in ("localhost", "127.0.0.1", "[::1]"))
