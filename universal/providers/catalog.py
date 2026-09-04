"""Named OpenAI-compatible presets. One company, one latest model.

Each row is a lab + its current flagship + the OpenAI-compatible URL that
reaches it. Nothing here constructs an HTTP client. Companies without a
public OpenAI-compatible API are reached through OpenRouter (one hop, still
one ``OpenAICompatProvider``).
"""

from __future__ import annotations

from dataclasses import dataclass

OPENROUTER = "https://openrouter.ai/api/v1"


@dataclass(frozen=True, slots=True)
class ModelProvider:
    company: str
    name: str
    base_url: str
    default_model: str
    docs: str = ""
    requires_api_key: bool = True

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "company": self.company,
            "name": self.name,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "docs": self.docs,
            "requires_api_key": self.requires_api_key,
        }


def _row(
    company: str,
    label: str,
    base_url: str,
    model: str,
    docs: str,
    *,
    requires_api_key: bool = True,
) -> ModelProvider:
    return ModelProvider(
        company=company,
        name=f"{company} ({label})",
        base_url=base_url,
        default_model=model,
        docs=docs,
        requires_api_key=requires_api_key,
    )


def _via_openrouter(company: str, label: str, model: str, docs: str) -> ModelProvider:
    return _row(
        company,
        label,
        OPENROUTER,
        model,
        f"{docs} Reached through OpenRouter's OpenAI-compatible endpoint. Use an OpenRouter API key.",
    )


