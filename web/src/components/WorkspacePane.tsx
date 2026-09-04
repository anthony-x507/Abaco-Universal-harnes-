import { Compass, Monitor, PlugZap, Puzzle, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getSituation, resetSituation, type Situation } from '../lib/api'
import { useAskSession } from '../lib/ask-session'
import { Button } from './ui/button'
import { ProofPanel } from './ProofPanel'
import { SituationPanel } from './SituationPanel'
import { cn } from '../lib/utils'

type WorkspaceTab = 'screen' | 'extension' | 'mission'

export function WorkspacePane({
  onClose,
  width,
  agentId,
}: {
  onClose: () => void
  width: number
  agentId?: string
}) {
  const [tab, setTab] = useState<WorkspaceTab>('screen')
  const [situation, setSituation] = useState<Situation | null>(null)
  const [busy, setBusy] = useState(false)
  const { showToast } = useAskSession()

  const loadSituation = async () => {
    if (!agentId) {
      setSituation(null)
      return
    }
    try {
      setSituation(await getSituation(agentId))
    } catch {
      setSituation(null)
    }
  }

  useEffect(() => {
    void loadSituation()
  }, [agentId])

  return (
    <aside
      className="flex h-full min-h-0 shrink-0 flex-col border-l border-border bg-surface"
      style={{ width }}
    >
      <header className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="text-xs font-medium uppercase tracking-wide text-muted">Workspace</div>
        <button type="button" className="text-muted hover:text-ink" onClick={onClose} aria-label="Close workspace">
          <X size={14} />
        </button>
      </header>

      <div className="flex border-b border-border">
        <button
          type="button"
          onClick={() => setTab('screen')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 px-2 py-2 text-xs',
            tab === 'screen' ? 'bg-surface-2 text-accent' : 'text-muted hover:text-ink',
          )}
        >
          <Monitor size={14} />
          Screen
        </button>
        <button
          type="button"
          onClick={() => setTab('extension')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 px-2 py-2 text-xs',
            tab === 'extension' ? 'bg-surface-2 text-accent' : 'text-muted hover:text-ink',
          )}
        >
          <Puzzle size={14} />
          Extension
        </button>
        <button
          type="button"
          onClick={() => {
            setTab('mission')
            void loadSituation()
          }}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 px-2 py-2 text-xs',
            tab === 'mission' ? 'bg-surface-2 text-accent' : 'text-muted hover:text-ink',
          )}
        >
          <Compass size={14} />
          Mission
        </button>
      </div>

      {tab === 'mission' ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <SituationPanel
            situation={situation}
            busy={busy}
            onRefresh={() => void loadSituation()}
            onReset={() => {
              if (!agentId) return
              setBusy(true)
              void resetSituation(agentId)
                .then((next) => setSituation(next))
                .catch((err) => showToast(err instanceof Error ? err.message : 'Could not reset the mission.'))
                .finally(() => setBusy(false))
            }}
          />
          <ProofPanel agentId={agentId} />
        </div>
      ) : tab === 'screen' ? (
        <div className="flex min-h-0 flex-1 flex-col gap-3 p-3">
          <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-black p-2">
            <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-wide text-muted">
              <span>Display</span>
              <span className="text-red-300">Offline</span>
            </div>
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 rounded-md bg-[#07090d] px-4 text-center">
              <Monitor className="text-accent" size={36} />
              <p className="text-sm font-medium">No screen connected</p>
              <p className="text-xs text-muted">
                This is the screen dock. A live share or remote display is not wired in this cut.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            title="coming soon"
            onClick={() => showToast('Screen connect is not available yet.')}
          >
            Connect screen (coming soon)
          </Button>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 p-3">
          <div className="rounded-lg border border-border bg-surface-2 p-3">
            <div className="flex items-center gap-2">
              <PlugZap size={16} className="text-accent" />
              <div className="text-sm font-medium">Universal companion</div>
            </div>
            <p className="mt-2 text-xs text-muted">
              Chrome extension status: not installed. The right column is reserved for the helper
              dock. Browser automation and login replay stay out.
            </p>
            <dl className="mt-3 space-y-1 text-xs">
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Dock</dt>
                <dd>Ready</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Extension</dt>
                <dd className="text-red-300">Not connected</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Page capture</dt>
                <dd>Off</dd>
              </div>
            </dl>
          </div>
          <Button
            size="sm"
            variant="outline"
            title="coming soon"
            onClick={() => showToast('The companion extension is not available yet.')}
          >
            Install extension (coming soon)
          </Button>
        </div>
      )}
    </aside>
  )
}
