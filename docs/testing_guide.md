# Testing guide (quality gate)

Source: `notes/59.md`. Hito 3 (webhook) is already shipped. This file is the executable map: every T/W id has a test, and none of those tests call a live LLM.

## How to run

```bash
python3 -m pytest
cd web && bun run test
```

Automatic tests use `FakeProvider` / `EchoProvider` / `vi.mock` / patched `httpx.post`. A fresh `Universal` fixture is created per Python test (`tests/conftest.py`).

Do **not** cover: a second registry, SQLite, history persistence, `/v1/chat/completions` as a product API, browser automation, scheduler, 40 providers, Aegis. Identity sidecar tests use `tmp_path`.

## Strategy (no false greens)

| Rule | Why |
|---|---|
| No live LLM in CI | Non-deterministic; quota and model drift hide wiring bugs |
| Echo / FakeProvider | The reply is a function of the prompt, so we know what the agent received |
| One `Universal` per test | Agents from test A must not appear in test B |
| Mock outbound HTTP | Webhook outbound never hits a real URL |
| Mock `fetch` in the SPA | Chat/Settings do not need `universal serve` |

## Factory and isolation

| Id | What | Test |
|---|---|---|
| T01 | `general` / `coder` install the six native plugins (not `system_prompt` / `transcript` / `tools`) | `tests/test_quality_guide.py` |
| T02 | `researcher` installs natives plus `tools` / `utc_now` | same |
| T03 | Provider sees one system message = `template.system_prompt` | same |
| T04 | Two agents keep separate histories | same |
| T05 | `reset_history` clears only that agent | same |
| T09 | `PUT /v1/settings` changes the provider for **new** agents only | same |

## Concurrency and HTTP

| Id | What | Test |
|---|---|---|
| T06 | Second `/ask` while answering → 409 | `tests/test_quality_guide.py` (in-flight gate + HTTP) |
| T07 | Delete during ask removes the agent and clears the lock | same (HTTP) + `web/src/pages/AgentsPage.test.tsx` (modal) |
| T08 | Stream / provider failure keeps the user turn | HTTP error event + SPA Retry |
| T11 | `/ask` on a created agent auto-starts | `tests/test_quality_guide.py` |
| T12 | `DELETE` works when lifecycle is `error` | same |
| T13 | `GET /v1/channels` is a list including `cli` and `webhook` | same |

## Locks (checklist)

| Check | Test |
|---|---|
| No `aegis` in `universal/` or `web/src` | `tests/test_quality_guide.py` |
| No `/v1/chat/completions` route | same + existing server tests |
| `serve` rejects `0.0.0.0` | same |

## SPA (Vitest + mocked fetch)

| Id | What | Test |
|---|---|---|
| T10 | Demo mode: API key disabled + copy | `web/src/pages/SettingsPage.test.tsx` |
| T14 | Send → `POST /v1/agents/{id}/ask` `{stream:true}` | `web/src/pages/ChatPage.test.tsx` |
| T15 | SSE tokens assemble the assistant turn | same |
| T16 | 409 → toast “Agent is already answering” | same |
| T17 | Broken SSE keeps the user turn + Retry | same |
| W05 | `webhook` is an enabled create option | `web/src/pages/AgentsPage.test.tsx` |

## Webhook (Hito 3)

| Id | What | Test |
|---|---|---|
| W01 | Inbound `{text}` → JSON `answer` (empty outbound) | `tests/test_webhook.py` / `tests/test_quality_guide.py` |
| W02 | Outbound POST `{agent_id,text}` when URL is set | same (`httpx.post` patched) |
| W03 | Outbound failure: agent still answers; JSON has `outbound_error` | same |
| W04 | `GET /v1/channels` includes `webhook` | same |
| W05 | UI option enabled | SPA test above |

Outbound failure is swallowed for the caller’s `answer`. The optional `outbound_error` field is how the factory reports the callback miss without skipping `handle_text`.

## Integrator checklist

- [x] `python3 -m pytest` (T01–T13, W01–W04, locks)
- [x] `cd web && bun test` (T10, T14–T17, T07 modal, W05)
- [ ] Manual: `--demo` Settings copy (also covered by T10)
- [x] No `aegis` in product source
- [x] No `/v1/chat/completions`
- [x] Serve binds localhost only
- [x] Double Send / 409 toast (T16)
- [x] Delete-while-answering modal (T07 SPA)
- [x] Stream error keeps user + Retry (T17)
- [x] Hito 4: ZIP UI, plugin labels, `/run`, identity sidecar, usage meter (`tests/test_hito4.py`)
- [x] Hito 5: README + DEMO.md + `demo.sh` (`tests/test_hito5_docs.py`)
- [x] Native plugins on every agent (`tests/test_native_plugins.py`)
