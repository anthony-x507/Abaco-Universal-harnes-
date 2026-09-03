import { Monitor, PlugZap, Puzzle, X } from 'lucide-react'
import { useState } from 'react'
import { Button } from './ui/button'
import { cn } from '../lib/utils'

type WorkspaceTab = 'screen' | 'extension'

export function WorkspacePane({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<WorkspaceTab>('screen')

  return (
    <aside className="flex h-full min-h-0 w-[20rem] shrink-0 flex-col border-l border-border bg-surface">
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
      </div>

      {tab === 'screen' ? (
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
          <Button size="sm" variant="outline" disabled title="coming soon">
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
          <Button size="sm" variant="outline" disabled title="coming soon">
            Install extension (coming soon)
          </Button>
        </div>
      )}
    </aside>
  )
}
