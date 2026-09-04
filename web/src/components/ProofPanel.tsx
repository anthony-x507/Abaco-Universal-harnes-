import { ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  challengeProof,
  draftAgentProof,
  getAgentProof,
  recordProofOracle,
  sealProof,
  type ProofSummary,
} from '../lib/api'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Textarea } from './ui/textarea'

function latestOracle(proof: ProofSummary, requirementId: string) {
  return [...proof.oracles].reverse().find((row) => row.requirement_id === requirementId)
}

export function ProofPanel({ agentId }: { agentId?: string }) {
  const [proof, setProof] = useState<ProofSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [objective, setObjective] = useState('')
  const [requirementsText, setRequirementsText] = useState('')
  const [evidence, setEvidence] = useState<Record<string, string>>({})
  const [mutation, setMutation] = useState<Record<string, string>>({})

  const load = async () => {
    if (!agentId) {
      setProof(null)
      return
    }
    setLoading(true)
    try {
      setProof(await getAgentProof(agentId))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the proof bundle.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [agentId])

  const run = async (work: () => Promise<ProofSummary>) => {
    setBusy(true)
    try {
      setProof(await work())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Proof action failed.')
    } finally {
      setBusy(false)
    }
  }

  if (!agentId) {
    return <p className="text-sm text-muted">Select an agent to draft or seal a proof.</p>
  }

  return (
    <div className="space-y-3 border-t border-border pt-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-accent" />
          <h3 className="font-medium">Sentinel Proof</h3>
        </div>
        <Button size="sm" variant="outline" onClick={() => void load()} disabled={busy || loading}>
          Refresh
        </Button>
      </div>
      <p className="text-xs text-muted">
        HMAC evidence on the signed factory. Not quantum. A seal needs a passing oracle on every
        requirement and at least one challenge that still holds.
      </p>
      {error && <p className="text-red-200">{error}</p>}
      {loading && !proof && <p className="text-muted">Loading proof bundle…</p>}
      {!loading && !proof && (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault()
            const requirements = requirementsText
              .split('\n')
              .map((row) => row.trim())
              .filter(Boolean)
            void run(() => draftAgentProof(agentId, { objective, requirements }))
          }}
        >
          <p className="text-muted">No proof bundle yet. Write atomic requirements for this mission.</p>
          <Input
            value={objective}
            onChange={(event) => setObjective(event.target.value)}
            placeholder="Objective"
            aria-label="Proof objective"
            disabled={busy}
          />
          <Textarea
            value={requirementsText}
            onChange={(event) => setRequirementsText(event.target.value)}
            placeholder="One requirement per line"
            aria-label="Proof requirements"
            disabled={busy}
          />
          <Button size="sm" type="submit" disabled={busy || !objective.trim() || !requirementsText.trim()}>
            Draft contract
          </Button>
        </form>
      )}
      {proof && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide">
            <span className={proof.verified ? 'text-emerald-200' : 'text-amber-200'}>{proof.status}</span>
            {proof.verified && <span className="text-emerald-200">HMAC verified</span>}
            <span className="text-muted">{proof.engine || 'sentinel-proof-v1'}</span>
            {proof.quantum ? <span className="text-red-200">quantum claim</span> : <span className="text-muted">not quantum</span>}
          </div>
          <div>
            <p className="text-xs text-muted">Claim</p>
            <p>{proof.objective}</p>
          </div>
          <ul className="space-y-3">
            {proof.requirements.map((req) => {
              const oracle = latestOracle(proof, req.id)
              const sealed = proof.status === 'sealed'
              return (
                <li key={req.id} className="rounded-md border border-border bg-surface-2 p-2">
                  <p className="font-medium">{req.text}</p>
                  <p className="text-xs text-muted">{req.id}</p>
                  {oracle ? (
                    <p className={oracle.passed ? 'text-emerald-100' : 'text-red-200'}>
                      Oracle {oracle.passed ? 'passed' : 'failed'}: {oracle.evidence}
                    </p>
                  ) : (
                    <p className="text-muted">No independent oracle yet.</p>
                  )}
                  {!sealed && (
                    <div className="mt-2 space-y-2">
                      <Input
                        value={evidence[req.id] || ''}
                        onChange={(event) => setEvidence((prev) => ({ ...prev, [req.id]: event.target.value }))}
                        placeholder="Oracle evidence"
                        aria-label={`Oracle evidence for ${req.id}`}
                        disabled={busy}
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy || !(evidence[req.id] || '').trim()}
                          onClick={() =>
                            void run(() =>
                              recordProofOracle(proof.id, {
                                requirement_id: req.id,
                                passed: true,
                                evidence: evidence[req.id],
                              }),
                            )
                          }
                        >
                          Pass oracle
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy || !(evidence[req.id] || '').trim()}
                          onClick={() =>
                            void run(() =>
                              recordProofOracle(proof.id, {
                                requirement_id: req.id,
                                passed: false,
                                evidence: evidence[req.id],
                              }),
                            )
                          }
                        >
                          Fail oracle
                        </Button>
                      </div>
                      <Input
                        value={mutation[req.id] || ''}
                        onChange={(event) => setMutation((prev) => ({ ...prev, [req.id]: event.target.value }))}
                        placeholder="Adversary mutation"
                        aria-label={`Challenge mutation for ${req.id}`}
                        disabled={busy}
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy || !(mutation[req.id] || '').trim()}
                          onClick={() =>
                            void run(() =>
                              challengeProof(proof.id, {
                                requirement_id: req.id,
                                mutation: mutation[req.id],
                                still_holds: true,
                              }),
                            )
                          }
                        >
                          Challenge holds
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy || !(mutation[req.id] || '').trim()}
                          onClick={() =>
                            void run(() =>
                              challengeProof(proof.id, {
                                requirement_id: req.id,
                                mutation: mutation[req.id],
                                still_holds: false,
                              }),
                            )
                          }
                        >
                          Challenge breaks
                        </Button>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
          {proof.challenges.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Challenges</p>
              <ul className="mt-1 space-y-1">
                {proof.challenges.map((row, index) => (
                  <li key={`${row.requirement_id}-${index}`} className={row.still_holds ? 'text-emerald-100' : 'text-red-200'}>
                    {row.still_holds ? 'Holds' : 'Broke'} · {row.mutation}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {proof.status !== 'sealed' && (
            <Button size="sm" disabled={busy} onClick={() => void run(() => sealProof(proof.id))}>
              Seal proof
            </Button>
          )}
          {proof.signature && (
            <p className="break-all text-xs text-muted">
              HMAC {proof.signature}
              {proof.payload_hash ? ` · hash ${proof.payload_hash.slice(0, 16)}…` : ''}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