# 40 labs. One latest flagship each. No second OpenAI, no second Llama host.
PROVIDERS: tuple[ModelProvider, ...] = (
    _row("OpenAI", "GPT-5.6 Sol", "https://api.openai.com/v1", "gpt-5.6-sol", "https://platform.openai.com/docs/models"),
    _via_openrouter("Anthropic", "Claude Fable 5.1", "anthropic/claude-fable-5.1", "https://docs.anthropic.com/"),
    _row(
        "Google",
        "Gemini 3.8 Flash",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-3.8-flash",
        "https://ai.google.dev/gemini-api/docs/openai",
    ),
    _row("xAI", "Grok 4.6", "https://api.x.ai/v1", "grok-4.6", "https://docs.x.ai/"),
    _row("Meta", "Muse Spark 1.3", "https://api.meta.ai/v1", "muse-spark-1.3", "https://llama.meta.com/docs/"),
    _row("DeepSeek", "V4 Pro", "https://api.deepseek.com/v1", "deepseek-v4-pro", "https://api-docs.deepseek.com/"),
    _row("Mistral", "Medium 3.5", "https://api.mistral.ai/v1", "mistral-medium-3-5", "https://docs.mistral.ai/"),
    _row(
        "Alibaba",
        "Qwen3.8 Max",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "qwen3.8-max",
        "https://www.alibabacloud.com/help/dashscope",
    ),
    _row("Zhipu", "GLM-5.2", "https://open.bigmodel.cn/api/paas/v4", "glm-5.2", "https://open.bigmodel.cn/"),
    _row("Moonshot", "Kimi K2.7", "https://api.moonshot.ai/v1", "kimi-k2.7", "https://platform.moonshot.ai/"),
    _row(
        "Together",
        "Latest",
        "https://api.together.xyz/v1",
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "https://docs.together.ai/",
    ),
    _row("MiniMax", "M3", "https://api.minimax.chat/v1", "MiniMax-M3", "https://www.minimax.io/"),
    _row(
        "ByteDance",
        "Doubao Seed 1.6",
        "https://ark.cn-beijing.volces.com/api/v3",
        "doubao-seed-1-6-250615",
        "https://www.volcengine.com/docs/82379",
    ),
    _row(
        "Tencent",
        "Hunyuan TurboS",
        "https://api.hunyuan.cloud.tencent.com/v1",
        "hunyuan-turbos-latest",
        "https://cloud.tencent.com/document/product/1729",
    ),
    _row(
        "Baidu",
        "ERNIE 4.5 Turbo",
        "https://qianfan.baidubce.com/v2",
        "ernie-4.5-turbo-128k",
        "https://cloud.baidu.com/doc/qianfan",
    ),
    _row("Cerebras", "Latest", "https://api.cerebras.ai/v1", "llama-4-scout-17b-16e-instruct", "https://inference-docs.cerebras.ai/"),
    _row(
        "Cohere",
        "Command A",
        "https://api.cohere.com/compatibility/v1",
        "command-a-03-2025",
        "https://docs.cohere.com/docs/compatibility-api",
    ),
    _via_openrouter("AI21", "Jamba 1.6 Large", "ai21/jamba-1.6-large", "https://docs.ai21.com/"),
    _via_openrouter("Amazon", "Nova Pro", "amazon/nova-pro-v1", "https://aws.amazon.com/ai/generative-ai/nova/"),
    _via_openrouter("Microsoft", "Phi-4", "microsoft/phi-4", "https://azure.microsoft.com/products/phi"),
    _via_openrouter("IBM", "Granite 3.3", "ibm-granite/granite-3.3-8b-instruct", "https://www.ibm.com/granite"),
    _row(
        "NVIDIA",
        "Nemotron Super",
        "https://integrate.api.nvidia.com/v1",
        "nvidia/llama-3.3-nemotron-super-49b-v1",
        "https://build.nvidia.com/",
    ),
    _row("Perplexity", "Sonar Pro", "https://api.perplexity.ai", "sonar-pro", "https://docs.perplexity.ai/"),
    _row("Groq", "Compound", "https://api.groq.com/openai/v1", "groq/compound", "https://console.groq.com/docs"),
    _row("Writer", "Palmyra X5", "https://api.writer.com/v1", "palmyra-x5", "https://dev.writer.com/"),
    _row("Upstage", "Solar Pro", "https://api.upstage.ai/v1/solar", "solar-pro", "https://developers.upstage.ai/"),
    _via_openrouter("Nous Research", "Hermes 3", "nousresearch/hermes-3-llama-3.1-405b", "https://nousresearch.com/"),
    _via_openrouter("Reka", "Flash 3", "rekaai/reka-flash-3", "https://www.reka.ai/"),
    _via_openrouter("LG", "EXAONE 4.0", "lgai/exaone-4.0", "https://www.lgresearch.ai/"),
    _via_openrouter("Allen AI", "OLMo 2 32B", "allenai/olmo-2-32b-instruct", "https://allenai.org/olmo"),
    _via_openrouter("TII", "Falcon 3 10B", "tiiuae/falcon3-10b-instruct", "https://falconllm.tii.ae/"),
    _row(
        "Fireworks",
        "Kimi K2.5",
        "https://api.fireworks.ai/inference/v1",
        "accounts/fireworks/models/kimi-k2p5-instruct",
        "https://fireworks.ai/",
    ),
    _via_openrouter("Databricks", "DBRX", "databricks/dbrx-instruct", "https://www.databricks.com/product/machine-learning/foundation-model-apis"),
    _via_openrouter("Snowflake", "Arctic", "snowflake/snowflake-arctic-instruct", "https://www.snowflake.com/en/data-cloud/arctic/"),
    _row("SambaNova", "Latest", "https://api.sambanova.ai/v1", "Meta-Llama-3.3-70B-Instruct", "https://docs.sambanova.ai/"),
    _via_openrouter("Shanghai AI Lab", "InternLM 3", "internlm/internlm3-8b-instruct", "https://internlm.intern-ai.org.cn/"),
    _row(
        "01.AI",
        "Yi Lightning",
        "https://api.lingyiwanwu.com/v1",
        "yi-lightning",
        "https://platform.lingyiwanwu.com/",
    ),
    _via_openrouter("StepFun", "Step 3", "stepfun/step-3", "https://platform.stepfun.com/"),
    _row(
        "Hugging Face",
        "SmolLM3",
        "https://router.huggingface.co/v1",
        "HuggingFaceTB/SmolLM3-3B",
        "https://huggingface.co/docs/inference-providers",
    ),
    _row("OpenRouter", "Auto", OPENROUTER, "openrouter/auto", "https://openrouter.ai/docs"),
    ModelProvider(
        company="Custom",
        name="Custom (URL)",
        base_url="",
        default_model="custom-model",
        docs="Any other OpenAI-compatible endpoint. Fill the base URL and model yourself.",
        requires_api_key=True,
    ),
)


def get_provider(name: str) -> ModelProvider | None:
    return next((row for row in PROVIDERS if row.name == name), None)


def list_providers() -> list[str]:
    return [row.name for row in PROVIDERS]


def list_providers_without_custom() -> list[str]:
    return [row.name for row in PROVIDERS if row.company != "Custom"]


def list_companies() -> list[str]:
    return [row.company for row in PROVIDERS if row.company != "Custom"]


def match_provider(base_url: str, model: str) -> ModelProvider:
    """Best catalog row for current settings. Custom if nothing matches."""
    base = (base_url or "").rstrip("/")
    for row in PROVIDERS:
        if row.company == "Custom":
            continue
        if row.base_url.rstrip("/") == base and row.default_model == model:
            return row
    custom = get_provider("Custom (URL)")
    assert custom is not None
    return custom


def is_local_base_url(base_url: str) -> bool:
    host = (base_url or "").lower()
    return any(token in host for token in ("localhost", "127.0.0.1", "[::1]"))
