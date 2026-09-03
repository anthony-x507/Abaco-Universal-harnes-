import { useEffect, useState } from 'react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { getHealth, getSettings, updateSettings } from '../lib/api'

export function SettingsPage() {
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [channel, setChannel] = useState('cli')
  const [hasKey, setHasKey] = useState(false)
  const [demo, setDemo] = useState(false)
  const [serverOk, setServerOk] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const [settings, health] = await Promise.all([getSettings(), getHealth()])
        if (cancelled) return
        setBaseUrl(settings.llm_base_url)
        setModel(settings.llm_model)
        setChannel(settings.default_channel)
        setHasKey(Boolean(settings.llm_api_key))
        setDemo(settings.demo)
        setServerOk(health.status === 'ok')
        setError('')
      } catch (err) {
        if (!cancelled) {
          setServerOk(false)
          setError(err instanceof Error ? err.message : 'Could not load settings.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const save = async () => {
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const saved = await updateSettings({
        llm_base_url: baseUrl,
        llm_api_key: apiKey.trim() || undefined,
        llm_model: model,
        default_channel: channel,
      })
      setHasKey(Boolean(saved.llm_api_key))
      setApiKey('')
      setMessage('Settings updated in this server process. They are not written to disk.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-muted">
          These values update the running Universal process. Leave the API key blank to keep the current secret.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-muted">Loading settings…</p>
      ) : (
        <Card className="space-y-4 p-5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">API connection</span>
            <span className={serverOk ? 'text-accent' : 'text-red-300'}>
              {serverOk ? (demo ? 'Connected (demo echo)' : 'Connected') : 'Offline'}
            </span>
          </div>
          <div className="space-y-1">
            <Label htmlFor="base-url">LLM base URL</Label>
            <Input id="base-url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="api-key">API key {hasKey ? '(set)' : '(missing)'}</Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={hasKey ? '••••••••  leave blank to keep' : 'Required for live completions'}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="model">Default model</Label>
            <Input id="model" value={model} onChange={(event) => setModel(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="channel">Default channel for new agents</Label>
            <select
              id="channel"
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
            >
              <option value="cli">cli</option>
              <option value="webhook" disabled>
                webhook (later)
              </option>
            </select>
          </div>
          <Button onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
          {message && <p className="text-sm text-accent">{message}</p>}
          {error && <p className="text-sm text-red-300">{error}</p>}
        </Card>
      )}
    </div>
  )
}
