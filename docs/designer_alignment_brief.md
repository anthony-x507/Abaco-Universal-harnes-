# Briefing for the designer — Universal platform alignment

This is the message engineering needs answered before we implement more of the integration plan. Please reply with an alignment plan: what stays, what drops, what the first face is, and which technical decisions you own.

Copy below the line and send it. English is the repo language; you can reply in Spanish.

---

Hello,

We have a working product spine and a large archive of design notes that describe a different product. The owner asked engineering to execute an integration plan, and asked us to send you this briefing so **you** can give us an alignment plan.

We will not copy the Aegis tree onto the running factory. We also will not guess your product intent where the notes and the locks disagree. We need your decisions.

## 1. What is actually built (today)

Product name: **Universal platform**. Python package: `universal`. Not Aegis. Not `factory/`. Not `aegis-agent/`.

There is one composition root, `Universal`, constructed once per process:

```
Universal
  ├── AgentRegistry      once
  ├── AgentLifecycle     once, holds that registry
  └── AgentFactory       injected with those two
        ├── AgentGenerator   create
        └── AgentManager     start / stop / list / delete / deploy
```

An **agent** is `provider + channel + PluginHost`.

- `Agent.complete(prompt)` is the model path (plugins → provider → tool loop).
- After `factory.start`, inbound text uses `Agent.accept`, which goes through the bound channel. The channel handler calls `complete`. Do not bypass the channel on a started agent.

**Shipped in v1**

| Piece | What it is |
|---|---|
| Provider | One real OpenAI-compatible HTTP client (`POST {base}/chat/completions`). Same client is reused for every agent this root creates. Env: `UNIVERSAL_LLM_BASE_URL`, `UNIVERSAL_LLM_API_KEY`, `UNIVERSAL_LLM_MODEL`. Works with OpenAI, OpenRouter, Ollama `/v1`, company gateways. Hugging Face and MLX are **not** stubbed. |
| Channel | One working channel: `cli`. `BaseCommunication` is the slot for later channels. |
| Templates | `general`, `researcher`, `coder`. Templates name plugin ids; they do not construct objects. |
| Plugins | Catalog: `system_prompt`, `transcript`, `tools`. Researcher ships `utc_now`. Hot-swap `attach_plugin` / `detach_plugin` works while running. |
| CLI | `python3 -m universal ask`, `chat`, `templates`, `deploy`, `shell`. |
| Factory session | `universal shell`: create / start / stop / list / delete / ask / deploy against **one process**. No disk/sqlite registry. |
| Deploy | ZIP works (`manifest.json`, `config.json`, `system_prompt.txt`, `README.txt`; API key redacted). GitHub deploy is a stub: it raises and writes nothing. |
| Tests | `python3 -m pytest` — wiring, injection, templates, packager, channel, session. |
| UI | **None.** Owner lock: face/app is built from zero. No LibreChat, no Open WebUI, no `ui/aegis-ui`, no pywebview ChatGPT clone. |

How to run a live answer:

```bash
python3 -m pip install -e ".[dev]"
export UNIVERSAL_LLM_BASE_URL=https://api.openai.com/v1
export UNIVERSAL_LLM_API_KEY=sk-...
export UNIVERSAL_LLM_MODEL=gpt-4o-mini
python3 -m universal ask "What is 2+2?"
```

`create` then `list` in two separate CLI processes will **not** see the same agents. Persistence is in-memory on purpose. Use `universal shell` (or, later, one HTTP process that holds one `Universal`).

## 2. What the notes described (archive, not the product)

The owner pasted **48 notes** (announced as 51; 49–51 never arrived). They are stored verbatim under `notes/` and were **not** integrated into `universal/`.

They describe **Aegis Agent Factory**:

- Package/folders: `factory/`, `aegis-agent/`, `api/`, `ui/aegis-ui`
- Generator and Manager each own their own registry + lifecycle (note 02)
- JSON file registry so CLI one-shots persist (note 02)
- 40 / 25+ LLM providers including placeholders and a fake local model (notes 04, 18)
- 30 / 25+ channels, many send-only skeletons (notes 06, 18)
- Desktop pywebview ChatGPT-like UI, then LibreChat / Open WebUI / Lobe Chat, then a static Aegis HTML panel, then a 10-step React app titled Aegis that talks to a clone OpenAI API (`/v1/chat/completions`) (notes 01, 14–22, 38–47)
- FastAPI `api.main` that constructs `AgentFactory()` again — a second factory (notes 15–19)
- Playwright global browser, click-all, cookie save/load, record/replay of logins as “skills”, AI-generated login sequences, cron + natural-language scheduler of `login_to_dashboard` (notes 23–33, 42, 44)
- Domain packs: 5G/6G, vehicle ECU/RF (relay/replay, CAN inject), drones, **jammers/EW**, mesh, FPGA flash, ChromaDB knowledge base (notes 07–13)
- Aegis `install.sh` / Docker / LibreChat+Mongo (notes 16, 35)
- Assembly letter: copy `requirements.txt` → `core/` → `api/` → `ui/aegis-ui/` → `factory/` (note 48)

