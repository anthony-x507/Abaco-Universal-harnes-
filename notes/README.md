# Incoming notes

The owner is sending **51 notes**, one at a time. They include advice for the owner, advice for the integrating agent, install steps, and code.

## Rules for this folder

- Save each note **verbatim** as `NN.md` (01, 02, … 51) when it arrives.
- **Do not integrate** into `universal/` until the owner says the set is complete.
- Product locks still win: package `universal`, product name Universal platform, never Aegis as a product name, no ChatGPT-shaped UI (the face/app is built from zero), one injected `AgentRegistry` + `AgentLifecycle`.
- If a note would break factory/channel/provider wiring, stop and report in this file and in the root README — do not silently push through.
- Redact secrets (API keys, tokens) if a note contains them. Keep the rest of the text.

## Received

| File | Title | Status |
|---|---|---|
| `01.md` | Ábaco universal Harnes — Factory assembly guide v0.1 | saved, not integrated |
| `02.md` | Part 1: Factory Core Module (registry, lifecycle, generator, manager, packager, templates) | saved, not integrated |
| `03.md` | Bun integration (Folder 3, explanation only) | saved, not integrated |
| `04.md` | Part 4: LLM Provider Manager expansion (40+ pattern) | saved, not integrated |
| `05.md` | Folder numbering so far / next-step options | saved, not integrated |
| `06.md` | Part 5: Communication Channels (Telegram, Discord, Slack, SMTP, webhook) | saved, not integrated |
| `07.md` | Domain 4 / Part 10: 5G/6G Wireless plugin, sandbox, template | saved, not integrated |
| `08.md` | Domain 5 / Part 11: Vehicle ECU & RF Security | saved, not integrated |
| `09.md` | Domain 6 / Part 12: Robotics & Drone Technology | saved, not integrated |
| `10.md` | Domain 7 / Part 13: Jammers & Electronic Warfare | saved, **never integrate jammer TX** |
| `11.md` | Domain 8 / Part 14: Mesh Networking & IoT Protocols | saved, not integrated |
| `12.md` | Domain 9 / Part 15: Embedded Systems & FPGA Development | saved, not integrated |
| `13.md` | Domain 10 / Part 16: Knowledge Base & Training Platform | saved, not integrated |
| `14.md` | UI integration via LibreChat / Open WebUI (ChatGPT-style) | saved, **historical — do not use those faces** |
| `15.md` | Part 17: FastAPI backend for ChatGPT-style UIs | saved, **historical — do not implement as product face** |
| `16.md` | Part 18: LibreChat + Docker Compose stack | saved, **historical — do not use that face** |
| `17.md` | Part 19: Streaming, file upload, sandbox code exec API | saved, **historical — do not implement for those UIs** |
| `18.md` | Part 20: 25+ LLM providers and 25+ communication channels | saved, not integrated |
| `19.md` | Part 21: Wire 25+ options into Factory/API (LibreChat path) | saved, **historical — do not implement clone API** |
| `20.md` | Part 22: Static Aegis factory panel (HTML/CSS/JS) | saved, **historical — do not use as product face** |
| `21.md` | Streaming SSE + activity indicator on Aegis panel / LibreChat | saved, **historical — do not implement clone API** |
| `22.md` | Part 24: Codex-like chat window on Aegis factory panel | saved, **historical — do not use as product face** |
| `23.md` | Part 25: Playwright browser testing panel on Aegis UI | saved, **historical — do not implement clone API** |
| `24.md` | Part 26: Advanced browser tests (click-all, a11y, cookies) | saved, **historical — do not implement clone API** |
| `25.md` | Part 27: Multi-tab + visual regression on Aegis browser panel | saved, **historical — do not implement clone API** |
| `26.md` | Part 28: Browser record/replay as reusable login skills | saved, **historical — do not implement** |
| `27.md` | Part 29: AI-generated browser skills + scheduler | saved, **historical — do not implement** |
| `28.md` | Part 30: Scheduler calls browser replay on a timer | saved, **historical — do not implement** |
| `29.md` | Part 31: Shared BrowserScheduler + login_to_dashboard plugin | saved, **historical — do not implement** |
| `30.md` | Part 32: Cron/timezone scheduling of browser replay | saved, **historical — do not implement** |
| `31.md` | Part 33: Persist state across scheduled browser replays | saved, **historical — do not implement** |
| `32.md` | Part 34: Skill state viewer/editor + agent HTTP access | saved, **historical — do not implement** |
| `33.md` | Part 35: NL scheduling of login_to_dashboard replay | saved, **historical — do not implement** |
| `34.md` | Part 36: E2E tests against Aegis FastAPI clone stack | saved, **historical — do not implement** |
| `35.md` | Part 37: Aegis install.sh / Docker one-command setup | saved, **historical — do not implement** |
| `36.md` | Decision: custom UI vs ChatGPT/LibreChat (asked as docs/decision_ui.md) | saved, **historical — lock already: face from zero** |
| `37.md` | Part 38: Aegis README + clone-stack API reference | saved, **historical — do not replace Universal README** |
| `38.md` | UI Step 1: Aegis design language / tokens | saved, not implemented |
| `39.md` | UI Step 2: Vite/React scaffold `ui/aegis-ui` | saved, **do not scaffold yet** |
| `40.md` | UI Step 3: Codex-like chat page against clone `/v1` | saved, **do not implement** |
| `41.md` | UI Step 4: Agent dashboard against clone `/v1/agents` | saved, **do not implement** |
| `42.md` | UI Step 5: Browser page (launch, replay, click-all, AI login) | saved, **do not implement** |
| `43.md` | UI Step 6: Plugins page against clone `/plugins` | saved, **do not implement** |
| `44.md` | UI Step 7: Scheduler page (cron + NL login-skill replay) | saved, **do not implement** |
| `45.md` | UI Step 8: Settings page (`aegis-settings`, clone `/v1`) | saved, **do not implement** |
| `46.md` | UI Step 9: Global polish (sidebar, Ctrl+K, Aegis chrome) | saved, **do not implement** |
| `47.md` | UI Step 10: PWA + Tauri/Electron packaging of Aegis UI | saved, **do not implement** |
| `48.md` | Aegis assembly letter (copy folders + `api/` + `ui/aegis-ui`) | saved, **do not follow as build order** |
| `49.md` | Designer alignment plan (Universal face, factory REST, no Aegis) | accepted — Hito 0–1 shipped |
| `50.md` | Designer answers + sí on Hito 2 streaming | accepted — Hito 2 shipped |
| `51.md` | Designer visto final (approve + polish list) | accepted — polish shipped |
| `52.md` | Confirm polish; wait for sí on Hito 3 | waiting — prep only, see `docs/hito3_webhook_prep.md` |
| `53.md` | Signs the lock-safe Hito 3 cut; still wait for “sí, Hito 3” | waiting — do not register webhook |
| `54.md` | Confirm wait; docs/URL design OK, no webhook code | waiting |

