import { useEffect, useState } from 'react'
import { createAgent, listTemplates, type Agent, type Template } from '../lib/api'
import { cn } from '../lib/utils'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'

export const FACE_EMOJIS = ['💬', '🔎', '💻', '😊', '😎', '🤖', '🧠', '🦊', '🐱', '🦉', '🐲', '⭐', '🔥', '🌱', '🎯']

export function CreateAgentForm({
  onCreated,
  submitLabel = 'Create agent',
}: {
  onCreated?: (agent: Agent) => void
  submitLabel?: string
}) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('general')
  const [emoji, setEmoji] = useState('💬')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const rows = await listTemplates()
        if (cancelled) return
        setTemplates(rows)
        setTemplate((current) => {
          if (rows.length > 0 && !rows.some((item) => item.id === current)) {
            setEmoji(rows[0].emoji || '💬')
            return rows[0].id
          }
          return current
        })
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load templates.')
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

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
      onCreated?.(agent)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-red-200">{error}</p>}
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Templates</h2>
        <ul className="mt-2 grid grid-cols-3 gap-2">
          {templates.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => {
                  setTemplate(item.id)
                  setEmoji(item.emoji || '💬')
                }}
                className={cn(
                  'flex w-full flex-col items-center rounded-2xl border px-2 py-3 text-center',
                  template === item.id ? 'border-accent/40 bg-white/5' : 'border-border hover:bg-white/5',
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
      </div>
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
                emoji === face ? 'border-accent bg-white/5' : 'border-border hover:bg-white/5',
              )}
              aria-label={`Face ${face}`}
              aria-pressed={emoji === face}
            >
              {face}
            </button>
          ))}
        </div>
      </div>
      <div>
        <Label htmlFor="design-agent-name">Name (optional)</Label>
        <Input
          id="design-agent-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Name (optional)"
        />
        <p className="mt-1 text-[11px] text-muted">Model and channel live in Settings.</p>
      </div>
      <Button onClick={() => void create()} disabled={creating}>
        {creating ? 'Creating…' : submitLabel}
      </Button>
    </div>
  )
}
