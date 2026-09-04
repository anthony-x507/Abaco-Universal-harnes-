import { Activity } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listEvents, type NervousEvent, type NervousHealth } from '../lib/api'
import { Button } from './ui/button'

export function EventsPanel() {
  const [events, setEvents] = useState<NervousEvent[]>([])
  const [health, setHealth] = useState<NervousHealth | null>(null)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const data = await listEvents()
      setEvents(data.events)
      setHealth(data.nervous)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load events.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div className="space-y-3 border-t border-border pt-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-accent" />
          <h3 className="font-medium">Wiring</h3>
        </div>
        <Button size="sm" variant="outline" onClick={() => void load()}>
          Refresh
        </Button>
      </div>
      <p className="text-xs text-muted">
        In-process event log. Not Redis. Not NATS. Notices, proofs, and improvements land here.
      </p>
      {health && (
        <p className="text-xs text-muted">
          Bus {health.bus} · circuit {health.circuit?.state || 'closed'} · events {health.events ?? events.length}
        </p>
      )}
      {error && <p className="text-red-200">{error}</p>}
      {events.length === 0 ? (
        <p className="text-muted">No events yet.</p>
      ) : (
        <ul className="space-y-1 text-xs">
          {events
            .slice()
            .reverse()
            .slice(0, 12)
            .map((row, index) => (
              <li key={`${row.at}-${row.kind}-${index}`}>
                <span className="text-accent">{row.kind}</span>{' '}
                <span className="text-muted">{row.at?.slice(11, 19)}</span>
                {row.message ? <div>{row.message}</div> : null}
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}
