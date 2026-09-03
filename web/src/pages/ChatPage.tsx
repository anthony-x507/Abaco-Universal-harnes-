import { FileText, Mic, Paperclip, PanelLeft, PanelRight, Square, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { WorkspacePane } from '../components/WorkspacePane'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Textarea } from '../components/ui/textarea'
import {
  ApiError,
  askAgentStream,
  createAgent,
  friendlyError,
  PROVIDER_ERROR_COPY,
  getAgent,
  getSettings,
  listAgents,
  listTemplates,
  resetAgent,
  type Agent,
  type HistoryTurn,
  type Template,
} from '../lib/api'
import { useAskSession } from '../lib/ask-session'
import { laterChannels, pluginListLabel, usageLabel } from '../lib/utils'
import { loadPaneState, savePaneState, type PaneId, type PaneState } from '../lib/layout'
import { cn } from '../lib/utils'

type Attachment = { name: string; kind: 'file' | 'audio'; note: string; body?: string }

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('agent') ?? ''
  const [panes, setPanes] = useState<PaneState>(() => loadPaneState())
  const [agents, setAgents] = useState<Agent[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [history, setHistory] = useState<HistoryTurn[]>([])
  const [prompt, setPrompt] = useState('')
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('general')
  const [channel, setChannel] = useState('cli')
  const [channels, setChannels] = useState<string[]>(['cli'])
  const [comingChannels, setComingChannels] = useState<string[]>([])
  const [outboundUrl, setOutboundUrl] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const { beginAsk, endAsk, showToast } = useAskSession()
  const [loadingList, setLoadingList] = useState(true)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const [creating, setCreating] = useState(false)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [activity, setActivity] = useState({ visible: false, text: '' })
  const [autoMode, setAutoMode] = useState(false)
  const activityTimer = useRef<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const selectedIdRef = useRef(selectedId)
  const threadRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    selectedIdRef.current = selectedId
  }, [selectedId])

  useEffect(() => {
    return () => {
      if (activityTimer.current) window.clearTimeout(activityTimer.current)
    }
  }, [])

  const selected = useMemo(
    () => agents.find((agent) => agent.id === selectedId) ?? null,
    [agents, selectedId],
  )

  const togglePane = (id: PaneId) => {
    setPanes((current) => {
      const next = { ...current, [id]: !current[id] }
      if (!next.left && !next.middle && !next.right) {
        next.middle = true
      }
      savePaneState(next)
      return next
    })
  }

  const refresh = async () => {
    const [rows, tpls, settings] = await Promise.all([listAgents(), listTemplates(), getSettings()])
    setAgents(rows)
    setTemplates(tpls)
    setChannels(settings.channels.length > 0 ? settings.channels : ['cli'])
    setComingChannels(settings.channels_coming)
    setChannel(settings.default_channel || 'cli')
    if (tpls.length > 0 && !tpls.some((item) => item.id === template)) {
      setTemplate(tpls[0].id)
    }
    return rows
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoadingList(true)
      try {
        const rows = await refresh()
        if (cancelled) return
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
      setLoadingHistory(false)
      return
    }
    setHistory([])
    setLoadingHistory(true)
    setError('')
    let cancelled = false
    const requested = selectedId
    const load = async () => {
      try {
        const agent = await getAgent(requested)
        if (cancelled || selectedIdRef.current !== requested) return
        setHistory(agent.history ?? [])
      } catch (err) {
        if (!cancelled && selectedIdRef.current === requested) {
          setHistory([])
          setError(err instanceof Error ? err.message : 'Could not load conversation.')
        }
      } finally {
        if (!cancelled && selectedIdRef.current === requested) setLoadingHistory(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [selectedId])

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight })
  }, [history, sending, loadingHistory])

  const buildPrompt = (text: string) => {
    if (attachments.length === 0) return text
    const extras = attachments
      .map((item) => {
        if (item.body) return `Attached file ${item.name}:\n${item.body}`
        return item.note
      })
      .join('\n\n')
    return `${text}\n\n${extras}`
  }

  const showActivity = (text: string, ms: number) => {
    if (activityTimer.current) window.clearTimeout(activityTimer.current)
    setActivity({ visible: true, text })
    activityTimer.current = window.setTimeout(() => {
      setActivity((current) => ({ ...current, visible: false }))
      activityTimer.current = null
    }, ms)
  }

  const sendPrompt = async (outbound: string, appendUser: boolean) => {
    if (!selectedId) return
    const controller = beginAsk(selectedId)
    if (!controller) return
    const agentId = selectedId
    setSending(true)
    setError('')
    setHistory((current) => {
      const next = current.filter((turn) => !turn.failed)
      if (appendUser) next.push({ role: 'user', content: outbound })
      next.push({ role: 'assistant', content: '' })
      return next
    })
    try {
      const result = await askAgentStream(
        agentId,
        outbound,
        (delta) => {
          if (selectedIdRef.current !== agentId) return
          setHistory((current) => {
            const next = [...current]
            const last = next[next.length - 1]
            if (last?.role === 'assistant' && !last.failed) {
              next[next.length - 1] = { role: 'assistant', content: last.content + delta }
            }
            return next
          })
        },
        controller.signal,
        (status) => {
          if (status.type === 'tool_execution') {
            showActivity(`🔧 Executing tool: ${status.tool || 'tool'}...`, 2000)
            return
          }
          if (status.type === 'delegating') {
            showActivity(`📤 Agent sent message to "${status.target || 'another agent'}"`, 3000)
          }
        },
        { autonomous: autoMode },
      )
      if (selectedIdRef.current !== agentId) return
      setHistory(result.history ?? [])
      setAgents((current) => current.map((agent) => (agent.id === result.id ? result : agent)))
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      if (err instanceof ApiError && err.status === 409) {
        showToast('Agent is already answering. Please wait.')
        setHistory((current) => {
          const next = [...current]
          if (next[next.length - 1]?.role === 'assistant' && !next[next.length - 1]?.content) next.pop()
          return next
        })
        return
      }
      const message = friendlyError(err)
      if (err instanceof ApiError && PROVIDER_ERROR_COPY[err.status]) {
        showToast(message)
      }
      if (selectedIdRef.current !== agentId) return
      setHistory((current) => {
        const next = [...current]
        const last = next[next.length - 1]
        if (last?.role === 'assistant') {
          next[next.length - 1] = { role: 'assistant', content: message, failed: true }
        } else {
          next.push({ role: 'assistant', content: message, failed: true })
        }
        return next
      })
    } finally {
      endAsk(agentId)
      if (selectedIdRef.current === agentId) setSending(false)
    }
  }

  const send = async () => {
    const text = prompt.trim()
    if ((!text && attachments.length === 0) || !selectedId) return
    if (sending) {
      showToast('Agent is already answering. Please wait.')
      return
    }
    const outbound = buildPrompt(text || '(attachment only)')
    setPrompt('')
    setAttachments([])
    await sendPrompt(outbound, true)
  }

  const clearHistory = async () => {
    if (!selectedId) return
    setClearing(true)
    setError('')
    try {
      const agent = await resetAgent(selectedId)
      setHistory(agent.history ?? [])
      setAgents((current) => current.map((row) => (row.id === agent.id ? { ...row, ...agent } : row)))
      setConfirmClear(false)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setClearing(false)
    }
  }

  const retryLast = async () => {
    const lastUser = [...history].reverse().find((turn) => turn.role === 'user')
    if (!lastUser || sending) return
    await sendPrompt(lastUser.content, false)
  }

  const onFiles = async (list: FileList | null) => {
    if (!list) return
    const next: Attachment[] = []
    for (const file of Array.from(list)) {
      const textLike = file.type.startsWith('text/') || /\.(md|txt|json|csv|py|ts|tsx|js)$/i.test(file.name)
      if (textLike && file.size < 200_000) {
        const body = await file.text()
        next.push({
          name: file.name,
          kind: 'file',
          note: `Attached file ${file.name}`,
          body,
        })
      } else {
        next.push({
          name: file.name,
          kind: 'file',
          note: `Attached file ${file.name} (${Math.round(file.size / 1024)} KB). Binary content is not sent to the model in this cut.`,
        })
      }
    }
    setAttachments((current) => [...current, ...next])
  }

  const toggleRecord = async () => {
    if (recording) {
      recorderRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        const seconds = Math.max(1, Math.round(blob.size / 4000))
        setAttachments((current) => [
          ...current,
          {
            name: `audio-${Date.now()}.webm`,
            kind: 'audio',
            note: `Attached audio clip (~${seconds}s). Speech-to-text is not on the server; the model only sees this note.`,
          },
        ])
        setRecording(false)
        recorderRef.current = null
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Microphone is not available.')
    }
  }

  const create = async () => {
    setCreating(true)
    setError('')
    try {
      const agent = await createAgent({
        template,
        name: name.trim() || undefined,
        channel,
        outbound_url: channel === 'webhook' ? outboundUrl.trim() || undefined : undefined,
      })
      setName('')
      setOutboundUrl('')
      await refresh()
      setSearchParams({ agent: agent.id })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2">
        <Button size="sm" variant={panes.left ? 'default' : 'outline'} onClick={() => togglePane('left')}>
          <PanelLeft size={14} />
          Agents
        </Button>
        <Button size="sm" variant={panes.middle ? 'default' : 'outline'} onClick={() => togglePane('middle')}>
          Messages
        </Button>
        <Button size="sm" variant={panes.right ? 'default' : 'outline'} onClick={() => togglePane('right')}>
          <PanelRight size={14} />
          Workspace
        </Button>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-200">
          <span>{error}</span>
          <button type="button" className="text-red-100 hover:text-white" onClick={() => setError('')} aria-label="Dismiss error">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 overflow-x-auto">
        {panes.left && (
          <aside className="flex h-full min-h-0 w-80 shrink-0 flex-col border-r border-border bg-surface">
            <header className="flex items-center justify-between border-b border-border px-3 py-2">
              <div className="text-xs font-medium uppercase tracking-wide text-muted">Agents</div>
              <button type="button" className="text-muted hover:text-ink" onClick={() => togglePane('left')} aria-label="Close agents">
                <X size={14} />
              </button>
            </header>
            <div className="min-h-0 flex-1 overflow-auto">
              <section className="space-y-2 border-b border-border p-3">
                <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Templates</h2>
                <ul className="space-y-2">
                  {templates.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => setTemplate(item.id)}
                        className={cn(
                          'w-full rounded-md border px-2 py-2 text-left',
                          template === item.id ? 'border-accent/40 bg-surface-2' : 'border-border hover:bg-surface-2',
                        )}
                      >
                        <div className="text-sm font-medium">{item.name}</div>
                        <p className="mt-1 text-xs text-muted">{item.description}</p>
                      </button>
                    </li>
                  ))}
                </ul>
                <Label htmlFor="new-name">New agent</Label>
                <Input id="new-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Name (optional)" />
                <Label htmlFor="new-channel">Channel</Label>
                <select
                  id="new-channel"
                  value={channel}
                  onChange={(event) => setChannel(event.target.value)}
                  className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
                >
                  {channels.map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                  {laterChannels(channels, comingChannels).map((id) => (
                    <option key={id} value={id} disabled>
                      {id} (later)
                    </option>
                  ))}
                </select>
                {channel === 'webhook' && (
                  <>
                    <Label htmlFor="new-outbound">Outbound URL (optional)</Label>
                    <Input
                      id="new-outbound"
                      value={outboundUrl}
                      onChange={(event) => setOutboundUrl(event.target.value)}
                      placeholder="https://example.com/hooks/universal"
                    />
                  </>
                )}
                <Button size="sm" onClick={() => void create()} disabled={creating}>
                  {creating ? 'Creating…' : `Create ${templates.find((item) => item.id === template)?.name ?? 'agent'}`}
                </Button>
              </section>
              {loadingList ? (
                <p className="px-3 py-4 text-sm text-muted">Loading agents…</p>
              ) : agents.length === 0 ? (
                <p className="px-3 py-4 text-sm text-muted">No agents in this process yet. Create one above.</p>
              ) : (
                <ul>
                  {agents.map((agent) => {
                    const info = templates.find((item) => item.id === agent.template_id)
                    return (
                      <li key={agent.id}>
                        <button
                          type="button"
                          onClick={() => setSearchParams({ agent: agent.id })}
                          className={cn(
                            'flex w-full flex-col items-start gap-1 px-3 py-3 text-left hover:bg-surface-2',
                            agent.id === selectedId && 'bg-surface-2',
                          )}
                        >
                          <div className="flex w-full items-center justify-between gap-2">
                            <span className="text-sm font-medium">{agent.name}</span>
                            <Badge className={agent.state === 'running' ? 'border-accent/40 text-accent' : ''}>
                              {agent.state}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted">{info?.description ?? agent.template_id}</p>
                          <p className="text-[11px] text-muted">
                            {agent.channel} · {pluginListLabel(agent.plugin_labels, agent.plugins.length)}
                          </p>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </aside>
        )}

        {panes.middle && (
          <section className="flex min-h-0 min-w-[22rem] flex-1 flex-col bg-bg">
            <header className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <div className="font-medium">{selected?.name ?? 'Select an agent'}</div>
                <div className="text-xs text-muted">
                  {selected
                    ? `${selected.template_id} · ${selected.state} · one thread in memory`
                    : 'Create or pick an agent on the left.'}
                </div>
                {selected && (
                  <div className="mt-1 text-xs text-muted" data-testid="usage-meter">
                    {usageLabel(selected.usage)}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {selected && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={sending || clearing}
                    title="Clear history"
                    onClick={() => setConfirmClear(true)}
                  >
                    <Trash2 size={14} />
                    Clear history
                  </Button>
                )}
                <button type="button" className="text-muted hover:text-ink" onClick={() => togglePane('middle')} aria-label="Close messages">
                  <X size={14} />
                </button>
              </div>
            </header>

            <div ref={threadRef} className="min-h-0 flex-1 space-y-3 overflow-auto px-4 py-4">
              {!selected ? (
                <p className="text-sm text-muted">The writing area is here. Choose an agent to start the thread.</p>
              ) : loadingHistory ? (
                <p className="text-sm text-muted">Loading conversation…</p>
              ) : history.length === 0 ? (
                <p className="text-sm text-muted">No messages yet. Type below, or attach a file or audio note.</p>
              ) : (
                history
                  .filter((turn) => turn.role === 'user' || turn.role === 'assistant')
                  .map((turn, index) => (
                    <div
                      key={`${selectedId}-${turn.role}-${index}`}
                      className={cn(
                        'max-w-3xl rounded-lg px-3 py-2 text-sm leading-relaxed',
                        turn.role === 'user'
                          ? 'ml-auto bg-surface-2 text-ink'
                          : turn.failed
                            ? 'bg-red-500/10 text-red-100 ring-1 ring-red-500/40'
                            : 'bg-surface text-ink ring-1 ring-border',
                      )}
                    >
                      <div className="mb-1 text-[11px] uppercase tracking-wide text-muted">
                        {turn.failed ? 'error' : turn.role}
                      </div>
                      <div className="whitespace-pre-wrap">{turn.content || (turn.role === 'assistant' && sending ? '…' : '')}</div>
                      {turn.failed && (
                        <Button size="sm" variant="outline" className="mt-2" onClick={() => void retryLast()} disabled={sending}>
                          Retry
                        </Button>
                      )}
                    </div>
                  ))
              )}
              {sending && history.at(-1)?.role === 'assistant' && !history.at(-1)?.content && (
                <p className="text-sm text-accent">Waiting for the agent…</p>
              )}
            </div>

            {activity.visible && (
              <div
                role="status"
                className="mx-3 mb-0 mt-2 rounded-md border border-border bg-surface px-3 py-1.5 text-center text-sm text-muted"
              >
                {activity.text}
              </div>
            )}
            <form
              className="border-t border-border bg-surface p-3"
              onSubmit={(event) => {
                event.preventDefault()
                void send()
              }}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                void onFiles(event.dataTransfer.files)
              }}
            >
              {attachments.length > 0 && (
                <ul className="mb-2 flex flex-wrap gap-2">
                  {attachments.map((item) => (
                    <li
                      key={item.name}
                      className="flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-xs"
                    >
                      {item.kind === 'audio' ? <Mic size={12} /> : <FileText size={12} />}
                      {item.name}
                      <button
                        type="button"
                        className="text-muted hover:text-ink"
                        onClick={() => setAttachments((current) => current.filter((row) => row.name !== item.name))}
                        aria-label={`Remove ${item.name}`}
                      >
                        <X size={12} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <Textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void send()
                  }
                }}
                placeholder={selected ? 'Write in the middle column…' : 'Create an agent first'}
                disabled={!selected || sending || loadingHistory}
                rows={3}
                className="min-h-[72px]"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(event) => {
                    void onFiles(event.target.files)
                    event.target.value = ''
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={!selected || sending || loadingHistory}
                  title="File content is sent as text"
                  onClick={() => fileRef.current?.click()}
                >
                  <Paperclip size={14} />
                  File
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={recording ? 'danger' : 'outline'}
                  disabled={!selected || sending || loadingHistory}
                  title="Audio is attached as a note (no STT)"
                  onClick={() => void toggleRecord()}
                >
                  {recording ? <Square size={14} /> : <Mic size={14} />}
                  {recording ? 'Stop audio' : 'Audio'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={autoMode ? 'default' : 'outline'}
                  disabled={!selected || sending || loadingHistory}
                  aria-pressed={autoMode}
                  title="Autonomous tool loop. Off keeps one-turn ask."
                  onClick={() => setAutoMode((current) => !current)}
                >
                  Auto
                </Button>
                <Button type="submit" disabled={!selected || sending || loadingHistory || (!prompt.trim() && attachments.length === 0)}>
                  Send
                </Button>
                <p className="w-full text-[11px] text-muted">
                  Files are sent as text. Audio is attached as a note. No speech-to-text or OCR in this cut.
                </p>
              </div>
            </form>
          </section>
        )}

        {panes.right && <WorkspacePane onClose={() => togglePane('right')} />}
      </div>

      {confirmClear && selected && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4">
          <div className="max-w-md space-y-3 rounded-lg border border-border bg-surface p-5">
            <h2 className="text-sm font-medium">Clear history?</h2>
            <p className="text-sm text-muted">Are you sure? This will delete the conversation history.</p>
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => setConfirmClear(false)} disabled={clearing}>
                Cancel
              </Button>
              <Button size="sm" variant="danger" onClick={() => void clearHistory()} disabled={clearing}>
                {clearing ? 'Clearing…' : 'Clear history'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
