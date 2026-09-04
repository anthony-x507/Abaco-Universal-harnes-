import { Compass } from 'lucide-react'
import { Button } from './ui/button'
import type { Situation } from '../lib/api'
import { cn } from '../lib/utils'

const PHASE_CLASS: Record<string, string> = {
  idle: 'text-muted',
  planning: 'text-amber-200',
  executing: 'text-accent',
  evaluating: 'text-violet-200',
  blocked: 'text-red-200',
  deviating: 'text-amber-300',
  completed: 'text-emerald-200',
  failed: 'text-red-300',
}

export function SituationPanel({
  situation,
  onRefresh,
  onReset,
  busy,
}: {
  situation: Situation | null
  onRefresh: () => void
  onReset: () => void
  busy?: boolean
}) {
  if (!situation) {
    return <p className="text-sm text-muted">No mission state yet. Ask the agent to set an objective.</p>
  }
  const total = situation.steps_completed.length + situation.steps_remaining.length
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Compass size={16} className="text-accent" />
          <span className="font-medium">{situation.agent}</span>
        </div>
        <span className={cn('text-xs uppercase tracking-wide', PHASE_CLASS[situation.phase] || 'text-muted')}>
          {situation.phase}
        </span>
      </div>
      <div>
        <p className="text-xs text-muted">Objective</p>
        <p>{situation.objective || 'None yet'}</p>
      </div>
      <div>
        <p className="text-xs text-muted">Current step</p>
        <p>{situation.current_step || '—'}</p>
      </div>
      <p className="text-xs text-muted">
        Progress {situation.steps_completed.length}/{total || 0}
        {situation.team ? ` · Team ${situation.team}` : ''}
        {situation.attempts ? ` · Attempts ${situation.attempts}/${situation.max_attempts}` : ''}
      </p>
      {situation.steps_blocked.length > 0 && (
        <p className="text-red-200">Blocked: {situation.steps_blocked.join(', ')}</p>
      )}
      {situation.obstacles[0]?.obstacle && (
        <p className="text-red-100">{situation.obstacles[situation.obstacles.length - 1]?.obstacle}</p>
      )}
      {situation.alternatives[0]?.path && (
        <p className="text-amber-100">Alternative: {situation.alternatives[situation.alternatives.length - 1]?.path}</p>
      )}
      {situation.last_checkpoint && (
        <p className="text-xs text-muted">Checkpoint {situation.last_checkpoint}</p>
      )}
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={onRefresh} disabled={busy}>
          Refresh
        </Button>
        <Button size="sm" variant="ghost" onClick={onReset} disabled={busy}>
          Reset mission
        </Button>
      </div>
    </div>
  )
}
