# Sí / parar — Universal

A checkpoint process. Three agents reviewed the tree against the designer plan and the locks. This is the gate, not a license to implement Hito 2–5.

## Current verdict

| Slice | Verdict | Why |
|---|---|---|
| Hito 0 HTTP factory server | **Sí — shipped** | `python3 -m universal serve`. One `Universal` root. Factory REST only. |
| Hito 1 SPA Chat / Agents / Settings | **Sí — shipped** | `web/` talks to `/v1/agents`. Universal chrome. Demo echo works. |
| Hito 2 Streaming | **Parar until owner says sí** | Needs provider + agent + channel changes. Wrong path forks the factory. |
| Hito 3 Webhook | **Parar until Hito 2 is decided** | Must be a catalog channel at `create`. Not an extra HTTP route. |
| Hito 4 Plugin attach + ZIP in UI | **Parar** | Deploy API exists; UI must not grow until 2/3 are chosen. |
| Hito 5 Usage guide / owner demo | **Sí — light, anytime** | README + `web/README.md` already cover run. A short owner walkthrough can wait. |

**Default: stop after Hito 0–1.** Do not start streaming or webhook without an explicit **sí**.

## How a checkpoint works

1. Name the next slice in one sentence.
2. Run the **stop questions** below. Any **yes** → **parar** and report. Do not push through.
3. If all answers are **no**, the owner/designer says **sí**, implement only that slice.
4. `python3 -m pytest` must stay green. SPA still talks only to factory REST.
5. If the change would construct a second registry, lifecycle, factory, or chat API → **parar**.

## Stop questions (any yes = parar)

1. Does this construct a second `AgentRegistry` or `AgentLifecycle`?
2. Do Generator and Manager stop sharing the injected pair?
3. Does inbound skip `Agent.accept` after `factory.start`?
4. Does it add `/v1/chat/completions` or call the LLM from the HTTP route?
5. Does it add a live channel that is not in `ChannelCatalog` and not chosen at `create`?
6. Does it persist agents in JSON/sqlite so CLI one-shots look cross-process?
7. Does it brand Aegis, LibreChat, or a ChatGPT clone?
8. Does it register placeholder providers/channels?
9. Does it touch browser login-replay, click-all, scheduler-of-replay, or jammer TX?

## Safe next slices (only after sí)

### If sí on Hito 2 (streaming)

Do this path only:

1. `OpenAICompatProvider.stream` on the same client (plus `EchoProvider` for `--demo`).
2. Streaming inside the agent so plugins and the tool loop still run.
3. Channel can emit partial outbound (`send`).
4. `POST /v1/agents/{id}/ask` with SSE, still via `accept`.
5. Chat consumes SSE; keep the full-reply `ask` as fallback.

**Parar if** the route streams from the provider and skips the agent/channel.

### If sí on Hito 3 (webhook)

1. `WebhookChannel(BaseCommunication)`.
2. `catalog.register("webhook", ...)`.
3. `create(..., channel="webhook")`.
4. Enable the UI option from `/v1/channels`, not a hardcoded list.

**Parar if** `server.py` grows `POST /hooks/...` that is not that channel.

## Known gaps that are not stop reasons

- Designer note 49 mentioned **pause**. Accepted plan: no pause. Agents page says so. Start/stop only.
- Chat streaming indicator: deferred with Hito 2. Today: “Waiting for the agent…”.
- Browser check: Agents + Chat demo echo worked (`preview-bot` running; `(demo) hello Universal`). Settings was not screenshot-verified.
- Chat: switching agents can flash the previous history; a failed send leaves the optimistic user bubble.
- Settings load error can show a blank form. Fix when we next touch the SPA, not as a new product slice.

## Who says sí

| Role | Can say sí on | Cannot override |
|---|---|---|
| Owner | Start Hito 2, 3, or stop the project | Locks above |
| Designer | Visual / IA of the face | Factory wiring, Aegis, clone API |
| Engineering | Hito 0–1 maintenance, test fixes | Starting 2–5 without owner sí |

## Run (unchanged)

```bash
python3 -m pytest
python3 -m universal serve --demo --port 43124
cd web && bun run dev   # http://127.0.0.1:43123
```
