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

Expected: 51. Received: 26.

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
- Note 14 (LibreChat / Open WebUI / Chatbot UI / Lobe Chat) is **historical only**. Owner lock: we will not use those faces. Do not save it as live `docs/ui_integration.md`, do not fork those UIs, do not add a FastAPI OpenAI-compat wrapper just to plug a ChatGPT clone in front of the factory. A later HTTP API for a from-zero face can be reviewed separately; it must talk to the existing factory, not a second agent stack.
- Notes 15–17 and 19 (FastAPI for clones, LibreChat compose/Mongo, fake-stream SSE + `/code/execute`, hardcoded 25+ option lists including `ew_specialist`) are **historical only**. Do not add `api/` as a second factory (`AgentFactory()` in `main.py` would fork registry/lifecycle). Do not ship LibreChat, Mongo for that UI, or a dummy `sk-dummy` OpenAI shim. A later HTTP layer for the from-zero face may reuse endpoint *ideas* only if it injects the existing `Universal` root. Do not expose placeholder provider/channel lists or EW templates.
- Note 07 (5G/6G) includes network scan / SDR / security-testing placeholders. Archive only. Do not implement offensive wireless, radio, or unauthorized-access tooling at integrate time.
- Note 08 (vehicle / RF) describes relay/replay attacks, CAN inject, ECU flash, key-fob decode. Archive only. Do not implement attack or unauthorized-access tooling. Legal OBD diagnostics on a vehicle the owner controls can be considered later as a separate, scoped plugin.
- Note 09 (drones) includes live MAVLink control, RF detection, and later jammers/EW. Archive only. Do not implement jamming, spoofing, or unauthorized drone control. Simulation / mission-file planning can be reviewed later as a scoped plugin.
- Note 10 (EW/jammers) includes working `hackrf_transfer` jamming and counter-drone TX. **Never integrate into `universal/`.** Defensive recommendations-only text may be discussed later; transmit/jam/spoof code will not be built.
- Note 11 (mesh) is mostly placeholders plus host `ip`/`iw`/`batctl`/`tshark` commands. Archive only. A later scoped plugin may document owner-controlled mesh setup; do not auto-run root wireless changes.
- Note 12 (embedded/FPGA) compiles and flashes via `arduino-cli` / `iceprog`. Archive only. A later scoped plugin may compile firmware the owner writes; do not auto-flash USB devices or run privileged Docker for hardware.
- Note 13 (knowledge base) is a ChromaDB ingest/search scaffold plus quiz placeholders. Archive only. Do not add a second memory/store next to the existing agent memory. A later scoped RAG plugin can be reviewed if it stays local and does not fork the registry.
