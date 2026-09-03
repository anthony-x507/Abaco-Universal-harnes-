# Universal integration plan

The owner archived 48 notes (originally announced as 51) and asked for an integration plan. This document is the plan. It is **not** a license to copy the Aegis tree.

Package: `universal`. Product: **Universal platform**. Face/app is built from zero.

## What is already shipped

The first cut is done. Do not rebuild it from notes 01–02.

```
Universal                composition root
  ├── AgentRegistry      constructed once
  ├── AgentLifecycle     constructed once
  └── AgentFactory       injected pair
        ├── AgentGenerator
        └── AgentManager
```

An agent is `provider + channel + PluginHost`.

| Piece | Status |
|---|---|
| One OpenAI-compatible HTTP provider | shipped |
| One working channel (`cli`) | shipped |
| Three templates (`general`, `researcher`, `coder`) | shipped |
| Plugin catalog (`system_prompt`, `transcript`, `tools` / `utc_now`) | shipped |
| Hot-swap attach/detach | shipped |
| `python3 -m universal` (`ask`, `chat`, `templates`, `deploy`, `shell`) | shipped |
| ZIP deploy | shipped |
| GitHub deploy | stub (raises, writes nothing) |
| In-process factory session | shipped |
| Tests | `python3 -m pytest` |

Run path stays `python3 -m universal`. Live calls need `UNIVERSAL_LLM_API_KEY`.

## How to read the notes

The notes describe a second product: **Aegis Agent Factory** under `factory/` / `aegis-agent/` / `api/` / `ui/aegis-ui`. That stack constructs its own factory, registers dummy providers, and puts a ChatGPT-shaped UI in front.

**Integrating a note means taking an idea that fits the locks and implementing it on the existing `Universal` root.** It does not mean copying the note's files, folder names, or assembly order.

Note 48's copy-order (`requirements.txt` → `core/` → `api/` → `ui/aegis-ui/` → `factory/`) is the wrong spine. Universal already has core. Starting from that letter would fork registry and lifecycle.

## Three buckets

### Never integrate

| Notes | Why |
|---|---|
| 10 | Jammer TX / spoof / counter-drone. Never. |
| 07–09 | Offensive wireless, unauthorized vehicle/RF, unauthorized drone control. |
| 11 | Auto-run root `ip` / `iw` / `batctl` on the host. |
| 12 | Auto-flash USB / privileged hardware Docker. |
| 02 (file registry + per-class registry/lifecycle) | Second store; splits the injected pair. |
| 04, 18 | 25+ / 40 fake providers and send-only channel stubs. |
| 14–17, 19–22, 34–35, 37, 39–47 | LibreChat / clone FastAPI / Aegis HTML / `ui/aegis-ui` / Aegis installer. |
| 23–33, 42, 44 | Playwright global browser, click-all, cookie/login record-replay, AI login skills, cron/NL scheduler of replay. |
| 48 as build order | Reconstructs Aegis. Archive only. Do not write `docs/assembly_guide_es.md`. |

### Ideas only (reuse later, never copy)

| Notes | What may be reused |
|---|---|
| 06 | Channel *shapes* (Telegram, Discord, Slack, SMTP, webhook) as `BaseCommunication` plugins — one at a time, real credentials, chosen at `create`. |
| 03 | Bun as a later **tool plugin** (run `bun` for an owner project). Not the UI package manager unless we choose it then. |
| 13 | Local RAG as a scoped plugin. Must not become a second agent memory/store. |
| 21 (streaming idea) | Token stream on the **existing** OpenAI-compat client. Not a provider-bypass `/v1/chat/stream`. |
| 38 | Tokens (`#0B0E14`, `#00E5FF`, Inter) may inform a Universal face. No Aegis wordmark. |
| 39–41, 43, 45–47 | Vite/TS/Tailwind, palette, resize, PWA/Tauri *ideas*. Universal name; talk to the existing factory. |
| 08–09 (legal slice only) | Later: OBD on a vehicle the owner controls; mission-file drone *simulation*. Not relay/replay, not jamming. |

### Aligned cuts (do these, in this order)

Each cut is one slice. Stop if it would construct a second `AgentRegistry`, a second `AgentLifecycle`, a second provider client per agent, or a second live channel without `create` choosing it.

---

### Cut 1 — Channel chosen at `create`

**Why first.** `AgentGenerator.generate` hardcodes `CLIChannel()`. A web face or Telegram without this choice splits `factory.start`.

**Change.**

- `ChannelCatalog` (same pattern as `PluginCatalog`): id → factory. v1 registers `cli` only.
- `factory.create(template_id, name=None, *, channel="cli", provider=None)`.
- `AgentInfo.channel` already exists; keep it accurate.
- Shell: `create general --channel cli`.
- Tests: default is `cli`; unknown id raises; generator still injects the shared provider and registry.

