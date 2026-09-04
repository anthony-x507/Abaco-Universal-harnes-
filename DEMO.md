# Universal demo walkthrough

About ten minutes. English UI. No API key. You will start the factory, create a researcher (memory + tools), try Auto, hit the webhook, watch the usage meter, download a ZIP, and restart to see the identity snapshot.

**Need it in one command?** From the repo root:

```bash
./demo.sh
```

That installs the package if needed, starts `universal serve --demo` on `127.0.0.1:43124` when nothing is listening, creates `demo-researcher` (CLI) and `demo-hook` (webhook), and prints **Demo ready**. Then come back here at step 3.

The browser face is optional. Terminal 2:

```bash
cd web && bun install && bun run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). Without Vite, every `curl` below still works against port **43124**.

---

## Step 1 — Start the demo server

```bash
python3 -m pip install -e .
python3 -m universal serve --demo --host 127.0.0.1 --port 43124
```

`--demo` injects an echo provider. v1 binds localhost only.

Check:

```bash
curl -sS http://127.0.0.1:43124/health
```

You should see `"status":"ok"`, `"product":"Universal platform"`, `"demo":true`.

---

## Step 2 — Create a researcher (memory + tools)

**In the SPA (Design or Agents):** Design → **Create an agent** → template **Researcher**, name `demo-researcher`. Channel and model stay in Settings. Or create on Agents with channel `cli`, then **Start**.

The card should show readable labels (`Terminal: run_command`, …, **Tools: utc_now**), not raw catalog ids. Every template ships the six native tools; researcher adds `utc_now` and turns memory on. Facts go to `memory.json` keyed by this name.

**Or curl:**

```bash
curl -sS http://127.0.0.1:43124/v1/agents \
  -H 'Content-Type: application/json' \
  -d '{"template":"researcher","name":"demo-researcher","channel":"cli"}'
```

Save the `id`. Start it (`POST /v1/agents/{id}/start`) before Chat, or let `/ask` and `/run` auto-start.

Webhook face of the same template (step 4):

```bash
curl -sS http://127.0.0.1:43124/v1/agents \
  -H 'Content-Type: application/json' \
  -d '{"template":"researcher","name":"demo-hook","channel":"webhook"}'
```

`./demo.sh` already created both names if you used it.

---

## Step 3 — Auto (tool loop)

Open Chat, pick `demo-researcher`. Confirm **Auto** next to Send is **off** (one-turn `/ask`).

1. Turn **Auto** on.
2. Send: `What time is it in UTC? Investigate and summarize.`

Echo asks for `utc_now` once. A short notice (`Executing tool: utc_now`) appears under the write bar and is **not** a chat turn. The reply comes back without a second prompt.

Same path from the terminal:

```bash
curl -sS http://127.0.0.1:43124/v1/agents/AGENT_ID/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What time is it in UTC? Investigate and summarize."}'
```

`answer` starts with `(demo)`. `usage.calls` is at least 2 when the tool ran. Leave Auto off to stay on `/ask`.

---

## Step 4 — Webhook

Use the `demo-hook` id (`channel` must be `webhook`):

```bash
curl -sS http://127.0.0.1:43124/v1/agents/AGENT_ID/webhook \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello from another process"}'
```

The JSON includes `answer`. Empty `outbound_url` means no callback POST. You can still talk to this agent in Chat via Send.

---

## Step 5 — Usage meter

In Chat the header shows `Tokens: … | Cost: $…`. Demo echo costs `$0.000`; token counts still move after Ask or Auto.

The same object is on every agent payload:

```bash
curl -sS http://127.0.0.1:43124/v1/agents/AGENT_ID | python3 -m json.tool
```

Look at `usage`: `prompt_tokens`, `completion_tokens`, `estimated_cost`, `last_model`, `calls`. Live models use the fixed table in `universal/core/usage.py` (for example gpt-4o-mini `$0.00015` / `$0.0006` per 1K).

---

## Step 6 — Download the ZIP

**Agents → Download ZIP**, or:

```bash
curl -sS -X POST http://127.0.0.1:43124/v1/agents/AGENT_ID/deploy -o demo-researcher.zip
python3 -c "import zipfile; print(zipfile.ZipFile('demo-researcher.zip').namelist())"
```

Expect: `manifest.json`, `config.json`, `system_prompt.txt`, `README.txt`, `usage.json`. No API key inside.

---

## Step 7 — Restart and see the snapshot

Serve writes identities to `.universal/registry.json` (no history, no secrets). Stop the server (`Ctrl+C`) and start it again with the same command as step 1.

```bash
curl -sS http://127.0.0.1:43124/v1/agents
```

`demo-researcher` and `demo-hook` are back. `state` is `stopped`. `history` is empty. Press **Start** in the SPA (or `POST .../start`). Memory facts, if any, reload by **name** from `memory.json`.

---

## What you just proved

| Step | Capability |
|---|---|
| 1 | Factory HTTP + `--demo` echo |
| 2 | Templates, plugins, memory flag |
| 3 | `run` / Auto tool loop |
| 4 | Webhook channel through `accept` |
| 5 | Token and cost meter |
| 6 | Secret-free ZIP |
| 7 | Identity snapshot, no auto-start |

Live key: drop `--demo`, set `UNIVERSAL_LLM_*` or paste a key in Settings (new agents only). Full reference: [README.md](README.md).
