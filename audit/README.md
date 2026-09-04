# Harness audit

This folder is the integrator audit for **Universal platform** + **Sentinel Proof v1**.

The engine is `python3 -m universal audit`. It writes a sealed HMAC bundle and a markdown report. It is **not** `@sentinel-proof/cli`, not Docker, and not quantum.

## Run

```bash
chmod +x audit/scripts/run-audit.sh audit/scripts/verify-proof.sh
./audit/scripts/run-audit.sh
./audit/scripts/verify-proof.sh
```

Same thing without the shell wrappers:

```bash
python3 -m universal audit --output audit/output
python3 -m universal audit --verify audit/output/proof.sealed.json
```

`--doctor` checks `python3` / `git` / optional `node`. Docker is optional and unused. A missing npm CLI is expected.

## Verdicts

| Verdict | Meaning |
|---|---|
| `VERIFIED` | Every **required** oracle passed and every challenge still holds. HMAC seal is valid. |
| `PARTIAL` | A required non-critical oracle failed. Bundle is still sealed as evidence. |
| `FAILED` | A required critical oracle failed, or a challenge broke. |
| `BLOCKED` | The runner could not start (reserved). |

**Desired** rows (improvement evaluator, 3 AM scan, hierarchical memory, notarization) are recorded as out of scope. They do **not** fail `VERIFIED`.

## What the oracles actually check

- One `AgentRegistry` / `AgentLifecycle`, factory injected
- Provider and channel are not plugins
- Three templates; no `mother.yaml`
- Native Python plugins, wallet, Tor gate
- `MissionPhase` in `situation.py` — not lifecycle `AgentState`
- Teams of existing agents; delegate via `Agent.accept`
- DeepSeek scan on demand
- Sentinel Proof HMAC (`quantum: false`)
- Mission UI, notices, Models picker, history persistence, updater, entitlements

See `audit/contract.yaml` for the map and `universal/audit.py` for the executable checks.

## Output

```
audit/output/
  proof.sealed.json
  proof.json
  report.md
  attestations/
```

Keep the artifacts. The HMAC key lives under user data (`proof.key`), same as mission proofs. Tests isolate that directory with `UNIVERSAL_USER_DATA`.
