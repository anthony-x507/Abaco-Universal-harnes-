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

Expected: 51. Received: 6.

## Integration flags (do not apply until the set is complete)

- Notes still say Aegis / `factory/` / `aegis-agent/`. Product lock: Universal platform, package `universal/`.
- Note 02 gives Generator and Manager each their own `AgentRegistry` + `LifecycleManager`. Lock: construct those once and inject.
- Note 02 JSON file registry would be a second store next to the in-memory registry. Stop and report; do not add silently.
- Note 04 registers many providers including a fake-local style. Lock: one real OpenAI-compatible client first; no 40 fake providers.
- Note 06 adds five live channels. Lock: one working channel in v1 (CLI already exists). More channels later as plugins, one at a time, with channel chosen at `create`.
- Face/app is greenfield from zero — do not implement pywebview ChatGPT clones from these notes.
