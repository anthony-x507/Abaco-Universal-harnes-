# Designer alignment plan (accepted)

Source: `notes/49.md`. This is the live decision record. Locks still win if a later note conflicts.

## Product

Universal is a local/server agent platform with one process root (registry + lifecycle + factory). An agent is an OpenAI-compatible provider + one channel + plugins. First session: create from `general` / `researcher` / `coder`, start, talk, stop, ZIP. In-memory only.

## First face

SPA in the browser: **Chat**, **Agents**, **Settings**. Universal chrome. Tokens `#0B0E14` / `#00E5FF` / Inter. Conversation + side list layout, not a ChatGPT clone and not Aegis.

Out of the first face: 40-provider picker, plugin attach/detach (read-only names only), scheduler, browser automation, theme switcher.

## API

Factory REST under `/v1/agents/...` (and `/v1/templates`, `/v1/settings`). Not `/v1/chat/completions`. One `Universal` instance per server process.

Note: `universal.server` did not exist at alignment time. It is built as Hito 0.

## Persistence

Process lifetime. No SQLite/JSON registry in v1.

## Channels

`cli` now. Webhook after the SPA works. No Telegram/Discord stubs.

## Explicitly discarded or delayed

| Item | Decision |
|---|---|
| Browser / click-all / login replay | discarded |
| Scheduler | delayed (phase 3+, not login replay) |
| `ew_specialist` | discarded |
| 40 fake providers / HF / MLX stubs | delayed until real clients |
| Extra plugins (search, scraper, …) | delayed |
| Sandbox exec | discarded |
| GitHub deploy | delayed (ZIP only) |
| Bun as an agent tool | no; Bun may build the SPA |
| Original notes 49–51 | set closed |

## Engineering milestones

0. HTTP factory server on the existing root (`python3 -m universal serve`).
1. SPA: Chat, Agents, Settings. Full replies, no streaming.
2. Streaming (later).
3. Webhook channel (later).
4. Plugin list + ZIP from the UI (later).
5. Usage guide + demo (later).

Engineering notes that do not change the plan:

- There is no `pause` lifecycle state. Agents page uses start / stop / delete.
- Create takes a single `channel` id (`cli`), not `communication: [webhook]`.
- Settings may update in-memory `UNIVERSAL_LLM_*` on the running server; the API key is never written to the repo.
- `--demo` on `serve` injects an echo provider so the SPA can be exercised without a live key. It is not a registered “local” model.