**Out of scope.** Telegram, Discord, HTTP callback, second process.

---

### Cut 2 — HTTP control plane on the existing root

**Why.** A from-zero face needs HTTP. Notes 15–19's `api.main` that does `AgentFactory()` is a second factory. Do not add that.

**Change.**

- One process holds one `Universal` (same as `FactorySession`).
- Thin HTTP layer (FastAPI is fine) that **injects** that instance.
- Map factory operations, not an OpenAI clone:

  | Method | Path | Factory |
  |---|---|---|
  | GET | `/health` | process up |
  | GET | `/templates` | `list_templates()` |
  | GET | `/plugins` | `PluginCatalog.ids()` |
  | GET | `/agents` | `factory.list()` |
  | POST | `/agents` | `factory.create` |
  | POST | `/agents/{id}/start` | `factory.start` |
  | POST | `/agents/{id}/stop` | `factory.stop` |
  | DELETE | `/agents/{id}` | `factory.delete` |
  | POST | `/agents/{id}/ask` | `start` + `Agent.accept` |
  | POST | `/agents/{id}/deploy` | `factory.deploy` (zip) |

- Empty / loading / error JSON. No `sk-dummy`. No hardcoded 25+ provider list. No `ew_specialist`.
- Tests: TestClient against this app with a `FakeProvider`, asserting the same registry object.

**Out of scope.** `/v1/chat/completions`, `/browser/*`, `/scheduler/*`, `/plugins/execute` as a second runner, Mongo, LibreChat compose, `/code/execute` sandbox.

---

### Cut 3 — Face from zero

**Why.** Owner lock: face/app is built from zero. Notes 38–47 are a ChatGPT-mission-control Aegis app against the clone API.

**Change.**

- New web app (Vite + TypeScript + Tailwind is acceptable). Name it Universal. Not `ui/aegis-ui`.
- Talks only to Cut 2.
- First pages: **Chat** (ask/accept + transcript), **Agents** (list/create/start/stop), **Settings** (`universal-settings` in localStorage: model display, API origin, theme).
- Tokens from note 38 may be used without the “A” logo or “Aegis Agent Factory” chrome.
- Empty, loading, and error states. Desktop and mobile.

**Out of scope for this cut.** Browser page, scheduler page, command palette required, PWA/Tauri, plugin “execute arbitrary action” console.

Plugins in the UI, if shown, are catalog ids plus attach/detach on an agent — not a generic `/plugins/execute`.

---

### Cut 4 — One real extra channel

**Prerequisite.** Cut 1.

Pick **one**: webhook HTTP callback (natural pair with the web face) **or** Telegram with a real bot token. Implement `BaseCommunication`. Register in `ChannelCatalog`. `create` selects it.

**Out of scope.** 5 or 30 channels at once. SMTP/Discord/Slack until the first extra channel is proven.

---

### Cut 5 — Streaming on the existing provider

Add a stream path to `OpenAICompatProvider` and surface it on Cut 2 (`/agents/{id}/ask` SSE) and Cut 3. Channel handler still calls the agent; do not bypass `Agent.accept`.

---

### Later, one plugin at a time (optional)

Only after Cuts 1–3, and only if the owner asks for that plugin:

1. Extra tools on the existing `tools` belt (owner-safe: time, local file read the owner points at).
2. Bun tool plugin (note 03) — invoke Bun for a project path the owner names.
3. Local RAG plugin (note 13) — must not replace agent `_history` or add a second registry.
4. Owner-app test plugin — a11y/perf against **their** app URL. No click-all, no cookie jar, no login replay.
5. Hugging Face / MLX as **real** provider plugins when there is a working client — not a fake `local` model.

## Gate for every cut

Stop and report if the change would:

1. Construct a second `AgentRegistry` or `AgentLifecycle`.
2. Give Generator and Manager different instances of those.
3. Persist agents in JSON/sqlite so CLI one-shots look cross-process (use the HTTP process or `universal shell` instead).
4. Add a live channel without `create(..., channel=...)`.
5. Construct a new `httpx` client per agent.
6. Brand anything Aegis.
7. Ship LibreChat, Open WebUI, or a ChatGPT clone.
8. Register placeholder LLM providers or channels.
9. Touch jammer / spoof / unauthorized RF / login-replay / click-all.

## Recommended next action

Implement **Cut 1 only**. It is the smallest wiring change that unblocks Cuts 2–4 without forking the factory. Do not start the web app until Cut 1 and Cut 2 exist.

## What we will not do “because the notes did”

- Copy `factory/`, `api/`, `ui/aegis-ui/`, `install.sh`, `Dockerfile.full`.
- Replace this README or add an Aegis API reference.
- Save Spanish/English Aegis assembly or UI-decision docs as live product docs. Those stay in `notes/`.
- Schedule or AI-generate browser login skills.
