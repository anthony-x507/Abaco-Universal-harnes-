import { ArrowUp, Copy, FileText, Mic, Paperclip, PanelRight, Square, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ModelPicker, matchPreset } from '../components/ModelPicker'
import { WorkspacePane } from '../components/WorkspacePane'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import {
  ApiError,
  askAgentStream,
  friendlyError,
  PROVIDER_ERROR_COPY,
  getAgent,
  getHealth,
  getSettings,
  listAgents,
  listNotifications,
  ackNotification,
  resetAgent,
  startHostRecording,
  stopHostRecording,
  transcribeAudio,
  updateAgent,
  updateSettings,
  type Agent,
  type HistoryTurn,
  type Notice,
} from '../lib/api'
import { blobToWav, getUserMedia, MIC_UNAVAILABLE, speechRecognitionCtor, wordCount } from '../lib/audio'
import { useModels } from '../hooks/useModels'
import { useAskSession } from '../lib/ask-session'
import { cn, usageLabel } from '../lib/utils'
import { DragHandle } from '../components/DragHandle'
import { useLayout } from '../lib/layout-context'
import { SIZE_LIMITS } from '../lib/layout'
import { textToCopy, writeClipboard } from '../lib/clipboard'

type Attachment = {
  name: string
  kind: 'file' | 'audio' | 'image'
  note: string
  mime: string
  data?: string
  body?: string
  transcript?: string
}

const TEXT_FILE =
  /\.(md|txt|json|csv|py|ts|tsx|js|jsx|html|htm|xml|yaml|yml|toml|ini|log|rst|css|env|rtf|docx|pdf)$/i
