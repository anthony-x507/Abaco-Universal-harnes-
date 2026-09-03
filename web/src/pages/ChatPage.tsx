import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { ApiError, askAgentStream, getAgent, listAgents, type Agent, type HistoryTurn } from '../lib/api'
import { cn } from '../lib/utils'

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('agent') ?? ''
  const [agents, setAgents] = useState<Agent[]>([])
  const [history, setHistory] = useState<HistoryTurn[]>([])
  const [prompt, setPrompt] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const selected = useMemo(
    () => agents.find((agent) => agent.id === selectedId) ?? null,
    [agents, selectedId],
  )

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoadingList(true)
      try {
        const rows = await listAgents()
        if (cancelled) return
        setAgents(rows)
        setError('')
        const current = new URLSearchParams(window.location.search).get('agent')
        if (!current && rows.length > 0) {
          setSearchParams({ agent: rows[0].id }, { replace: true })
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load agents.')
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [setSearchParams])

  useEffect(() => {
    if (!selectedId) {
      setHistory([])
      return
    }
    let cancelled = false
    const load = async () => {
      try {
        const agent = await getAgent(selectedId)
        if (!cancelled) setHistory(agent.history ?? [])
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load conversation.')
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const send = async () => {
    const text = prompt.trim()
    if (!text || !selectedId) return
    setSending(true)
    setError('')
    setPrompt('')
    setHistory((current) => [
      ...current,
      { role: 'user', content: text },
      { role: 'assistant', content: '' },
    ])
    try {
      const result = await askAgentStream(selectedId, text, (delta) => {
        setHistory((current) => {
          const next = [...current]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = { role: 'assistant', content: last.content + delta }
          }
          return next
        })
      })
      setHistory(result.history ?? [])
      setAgents((current) => current.map((agent) => (agent.id === result.id ? result : agent)))
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Ask failed.'
      setError(message)
      setHistory((current) => {
        const next = [...current]
        const last = next[next.length - 1]
        if (last?.role === 'assistant' && last.content === '') {
          next.pop()
        }
        return next
      })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex h-full min-h-[calc(100svh-3rem)]">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-surface md:block">
        <div className="border-b border-border px-3 py-3 text-xs font-medium uppercase tracking-wide text-muted">
          Agents
        </div>
        {loadingList ? (
          <p className="px-3 py-4 text-sm text-muted">Loading agents…</p>
        ) : agents.length === 0 ? (
          <p className="px-3 py-4 text-sm text-muted">No agents yet.</p>
        ) : (
          <ul>
            {agents.map((agent) => (
              <li key={agent.id}>
                <button
                  type="button"
                  onClick={() => setSearchParams({ agent: agent.id })}
                  className={cn(
                    'flex w-full flex-col items-start gap-0.5 px-3 py-2.5 text-left hover:bg-surface-2',
                    agent.id === selectedId && 'bg-surface-2',
                  )}
                >
                  <span className="text-sm">{agent.name}</span>
                  <span className="text-[11px] text-muted">
                    {agent.template_id} · {agent.state}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        {error && (
          <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-200">{error}</div>
        )}

        {!loadingList && agents.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
            <h1 className="text-lg font-semibold">No agents in this process</h1>
            <p className="max-w-md text-sm text-muted">
              Create an agent from a template. Conversations live in memory until the server stops.
            </p>
            <Link
              to="/agents"
              className="inline-flex h-9 items-center rounded-md bg-accent px-3 text-sm font-medium text-bg hover:opacity-90"
            >
              Go to Agents
            </Link>
          </div>
        ) : (
          <>
            <div className="border-b border-border px-4 py-3">
              <div className="font-medium">{selected?.name ?? 'Select an agent'}</div>
              <div className="text-xs text-muted">
                {selected
                  ? `${selected.template_id} · ${selected.state} · ${selected.channel} · plugins: ${selected.plugins.join(', ') || 'none'}`
                  : 'Pick an agent from the list.'}
              </div>
              <div className="mt-2 md:hidden">
                <select
                  className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
                  value={selectedId}
                  onChange={(event) => setSearchParams({ agent: event.target.value })}
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-auto px-4 py-4">
              {history.length === 0 ? (
                <p className="text-sm text-muted">No messages yet. Ask something to start this conversation.</p>
              ) : (
                history
                  .filter((turn) => turn.role === 'user' || turn.role === 'assistant')
                  .map((turn, index) => (
                    <div
                      key={`${turn.role}-${index}`}
                      className={cn(
                        'max-w-3xl rounded-lg px-3 py-2 text-sm leading-relaxed',
                        turn.role === 'user'
                          ? 'ml-auto bg-surface-2 text-ink'
                          : 'bg-surface text-ink ring-1 ring-border',
                      )}
                    >
                      <div className="mb-1 text-[11px] uppercase tracking-wide text-muted">{turn.role}</div>
                      <div className="whitespace-pre-wrap">{turn.content}</div>
                    </div>
                  ))
              )}
              {sending && <p className="text-sm text-accent">Waiting for the agent…</p>}
            </div>

            <form
              className="flex gap-2 border-t border-border p-3"
              onSubmit={(event) => {
                event.preventDefault()
                void send()
              }}
            >
              <Textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void send()
                  }
                }}
                placeholder={selected ? 'Message this agent…' : 'Create an agent first'}
                disabled={!selected || sending}
                rows={2}
                className="min-h-[52px]"
              />
              <Button type="submit" disabled={!selected || sending || !prompt.trim()}>
                Send
              </Button>
            </form>
          </>
        )}
      </section>
    </div>
  )
}
