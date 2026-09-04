import { useEffect, useState } from 'react'
import { getAudit, runAudit, type AuditSummary } from '../lib/api'
import { Button } from './ui/button'

export function AuditReport() {
  const [report, setReport] = useState<AuditSummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      setReport(await getAudit())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the audit.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const run = async () => {
    setBusy(true)
    try {
      setReport(await runAudit())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audit failed to start.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Harness audit</h2>
        <Button size="sm" variant="outline" onClick={() => void run()} disabled={busy}>
          {busy ? 'Auditing…' : 'Run audit'}
        </Button>
      </div>
      <p className="text-muted">
        Offline oracles plus HMAC seal (<code>sentinel-proof-v1</code>). Not quantum. Not{' '}
        <code>@sentinel-proof/cli</code>. Desired designer extras stay out of scope and do not fail
        VERIFIED.
      </p>
      {error && <p className="text-red-200">{error}</p>}
      {!report && !error && <p className="text-muted">No sealed audit yet. Run audit to produce one.</p>}
      {report && (
        <div className="space-y-1">
          <p>
            <span className="text-muted">Verdict</span>{' '}
            <span className={report.verdict === 'VERIFIED' ? 'text-emerald-200' : 'text-amber-200'}>
              {report.verdict || report.status}
            </span>
            {report.verified ? <span className="text-emerald-200"> · HMAC verified</span> : null}
            {report.quantum ? <span className="text-red-200"> · quantum claim</span> : <span className="text-muted"> · not quantum</span>}
          </p>
          {report.id ? (
            <p>
              <span className="text-muted">Proof</span> {report.id}
            </p>
          ) : null}
          {report.signature ? <p className="break-all text-xs text-muted">HMAC {report.signature}</p> : null}
          {report.sealed_at ? <p className="text-xs text-muted">Sealed {report.sealed_at}</p> : null}
        </div>
      )}
    </div>
  )
}
