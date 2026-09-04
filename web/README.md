# Universal web face

Browser SPA for the Universal platform. Pages: Chat, Agents, Design, Settings.

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

After `bun run build`, `universal serve` also serves `web/dist` from the factory origin (`/`). `universal desktop` opens that same URL in a native window. On a Mac, `scripts/build_macos.sh` builds `Universal.app`.

Without `--demo`, set `UNIVERSAL_LLM_*` or paste a key in Settings or in the agent's Settings tab. Keys persist under user data and rebind existing agents. They are never written into a ZIP.

Create can choose `cli` or `webhook` once `GET /v1/channels` lists both. A webhook agent still answers in Chat via `/ask`. Other processes POST `{ "text": "…" }` to `/v1/agents/{id}/webhook`. Optional outbound URL is per agent, in memory.

Agents page: **Download ZIP** calls `POST /v1/agents/{id}/deploy` and saves the archive. Cards show readable plugin names (`Terminal: run_command`, `Tools: utc_now`, `Rule Enforcer: list_rules, check_rule`, …), not catalog ids. Every created agent includes the native tools. Settings → Governance lists the signed-core rules.

Chat: **Auto** next to Send is off by default (one-turn `/ask`). On, Send posts `/v1/agents/{id}/run` so the agent can loop tools. The message header shows `Tokens: … | Cost: $…` from the agent usage totals. Drop any document on the write bar. Audio is transcribed with local Whisper via `POST /v1/transcribe` (`pip install 'universal[media]'` if `/health` says `"whisper": false`). The write bar holds about 5,000 words. Workspace → **Mission** shows the saved objective and blockers. Blocked work also raises a dismissible banner from `/v1/notifications`.

Demo: `universal serve --demo`, create **Researcher**, toggle Auto, send `What time is it in UTC? Investigate and summarize.`
