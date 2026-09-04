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
  listAgents,
  listTemplates,
  resetAgent,
  type Agent,
  type HistoryTurn,
  type Template,
} from '../lib/api'
import { useAskSession } from '../lib/ask-session'
import { cn, pluginListLabel, usageLabel } from '../lib/utils'
import { DragHandle } from '../components/DragHandle'
import { useLayout } from '../lib/layout-context'
import { SIZE_LIMITS, type PaneId } from '../lib/layout'

type Attachment = {
  name: string
  kind: 'file' | 'audio' | 'image'
  note: string
  mime: string
  data?: string
  body?: string
}

const FACE_EMOJIS = ['💬', '🔎', '💻', '😊', '😎', '🤖', '🧠', '🦊', '🐱', '🦉', '🐲', '⭐', '🔥', '🌱', '🎯']

function fileToBase64(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || '')
      const comma = text.indexOf(',')
      resolve(comma >= 0 ? text.slice(comma + 1) : text)
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('agent') ?? ''
  const { layout, updateLayout } = useLayout()
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [history, setHistory] = useState<HistoryTurn[]>([])
  const [prompt, setPrompt] = useState('')
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('general')
  const [emoji, setEmoji] = useState('💬')
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
  const speechRef = useRef<{ stop: () => void } | null>(null)
  const spokenRef = useRef('')
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
    const next = {
      left: id === 'left' ? !layout.left : layout.left,
      middle: id === 'middle' ? !layout.middle : layout.middle,
      right: id === 'right' ? !layout.right : layout.right,
    }
    if (!next.left && !next.middle && !next.right) next.middle = true
    updateLayout(next)
  }

  const refresh = async () => {
    const [rows, tpls] = await Promise.all([listAgents(), listTemplates()])
    setAgents(rows)
    setTemplates(tpls)
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

  const sendPrompt = async (
    outbound: string,
    appendUser: boolean,
    files: Attachment[] = [],
  ) => {
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
        {
          autonomous: autoMode,
          attachments: files
            .filter((item) => item.data)
            .map((item) => ({
              name: item.name,
              mime: item.mime,
              data: item.data as string,
              kind: item.kind,
            })),
        },
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
    const pending = attachments
    const outbound = buildPrompt(text || (pending.length ? '' : '(attachment only)'))
    setPrompt('')
    setAttachments([])
    await sendPrompt(outbound, true, pending)
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
      const data = await fileToBase64(file)
      const image = file.type.startsWith('image/')
      const textLike = file.type.startsWith('text/') || /\.(md|txt|json|csv|py|ts|tsx|js)$/i.test(file.name)
      next.push({
        name: file.name,
        kind: image ? 'image' : 'file',
        mime: file.type || 'application/octet-stream',
        data,
        note: image ? `Photo ${file.name}` : `Attached file ${file.name}`,
        body: textLike && file.size < 200_000 ? await file.text() : undefined,
      })
    }
    setAttachments((current) => [...current, ...next])
  }

  const toggleRecord = async () => {
    if (recording) {
      speechRef.current?.stop()
      speechRef.current = null
      recorderRef.current?.stop()
      return
    }
    spokenRef.current = ''
    try {
      const SpeechAPI = (
        window as unknown as {
          SpeechRecognition?: new () => {
            continuous: boolean
            interimResults: boolean
            lang: string
            start: () => void
            stop: () => void
            onresult: ((event: { resultIndex: number; results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null
            onerror: (() => void) | null
          }
          webkitSpeechRecognition?: new () => {
            continuous: boolean
            interimResults: boolean
            lang: string
            start: () => void
            stop: () => void
            onresult: ((event: { resultIndex: number; results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null
            onerror: (() => void) | null
          }
        }
      ).SpeechRecognition || (window as unknown as { webkitSpeechRecognition?: new () => never }).webkitSpeechRecognition
      if (SpeechAPI) {
        const recognition = new SpeechAPI()
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = navigator.language || 'en-US'
        recognition.onresult = (event) => {
          let spoken = ''
          for (let i = event.resultIndex; i < event.results.length; i += 1) {
            spoken += event.results[i][0].transcript
          }
          spokenRef.current = spoken.trim()
          if (spokenRef.current) setPrompt((current) => (current ? current : spokenRef.current))
        }
        recognition.onerror = () => undefined
        recognition.start()
        speechRef.current = recognition
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        void fileToBase64(blob).then((data) => {
          setAttachments((current) => [
            ...current,
            {
              name: `audio-${Date.now()}.webm`,
              kind: 'audio',
              mime: blob.type || 'audio/webm',
              data,
              note: spokenRef.current ? `Audio: ${spokenRef.current}` : 'Audio clip ready to transcribe',
            },
          ])
          if (spokenRef.current) {
            setPrompt((current) => current || spokenRef.current)
          }
        })
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
        emoji,
      })
      setName('')
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
        <Button size="sm" variant={layout.left ? 'default' : 'outline'} onClick={() => togglePane('left')}>
          <PanelLeft size={14} />
          Agents
        </Button>
        <Button size="sm" variant={layout.middle ? 'default' : 'outline'} onClick={() => togglePane('middle')}>
          Messages
        </Button>
        <Button size="sm" variant={layout.right ? 'default' : 'outline'} onClick={() => togglePane('right')}>
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
        {layout.left && (
          <aside
            className="flex h-full min-h-0 shrink-0 flex-col border-r border-border bg-surface"
            style={{ width: layout.leftWidth }}
          >
            <header className="flex items-center justify-between border-b border-border px-3 py-2">
              <div className="text-xs font-medium uppercase tracking-wide text-muted">Agents</div>
              <button type="button" className="text-muted hover:text-ink" onClick={() => togglePane('left')} aria-label="Close agents">
                <X size={14} />
              </button>
            </header>
            <div className="min-h-0 flex-1 overflow-auto">
              <section className="space-y-3 border-b border-border p-3">
                <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Templates</h2>
                <ul className="grid grid-cols-3 gap-2">
                  {templates.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setTemplate(item.id)
                          setEmoji(item.emoji || '💬')
                        }}
                        className={cn(
                          'flex w-full flex-col items-center rounded-md border px-1 py-2 text-center',
                          template === item.id ? 'border-accent/40 bg-surface-2' : 'border-border hover:bg-surface-2',
                        )}
                      >
                        <span className="text-2xl" aria-hidden>
                          {item.emoji || '💬'}
                        </span>
                        <span className="mt-1 text-xs font-medium">{item.name}</span>
                        <p className="mt-0.5 line-clamp-2 text-[10px] leading-tight text-muted">{item.description}</p>
                      </button>
                    </li>
                  ))}
                </ul>
                <div>
                  <Label>Face</Label>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {FACE_EMOJIS.map((face) => (
                      <button
                        key={face}
                        type="button"
                        onClick={() => setEmoji(face)}
                        className={cn(
                          'flex h-8 w-8 items-center justify-center rounded-md border text-lg',
                          emoji === face ? 'border-accent bg-surface-2' : 'border-border hover:bg-surface-2',
                        )}
                        aria-label={`Face ${face}`}
                        aria-pressed={emoji === face}
                      >
                        {face}
                      </button>
                    ))}
                  </div>
                </div>
                <Label htmlFor="new-name">Name (optional)</Label>
                <Input id="new-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Name (optional)" />
                <p className="text-[11px] text-muted">Model and channel live in Settings.</p>
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
                            <span className="flex items-center gap-2 text-sm font-medium">
                              <span className="text-xl" aria-hidden>
                                {agent.emoji || info?.emoji || '💬'}
                              </span>
                              {agent.name}
                            </span>
                            <Badge className={agent.state === 'running' ? 'border-accent/40 text-accent' : ''}>
                              {agent.state}
                            </Badge>
                          </div>
                          <p className="text-[11px] leading-snug text-muted">{info?.description ?? agent.template_id}</p>
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
        {layout.left && (
          <DragHandle
            axis="x"
            value={layout.leftWidth}
            min={SIZE_LIMITS.pane.min}
            max={SIZE_LIMITS.pane.max}
            onValue={(leftWidth) => updateLayout({ leftWidth })}
            label="Resize agents panel"
            testId="agents-pane-resize"
          />
        )}

        {layout.middle && (
          <section className="flex min-h-0 min-w-[22rem] flex-1 flex-col bg-bg">
            <header className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <div className="font-medium">
                  {selected ? `${selected.emoji || '💬'} ${selected.name}` : 'Select an agent'}
                </div>
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
            {layout.composerOpen ? (
              <div className="relative z-10 shrink-0 border-t border-border bg-surface">
                <DragHandle
                  axis="y"
                  invert
                  value={layout.composerHeight}
                  min={SIZE_LIMITS.composer.min}
                  max={SIZE_LIMITS.composer.max}
                  onValue={(composerHeight) => updateLayout({ composerHeight })}
                  label="Resize message box"
                  testId="composer-resize"
                />
                <form
                  className="p-3"
                  onSubmit={(event) => {
                    event.preventDefault()
                    if (!selected) {
                      showToast('Pick or create an agent on the left first.')
                      return
                    }
                    void send()
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault()
                    void onFiles(event.dataTransfer.files)
                  }}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-[11px] uppercase tracking-wide text-muted">Message</span>
                    <button
                      type="button"
                      className="text-muted hover:text-ink"
                      onClick={() => updateLayout({ composerOpen: false })}
                      aria-label="Close message box"
                    >
                      <X size={14} />
                    </button>
                  </div>
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
                    ref={composerRef}
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    onClick={() => {
                      if (!selected) showToast('Pick or create an agent on the left first.')
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        if (!selected) {
                          showToast('Pick or create an agent on the left first.')
                          return
                        }
                        void send()
                      }
                    }}
                    placeholder={selected ? 'Write in the middle column…' : 'Create an agent first'}
                    disabled={sending}
                    rows={3}
                    className="resize-none"
                    style={{ height: layout.composerHeight }}
                  />
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      ref={fileRef}
                      type="file"
                      multiple
                      accept="image/*,audio/*,.txt,.md,.json,.csv,.py,.ts,.tsx,.js"
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
                      disabled={sending}
                      title="File content is sent as text"
                      onClick={() => {
                        if (!selected) {
                          showToast('Pick or create an agent on the left first.')
                          return
                        }
                        fileRef.current?.click()
                      }}
                    >
                      <Paperclip size={14} />
                      File
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={recording ? 'danger' : 'outline'}
                      disabled={sending}
                      title="Audio is attached as a note (no STT)"
                      onClick={() => {
                        if (!selected) {
                          showToast('Pick or create an agent on the left first.')
                          return
                        }
                        void toggleRecord()
                      }}
                    >
                      {recording ? <Square size={14} /> : <Mic size={14} />}
                      {recording ? 'Stop audio' : 'Audio'}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={autoMode ? 'default' : 'outline'}
                      disabled={sending}
                      aria-pressed={autoMode}
                      title="Autonomous tool loop. Off keeps one-turn ask."
                      onClick={() => setAutoMode((current) => !current)}
                    >
                      Auto
                    </Button>
                    <Button type="submit" disabled={sending || (!prompt.trim() && attachments.length === 0)}>
                      Send
                    </Button>
                    <p className="w-full text-[11px] text-muted">
                      Drag the bar above to make this box taller. Photos are sent to the agent. Audio is transcribed.
                    </p>
                  </div>
                </form>
              </div>
            ) : (
              <button
                type="button"
                className="relative z-10 flex w-full shrink-0 items-center justify-between border-t border-border bg-surface px-4 py-3 text-left text-sm text-muted hover:bg-surface-2 hover:text-ink"
                onClick={() => {
                  updateLayout({ composerOpen: true })
                  window.setTimeout(() => composerRef.current?.focus(), 0)
                }}
                aria-label="Open message box"
              >
                <span>Write a message…</span>
                <span className="text-xs">Open</span>
              </button>
            )}
          </section>
        )}

        {layout.right && (
          <>
            <DragHandle
              axis="x"
              invert
              value={layout.rightWidth}
              min={SIZE_LIMITS.pane.min}
              max={SIZE_LIMITS.pane.max}
              onValue={(rightWidth) => updateLayout({ rightWidth })}
              label="Resize workspace"
              testId="workspace-resize"
            />
            <WorkspacePane width={layout.rightWidth} onClose={() => togglePane('right')} />
          </>
        )}
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
