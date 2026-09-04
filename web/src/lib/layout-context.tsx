import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { loadLayout, saveLayout, type LayoutState } from './layout'

type LayoutContextValue = {
  layout: LayoutState
  updateLayout: (patch: Partial<LayoutState>) => void
}

const LayoutContext = createContext<LayoutContextValue | null>(null)

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [layout, setLayout] = useState<LayoutState>(() => loadLayout())

  const value = useMemo<LayoutContextValue>(
    () => ({
      layout,
      updateLayout: (patch) => {
        setLayout((current) => {
          const next = { ...current, ...patch }
          saveLayout(next)
          return next
        })
      },
    }),
    [layout],
  )

  return <LayoutContext.Provider value={value}>{children}</LayoutContext.Provider>
}

export function useLayout() {
  const ctx = useContext(LayoutContext)
  const [fallback, setFallback] = useState<LayoutState>(() => loadLayout())
  if (ctx) return ctx
  return {
    layout: fallback,
    updateLayout: (patch: Partial<LayoutState>) => {
      setFallback((current) => {
        const next = { ...current, ...patch }
        saveLayout(next)
        return next
      })
    },
  }
}
