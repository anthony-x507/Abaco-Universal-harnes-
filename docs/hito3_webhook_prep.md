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

## External URL design (docs only — no webhook code yet)

Serve stays localhost-only. An external system talks to Universal on the same machine (or via the owner’s own tunnel). Universal never binds `0.0.0.0` in this cut.

### Inbound (world → agent)

```
POST http://127.0.0.1:43124/v1/agents/{agent_id}/webhook
Content-Type: application/json

{ "text": "hello from the other system" }
```

Optional fields later, not required for v1: `sender_id`, `metadata`.

The route is legal only when:

- `{agent_id}` exists in the one registry,
- that agent’s channel name is `webhook`,
- the agent has been started (same auto-start rule as `/ask` is acceptable),
- the text is handed to `channel.handle_text` → bound `accept` / `complete`. Not `complete` from the route.

Reply to the caller (v1 proposal):

```
{ "answer": "…", "id": "{agent_id}" }
```

Same history append as `/ask`. No SSE on this inbound in v1 unless the designer asks.

### Outbound (agent → world)

Per-agent callback, process memory only (create body or a later `PUT` on that agent). Not written to `.env` from the UI.

```
POST {agent.outbound_url}
Content-Type: application/json

{ "agent_id": "…", "text": "the reply" }
```

If `outbound_url` is empty, `WebhookChannel.send` is a no-op (inbound still works; the HTTP response carries `answer`). That matches “configure an external endpoint when you have one.”

Create sketch (not implemented):

```
POST /v1/agents
{ "template": "general", "channel": "webhook", "outbound_url": "https://example.com/hooks/universal" }
```

`outbound_url` is ignored unless `channel` is `webhook`.

### UI after catalog lists webhook

- Create + Settings: `webhook` is a normal option, not `(later)`.
- Chat can still talk to a webhook agent through `/ask` (factory control plane). The webhook route is the *channel* inbound for other systems.

## Activation phrase

Implement only after: **sí, Hito 3** (designer or owner). Until then, this document is the prep. Note 54: more ground-prep (this section) is allowed; webhook source files are not.
