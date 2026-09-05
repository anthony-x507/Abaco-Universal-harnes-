"""Local OpenAI-compatible shims (Ollama, LM Studio, vLLM)."""

from universal.providers.openai import OpenAIAdapter


class LocalAdapter(OpenAIAdapter):
    """Same payload as OpenAI; empty keys are allowed."""

    name = "local"

    def allows_empty_key(self) -> bool:
        return True

    def get_headers(self) -> dict[str, str]:
        headers = super().get_headers()
        if "Authorization" not in headers:
            headers["Authorization"] = "Bearer local"
        return headers


class OllamaAdapter(LocalAdapter):
    name = "ollama"


class LMStudioAdapter(LocalAdapter):
    name = "lmstudio"


class VLLMAdapter(LocalAdapter):
    name = "vllm"
