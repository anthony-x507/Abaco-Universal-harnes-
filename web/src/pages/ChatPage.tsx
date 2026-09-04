import { ArrowUp, FileText, Mic, Paperclip, PanelRight, Square, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { WorkspacePane } from '../components/WorkspacePane'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import {
  ApiError,
  askAgentStream,
  friendlyError,
  PROVIDER_ERROR_COPY,
  getAgent,
  listAgents,
  resetAgent,
  type Agent,
  type HistoryTurn,
} from '../lib/api'
import { useAskSession } from '../lib/ask-session'
import { cn, usageLabel } from '../lib/utils'
import { DragHandle } from '../components/DragHandle'
import { useLayout } from '../lib/layout-context'
import { SIZE_LIMITS } from '../lib/layout'

type Attachment = {
  name: string
  kind: 'file' | 'audio' | 'image'
  note: string
  mime: string
  data?: string
  body?: string
}

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
  const [history, setHistory] = useState<HistoryTurn[]>([])
  const [prompt, setPrompt] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const { beginAsk, endAsk, showToast } = useAskSession()
  const [statusLine, setStatusLine] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [autoMode, setAutoMode] = useState(false)
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

  const selected = useMemo(
    () => agents.find((agent) => agent.id === selectedId) ?? null,
    [agents, selectedId],
  )

  const refresh = async () => {
    const rows = await listAgents()
    setAgents(rows)
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

  const sendPrompt = async (
    outbound: string,
    appendUser: boolean,
    files: Attachment[] = [],
  ) => {
    if (!selectedId) return
    const controller = beginAsk(selectedId)
    if (!controller) return
    const agentId = selectedId
    const agentName = selected?.name || 'Agent'
    setSending(true)
    setError('')
    setStatusLine('Thinking…')
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
          setStatusLine('')
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
            setStatusLine(`🔧 Executing tool: ${status.tool || 'tool'}...`)
            return
          }
          if (status.type === 'delegating') {
            setStatusLine(`Talking to ${status.target || 'another agent'}…`)
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
      setStatusLine('')
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      if (err instanceof ApiError && err.status === 409) {
        showToast('Agent is already answering. Please wait.')
        setStatusLine('')
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
      setStatusLine('')
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
      if (selectedIdRef.current === agentId) {
        setSending(false)
        setStatusLine('')
      }
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

  const requireAgent = () => {
    if (selected) return true
    showToast('Create an agent in Design first.')
    return false
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

  const emptyThread = !loadingHistory && history.length === 0

  return (
    <div className="flex h-full min-h-0 flex-col">
      {error && (
        <div className="flex items-center justify-between gap-3 border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-200">
          <span>{error}</span>
          <button type="button" className="text-red-100 hover:text-white" onClick={() => setError('')} aria-label="Dismiss error">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <section className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-bg">
          <header className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              {loadingList ? (
                <p className="text-sm text-muted">Loading agents…</p>
              ) : agents.length === 0 ? (
                <p className="text-sm text-muted">
                  No agents yet.{' '}
                  <Link className="text-accent hover:underline" to="/design">
                    Create one in Design
                  </Link>
                  .
                </p>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <label className="sr-only" htmlFor="chat-agent">
                    Agent
                  </label>
                  <select
                    id="chat-agent"
                    value={selectedId}
                    onChange={(event) => setSearchParams({ agent: event.target.value })}
                    className="max-w-[16rem] rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-ink"
                  >
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.emoji || '💬'} {agent.name}
                      </option>
                    ))}
                  </select>
                  {selected && (
                    <Badge className={selected.state === 'running' ? 'border-accent/40 text-accent' : ''}>
                      {selected.state}
                    </Badge>
                  )}
                  {selected && (
                    <span className="text-xs text-muted" data-testid="usage-meter">
                      {usageLabel(selected.usage)}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {selected && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={sending || clearing}
                  title="Clear history"
                  onClick={() => setConfirmClear(true)}
                >
                  <Trash2 size={14} />
                  Clear history
                </Button>
              )}
              <Button
                size="sm"
                variant={layout.right ? 'default' : 'ghost'}
                onClick={() => updateLayout({ right: !layout.right, middle: true })}
              >
                <PanelRight size={14} />
                Workspace
              </Button>
            </div>
          </header>

          <div
            ref={threadRef}
            className={cn(
              'min-h-0 flex-1 overflow-auto px-4',
              emptyThread ? 'flex flex-col items-center justify-end pb-2' : 'space-y-3 py-2',
            )}
          >
            {emptyThread ? (
              <div className="mb-4 max-w-xl text-center">
                <h1 className="font-serif text-3xl text-ink md:text-4xl">What should we work on?</h1>
                <p className="mt-2 text-sm text-muted">Write in the glass bar. Your notes sit on the right.</p>
              </div>
            ) : !selected ? (
              <p className="mx-auto max-w-lg py-10 text-center text-sm text-muted">
                Create an agent in Design, then come back here.
              </p>
            ) : loadingHistory ? (
              <p className="text-sm text-muted">Loading conversation…</p>
            ) : (
              history
                .filter((turn) => turn.role === 'user' || turn.role === 'assistant')
                .map((turn, index) => {
                  const mine = turn.role === 'user'
                  return (
                    <div
                      key={`${selectedId}-${turn.role}-${index}`}
                      className={cn('flex w-full', mine ? 'justify-end' : 'justify-start')}
                    >
                      <div
                        className={cn(
                          'max-w-[min(36rem,92%)] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                          mine && 'bg-sky-500/20 text-ink ring-1 ring-sky-400/30',
                          !mine && turn.failed && 'bg-red-500/10 text-red-100 ring-1 ring-red-500/40',
                          !mine && !turn.failed && 'bg-amber-500/10 text-ink ring-1 ring-amber-400/25',
                        )}
                      >
                        <div
                          className={cn(
                            'mb-1 text-[11px] font-medium uppercase tracking-wide',
                            turn.failed ? 'text-red-200' : mine ? 'text-sky-300' : 'text-amber-200',
                          )}
                        >
                          {turn.failed ? 'error' : mine ? 'You' : selected?.name || 'Agent'}
                        </div>
                        <div className="whitespace-pre-wrap">
                          {turn.content || (turn.role === 'assistant' && sending ? '…' : '')}
                        </div>
                        {turn.failed && (
                          <Button size="sm" variant="outline" className="mt-2" onClick={() => void retryLast()} disabled={sending}>
                            Retry
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })
            )}
            {sending && history.at(-1)?.role === 'assistant' && !history.at(-1)?.content && (
              <p className="mx-auto max-w-2xl text-sm text-accent">Waiting for the agent…</p>
            )}
          </div>

          <div className="mx-auto flex w-full max-w-2xl flex-col gap-3 px-4 pb-5 pt-1">
            <form
              className="glass-panel rounded-[28px] p-3"
              onSubmit={(event) => {
                event.preventDefault()
                if (!requireAgent()) return
                void send()
              }}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                if (!requireAgent()) return
                void onFiles(event.dataTransfer.files)
              }}
            >
              {attachments.length > 0 && (
                <ul className="mb-2 flex flex-wrap gap-2 px-1">
                  {attachments.map((item) => (
                    <li
                      key={item.name}
                      className="flex items-center gap-1 rounded-full border border-white/10 bg-black/20 px-2 py-1 text-xs"
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
              <textarea
                ref={composerRef}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onClick={() => {
                  if (!selected) showToast('Create an agent in Design first.')
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    if (!requireAgent()) return
                    void send()
                  }
                }}
                placeholder={selected ? 'How can I help you today?' : 'Create an agent in Design first'}
                disabled={sending}
                rows={3}
                className="w-full resize-none bg-transparent px-3 py-2 text-sm text-ink outline-none placeholder:text-muted"
              />
              <div className="mt-1 flex flex-wrap items-center gap-1.5 px-1">
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
                  variant="ghost"
                  disabled={sending}
                  title="Attach a file or photo"
                  onClick={() => {
                    if (!requireAgent()) return
                    fileRef.current?.click()
                  }}
                >
                  <Paperclip size={14} />
                  File
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={recording ? 'danger' : 'ghost'}
                  disabled={sending}
                  title="Record audio for the agent"
                  onClick={() => {
                    if (!requireAgent()) return
                    void toggleRecord()
                  }}
                >
                  {recording ? <Square size={14} /> : <Mic size={14} />}
                  {recording ? 'Stop audio' : 'Audio'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={autoMode ? 'default' : 'ghost'}
                  disabled={sending}
                  aria-pressed={autoMode}
                  title="Autonomous tool loop. Off keeps one-turn ask."
                  onClick={() => setAutoMode((current) => !current)}
                >
                  Auto
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  className="ml-auto h-9 w-9 rounded-xl p-0"
                  disabled={sending || (!prompt.trim() && attachments.length === 0)}
                  aria-label="Send"
                >
                  <ArrowUp size={16} />
                </Button>
              </div>
            </form>

            <div data-testid="thinking-status" className="min-h-6 px-2 text-center">
              {statusLine ? (
                <p role="status" className="text-sm text-muted">
                  {statusLine}
                </p>
              ) : null}
            </div>
          </div>
        </section>

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
            <WorkspacePane width={layout.rightWidth} onClose={() => updateLayout({ right: false })} />
          </>
        )}
      </div>

      {confirmClear && selected && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4">
          <div className="max-w-md space-y-3 rounded-2xl border border-border bg-surface p-5">
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
