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
```

Open `http://127.0.0.1:43123`. Tab title: **Universal – Agents**.

Without `--demo`, set `UNIVERSAL_LLM_*` or paste a key in Settings. Settings update the running process only; they are not written to disk.
