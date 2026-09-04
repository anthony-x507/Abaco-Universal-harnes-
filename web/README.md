# Universal web face

Browser SPA for the Universal platform. Pages: Chat, Agents, Settings.

It talks to `python3 -m universal serve` through the Vite proxy (`/v1`, `/health` → `127.0.0.1:43124`).

```bash
# terminal 1
python3 -m universal serve --demo --port 43124

# terminal 2
cd web
bun install
bun run dev
# tests (mocked fetch, no live server)
bun run test
```

Owner walkthrough: [../DEMO.md](../DEMO.md). `./demo.sh` from the repo root starts the factory and sample agents.


Open `http://127.0.0.1:43123`. Tab title: **Universal – Agents**.

Without `--demo`, set `UNIVERSAL_LLM_*` or paste a key in Settings. Settings update the running process only; they are not written to disk.

Create can choose `cli` or `webhook` once `GET /v1/channels` lists both. A webhook agent still answers in Chat via `/ask`. Other processes POST `{ "text": "…" }` to `/v1/agents/{id}/webhook`. Optional outbound URL is per agent, in memory.

Agents page: **Download ZIP** calls `POST /v1/agents/{id}/deploy` and saves the archive. Cards show readable plugin names (`Terminal: run_command`, `Tools: utc_now`, …), not catalog ids. Every created agent includes the six native tools.

Chat: **Auto** next to Send is off by default (one-turn `/ask`). On, Send posts `/v1/agents/{id}/run` so the agent can loop tools. The message header shows `Tokens: … | Cost: $…` from the agent usage totals.

Demo: `universal serve --demo`, create **Researcher**, toggle Auto, send `What time is it in UTC? Investigate and summarize.`
