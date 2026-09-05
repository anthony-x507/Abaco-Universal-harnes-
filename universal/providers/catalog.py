"""Named model presets. One company, one latest model.

China: 10 labs. United States: 40 hosts (labs, inference, local).
Each row names an adapter id. The live client is still one HTTP socket;
the factory picks the dialect (OpenAI, Anthropic, Gemini, or China/local).
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
    region: str = "us"
    adapter: str = "openai"

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "company": self.company,
            "name": self.name,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "docs": self.docs,
            "requires_api_key": self.requires_api_key,
            "region": self.region,
            "adapter": self.adapter,
        }


def _row(
    company: str,
    label: str,
    base_url: str,
    model: str,
    docs: str,
    *,
    region: str = "us",
    requires_api_key: bool = True,
    adapter: str = "openai",
) -> ModelProvider:
    return ModelProvider(
        company=company,
        name=f"{company} ({label})",
        base_url=base_url,
        default_model=model,
        docs=docs,
        requires_api_key=requires_api_key,
        region=region,
        adapter=adapter,
    )


def _via_openrouter(company: str, label: str, model: str, docs: str, *, region: str = "us") -> ModelProvider:
    return _row(
        company,
        label,
        OPENROUTER,
        model,
        f"{docs} Reached through OpenRouter's OpenAI-compatible endpoint. Use an OpenRouter API key.",
        region=region,
    )


# 10 China + 40 United States. One latest flagship each. Custom is extra.
PROVIDERS: tuple[ModelProvider, ...] = (
    _row("DeepSeek", "V4 Pro", "https://api.deepseek.com/v1", "deepseek-v4-pro", "https://api-docs.deepseek.com/", region="cn", adapter="deepseek"),
    _row("MiniMax", "M3", "https://api.minimax.io/v1", "MiniMax-M3", "https://platform.minimax.io/docs/api-reference/text-openai-api", region="cn", adapter="minimax"),
    _row("Zhipu", "GLM-5.2", "https://api.z.ai/api/paas/v4", "glm-5.2", "https://docs.z.ai/", region="cn", adapter="zhipu"),
    _row(
        "Baidu",
        "ERNIE 4.5 Turbo",
        "https://qianfan.baidubce.com/v2",
        "ernie-4.5-turbo-128k",
        "https://cloud.baidu.com/doc/qianfan",
        region="cn",
        adapter="baidu",
    ),
    _row(
        "Alibaba",
        "Qwen3.8 Max",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "qwen3.8-max",
        "https://www.alibabacloud.com/help/dashscope",
        region="cn",
        adapter="alibaba",
    ),
    _row(
        "Tencent",
        "Hunyuan TurboS",
        "https://api.hunyuan.cloud.tencent.com/v1",
        "hunyuan-turbos-latest",
        "https://cloud.tencent.com/document/product/1729",
        region="cn",
        adapter="tencent",
    ),
    _row("Moonshot", "Kimi K2.7", "https://api.moonshot.ai/v1", "kimi-k2.7", "https://platform.moonshot.ai/", region="cn", adapter="moonshot"),
    _row("01.AI", "Yi Lightning", "https://api.lingyiwanwu.com/v1", "yi-lightning", "https://platform.lingyiwanwu.com/", region="cn", adapter="yi"),
    _row(
        "ByteDance",
        "Doubao Seed 1.6",
        "https://ark.cn-beijing.volces.com/api/v3",
        "doubao-seed-1-6-250615",
        "https://www.volcengine.com/docs/82379",
        region="cn",
        adapter="doubao",
    ),
    _via_openrouter("SenseTime", "SenseNova 5.5", "sensenova/sensechat-5", "https://platform.sensenova.cn/", region="cn"),
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
    _row("Mistral", "Medium 3.5", "https://api.mistral.ai/v1", "mistral-medium-3-5", "https://docs.mistral.ai/", adapter="mistral"),
    _row(
        "Cohere",
        "Command A",
        "https://api.cohere.com/compatibility/v1",
        "command-a-03-2025",
        "https://docs.cohere.com/docs/compatibility-api",
        adapter="cohere",
    ),
    _row("Perplexity", "Sonar Pro", "https://api.perplexity.ai", "sonar-pro", "https://docs.perplexity.ai/"),
    _row("Groq", "Compound", "https://api.groq.com/openai/v1", "groq/compound", "https://console.groq.com/docs"),
    _row(
        "Together",
        "Latest",
        "https://api.together.xyz/v1",
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "https://docs.together.ai/",
    ),
    _row(
        "Fireworks",
        "Kimi K2.5",
        "https://api.fireworks.ai/inference/v1",
        "accounts/fireworks/models/kimi-k2p5-instruct",
        "https://fireworks.ai/",
    ),
    _via_openrouter("Replicate", "Latest", "meta-llama/llama-4-maverick", "https://replicate.com/"),
    _row(
        "Anyscale",
        "Latest",
        "https://api.endpoints.anyscale.com/v1",
        "meta-llama/Meta-Llama-3.1-405B-Instruct",
        "https://docs.anyscale.com/",
    ),
    _row("Lepton", "Latest", "https://llama3-1-405b.lepton.run/api/v1", "llama3.1-405b", "https://www.lepton.ai/"),
    _row("OpenRouter", "Auto", OPENROUTER, "openrouter/auto", "https://openrouter.ai/docs"),
    _row("Ollama", "Local", "http://127.0.0.1:11434/v1", "llama3.2", "https://ollama.com/", requires_api_key=False, adapter="ollama"),
    _row("LM Studio", "Local", "http://127.0.0.1:1234/v1", "local-model", "https://lmstudio.ai/", requires_api_key=False, adapter="lmstudio"),
    _row("vLLM", "Local", "http://127.0.0.1:8000/v1", "local-model", "https://docs.vllm.ai/", requires_api_key=False, adapter="vllm"),
    _row(
        "Text Generation WebUI",
        "Local",
        "http://127.0.0.1:5000/v1",
        "local-model",
        "https://github.com/oobabooga/text-generation-webui",
        requires_api_key=False,
    ),
    _row(
        "Hugging Face",
        "SmolLM3",
        "https://router.huggingface.co/v1",
        "HuggingFaceTB/SmolLM3-3B",
        "https://huggingface.co/docs/inference-providers",
    ),
    _via_openrouter("Nous Research", "Hermes 3", "nousresearch/hermes-3-llama-3.1-405b", "https://nousresearch.com/"),
    _via_openrouter("Microsoft", "Phi-4", "microsoft/phi-4", "https://azure.microsoft.com/products/phi"),
    _row(
        "NVIDIA",
        "Nemotron Super",
        "https://integrate.api.nvidia.com/v1",
        "nvidia/llama-3.3-nemotron-super-49b-v1",
        "https://build.nvidia.com/",
    ),
    _row("Cerebras", "Latest", "https://api.cerebras.ai/v1", "llama-4-scout-17b-16e-instruct", "https://inference-docs.cerebras.ai/"),
    _row("SambaNova", "Latest", "https://api.sambanova.ai/v1", "Meta-Llama-3.3-70B-Instruct", "https://docs.sambanova.ai/"),
    _via_openrouter("AI21", "Jamba 1.6 Large", "ai21/jamba-1.6-large", "https://docs.ai21.com/"),
    _row("Writer", "Palmyra X5", "https://api.writer.com/v1", "palmyra-x5", "https://dev.writer.com/"),
    _via_openrouter("Adept", "Fuyu Heavy", "adept/fuyu-heavy", "https://www.adept.ai/"),
    _via_openrouter("Databricks", "DBRX", "databricks/dbrx-instruct", "https://www.databricks.com/product/machine-learning/foundation-model-apis"),
    _via_openrouter("Snowflake", "Arctic", "snowflake/snowflake-arctic-instruct", "https://www.snowflake.com/en/data-cloud/arctic/"),
    _via_openrouter("Amazon", "Nova Pro", "amazon/nova-pro-v1", "https://aws.amazon.com/ai/generative-ai/nova/"),
    _via_openrouter("IBM", "Granite 3.3", "ibm-granite/granite-3.3-8b-instruct", "https://www.ibm.com/granite"),
    _via_openrouter("Inflection", "Pi", "inflection/inflection-3-pi", "https://inflection.ai/"),
    _via_openrouter("Stability AI", "Stable LM", "stabilityai/stablelm-2-12b-chat", "https://stability.ai/"),
    _via_openrouter("Allen AI", "OLMo 2 32B", "allenai/olmo-2-32b-instruct", "https://allenai.org/olmo"),
    _via_openrouter("Reka", "Flash 3", "rekaai/reka-flash-3", "https://www.reka.ai/"),
    _row("Lambda", "Latest", "https://api.lambdalabs.com/v1", "llama3.3-70b-instruct-fp8", "https://docs.lambda.ai/"),
    _row(
        "Cloudflare",
        "Workers AI",
        "https://api.cloudflare.com/client/v4/accounts/default/ai/v1",
        "@cf/meta/llama-3.3-70b-instruct",
        "https://developers.cloudflare.com/workers-ai/",
    ),
    _row("Baseten", "Latest", "https://bridge.baseten.co/v1", "openai/gpt-oss-120b", "https://docs.baseten.co/"),
    _row("Deepinfra", "Latest", "https://api.deepinfra.com/v1/openai", "meta-llama/Meta-Llama-3.1-405B-Instruct", "https://deepinfra.com/docs"),
    ModelProvider(
        company="Custom",
        name="Custom (URL)",
        base_url="",
        default_model="custom-model",
        docs="Any other OpenAI-compatible endpoint. Fill the base URL and model yourself.",
        requires_api_key=True,
        region="",
        adapter="openai",
    ),
)


def get_provider(name: str) -> ModelProvider | None:
    return next((row for row in PROVIDERS if row.name == name), None)


def list_providers(region: str | None = None) -> list[str]:
    rows = PROVIDERS
    if region:
        rows = tuple(row for row in PROVIDERS if row.region == region)
    return [row.name for row in rows]


def list_providers_without_custom() -> list[str]:
    return [row.name for row in PROVIDERS if row.company != "Custom"]


def list_companies(region: str | None = None) -> list[str]:
    rows = [row for row in PROVIDERS if row.company != "Custom"]
    if region:
        rows = [row for row in rows if row.region == region]
    return [row.company for row in rows]


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
