import { useEffect, useState } from 'react'
import { getDeepSeekReport, scanDeepSeek, type DeepSeekReport } from '../lib/api'
import { Button } from './ui/button'

export function StrategistReport() {
  const [report, setReport] = useState<DeepSeekReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      setReport(await getDeepSeekReport())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the DeepSeek report.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const scan = async () => {
    setBusy(true)
    try {
      setReport(await scanDeepSeek())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">DeepSeek Insights</h2>
        <Button size="sm" variant="outline" onClick={() => void scan()} disabled={busy}>
          {busy ? 'Scanning…' : 'Scan DeepSeek'}
        </Button>
      </div>
      <p className="text-muted">
        Public GitHub for <code>deepseek-ai/deepseek-harness</code>. Compared with Universal, not a second
        product. Mentions use DuckDuckGo. X/Twitter is not wired. There is no 7 AM background job — scan
        when you want a fresh report.
      </p>
      {error && <p className="text-red-200">{error}</p>}
      {!report && !error && <p className="text-muted">Loading last report…</p>}
      {report?.blocked && <p className="text-amber-100">Tracking is off ({report.reason}).</p>}
      {report && !report.blocked && !report.harness && !report.scanned && (
        <p className="text-muted">No scan yet. Scan DeepSeek reads the public GitHub API.</p>
      )}
      {report?.harness && (
        <div className="space-y-1">
          <p>
            <span className="text-muted">Repo</span> {report.harness.full_name}
          </p>
          <p>
            <span className="text-muted">Stars</span> {report.harness.stars ?? 0}
            {report.updated_at ? (
              <>
                {' '}
                <span className="text-muted">Updated</span> {report.updated_at}
              </>
            ) : null}
          </p>
          {report.harness.description ? <p>{report.harness.description}</p> : null}
        </div>
      )}
      {report?.new_releases?.length ? (
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">Recent releases</p>
          <ul className="mt-1 space-y-1">
            {report.new_releases.slice(0, 5).map((rel) => (
              <li key={`${rel.repo}-${rel.tag}`}>
                <span className="text-accent">{rel.tag}</span>
                {rel.published_at ? <span className="text-muted"> {rel.published_at.slice(0, 10)}</span> : null}
                {rel.body ? <div className="text-muted">{rel.body.slice(0, 200)}</div> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {report?.comparisons?.length ? (
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">Compared with Universal</p>
          <ul className="mt-1 space-y-2">
            {report.comparisons.map((row) => (
              <li key={row.feature}>
                <div className="font-medium">{row.feature}</div>
                <div>{row.status}</div>
                <div className="text-muted">{row.recommendation}</div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {report?.popularity ? (
        <p className="text-xs text-muted">
          DuckDuckGo mentions {report.popularity.mention_count ?? 0}. X/Twitter {report.popularity.twitter || 'not_available'}.
        </p>
      ) : null}
      {report?.scanned_at ? <p className="text-xs text-muted">Last scan {report.scanned_at}</p> : null}
    </div>
  )
}