Note 36 agrees the ChatGPT/LibreChat faces are historical and the UI should be built from scratch — but then notes 38–47 still specify an Aegis-branded ChatGPT-like mission-control app against that clone API.

## 3. Owner locks (these win over the notes)

1. Product name Universal platform. Package `universal`. **Never name anything Aegis** in product or code.
2. English only in code, comments, UI copy, README, commits.
3. One `AgentRegistry` + one `AgentLifecycle`, constructed once on `Universal` and **injected**. Generator and Manager must not each own a pair.
4. First ship was: agent that answers + one real OpenAI-compatible provider + one working CLI channel + three templates + tests. That ship is done.
5. Do **not** register 40 fake providers or a fake “local” model. HF/MLX later as real plugins.
6. Plugin architecture is the spine (model + channel + plugins). Hot-swap exists.
7. Face/app is built **from zero**. No ChatGPT-branded UI. No LibreChat / Open WebUI / Lobe Chat as the product face.
8. If a note is consistent but integration would break wiring, **stop and report**. Prefer a smaller aligned cut.
9. Never implement jammer TX / spoofing / counter-drone jamming.
10. Do not implement click-all, credential/cookie replay, AI login skills, or scheduled login replay.
11. Do not add a second memory/store next to agent history without a deliberate design.

## 4. Engineering integration plan we drafted (not started)

We wrote `docs/integration_plan.md`. We have **not** implemented cuts 1–5. We are waiting on your alignment before we grow the surface.

| Cut | Intent |
|---|---|
| 1 | `create(..., channel="cli")` via a `ChannelCatalog`. Today the generator hardcodes `CLIChannel()`. Without this, a web face or Telegram splits `factory.start`. |
| 2 | Thin HTTP on **the same** `Universal` instance. Factory routes (`/agents`, `/ask`, `/templates`). Not an OpenAI `/v1` clone. Not `/browser/*`. Not `/scheduler/*`. |
| 3 | Face from zero: Vite + TypeScript + Tailwind is acceptable. Universal name. First pages: Chat, Agents, Settings. Talks only to cut 2. |
| 4 | One real extra channel (webhook **or** Telegram), chosen at `create`. |
| 5 | Streaming on the existing provider; still goes through `Agent.accept`. |

Optional later, one at a time: extra tools, Bun as a **tool** plugin, local RAG that does not replace history, owner-app a11y/perf (not login replay), real HF/MLX clients.

## 5. Things that do not match — we need you to resolve these

These are the conflicts. Please answer each. “Keep the note” or “keep the lock” is enough when that is the decision.

### A. Identity and face

1. **Name.** Notes brand Aegis Agent Factory (wordmark “A”, `com.aegis.agentfactory`, `aegis-settings`). Lock is Universal. Is Aegis retired forever, including in UI, PWA, Tauri, and docs?

2. **What “from zero” means.** Note 36 says custom UI, not LibreChat. Notes 38–47 still specify ChatGPT-like sidebar, conversation list, Codex chat, `/v1/chat/completions`. Is the face allowed to *feel* like ChatGPT/Codex if it is Universal-branded and talks to our factory? Or must the information architecture be different (factory-first, not chat-first)?

3. **First UI slice.** Engineering proposed Chat + Agents + Settings only. Your notes also require Browser, Plugins execute, Scheduler, Ctrl+K, PWA, Tauri. What is in the first ship of the face? What is explicitly later?

4. **Tokens.** Note 38: dark `#0B0E14`, cyan `#00E5FF`, Inter. May we use those colors/type on a Universal face with no Aegis mark?

5. **Shell.** Notes bounce between pywebview, LibreChat in Docker, static HTML, Vite SPA, PWA, Tauri, Electron. What is the first delivery: browser SPA, desktop webview, or both? Engineering recommends browser SPA after HTTP exists; desktop later.

6. **UI language.** Repo lock is English UI copy. Confirm.

### B. Factory and API

7. **Who is the composition root?** Notes 02/15 construct factory inside `api.main` and give Generator/Manager their own registry+lifecycle. We already have one injected pair. Confirm: all HTTP and UI go through the existing `Universal` root. No second factory.

8. **API shape.** Notes expose OpenAI-compatible `/v1/chat/completions` (and stream that bypasses the agent). We proposed factory REST: `POST /agents/{id}/ask` → `Agent.accept`. Which contract does the face speak? If you need `/v1` for a third-party UI, that contradicts “face from zero” and LibreChat rejection.

