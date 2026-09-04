import { useEffect, useState } from 'react'
import { FACE_EMOJIS } from './CreateAgentForm'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { ModelPicker, matchPreset } from './ModelPicker'
import { getSettings, updateAgent, type Agent } from '../lib/api'
import { useModels } from '../hooks/useModels'
import { laterChannels, cn } from '../lib/utils'

type EditTab = 'face' | 'settings' | 'instructions'

export function AgentEditDialog({
  agent,
  onClose,
  onSaved,
}: {
  agent: Agent
  onClose: () => void
  onSaved: (agent: Agent) => void
}) {
  const [tab, setTab] = useState<EditTab>('face')
  const [emoji, setEmoji] = useState(agent.emoji || '💬')
  const [name, setName] = useState(agent.name)
  const [channel, setChannel] = useState(agent.channel)
  const [outboundUrl, setOutboundUrl] = useState(agent.outbound_url || '')
  const [instructions, setInstructions] = useState(agent.system_prompt || '')
  const [channels, setChannels] = useState<string[]>([agent.channel || 'cli'])
  const [coming, setComing] = useState<string[]>([])
  const [provider, setProvider] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [hasKey, setHasKey] = useState(Boolean(agent.has_api_key))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const { models } = useModels()

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const settings = await getSettings()
        if (cancelled) return
        setChannels(settings.channels.length > 0 ? settings.channels : [agent.channel || 'cli'])
        setComing(settings.channels_coming)
        setHasKey(Boolean(agent.has_api_key) || Boolean(settings.llm_api_key))
      } catch {
        if (!cancelled) setChannels([agent.channel || 'cli'])
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [agent.channel])

  useEffect(() => {
    if (models.length === 0) return
    setProvider((current) => current || matchPreset(models, agent.model))
  }, [models, agent.model])

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      const next = await updateAgent(agent.id, {
        name: name.trim() || agent.name,
        emoji,
        channel,
        outbound_url: channel === 'webhook' ? outboundUrl.trim() : '',
        system_prompt: instructions,
        provider: provider || undefined,
        llm_api_key: apiKey.trim() || undefined,
      })
      setHasKey(Boolean(next.has_api_key) || hasKey || Boolean(apiKey.trim()))
      setApiKey('')
      onSaved(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this agent.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[90svh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-border bg-surface">
        <header className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-medium">Edit {agent.emoji || '💬'} {agent.name}</h2>
          <p className="mt-1 text-xs text-muted">Face, model, channel, and the instructions for this agent.</p>
        </header>
        <div className="flex gap-1 border-b border-border px-3 pt-2">
          {(
            [
              ['face', 'Face'],
              ['settings', 'Settings'],
              ['instructions', 'Instructions'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={cn(
                'rounded-t-md px-3 py-2 text-xs',
                tab === id ? 'bg-surface-2 text-ink' : 'text-muted hover:text-ink',
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
          {error && <p className="mb-3 text-sm text-red-200">{error}</p>}
          {tab === 'face' && (
            <div>
              <Label>Emoji</Label>
              <div className="mt-2 flex flex-wrap gap-1">
                {FACE_EMOJIS.map((face) => (
                  <button
                    key={face}
                    type="button"
                    onClick={() => setEmoji(face)}
                    className={cn(
                      'flex h-9 w-9 items-center justify-center rounded-md border text-lg',
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
          )}
          {tab === 'settings' && (
            <div className="space-y-3">
              <div>
                <Label htmlFor="edit-agent-name">Name</Label>
                <Input id="edit-agent-name" value={name} onChange={(event) => setName(event.target.value)} />
              </div>
              <div>
                <Label htmlFor="edit-agent-channel">Channel</Label>
                <select
                  id="edit-agent-channel"
                  value={channel}
                  onChange={(event) => setChannel(event.target.value)}
                  className="mt-1 h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
                >
                  {channels.map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                  {laterChannels(channels, coming).map((id) => (
                    <option key={id} value={id} disabled>
                      {id} (later)
                    </option>
                  ))}
                </select>
              </div>
              <ModelPicker
                id="edit-agent-model"
                label="Models"
                value={provider}
                onChange={setProvider}
                models={models}
                currentModel={agent.model}
              />
              <div>
                <Label htmlFor="edit-agent-key">API key</Label>
                <Input
                  id="edit-agent-key"
                  type="password"
                  autoComplete="off"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder={hasKey ? '••••••••  leave blank to keep' : 'Save a key for this agent'}
                />
              </div>
              {channel === 'webhook' && (
                <div>
                  <Label htmlFor="edit-agent-outbound">Outbound URL</Label>
                  <Input
                    id="edit-agent-outbound"
                    value={outboundUrl}
                    onChange={(event) => setOutboundUrl(event.target.value)}
                    placeholder="https://example.com/hooks/universal"
                  />
                </div>
              )}
              <p className="text-[11px] text-muted">
                Save the model and API key on this agent. The secret stays in your user data, not in a ZIP.
              </p>
            </div>
          )}
          {tab === 'instructions' && (
            <div>
              <Label htmlFor="edit-agent-md">system_prompt.md</Label>
              <Textarea
                id="edit-agent-md"
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
                rows={12}
                className="mt-1 font-mono text-xs"
              />
              <p className="mt-1 text-[11px] text-muted">
                This is the markdown the agent reads as its instructions. Same text the ZIP ships as system_prompt.txt.
              </p>
            </div>
          )}
        </div>
        <footer className="flex justify-end gap-2 border-t border-border px-5 py-3">
          <Button size="sm" variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </footer>
      </div>
    </div>
  )
}
