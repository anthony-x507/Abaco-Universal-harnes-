# Provider adapter layer

The agent talks to one `Provider` (`OpenAICompatProvider`). That client owns a single `httpx` socket.

`ProviderAdapter` only changes **dialect**: headers, URL, payload, and parse. Adapters are not plugins. They are not a second registry.

## How a host is chosen

1. The UI sends the catalog preset name (`provider` / `llm_provider`).
2. `/v1/models` includes `adapter` on each row.
3. `detect_adapter_type` uses the explicit adapter, then company, then URL.
4. OpenRouter and Google’s `/openai` shim stay on the OpenAI dialect.

## Files

| File | Role |
|---|---|
| `universal/providers/base.py` | `Provider` + `ProviderAdapter` |
| `universal/providers/factory.py` | `PROVIDER_MAP`, `get_provider_adapter`, `build_live_provider` |
| `universal/providers/openai.py` | OpenAI / DeepSeek / Groq / OpenRouter |
| `universal/providers/anthropic.py` | Native Claude Messages API |
| `universal/providers/google.py` | Native Gemini `generateContent` |
| China / local modules | Named subclasses (Zhipu, MiniMax, Ollama, …) |

## Locks that still hold

- Factory REST stays under `/v1/agents/...`. No `/v1/chat/completions` on Universal.
- Echo exists only with `universal serve --demo`.
- One registry, one lifecycle.