9. **Persistence.** Notes want a JSON file registry and skill-state files. We refused a second store. Agents die when the process dies. For a UI, the HTTP process *is* the process. Is that acceptable for v1, or do you need agents to survive restart? If yes, that is a **redesign** of registry/lifecycle — not a silent sqlite drop-in.

10. **Streaming.** Where does the token stream attach: provider inside `complete`/`accept`, or a side path that calls the LLM and skips the agent? We will only do the first.

11. **Generic plugin execute.** Notes 43: `POST /plugins/execute` with arbitrary `plugin_name` + `action` + JSON. Our plugins are hooks + tools on an agent, not a remote RPC bus. Should the UI list catalog ids and attach/detach on an agent, or do you need a second plugin runner?

### C. Models and channels

12. **40 / 25+ providers.** We have one client + a base URL. DeepSeek/Groq/Mistral work by pointing the same client at their OpenAI-compatible URL. Are you asking for (a) that, plus a settings field for base URL, or (b) 25 named buttons that do not have real clients? We will not ship (b).

13. **Local / HF / MLX.** Notes register a fake local model. When do you want a **real** HF or MLX plugin? Not in the first face cut unless you have a working runtime to target.

14. **Channels.** Notes 06/18 want Telegram, Discord, Slack, SMTP, webhook, and 25+ stubs. We will add **one** live channel at a time, chosen at `create`. Which is first after CLI: webhook (pairs with the web face) or Telegram? Confirm we do not register stubs.

15. **`create` must choose channel.** Today it cannot. Cut 1 is blocked on you agreeing this is the next engineering step before UI.

### D. Browser, scheduler, domains

16. **Browser automation.** Notes 23–33, 42, 44 are a large product: launch Playwright, screenshot poll, click every link, save cookies, record CSS+typed values, replay logins, AI-write login skills, cron/NL “run login_to_dashboard at 9am”. We will not build unauthorized-access-adjacent replay. Do you want **any** browser capability in the product? If yes, what is the legal, owner-controlled slice (e.g. a11y/perf against a URL the owner types, no credential store)?

17. **Scheduler.** Every scheduler note triggers browser skill replay. Is there a scheduler that is **not** login/replay (e.g. “ask this agent this prompt every morning”)? If no, we drop scheduler from the face.

18. **Domain packs (07–13).** 5G/SDR, vehicle relay/CAN, drones, jammers, mesh root commands, FPGA flash, ChromaDB. Which of these are product, which are research notes to ignore, which become a later scoped plugin with a legal brief? **Jammer TX is never implemented.** Please say so explicitly if you agree.

19. **Knowledge base (13).** ChromaDB next to agent `_history` is a second memory. If you want RAG, it must be a plugin that does not fork the registry. Confirm.

20. **Sandbox `/code/execute` (17).** Not implemented. Do you want a constrained exec plugin later, or drop it?

21. **`ew_specialist` template** appears in factory panel and API option lists. Drop?

### E. Packaging and process

22. **Install path.** Notes 35/48: `install.sh`, `Dockerfile.full`, `uvicorn api.main:app`, LibreChat compose. Ours: `python3 -m universal`. What does the designer consider “shipped” for a demo: CLI only, CLI+HTTP, or CLI+HTTP+SPA?

23. **GitHub deploy.** Stub today. Do you need real GitHub repo creation in the first three cuts? Engineering says no.

24. **Bun (03).** Package manager for the UI, or a tool the agent can invoke on an owner project path, or both, or later?

25. **Missing notes.** You announced 51, we have 48. Are 49–51 coming, or is the set closed?

26. **Who decides IA vs pixels vs factory?** Please state: you own visual + information architecture of the from-zero face; engineering owns factory wiring and will refuse cuts that fork registry/channel/provider; owner lock list above is not negotiable without the owner.

## 6. What we need back from you

A short **alignment plan**, not more Aegis file dumps. Ideal shape:

1. One-paragraph product definition of Universal (who uses it, what they do in the first session).
2. First face: page list, and what is forbidden on those pages.
3. API contract: factory REST vs OpenAI `/v1` (pick one).
4. Persistence: process-lifetime vs redesign.
5. First extra channel (or “CLI only until face works”).
6. Browser / scheduler / EW / 40-providers: keep, delay, or kill — per item.
7. Visual: tokens yes/no; ChatGPT-like chrome yes/no; name on the chrome.
8. Ordered milestones you want engineering to execute (we can map them to cuts 1–5 if they fit).

Until that comes back we will not scaffold `ui/aegis-ui`, will not add `api.main` as a second factory, and will not implement browser login replay.

Thank you. We can move as soon as the alignment plan is in.
