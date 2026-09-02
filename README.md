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
python3 -m universal shell
```

`ask` and `chat` go through the bound CLI channel after `factory.start` (`Agent.accept` / `serve_forever`). `complete` is the model path the channel handler calls — do not call it from a started agent if you want the channel contract.

`universal shell` is the factory control plane in one process: `create`, `start`, `stop`, `list`, `delete`, `ask`, `deploy`. That is how those operations stay on the single injected registry.

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

An **Agent** is `provider + channel + PluginHost`. `Agent.complete(prompt)` is the model path. After `factory.start`, inbound text uses `Agent.accept` so it goes through the bound channel. `PluginCatalog` turns template plugin ids into instances.

**Hot-swap:** `agent.attach_plugin(plugin)` / `agent.detach_plugin(name)` work while the agent is running. Plugins hook `before_complete`, `after_complete`, and optional tools. This is implemented in v1.

```
universal/
  core/          Agent, registry, lifecycle, factory, generator, manager
  providers/     OpenAI-compatible HTTP client (the only v1 provider)
  channels/      BaseCommunication + CLI channel
  plugins/       catalog + system prompt, transcript, tool belt
  templates/     general, researcher, coder
  deploy/        ZIP packager + GitHub stub interface
  session.py     in-process factory shell (one Universal root)
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
- Telegram / Slack / HTTP-callback channels (`BaseCommunication` is the slot)
- GitHub deploy (interface only; calling it does not write a ZIP)
- Cross-process registry (see integration risks)
- Streaming tokens
- A web or ChatGPT-shaped UI — not in scope

## Conflicts with earlier notes

Notes 00–01 are not in this tree. What we have from the brief: an “Aegis” sketch under `factory/`, many fake LLM providers, a fake local model, and ChatGPT-branded UI clones. Those conflict with the locks. This repo uses **Universal platform** / package `universal`, core under `universal/`, one real OpenAI-compatible client, no fake local model, no ChatGPT UI.

## Integration risks (stopped here)

The owner lock is: if a note is consistent but the integration would break another subsystem or the wiring, stop and report — do not push through. A smaller aligned cut wins.

**Judged against the locked contracts (one registry, one lifecycle, one provider, one channel, plugin assembly).** Notes 00–01 were not available in-repo, so this list is wiring risk, not only name conflicts.

1. **No second registry.** A file, sqlite, or sidecar store so `universal create` then `universal list` works across processes would duplicate `AgentRegistry` / `AgentLifecycle`. Generator and Manager would no longer share one in-memory pair. **Stopped.** Use `universal shell` or the library in one process.

2. **No `start` / `stop` / `delete` as one-shot CLI commands.** They would look like they persist and would invite a store. Factory methods exist; the shell and the library call them.

3. **No second live channel in this cut.** An HTTP callback next to the CLI channel would mean `factory.start` has to pick a transport or run two. That splits the “one working channel” contract. Telegram/Slack stay behind `BaseCommunication`.

4. **No extra provider objects per agent.** The generator caches one client and injects it. A per-agent `httpx.Client` would leak and hide the “one provider” wiring.

5. **GitHub deploy is not a silent ZIP.** `target="github"` raises `DeployError` and writes nothing. The working target is `zip`.

6. **System prompt has two honest layers, not a third.** `Agent.complete` prepends `agent.system_prompt` so an agent without plugins still works. `SystemPromptPlugin` replaces leading system messages. The generator sets both from the same template string. A sync service between them would be a third owner — **not added.** Mutate both if you change the prompt, or detach the plugin and set `agent.system_prompt`.

7. **Plugin ids go through `PluginCatalog`.** Templates name plugins; the generator does not `if plugin_id == ...`. Filesystem plugin discovery is deferred (it would load code the factory did not inject).

If a later note asks for any of the above “because the sketch did”, do not implement it until the registry/lifecycle/channel contracts are redesigned on purpose.

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
