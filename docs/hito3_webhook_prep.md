# Hito 3 webhook — prepared, not activated

Status: **waiting for an explicit designer “sí, Hito 3”.** Note 51 approved the polish and said to ask again before webhook. Note 52 confirms the polish and repeats that wait. This file is the lock-safe prep so we do not implement the wrong spine.

Do **not** register `webhook` in `ChannelCatalog` until that sí. A registered empty channel would be a placeholder (stop question 8).

## What we will not do (note 52 sketch vs locks)

| Suggested | Why we stop |
|---|---|
| `universal/communication/channels.py` | Channels already live in `universal/channels/` (`base.py`, `cli.py`, `catalog.py`). A second tree is a second spine. |
| A free-standing `WebhookHandler` that `POST /webhook/{agent_id}` **enqueues to `Agent.accept`** | After `factory.start`, inbound must go through the **bound channel**. A server route that calls `accept` (or `complete`) and skips `channel.handle_text` is a bypass. `docs/go_no_go.md`: *Parar if `server.py` grows `POST /hooks/...` that is not that channel.* |
| Registering webhook before sí | Placeholder channel. |

Webhook is a **channel**, same class of citizen as `cli`. It is not a plugin. It is not a second factory HTTP API.

## What we will implement when sí arrives

1. `WebhookChannel(BaseCommunication)` in **`universal/channels/webhook.py`** (next to `cli.py`).
2. `ChannelCatalog.register("webhook", ...)`.
3. `create(..., channel="webhook")` — already the factory path; the catalog is what is missing.
4. Inbound: one factory route that **is** the channel, for example `POST /v1/agents/{id}/inbound` (or `/v1/channels/webhook/{id}`), which only runs if:
   - the agent exists,
   - its channel `name == "webhook"`,
   - the agent is started (`factory.start` / existing ask auto-start rule),
   - the body text is passed to `agent.accept` **via** `channel.handle_text` (same contract as CLI `deliver` / `handle_text`).
5. Outbound: `WebhookChannel.send` POSTs the reply to an external URL the owner configures (process memory, same as Settings — not a `.env` write from the UI). That is “how to point an external endpoint at Universal.”
6. SPA: Create/Settings already read `settings.channels` + `default_channel`. When `/v1/channels` lists `webhook`, the option is enabled. No hardcoded “un-disable.”
7. Docs: one README section — inbound URL, JSON body `{ "text": "..." }`, optional outbound callback URL, localhost-only still.

## Questions already answered (do not reopen)

- Provider and channel stay first-class, not plugins (note 51).
- No `/v1/chat/completions`.
- No second registry.
- Localhost, no login, until a later bind+auth decision.

## Signed cut (note 53)

The inbound factory route, when sí arrives, is `POST /v1/agents/{id}/webhook` (channel-owned, then `handle_text` → `accept`). Outbound URL is per-agent, in memory. UI enables webhook only after `GET /v1/channels` lists it.

## Activation phrase

Implement only after: **sí, Hito 3** (designer or owner). Until then, this document is the prep.
