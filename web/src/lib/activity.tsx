import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export type ActivityKind = 'tool' | 'agent' | 'team' | 'skill' | 'design'

export type ActivityEvent = {
  id: string
  at: number
  text: string
  kind: ActivityKind
}

type ActivityValue = {
  events: ActivityEvent[]
  pushActivity: (text: string, kind?: ActivityKind) => void
  clearActivity: () => void
}

const ActivityContext = createContext<ActivityValue | null>(null)
const MAX_EVENTS = 24

export function ActivityProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<ActivityEvent[]>([])

  const pushActivity = useCallback((text: string, kind: ActivityKind = 'agent') => {
    setEvents((current) => {
      const next: ActivityEvent = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        at: Date.now(),
        text,
        kind,
      }
      return [next, ...current].slice(0, MAX_EVENTS)
    })
  }, [])

  const clearActivity = useCallback(() => setEvents([]), [])

  const value = useMemo(
    () => ({ events, pushActivity, clearActivity }),
    [events, pushActivity, clearActivity],
  )

  return <ActivityContext.Provider value={value}>{children}</ActivityContext.Provider>
}

export function useActivity() {
  const value = useContext(ActivityContext)
  if (!value) {
    throw new Error('useActivity must be used inside ActivityProvider')
  }
  return value
}