const COMPOSER_MAX_PX = 252

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
  const composerDockRef = useRef<HTMLDivElement>(null)
  const [dockPad, setDockPad] = useState(168)
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
  const [dropActive, setDropActive] = useState(false)
  const [whisperReady, setWhisperReady] = useState<boolean | null>(null)
  const [transcribing, setTranscribing] = useState(false)
  const [modelPreset, setModelPreset] = useState('')
  const [savingModel, setSavingModel] = useState(false)
  const [composerKey, setComposerKey] = useState('')
  const [hasApiKey, setHasApiKey] = useState(false)
  const [demoMode, setDemoMode] = useState(false)
  const [notices, setNotices] = useState<Notice[]>([])
  const { models } = useModels()
  const fileRef = useRef<HTMLInputElement>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const speechRef = useRef<{ stop: () => void } | null>(null)
  const spokenRef = useRef('')
  const hostRecordRef = useRef(false)
  const selectedIdRef = useRef(selectedId)
  const threadRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    selectedIdRef.current = selectedId
  }, [selectedId])

  const selected = useMemo(
    () => agents.find((agent) => agent.id === selectedId) ?? null,
    [agents, selectedId],
  )

  useEffect(() => {
    if (!selected || models.length === 0) return
    setModelPreset(matchPreset(models, selected.model))
  }, [selected, models])

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
        const [rows, settings] = await Promise.all([refresh(), getSettings().catch(() => null)])
        if (cancelled) return
        if (settings) {
          setDemoMode(Boolean(settings.demo))
        }
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
        setHasApiKey(Boolean(agent.has_api_key))
        setAgents((current) => current.map((row) => (row.id === agent.id ? { ...row, ...agent } : row)))
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

  useEffect(() => {
    let cancelled = false
    void getHealth()
      .then((health) => {
        if (!cancelled) setWhisperReady(health.whisper ?? false)
      })
      .catch(() => {
        if (!cancelled) setWhisperReady(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const rows = await listNotifications()
        if (!cancelled) setNotices(rows)
      } catch {
        if (!cancelled) setNotices([])
      }
    }
    void load()
    const timer = window.setInterval(() => void load(), 4000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const dismissNotice = async (id: string) => {
    try {
      await ackNotification(id)
      setNotices((current) => current.filter((row) => row.id !== id))
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not dismiss the notice.')
    }
  }

  useEffect(() => {
    const box = composerRef.current
    if (!box) return
    box.style.height = 'auto'
    box.style.height = `${Math.min(box.scrollHeight, COMPOSER_MAX_PX)}px`
  }, [prompt])

  useEffect(() => {
    const dock = composerDockRef.current
    if (!dock || typeof ResizeObserver === 'undefined') return
    const apply = () => setDockPad(Math.round(dock.offsetHeight * 0.45))
    apply()
    const observer = new ResizeObserver(apply)
    observer.observe(dock)
    return () => observer.disconnect()
  }, [attachments.length, statusLine, selectedId])

  const copyTurn = async (full: string) => {
    const selection = window.getSelection()?.toString() ?? ''
    const text = textToCopy(full, selection)
    const ok = await writeClipboard(text)
    showToast(ok ? (selection.trim() && text === selection.trim() ? 'Copied selection' : 'Copied message') : 'Could not copy.')
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
              transcript: item.transcript,
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
    if (composerKey.trim()) await saveComposerKey()
    const pending = attachments
    const outbound = text || (pending.length ? '' : '(attachment only)')
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
      const audio = file.type.startsWith('audio/')
      const textLike = file.type.startsWith('text/') || TEXT_FILE.test(file.name)
      next.push({
        name: file.name || `file-${Date.now()}`,
        kind: image ? 'image' : audio ? 'audio' : 'file',
        mime: file.type || 'application/octet-stream',
        data,
        note: image ? `Photo ${file.name}` : audio ? `Audio ${file.name}` : `Attached file ${file.name}`,
        body: textLike && file.size < 2_000_000 ? await file.text() : undefined,
      })
    }
    setAttachments((current) => [...current, ...next])
    if (next.length) showToast(next.length === 1 ? `Attached ${next[0].name}` : `Attached ${next.length} files`)
  }

  const saveComposerKey = async () => {
    const key = composerKey.trim()
    if (!key) return
    try {
      if (selectedId) {
        const next = await updateAgent(selectedId, { llm_api_key: key })
        setAgents((current) => current.map((row) => (row.id === next.id ? { ...row, ...next } : row)))
        setHasApiKey(Boolean(next.has_api_key) || Boolean(key))
      }
      const saved = await updateSettings({ llm_api_key: key })
      setHasApiKey(Boolean(saved.llm_api_key) || Boolean(key))
      setComposerKey('')
      showToast('API key saved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the API key.')
    }
  }

  const changeModel = async (name: string) => {
    if (!selectedId || savingModel) return
    setModelPreset(name)
    setSavingModel(true)
    try {
      const next = await updateAgent(selectedId, { provider: name })
      setAgents((current) => current.map((row) => (row.id === next.id ? { ...row, ...next } : row)))
      if (composerKey.trim()) await saveComposerKey()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change the model.')
    } finally {
      setSavingModel(false)
    }
  }

  const applyHeardAudio = (name: string, data: string, spoken: string) => {
    setAttachments((current) => [
      ...current,
      {
        name,
        kind: 'audio',
        mime: 'audio/wav',
        data,
        note: spoken ? `Audio: ${spoken}` : 'Audio clip',
        transcript: spoken || undefined,
      },
    ])
    if (spoken) {
      setPrompt((current) => (current.trim() ? `${current.trim()} ${spoken}` : spoken))
    }
  }

  const finishHostRecording = async () => {
    setRecording(false)
    setTranscribing(true)
    setStatusLine('Transcribing with local Whisper…')
    try {
      const clip = await stopHostRecording()
      const name = clip.name || `audio-${Date.now()}.wav`
      let transcript = ''
      try {
        const result = await transcribeAudio({ name, mime: clip.mime || 'audio/wav', data: clip.data })
        transcript = result.text.trim()
      } catch (err) {
        const message = friendlyError(err)
        showToast(message)
        setError(message)
      }
      const spoken = transcript || spokenRef.current
      applyHeardAudio(name, clip.data, spoken)
      if (spoken) showToast('Voice captured')
      else setError('No speech was captured. Press Audio, speak, then Stop audio.')
    } catch (err) {
      setError(err instanceof Error ? err.message : MIC_UNAVAILABLE)
    } finally {
      hostRecordRef.current = false
      setTranscribing(false)
      setStatusLine('')
    }
  }

  const beginHostRecording = async () => {
    await startHostRecording()
    hostRecordRef.current = true
    setRecording(true)
    setStatusLine('Listening on this Mac… speak, then press Stop audio')
  }

  const toggleRecord = async () => {
    if (recording) {
      speechRef.current?.stop()
      speechRef.current = null
      if (hostRecordRef.current) {
        await finishHostRecording()
        return
      }
      if (recorderRef.current) {
        recorderRef.current.stop()
        return
      }
      setRecording(false)
      setStatusLine('')
      const spoken = spokenRef.current.trim()
      if (spoken) {
        setPrompt((current) => (current.trim() ? `${current.trim()} ${spoken}` : spoken))
        showToast('Voice captured')
      } else {
        setError('No speech was captured. Press Audio, speak, then Stop audio.')
      }
      return
    }
    spokenRef.current = ''
    try {
      const SpeechAPI = speechRecognitionCtor()
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
      const requestMic = getUserMedia()
      if (!requestMic) {
        try {
          await beginHostRecording()
          return
        } catch (err) {
          if (speechRef.current) {
            setRecording(true)
            setStatusLine('Listening… speak, then press Stop audio')
            return
          }
          setError(err instanceof Error ? err.message : MIC_UNAVAILABLE)
          return
        }
      }
      const stream = await requestMic({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        setRecording(false)
        recorderRef.current = null
        void (async () => {
          setTranscribing(true)
          setStatusLine('Transcribing with local Whisper…')
          try {
            const wav = await blobToWav(blob)
            const data = await fileToBase64(wav)
            const name = `audio-${Date.now()}.wav`
            let transcript = ''
            try {
              const result = await transcribeAudio({ name, mime: 'audio/wav', data })
              transcript = result.text.trim()
            } catch (err) {
              const message = friendlyError(err)
              showToast(message)
              setError(message)
            }
            applyHeardAudio(name, data, transcript || spokenRef.current)
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Could not prepare the recording.')
          } finally {
            setTranscribing(false)
            setStatusLine('')
          }
        })()
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      speechRef.current?.stop()
      speechRef.current = null
      try {
        await beginHostRecording()
        return
      } catch {
        const text = err instanceof Error ? err.message : ''
        setError(
          /mediaDevices|getUserMedia|permission|not allowed|undefined is not an object/i.test(text)
            ? MIC_UNAVAILABLE
            : text || MIC_UNAVAILABLE,
        )
      }
    }
  }

  const emptyThread = !loadingHistory && history.length === 0
  const words = wordCount(prompt)

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
      {notices.map((notice) => (
        <div
          key={notice.id}
          data-testid="mission-notice"
          role="status"
          className="flex items-center justify-between gap-3 border-b border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-100"
        >
          <span>{notice.message}</span>
          <button
            type="button"
            className="text-amber-100 hover:text-white"
            onClick={() => void dismissNotice(notice.id)}
            aria-label="Dismiss notice"
          >
            <X size={14} />
          </button>
        </div>
      ))}

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <section className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-transparent">
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
              emptyThread ? 'flex flex-col items-center justify-end' : 'space-y-3 py-2',
            )}
            style={{ paddingBottom: dockPad }}
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
                            'mb-1 flex items-center justify-between gap-2 text-[11px] font-medium uppercase tracking-wide',
                            turn.failed ? 'text-red-200' : mine ? 'text-sky-300' : 'text-amber-200',
                          )}
                        >
                          <span>{turn.failed ? 'error' : mine ? 'You' : selected?.name || 'Agent'}</span>
                          {turn.content ? (
                            <button
                              type="button"
                              className="rounded-md p-1 text-muted normal-case tracking-normal hover:bg-white/10 hover:text-ink"
                              aria-label="Copy message"
                              title="Copy message, or selected text"
                              onClick={() => void copyTurn(turn.content)}
                            >
                              <Copy size={12} />
                            </button>
                          ) : null}
                        </div>
                        <div className="cursor-text select-text whitespace-pre-wrap">
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

          <div
            ref={composerDockRef}
            data-testid="composer-dock"
            className="composer-dock absolute inset-x-0 bottom-0 z-10 mx-auto flex w-full max-w-2xl flex-col gap-1.5 px-4 pb-3 pt-2"
          >
            <form
              className={cn('glass-composer relative rounded-[22px] p-2', dropActive && 'ring-2 ring-accent/50')}
              onSubmit={(event) => {
                event.preventDefault()
                if (!requireAgent()) return
                void send()
              }}
              onDragEnter={(event) => {
                event.preventDefault()
                setDropActive(true)
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node)) setDropActive(false)
              }}
              onDrop={(event) => {
                event.preventDefault()
                setDropActive(false)
                if (!requireAgent()) return
                void onFiles(event.dataTransfer.files)
              }}
            >
              {dropActive && (
                <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-[22px] bg-accent/10 text-sm text-accent">
                  Drop any document here
                </div>
              )}
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
                disabled={sending || transcribing}
                rows={3}
                className="max-h-[252px] min-h-[4.5rem] w-full resize-y overflow-y-auto bg-transparent px-3 py-1.5 text-sm leading-relaxed text-ink outline-none placeholder:text-muted"
              />
              <div className="px-3 text-[11px] text-muted">
                {words.toLocaleString('en-US')} / 5,000 words
                {words > 5000 ? ' — still sending the full note' : ''}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5 px-1">
                {selected && (
                  <ModelPicker
                    id="chat-model"
                    label="Models"
                    value={modelPreset}
                    onChange={(name) => void changeModel(name)}
                    models={models}
                    currentModel={selected.model}
                    disabled={sending || savingModel}
                    compact
                  />
                )}
                {selected &&
                  !demoMode &&
                  Boolean(models.find((row) => row.name === modelPreset)?.requires_api_key) && (
                    <label className="flex min-w-0 items-center gap-2">
                      <span className="sr-only">API key</span>
                      <input
                        type="password"
                        autoComplete="off"
                        placeholder={selected?.has_api_key || hasApiKey ? 'API key saved' : 'API key'}
                        value={composerKey}
                        disabled={sending}
                        onChange={(event) => setComposerKey(event.target.value)}
                        onBlur={() => void saveComposerKey()}
                        className="h-8 w-36 rounded-full border border-white/10 bg-white/5 px-3 text-xs text-ink outline-none placeholder:text-muted"
                      />
                    </label>
                  )}
                <input
                  ref={fileRef}
                  type="file"
                  multiple
                  accept="*/*"
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
                  title={
                    whisperReady === false
                      ? "Local Whisper is not installed. pip install 'universal[media]'"
                      : 'Record audio — local Whisper transcribes it'
                  }
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
                  disabled={sending || transcribing || (!prompt.trim() && attachments.length === 0)}
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
            <WorkspacePane
              width={layout.rightWidth}
              agentId={selectedId || undefined}
              onClose={() => updateLayout({ right: false })}
            />
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
