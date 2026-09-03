# Designer questions — round 2

Hito 0–1 are shipped. The first alignment plan closed the big forks. These are the leftovers implementation surfaced. Reply per item; “keep current” is a valid answer.

1. **Pause.** Your note listed create/start/stop/pause/delete. We shipped start/stop only (no paused lifecycle). Keep that, or do you want a real paused state later?

2. **Streaming in the first Chat.** You asked for a streaming indicator on Hito 1. Hito 1 shows “Waiting for the agent…” and then the full reply. Token streaming is Hito 2. Is that acceptable until you say sí on Hito 2?

3. **`--demo`.** `universal serve --demo` uses an echo provider so the SPA works without a live API key. It is not a registered “local” model. OK for reviews and owner demos?

4. **Bind / auth.** You said local or server. Today `serve` defaults to `127.0.0.1` and has no login. May we keep localhost-only until you specify bind address + auth? We will not expose Settings (API key) on `0.0.0.0` without that.

5. **Mark.** Chrome uses a “U” block, no logo file. Are you sending a Universal mark, or keep the letter?

6. **Primary face.** Is the SPA now the main product surface, or is CLI still first and the SPA a companion?

7. **One thread per agent.** Chat has no conversation list or titles — one history per agent, in memory. Confirm.

8. **Settings.** Save updates the running process only. Blank API key keeps the current secret. We will not write `.env` from the UI unless you insist (and even then, never commit it).

9. **Next sí.** Pick one: stay stopped after Hito 0–1 · Hito 2 streaming · small Chat/Settings polish (stale history on switch, failed-send bubble) · Hito 3 webhook.

Locks unchanged: no Aegis, no `/v1/chat/completions`, no second factory, no login replay.
