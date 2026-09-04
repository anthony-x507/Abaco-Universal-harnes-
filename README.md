# Universal platform

Universal is a **plugin-based agent factory and harness**. You assemble an agent from a **model**, a **channel**, and **plugins**, then run it from a CLI, a localhost HTTP factory, or the browser SPA.

It is for people who want a small, honest runtime: one registry, one lifecycle, one OpenAI-compatible provider, and inbound text that always goes through the agent’s bound channel. It is not a Chat Completions clone and not a bag of placeholder providers.

**What ships today**

- Three templates: `general`, `researcher`, `coder`
- Live OpenAI-compatible HTTP, plus `--demo` echo for the SPA
- CLI (`ask`, `chat`, `shell`, `deploy`) and webhook channel
- Browser face: Chat, Agents, Design, Settings
- Persistent facts (`memory.json`), Auto tool loop (`run`), identity snapshot, token/cost meter
- Native tools on every agent: terminal, TTS (voice + speed), Whisper STT, vision, web search, scraper
- ZIP export with no secrets

Package name: `universal`. Product name: **Universal platform**.

Walk through every face in about ten minutes: **[DEMO.md](DEMO.md)**. One-command setup: **[demo.sh](demo.sh)**.

## Install

**Mac:** download **only** `Universal.dmg` from [Releases](https://github.com/anthony-x507/Abaco-Universal-harnes-/releases). Open it and drag **Universal.app** to `/Applications`. That is the official install. Source zips are not a product install and cannot self-update.

Python 3.11+. The supported path is pip (the project uses hatchling; Poetry is not required).

```bash
python3 -m pip install -e ".[dev]"
cp .env.example .env   # then set UNIVERSAL_LLM_* for live calls
```

The console script `universal` is the same as `python3 -m universal` once your scripts directory is on `PATH`.

Browser face (optional, second terminal):

```bash
cd web
bun install
bun run dev          # http://127.0.0.1:43123  → proxies /v1 to :43124
```

## Quick start

**Demo (no API key)** — factory + echo provider on localhost:

```bash
./demo.sh
# or:
python3 -m universal serve --demo --host 127.0.0.1 --port 43124
```

Open `http://127.0.0.1:43123` if Vite is running, or call the factory directly:

```bash
curl -sS http://127.0.0.1:43124/health
```

**Live one-shot** — needs `UNIVERSAL_LLM_API_KEY`:

```bash
export UNIVERSAL_LLM_BASE_URL=https://api.openai.com/v1
export UNIVERSAL_LLM_API_KEY=sk-...
export UNIVERSAL_LLM_MODEL=gpt-4o-mini

python3 -m universal ask "What is 2+2?"
python3 -m universal ask --template researcher "Summarize why event sourcing is used"
python3 -m universal ask --template coder "Write a Python function that reverses a string"
```

Any OpenAI Chat Completions–compatible server works (OpenAI, OpenRouter, Ollama `/v1`, a company gateway). Hugging Face and MLX are not stubbed here.

`GET /v1/models` and `universal models` list **40 companies**, each with that lab's **latest** flagship (OpenAI GPT-5.6 Sol, Anthropic Claude Fable 5.1, Google Gemini 3.8 Flash, …). There is not a second OpenAI row and not ten Llama hosts. They only fill `UNIVERSAL_LLM_BASE_URL` and `UNIVERSAL_LLM_MODEL` for the existing `OpenAICompatProvider`. Settings offers the same picker; Design create uses the process default. This is not 40 HTTP clients. Labs without a public OpenAI-compatible API are reached through OpenRouter.

## CLI

| Command | What it does |
|---|---|
| `universal ask "…"` | Create, start, `accept` the prompt, print, stop. One process. |
| `universal chat` | Interactive CLI channel. Type `/quit` to exit. |
| `universal templates` | List `general`, `researcher`, `coder`. |
| `universal create <template>` | Print an id. The agent dies when this process exits. |
| `universal list` | Agents **in this process only**. |
| `universal deploy [template]` | Create an agent and write a ZIP. |
| `universal shell` | One process, one registry: `create` / `start` / `stop` / `list` / `delete` / `ask` / `deploy`. |
| `universal serve [--demo]` | HTTP factory on `127.0.0.1:43124`. Localhost only. |
| `universal desktop [--demo]` | Native window (pywebview) on the same factory + built SPA. |
| `universal update` | Check GitHub Releases for a newer `Universal.dmg`. `--apply` on the packaged Mac app. |

`ask` and `chat` go through the bound CLI channel after `factory.start` (`Agent.accept`). `complete` is the model path the channel handler calls — do not call it from a started agent if you want the channel contract.

There is **no** one-shot `universal start` / `stop` / `delete`. Those live on the factory, the shell, and `serve`, so they cannot pretend to persist across CLI processes.

Shell example (one registry for the whole session):

```text
universal> create researcher --name lab
universal> start <id>
universal> ask <id> What time is it in UTC?
universal> deploy <id> --out ./lab.zip
universal> quit
```

## Browser SPA

`python3 -m universal serve` is the control plane (`GET /health`, factory REST under `/v1/agents`, `/v1/templates`, `/v1/settings`, `/v1/channels`). It is **not** `/v1/chat/completions`.

The SPA in `web/` talks only to that factory. Chat is nav, messages, and workspace. Drop any document on the write bar. Audio records to WAV and `POST /v1/transcribe` runs local Whisper (`tiny`). The composer holds about 5,000 words without a cutoff. Install the optional extra if health shows `"whisper": false`: `pip install 'universal[media]'`.

| Control | Behavior |
|---|---|
| Send (Auto off) | `POST /v1/agents/{id}/ask` with SSE |
| **Auto** (toggle, default off) | `POST /v1/agents/{id}/run` — tool loop without extra user turns |
| Clear history | `POST /v1/agents/{id}/reset` — state unchanged |
| Download ZIP | `POST /v1/agents/{id}/deploy` |
| Plugin line | Readable labels such as `Terminal: run_command`, `Tools: utc_now` |
| Usage meter | `Tokens: 1,234 \| Cost: $0.002` |

`--demo` injects an echo provider. Settings update the running process only; they are never written to disk. The API key is never packed into a ZIP.

More SPA notes: [web/README.md](web/README.md).

## Webhook

`create(..., channel="webhook")` is registered. Other processes POST inbound to the factory on localhost. The route only accepts agents whose channel is `webhook`. Inbound is `Agent.accept` → `WebhookChannel.handle_text`, not a bypass.

```bash
python3 -m universal serve --demo --port 43124

curl -sS http://127.0.0.1:43124/v1/agents \
  -H 'Content-Type: application/json' \
  -d '{"template":"researcher","name":"hook","channel":"webhook"}'

curl -sS http://127.0.0.1:43124/v1/agents/AGENT_ID/webhook \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello from another process"}'
```

The JSON response includes `answer`. Optional `outbound_url` at create: the channel POSTs `{ "agent_id", "text" }` there after each reply. Empty URL means no outbound. A failed callback sets `outbound_error` and still returns `answer`. Serve stays on localhost.

A webhook agent can still answer in Chat via `/ask`.

## Memory

The researcher template sets `memory=True`. Facts go to `memory.json` under `UNIVERSAL_MEMORY_DIR` (default: a temp folder), keyed by **agent name** — not a second registry.

- Recreate an agent with the same name to reload facts after the process exits.
- The model sees the last **10** turns plus the system prompt. The UI keeps the full thread until **Clear history**.
- Chat history is **not** written to the registry snapshot.

`--demo` Echo will not invent remembered names. A provider that reads the injected memory facts will.

## Autonomous loop (Auto)

`Agent.complete` already loops tools. `Agent.run(prompt, max_iterations=5)` is a layer **above** `accept`: same inbound, a cap on that loop. `ask` and `accept` stay one-turn as before.

```bash
# HTTP (after serve --demo and a started researcher)
curl -sS http://127.0.0.1:43124/v1/agents/AGENT_ID/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What time is it in UTC? Investigate and summarize."}'
```

In Chat, leave Auto off for `/ask`. Turn Auto on for `/run`. Demo echo issues `utc_now` when you ask about time; a 2s banner shows the tool and is not stored as a chat turn.

## Registry snapshot

`universal serve` writes agent **identities** to `.universal/registry.json` (or `UNIVERSAL_REGISTRY_FILE`). Same in-memory `AgentRegistry`. No history, no API keys, no auto-start.

After a restart, Agents lists the same names as `stopped` (or `error`). Press **Start**. CLI one-shots do not write this file unless the env is set. An empty `UNIVERSAL_REGISTRY_FILE` keeps serve in memory only.

## Usage meter

Each provider call records prompt tokens, completion tokens, model, latency, and a **fixed-price** estimate (not a billing API). Example: gpt-4o-mini `$0.00015` / `$0.0006` per 1K tokens. Echo and fake models cost `$0`. If the provider omits `usage`, tokens are estimated as `len/4`.

Totals live on the agent (not in the snapshot) and ship in the ZIP as `usage.json`. Chat shows them in the message header.

## Plugins

Templates name plugin ids. `PluginCatalog` turns those ids into instances. The generator does not `if plugin_id == ...`. Native plugins are **always** installed on create (even if you pass an empty plugin list).

Built-in catalog ids:

| Id | Tool | Notes |
|---|---|---|
| `terminal` | `run_command` | Local shell. Timeout 15s. Refuses obvious destroyers (`rm -rf /`, `mkfs`, `dd of=`, shutdown). `UNIVERSAL_TERMINAL_DIR` sets cwd. |
| `tts` | `speak` | Voice `male` / `female` / `default`, speed `0.5`–`2.0`. Uses `say`, `espeak`/`espeak-ng`, or `spd-say` when present. Text is never interpolated into a shell string. |
| `stt` | `transcribe` | Local Whisper (`tiny`…`large`). Optional extra: `pip install 'universal[media]'`. Missing Whisper returns an error string; CI does not download models. |
| `vision` | `describe_image` | Demo caption without a vision method. Live `OpenAICompatProvider.complete_vision` uses the same HTTP client (not a second provider). |
| `web_search` | `search_web` | DuckDuckGo Instant Answer. No API key. |
| `scraper` | `scrape_url` | BeautifulSoup. http(s) only; localhost and private IPs are rejected. |
| `tools` | `utc_now` | Researcher only, in addition to the six natives. |
| `transcript` / `system_prompt` | — | Catalog only. Templates do **not** install them. The system prompt is `agent.system_prompt`. |

Hot-swap on a live agent:

```python
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool

belt = ToolBeltPlugin()
belt.add(utc_now_tool())
agent.attach_plugin(belt)
# agent.detach_plugin("tools")
```

Register a factory so templates can name it:

```python
from universal.plugins.catalog import PluginCatalog
from universal.plugins.tools import ToolBeltPlugin, utc_now_tool

def clock_plugin(**_kwargs):
    belt = ToolBeltPlugin()
    belt.add(utc_now_tool())
    return belt

plugins = PluginCatalog()
plugins.register("tools", clock_plugin)
```

`utc_now` is a real tool: current UTC as ISO-8601. No network, no secrets. That is the working example — add more `BoundTool`s the same way.

Filesystem plugin discovery is deferred (it would load code the factory did not inject).

## ZIP deploy

`deploy` writes:

`manifest.json` · `config.json` · `system_prompt.txt` · `README.txt` · `usage.json`

API keys are never written. GitHub deploy is a stub: it raises and writes nothing.

```bash
python3 -m universal deploy researcher --name boxed --out ./boxed.zip
# or Agents → Download ZIP, or:
curl -sS -X POST http://127.0.0.1:43124/v1/agents/AGENT_ID/deploy -o agent.zip
```

Unpack and recreate with `universal create <template> --name <name>` (or the SPA). The ZIP is a portable description, not a second runtime.

## macOS desktop app

The factory plugins above are already in the Python package. A download does **not** need a second plugin tree. The Mac wrapper starts the same `universal serve` app and opens a native window on that localhost URL (SPA + `/v1` on port **43124**, not a second factory).

```bash
python3 -m pip install -e ".[desktop]"
cd web && bun install && bun run build && cd ..
python3 -m universal desktop --demo          # window (needs pywebview)
python3 -m universal desktop --check         # CI / headless: health + web/dist
```

On a Mac:

```bash
scripts/build_macos.sh    # bun build + PyInstaller → Universal.app
scripts/create_dmg.sh     # Universal.dmg (hdiutil)
```

`build_macos.sh` on Linux only builds the SPA and runs `--check` (there is no `.app` on this OS). Whisper is **not** bundled; install `universal[media]` if you want local STT. TTS uses macOS `say`. Offline: terminal, TTS, STT (if Whisper is present), and local vision captions. Live LLM and `search_web` / `scrape_url` need the network.

The crystal Ábaco mark (`web/src/assets/logo.png`) is the window watermark (15% opacity), the header lockup next to **Abaco Universal Harness**, and the splash shown while the SPA mounts. `scripts/make_icns.sh` builds `Universal.icns` for the Dock, Finder, and title-bar icon; `build_macos.sh` packages that file into `Universal.app`.

`app.py` is the PyInstaller entry. It calls `universal.desktop.main` — it does not construct a second registry.

Replacing `Universal.app` does **not** wipe agents. Memory and the identity sidecar live under Application Support (`~/Library/Application Support/Universal` on a Mac), not inside the `.app`. Native plugin **code** stays in the package so an update ships the six tools again. A `plugins/manifest.json` records the ids; the factory does not import `.py` from that folder.

Self-update (packaged Mac app only): the repo `anthony-x507/Abaco-Universal-harnes-` is baked into `version.json`. On launch the SPA checks silently and prompts if a newer `.dmg` exists. Settings → **Check for Updates**. **Download now** replaces `/Applications/Universal.app` and relaunches. Nothing is overwritten until you confirm. If the app is not in `/Applications`, Settings warns that updates will fail. Gatekeeper override is required until signing exists.

```bash
universal update                 # check
universal update --apply         # packaged Mac app only
```

A tag `v*` on GitHub runs `.github/workflows/release.yml` (macOS runner, no Whisper) and attaches `Universal.dmg`.

## Library

```python
from universal import Universal
from universal.config import Settings

platform = Universal(Settings.from_env())
agent = platform.factory.create("general", name="helper")
platform.factory.start(agent.id)
print(agent.accept("What is 2+2?"))
platform.factory.stop(agent.id)
platform.factory.deploy(agent.id, dest="helper.zip")
```

Tests inject a fake provider. Do not construct a second `AgentRegistry` or `AgentLifecycle` — `Universal` builds those once and injects them.

```python
platform = Universal(settings, provider=my_fake_provider)
```

## Environment variables

| Variable | Required for live calls | Default |
|---|---|---|
| `UNIVERSAL_LLM_BASE_URL` | yes | `https://api.openai.com/v1` |
| `UNIVERSAL_LLM_API_KEY` | yes | empty |
| `UNIVERSAL_LLM_MODEL` | yes | `gpt-4o-mini` |
| `UNIVERSAL_LLM_TIMEOUT` | no | `60` |
| `UNIVERSAL_LLM_ORGANIZATION` | no | empty |
| `UNIVERSAL_REGISTRY_FILE` | no | serve: `.universal/registry.json`; empty disables |
| `UNIVERSAL_MEMORY_DIR` | no | temp folder / `universal-memory` |
| `UNIVERSAL_WEB_DIST` | no | `web/dist` (or the PyInstaller extract dir) |
| `UNIVERSAL_TERMINAL_DIR` | no | process cwd for `run_command` |
| `UNIVERSAL_USER_DATA` | no | override Application Support / XDG data dir (tests) |

Copy `.env.example`. **Do not commit secrets.**

## Architecture

```
Universal          composition root
  ├── AgentRegistry     constructed once (optional JSON identity sidecar)
  ├── AgentLifecycle    constructed once, holds the registry
  ├── StatsCollector    usage / fixed-price estimates
  └── AgentFactory      injected with those objects
        ├── AgentGenerator   create
        └── AgentManager     start / stop / list / delete / deploy
```

An **Agent** is `provider + channel + PluginHost`. After `factory.start`, inbound uses `accept` / `accept_stream` so it goes through the bound channel.

```
universal/
  core/          Agent, registry, lifecycle, factory, generator, manager
  providers/     OpenAI-compatible HTTP client (the only v1 provider)
  channels/      BaseCommunication + CLI and webhook
  plugins/       catalog + system prompt, transcript, tool belt
  templates/     general, researcher, coder
  deploy/        ZIP packager + GitHub stub
  session.py     in-process factory shell
  server.py      HTTP factory control plane
web/             SPA (Chat, Agents, Design, Settings)
```

### Templates

| Id | Role |
|---|---|
| `general` | Everyday questions |
| `researcher` | Known / inferred / missing; `utc_now` + memory |
| `coder` | Software-engineering answers |

### Design locks (do not “fix” these)

1. One in-memory registry and lifecycle, injected into Generator and Manager. The serve JSON file is an identity sidecar, not a second registry. No SQLite. No history or secrets on disk via that file.
2. Inbound after start uses `Agent.accept`. HTTP does not call the provider.
3. No `/v1/chat/completions`. Serve binds localhost only.
4. One live provider object, cached on the generator. `--demo` echo is not a registered “local” model.
5. Channels are registered and chosen at `create`. Telegram/Slack wait.
6. Plugin ids go through `PluginCatalog`.

## Extend

- **Plugin:** implement `Plugin`, register a factory, name it from a template or `attach_plugin`.
- **Channel:** subclass `BaseCommunication`, `catalog.register("id", factory)`, choose it at `create`.
- **Template:** add a dataclass in `universal/templates/catalog.py` (not YAML).
- **Provider:** later, as a real client — not a dummy registry row.

See `docs/testing_guide.md` and `docs/integration_plan.md` before growing the spine.

## Tests

```bash
python3 -m pytest
cd web && bun run test
cd web && bun run build
```

Quality-gate ids T01–T17 and W01–W05: `docs/testing_guide.md`. CI uses `FakeProvider` / `EchoProvider` and mocked `fetch` / `httpx.post` — never a live LLM.

## Deferred

- Hugging Face / MLX as real provider plugins
- Telegram / Slack (after webhook)
- GitHub deploy (interface only)
- Cross-process CLI (`universal create` then `universal list` in another process)

## Docs

| File | What |
|---|---|
| [DEMO.md](DEMO.md) | Ten-minute walkthrough |
| [demo.sh](demo.sh) | Install, serve --demo, create sample agents |
| [web/README.md](web/README.md) | SPA ports and buttons |
| [docs/testing_guide.md](docs/testing_guide.md) | Quality gates |
| [docs/go_no_go.md](docs/go_no_go.md) | Slice gate |
