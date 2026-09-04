import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  acceptImprovement,
  listImprovements,
  proposeImprovement,
  rejectImprovement,
  type Improvement,
} from '../lib/api'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Textarea } from './ui/textarea'

export function ImprovementPanel({ agentId }: { agentId?: string }) {
  const [rows, setRows] = useState<Improvement[]>([])
  const [task, setTask] = useState('')
  const [plan, setPlan] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    if (!agentId) {
      setRows([])
      return
    }
    try {
      setRows(await listImprovements(agentId))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load improvements.')
    }
  }

  useEffect(() => {
    void load()
  }, [agentId])

  if (!agentId) {
    return <p className="text-sm text-muted">Select an agent to propose a better plan.</p>
  }

  return (
    <div className="space-y-3 border-t border-border pt-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <h3 className="font-medium">Visible improvement</h3>
        </div>
        <Button size="sm" variant="outline" onClick={() => void load()} disabled={busy}>
          Refresh
        </Button>
      </div>
      <p className="text-xs text-muted">
        The agent may propose a better plan. You accept or reject it. Nothing switches by itself.
      </p>
      {error && <p className="text-red-200">{error}</p>}
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault()
          setBusy(true)
          void proposeImprovement(agentId, { task, proposed_plan: plan })
            .then(() => {
              setTask('')
              setPlan('')
              return load()
            })
            .catch((err) => setError(err instanceof Error ? err.message : 'Propose failed.'))
            .finally(() => setBusy(false))
        }}
      >
        <Input
          value={task}
          onChange={(event) => setTask(event.target.value)}
          placeholder="Task"
          aria-label="Improvement task"
          disabled={busy}
        />
        <Textarea
          value={plan}
          onChange={(event) => setPlan(event.target.value)}
          placeholder="Proposed plan"
          aria-label="Proposed plan"
          disabled={busy}
        />
        <Button size="sm" type="submit" disabled={busy || !task.trim() || !plan.trim()}>
          Propose improvement
        </Button>
      </form>
      {rows.length === 0 ? (
        <p className="text-muted">No proposals yet.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li key={row.id} className="rounded-md border border-border bg-surface-2 p-2">
              <p className="text-xs uppercase tracking-wide text-muted">{row.status}</p>
              <p className="font-medium">{row.task}</p>
              <p>{row.proposed_plan}</p>
              {row.status === 'pending' && (
                <div className="mt-2 flex gap-2">
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() => {
                      setBusy(true)
                      void acceptImprovement(row.id)
                        .then(() => load())
                        .catch((err) => setError(err instanceof Error ? err.message : 'Accept failed.'))
                        .finally(() => setBusy(false))
                    }}
                  >
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => {
                      setBusy(true)
                      void rejectImprovement(row.id)
                        .then(() => load())
                        .catch((err) => setError(err instanceof Error ? err.message : 'Reject failed.'))
                        .finally(() => setBusy(false))
                    }}
                  >
                    Reject
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