Expected: 51. Received: 48 design notes + designer alignment (`49.md`). Original notes 49–51 never arrived; designer closed the set.

## Integration flags (do not apply until the set is complete)

- Notes still say Aegis / `factory/` / `aegis-agent/`. Product lock: Universal platform, package `universal/`.
- Note 02 gives Generator and Manager each their own `AgentRegistry` + `LifecycleManager`. Lock: construct those once and inject.
- Note 02 JSON file registry would be a second store next to the in-memory registry. Stop and report; do not add silently.
- Note 04 registers many providers including a fake-local style. Lock: one real OpenAI-compatible client first; no 40 fake providers.
- Note 18 repeats the 25+ provider/channel count with dummy registry entries (`nlpcloud`, `gooseai`, …) and send-only channel skeletons. Same lock: do not register placeholders. More real providers/channels later one at a time; the existing OpenAI-compat client already covers DeepSeek/Groq/Mistral-style bases when pointed at their URL.
- Note 06 adds five live channels. Lock: one working channel in v1 (CLI already exists). More channels later as plugins, one at a time, with channel chosen at `create`.
- Face/app is greenfield from zero — do not implement pywebview ChatGPT clones from these notes.
- Note 20 (static `ui/factory_panel` titled Aegis, includes `ew_specialist`) is **historical only**. Do not ship that HTML as the product face, do not wrap it in pywebview, do not serve it next to LibreChat. The from-zero face comes later and talks to the existing factory.
- Note 21 (legacy OpenAI `ChatCompletion` stream, `/v1/chat/stream` bypassing the agent, pulse indicator on that panel) is **historical only**. Do not add a provider-bypass chat path or polish the Aegis/LibreChat UI. Real streaming can be considered later on the existing OpenAI-compat client for the from-zero face.
- Note 22 (Codex-like chat pane on the Aegis HTML panel, `/conversations`, `ew_specialist`) is **historical only**. Do not ship that chat UI. The from-zero face is a later, separate surface.
- Note 23 (Playwright `/browser/*` plus screenshot-polling panel) is **historical only**. Do not add a global headless browser to the clone API. A later scoped browser-test plugin can be reviewed if it is owner-driven and not bolted onto that HTML face.
- Note 24 (auto-click all links, axe inject, cookie save/load on that panel) is **historical only**. Do not implement click-all or session replay on the clone stack. Owner-controlled a11y/perf on their own app can be reviewed later as a scoped plugin.
- Note 25 (multi-tab Playwright + pixel MSE compare) is **historical only**. Same lock: do not grow the clone browser API. Visual regression on an app the owner maintains can be reviewed later as a scoped plugin.
- Note 26 (record CSS selectors + input values, replay logins as “skills”) is **historical only**. Do not implement browser record/replay or store typed credentials. Owner-driven tests on their own app can be reviewed later without credential replay.
- Note 27 (LLM-generated login/click sequences, `browser_skills` plugin, in-memory scheduler) is **historical only**. Do not implement AI web-automation skills or scheduled replay. That path is unauthorized-access adjacent and forks the factory.
- Note 28 (scheduler HTTP-calls `/browser/record/replay` every 10s) is **historical only**. Do not wire timed replay of stored browser skills.
- Note 29 (`tools/browser_scheduler.py` plus `login_to_dashboard` daily replay) is **historical only**. Do not add a second scheduler instance or agent-initiated login automation.
- Note 30 (croniter/pytz cron replay of browser skills) is **historical only**. Do not add cron-driven login/replay.
- Note 31 (JSON state files passed into replay) is **historical only**. Do not persist browser-skill state or grow that replay path. Do not add a second store next to existing agent memory.
- Note 32 (GET/PUT skill state + Aegis editor) is **historical only**. Same lock: no second memory store and no clone-stack state UI.
- Note 33 (LLM parses “run login_to_dashboard every day at 9am”) is **historical only**. Do not implement NL scheduling of browser login/replay.
- Note 34 (pytest TestClient against `api.main`, scheduler, browser state) is **historical only**. Do not add tests that require the clone API. Existing `universal` tests stay the suite.
- Note 35 (`install.sh` / `Dockerfile.full` launching `uvicorn api.main:app` as Aegis) is **historical only**. Do not add an Aegis installer or compose stack. Universal already has its own run path (`python3 -m universal`).
- Note 36 (custom UI vs LibreChat) agrees with the owner lock: face from zero. Do **not** write live `docs/decision_ui.md` under the Aegis name, and do not start the “10-step React + Tailwind” face until the note set is complete. A later from-zero face talks to the existing `Universal` factory.
- Note 38 (design tokens, ChatGPT-familiar mission-control chrome, named Aegis) is archived only. Tokens may inform the later Universal face; do not scaffold that UI or brand it Aegis now.
- Note 39 (`ui/aegis-ui` Vite + ChatGPT-like sidebar, proxy to clone `:8000`) is **not implemented**. Do not create that package. A later from-zero face can use Vite/TS/Tailwind if chosen, but it must be Universal-branded and talk to the existing factory, not `api.main`.
- Note 40 (ChatGPT-like conversation list + SSE to `/v1/chat/completions`) is **not implemented**. Same lock: no clone-API chat UI. The CLI remains the v1 channel.
- Note 41 (Agents dashboard calling clone `/v1/agents`) is **not implemented**. A later factory UI can talk to the existing `Universal` session, not a second FastAPI factory.
- Note 42 (Browser page: Playwright launch, record/replay, click-all, AI “log in to example.com”) is **not implemented**. Same locks as notes 23–33.
- Note 43 (Plugins page listing/executing against clone `/plugins` and `/plugins/execute`) is **not implemented**. Universal already has a `PluginCatalog`; a later factory UI can surface that catalog through the existing `Universal` root, not a second FastAPI plugin runner.
- Note 44 (Scheduler page: cron/NL add of browser `skill_name` replay via `/scheduler/*`) is **not implemented**. Same locks as notes 28–33. Do not schedule login/replay skills.
- Note 45 (Settings page: `aegis-settings` localStorage, default model, `/v1` base, `/health` ping) is **not implemented**. Do not brand settings Aegis or point a client at the clone API. A later Universal face can keep local prefs under a Universal key and talk to the existing factory.
- Note 46 (resizable sidebar, Ctrl+K palette, “Aegis Agent Factory” top bar wiring Chat/Browser/Scheduler routes) is **not implemented**. Same lock: do not assemble the clone-stack face. Layout ideas (palette, resize) may inform a later Universal-branded UI.
- Note 47 (PWA manifest `Aegis Agent Factory`, `aegis-ui-v1` SW, Tauri `com.aegis.agentfactory` / Electron wrap) is **not implemented**. Do not package the clone face. A later Universal desktop shell can reuse Tauri/PWA *ideas* under Universal naming.
- Note 48 (Aegis assembly order: `requirements.txt` → `core/` → `api/` → `ui/aegis-ui/` → `factory/`) is **historical only**. Do not write live `docs/assembly_guide_es.md`. Do not copy that tree. Universal already has a composition root; the integration plan is `docs/integration_plan.md`.
- `51.md` is the designer visto final (approve + corrections). Immediate work is the polish list; Hito 3 waits until that list is done.
- `52.md` confirms the polish and waits for designer **sí** before Hito 3. Suggested path `universal/communication/channels.py` + a handler that POSTs straight into `Agent.accept` is **not** the lock-safe prep. See `docs/hito3_webhook_prep.md`.
- Designer final-review packet (not an incoming Aegis note): `docs/designer_final_review.md`. Status of Hito 0–2, plugin vs non-plugin assembly, wiring audit, and numbered questions for the designer’s visto final.
- Note 49 is the designer alignment plan. Accepted: factory REST (not OpenAI `/v1/chat/completions`), in-memory registry, Chat/Agents/Settings SPA, webhook later, browser/scheduler/EW/40-providers out. `universal.server` did **not** exist when they wrote Hito 0 — engineering builds it on the existing `Universal` root. No pause state (start/stop only). No Aegis chrome.
- Note 37 (Aegis README advertising EW, 25+ providers, browser replay, `ui/factory_panel`) is **historical only**. Do not overwrite the Universal README or add `docs/api_reference.md` for the clone stack.
- Note 14 (LibreChat / Open WebUI / Chatbot UI / Lobe Chat) is **historical only**. Owner lock: we will not use those faces. Do not save it as live `docs/ui_integration.md`, do not fork those UIs, do not add a FastAPI OpenAI-compat wrapper just to plug a ChatGPT clone in front of the factory. A later HTTP API for a from-zero face can be reviewed separately; it must talk to the existing factory, not a second agent stack.
- Notes 15–17 and 19 (FastAPI for clones, LibreChat compose/Mongo, fake-stream SSE + `/code/execute`, hardcoded 25+ option lists including `ew_specialist`) are **historical only**. Do not add `api/` as a second factory (`AgentFactory()` in `main.py` would fork registry/lifecycle). Do not ship LibreChat, Mongo for that UI, or a dummy `sk-dummy` OpenAI shim. A later HTTP layer for the from-zero face may reuse endpoint *ideas* only if it injects the existing `Universal` root. Do not expose placeholder provider/channel lists or EW templates.
- Note 07 (5G/6G) includes network scan / SDR / security-testing placeholders. Archive only. Do not implement offensive wireless, radio, or unauthorized-access tooling at integrate time.
- Note 08 (vehicle / RF) describes relay/replay attacks, CAN inject, ECU flash, key-fob decode. Archive only. Do not implement attack or unauthorized-access tooling. Legal OBD diagnostics on a vehicle the owner controls can be considered later as a separate, scoped plugin.
- Note 09 (drones) includes live MAVLink control, RF detection, and later jammers/EW. Archive only. Do not implement jamming, spoofing, or unauthorized drone control. Simulation / mission-file planning can be reviewed later as a scoped plugin.
- Note 10 (EW/jammers) includes working `hackrf_transfer` jamming and counter-drone TX. **Never integrate into `universal/`.** Defensive recommendations-only text may be discussed later; transmit/jam/spoof code will not be built.
- Note 11 (mesh) is mostly placeholders plus host `ip`/`iw`/`batctl`/`tshark` commands. Archive only. A later scoped plugin may document owner-controlled mesh setup; do not auto-run root wireless changes.
- Note 12 (embedded/FPGA) compiles and flashes via `arduino-cli` / `iceprog`. Archive only. A later scoped plugin may compile firmware the owner writes; do not auto-flash USB devices or run privileged Docker for hardware.
- Note 13 (knowledge base) is a ChromaDB ingest/search scaffold plus quiz placeholders. Archive only. Do not add a second memory/store next to the existing agent memory. A later scoped RAG plugin can be reviewed if it stays local and does not fork the registry.
