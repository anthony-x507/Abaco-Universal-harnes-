# Universal platform

Plugin-based agent factory and harness. Agents are assembled from a **model**, a **channel**, and **plugins**. This repository is the first working cut: one agent that answers, one real LLM provider, one working channel, and three templates.

Package name: `universal`. Product name: **Universal platform**.

## One-command run

```bash
python3 -m pip install -e ".[dev]"

export UNIVERSAL_LLM_BASE_URL=https://api.openai.com/v1
export UNIVERSAL_LLM_API_KEY=sk-...
export UNIVERSAL_LLM_MODEL=gpt-4o-mini

python3 -m universal ask "What is 2+2?"
```

That creates a `general` agent, starts it, completes the prompt through the OpenAI-compatible provider, prints the answer, and stops the agent. The `universal` console script is the same as `python3 -m universal` once the scripts directory is on `PATH`.

Other faces:

```bash
python3 -m universal ask --template researcher "Summarize why event sourcing is used"
python3 -m universal ask --template coder "Write a Python function that reverses a string"
python3 -m universal chat --template general
python3 -m universal templates
python3 -m universal deploy general --out ./agent.zip
```

## Environment variables

| Variable | Required for live calls | Default |
|---|---|---|
| `UNIVERSAL_LLM_BASE_URL` | yes | `https://api.openai.com/v1` |
| `UNIVERSAL_LLM_API_KEY` | yes | empty |
| `UNIVERSAL_LLM_MODEL` | yes | `gpt-4o-mini` |
| `UNIVERSAL_LLM_TIMEOUT` | no | `60` |
| `UNIVERSAL_LLM_ORGANIZATION` | no | empty |

Copy `.env.example`. **Do not commit secrets.** The ZIP packager redacts the API key.

Any server that speaks the OpenAI Chat Completions API works: OpenAI, OpenRouter, an Ollama `/v1` shim, a company gateway. Hugging Face and MLX are not stubbed here; they land later as real provider plugins.

## Architecture

```
Universal          composition root
  ├── AgentRegistry     constructed once
  ├── AgentLifecycle    constructed once, holds the registry
  └── AgentFactory      injected with those two objects
        ├── AgentGenerator   create — same registry + lifecycle
        └── AgentManager     start / stop / list / delete / deploy
```

An **Agent** is `provider + channel + PluginHost`. `Agent.complete(prompt)` runs plugin hooks, calls the provider, and loops on tool calls.

**Hot-swap:** `agent.attach_plugin(plugin)` / `agent.detach_plugin(name)` work while the agent is running. Plugins hook `before_complete`, `after_complete`, and optional tools. This is implemented in v1.

```
universal/
  core/          Agent, registry, lifecycle, factory, generator, manager
  providers/     OpenAI-compatible HTTP client (the only v1 provider)
  channels/      BaseCommunication + CLI channel
  plugins/       system prompt, transcript, tool belt
  templates/     general, researcher, coder
  deploy/        ZIP packager + GitHub stub interface
```

### Templates (the first three faces)

| Id | Role |
|---|---|
| `general` | Everyday questions |
| `researcher` | Known / inferred / missing; ships the `utc_now` tool |
| `coder` | Software-engineering answers |

### Factory operations

`create` · `start` · `stop` · `list` · `delete` · `deploy`

`deploy` writes a ZIP (`manifest.json`, `config.json`, `system_prompt.txt`, `README.txt`). GitHub deploy is a stub interface that returns “deferred”.

## Tests

```bash
python3 -m pytest
```

Coverage that the brief asked for:

- shared registry/lifecycle injected into Generator and Manager
- agent answers via a mocked provider (and a recorded HTTP provider test)
- three templates load
- packager writes a zip

## Deferred

- Hugging Face / MLX as real provider plugins (not fake “local” models)
- Telegram / Slack channels (`BaseCommunication` is the slot)
- GitHub deploy (interface only)
- Session persistence across processes (registry is in-memory)
- Streaming tokens
- A web or ChatGPT-shaped UI — not in scope

## Conflicts with earlier notes

Early design notes used the name “Aegis” and sketched a tree under `factory/`. That name is ChatGPT design history, not the product. This repo uses **Universal platform** / package `universal`, and the real core lives under `universal/`.

Those notes also suggested many fake LLM providers, a fake local model, and ChatGPT-branded UI clones. Those locks win: one real OpenAI-compatible client, no fake local model, no ChatGPT UI.

## Library usage

```python
from universal import Universal
from universal.config import Settings

platform = Universal(Settings.from_env())
agent = platform.factory.create("general", name="helper")
platform.factory.start(agent.id)
print(agent.complete("What is 2+2?"))
platform.factory.stop(agent.id)
platform.factory.deploy(agent.id, dest="helper.zip")
```

Inject a fake provider in tests:

```python
platform = Universal(settings, provider=my_fake_provider)
```
