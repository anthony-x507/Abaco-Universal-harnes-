# Gold-close wiring map

This is the lock-safe map of the harness. It is **not** Redis, NATS, `mother.yaml`, or `@sentinel-proof/cli`.

```
User
  └─ SPA (Chat / Agents / Design / Settings)  :43123
       └─ Factory REST                         :43124
            ├─ Universal (one registry, one lifecycle, injected factory)
            ├─ Mission   situation.py + NavigatorPlugin
            ├─ Teams     teams.py of existing agents
            ├─ Proof     proof.py HMAC (quantum: false)
            ├─ Audit     python3 -m universal audit
            ├─ Improve   improvement.py (accept / reject)
            ├─ Strategist DeepSeek on demand
            └─ Nervous   events.jsonl + provider circuit
```

## What is wired

| Piece | Where it lives | How it connects |
|---|---|---|
| Core | `universal/core/platform.py` | Only place that constructs `AgentRegistry` / `AgentLifecycle` |
| Native plugins | `universal/plugins/` | Installed on every agent. Provider and channel are **not** plugins |
| Wallet / Tor | Python core + permission gate | Node may *propose*; it does not encrypt or run torsocks |
| Mission | `situation/{id}.json` | `MissionPhase`, not lifecycle `AgentState` |
| Notices | `notifications.json` | Chat banners; also written to the event log |
| Improvements | `proposals/{id}.json` | Mission → Visible improvement |
| Proof | `proofs/{id}.json` | HMAC seal. Roles are stages, not templates |
| Audit | `audit/` + `universal audit` | Offline oracles, sealed verdict |
| Events | `events.jsonl` | `GET /v1/events`. In-process. No Redis |
| Circuit | `universal/nervous.py` | Opens after 3 provider failures |
| LLM dialect | `universal/providers/factory.py` | One HTTP client; adapter picks auth/payload/parse |
| Health | `GET /health` | Includes `nervous` snapshot |
| Mac install | `Universal.dmg` → `/Applications` | `scripts/build_macos.sh`, `sign_macos.sh`, `create_dmg.sh` |

## What is not in this product

- `universal/core.py` rewrite, `shared/*.js`, Redis, NATS
- `mother.yaml` / fourth Sentinels template
- Node `navigator.js` / `orchestrator.js` / `improvement_evaluator.js`
- Nightly 3 AM job
- Hierarchical working / episodic / semantic store
- Quantum verification
- npm `sentinel-proof` CLI
- Notarization on Linux CI (Apple credentials, Mac only)

## Acceptance (this close)

- Event log receives notices, proofs, and improvements
- State of truth for missions stays `situation/*.json`
- Circuit breaker does not invent a second HTTP client
- Health reports `redis: false`
- Audit still seals **VERIFIED**
- UI Mission shows situation, proof, improvement, and wiring
