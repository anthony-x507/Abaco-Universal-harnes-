import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

type AskSessionValue = {
  askingId: string | null
  toast: string
  showToast: (message: string) => void
  clearToast: () => void
  beginAsk: (agentId: string) => AbortController | null
  endAsk: (agentId: string) => void
  abortAsk: () => void
}

const AskSessionContext = createContext<AskSessionValue | null>(null)

export function AskSessionProvider({ children }: { children: ReactNode }) {
  const [askingId, setAskingId] = useState<string | null>(null)
  const [toast, setToast] = useState('')
  const controllerRef = useRef<AbortController | null>(null)
  const askingIdRef = useRef<string | null>(null)
  const toastTimer = useRef<number | null>(null)

  const showToast = useCallback((message: string) => {
    setToast(message)
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(''), 4000)
  }, [])

  const clearToast = useCallback(() => {
    setToast('')
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
  }, [])

  const beginAsk = useCallback(
    (agentId: string) => {
      if (askingIdRef.current) {
        showToast('Agent is already answering. Please wait.')
        return null
      }
      const controller = new AbortController()
      controllerRef.current = controller
      askingIdRef.current = agentId
      setAskingId(agentId)
      return controller
    },
    [showToast],
  )

  const endAsk = useCallback((agentId: string) => {
    if (askingIdRef.current !== agentId) return
    askingIdRef.current = null
    controllerRef.current = null
    setAskingId(null)
  }, [])

  const abortAsk = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    askingIdRef.current = null
    setAskingId(null)
  }, [])

  const value = useMemo(
    () => ({ askingId, toast, showToast, clearToast, beginAsk, endAsk, abortAsk }),
    [askingId, toast, showToast, clearToast, beginAsk, endAsk, abortAsk],
  )

  return (
    <AskSessionContext.Provider value={value}>
      {children}
      {toast && (
        <div
          role="status"
          className="fixed bottom-4 left-1/2 z-50 max-w-sm -translate-x-1/2 rounded-md border border-border bg-surface-2 px-4 py-2 text-sm text-ink shadow-lg"
        >
          {toast}
        </div>
      )}
    </AskSessionContext.Provider>
  )
}

export function useAskSession() {
  const value = useContext(AskSessionContext)
  if (!value) {
    throw new Error('useAskSession must be used inside AskSessionProvider')
  }
  return value
}
